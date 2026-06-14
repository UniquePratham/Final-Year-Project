import os
import sys
import json
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Adjust Python Path to find backend shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.shared.types import IntentObject
from backend.shared.ai_adapter import AIAdapter
from backend.shared.json_utils import extract_json
from backend.shared.utils import get_logger, get_config

logger = get_logger("IntentAgent")

app = FastAPI(title="Sentinel Forge - Intent Agent Service")

class IntentRequest(BaseModel):
    prompt: str
    context: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None

SYSTEM_INSTRUCTION = """You are the Intent Agent for Sentinel Forge: AI Log Analyzer.
Your task is to transform natural-language user prompts (which can be in any language) into structured machine-readable JSON objects matching the Intent schema.

Predefined Intent Classes:
1. "Security" -> brute-force, intrusion, unauthorized access, malware.
2. "Performance" -> latency, resource spikes (CPU/RAM), slow queries, bandwidth.
3. "Availability" -> downtime, service crashes, network drops, connection failures.
4. "Compliance" -> audit requirements, access control violations, security policies.
5. "Usage Analytics" -> active users, request count, traffic volume, usage patterns.

Response Schema (MUST be strict JSON):
{
  "intent_class": "Security | Performance | Availability | Compliance | Usage Analytics",
  "entities": {
    "ip_address": "string or null",
    "user": "string or null",
    "resource": "string or null"
  },
  "conditions": {
    "threshold": int or null,
    "time_window": "string or null"
  },
  "raw_prompt": "string"
}

Respond ONLY with the raw JSON. Do not include markdown code fences (```json), explanation, or other text.
"""

FEW_SHOT_EXAMPLES = """
Example 1:
Prompt: "Search for brute force attacks on our login server"
Result:
{
  "intent_class": "Security",
  "entities": {
    "ip_address": null,
    "user": null,
    "resource": "login server"
  },
  "conditions": {
    "threshold": 5,
    "time_window": "5m"
  },
  "raw_prompt": "Search for brute force attacks on our login server"
}

Example 2:
Prompt: "Vérifier si le serveur de base de données a été arrêté hier"
Result:
{
  "intent_class": "Availability",
  "entities": {
    "ip_address": null,
    "user": null,
    "resource": "database server"
  },
  "conditions": {
    "threshold": null,
    "time_window": "24h"
  },
  "raw_prompt": "Vérifier si le serveur de base de données a été arrêté hier"
}
"""

@app.post("/analyze-intent", response_model=IntentObject)
async def analyze_intent(request: IntentRequest):
    logger.info(f"Received intent analysis request: '{request.prompt}'")
    
    # Read default provider and model from environment if not specified
    provider = request.provider or get_config("DEFAULT_PROVIDER", "ollama")
    model = request.model or get_config("DEFAULT_MODEL", "llama3")
    
    try:
        adapter = AIAdapter(provider=provider, model=model, api_key=request.api_key, base_url=request.api_base_url)
        
        # Multilingual & Hinglish Support: Detect if prompt needs translation to English
        is_english = True
        if any(ord(char) > 127 for char in request.prompt):
            is_english = False
        else:
            common_eng_starts = ("detect", "check", "find", "search", "show", "analyze", "audit", "get", "list", "query", "is", "are", "what", "how", "who", "where", "when", "why")
            words = request.prompt.lower().split()
            if words and not words[0].startswith(common_eng_starts):
                is_english = False

        translated_prompt = request.prompt
        if not is_english:
            try:
                translation_system = "You are a translation assistant. Translate the user's input query into clear, concise English for a security log analysis tool. Output ONLY the English translation. Do not explain, do not add introductory text, do not put it in quotes."
                res = adapter.generate(
                    prompt=f"Query to translate: {request.prompt}",
                    system_instruction=translation_system,
                    temperature=0.1
                )
                if res and res.strip():
                    translated_prompt = res.strip().strip('"').strip("'").strip()
                    logger.info(f"Translated query: '{request.prompt}' -> '{translated_prompt}'")
            except Exception as e:
                logger.warning(f"Translation failed: {e}. Falling back to original prompt.")

        full_prompt = f"{FEW_SHOT_EXAMPLES}\n\nPrompt: \"{translated_prompt}\"\nContext: {request.context or 'None'}\nResult:"
        
        response_text = adapter.generate(prompt=full_prompt, system_instruction=SYSTEM_INSTRUCTION, temperature=0.1)
        
        json_data = extract_json(response_text)
        
        # Ensure raw_prompt matches
        json_data["raw_prompt"] = request.prompt
        
        return IntentObject(**json_data)
        
    except ValueError as ve:
        # extract_json failed — try regex fallback to salvage intent_class
        logger.warning(f"JSON extraction failed, attempting regex fallback: {ve}")
        import re
        intent_classes = ["Security", "Performance", "Availability", "Compliance", "Usage Analytics"]
        detected_class = "Security"  # safe default
        for ic in intent_classes:
            if ic.lower() in response_text.lower():
                detected_class = ic
                break
        return IntentObject(
            intent_class=detected_class,
            entities={"ip_address": None, "user": None, "resource": None},
            conditions={"threshold": 5, "time_window": None},
            raw_prompt=request.prompt
        )
    except Exception as e:
        logger.error(f"Error in intent analysis agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
