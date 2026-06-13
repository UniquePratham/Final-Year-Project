import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Adjust Python Path to find backend shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.shared.types import IntentObject, AnalysisResult, FinalReport
from backend.shared.ai_adapter import AIAdapter
from backend.shared.utils import get_logger, get_config

logger = get_logger("ReportAgent")

app = FastAPI(title="Sentinel Forge - Report Agent Service")

class ReportRequest(BaseModel):
    intent: IntentObject
    analysis_result: AnalysisResult
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None

SYSTEM_INSTRUCTION = """You are the Report Agent for Sentinel Forge: AI Log Analyzer.
Your task is to compile technical log analysis findings into an executive report.

Classify the overall system health state as:
- "Good": System normal. No anomalies or only minor low-severity indicators.
- "Warning": Non-critical alerts, pattern matches, or moderate-severity metrics.
- "Bad": Security breaches, active brute-force indicators, system crash, or critical errors.

Response Schema (Strict JSON):
{
  "status": "Good | Warning | Bad",
  "summary": "Executive summary of findings in Markdown format.",
  "recommendations": "Actionable recommendations in Markdown format.",
  "affected_resources": ["resource1", "resource2"]
}

Output ONLY raw JSON. Do not include markdown fences, comments, or extra text.
"""

@app.post("/generate-report", response_model=FinalReport)
async def generate_report(request: ReportRequest):
    logger.info(f"Generating final log intelligence report. Severity={request.analysis_result.severity}")
    
    provider = request.provider or get_config("DEFAULT_PROVIDER", "ollama")
    model = request.model or get_config("DEFAULT_MODEL", "llama3")
    
    # Heuristically map severity to state
    severity = request.analysis_result.severity.upper()
    status = "Good"
    if severity == "CRITICAL" or severity == "HIGH":
        status = "Bad"
    elif severity == "MEDIUM":
        status = "Warning"
        
    try:
        adapter = AIAdapter(provider=provider, model=model, api_key=request.api_key)
        
        prompt = f"""
        User Intent Class: {request.intent.intent_class}
        Original Prompt: {request.intent.raw_prompt}
        
        Analysis Severity: {request.analysis_result.severity}
        Confidence Score: {request.analysis_result.confidence_score}
        
        Findings:
        {json.dumps(request.analysis_result.findings, indent=2)}
        
        Anomalies:
        {json.dumps(request.analysis_result.anomalies, indent=2)}
        
        Heuristic Calculated Status: {status}
        """
        
        response_text = adapter.generate(prompt=prompt, system_instruction=SYSTEM_INSTRUCTION)
        
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```"):
            lines = cleaned_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned_text = "\n".join(lines).strip()
            
        json_data = json.loads(cleaned_text)
        
        # Ensure timestamp field is set
        json_data["generated_at"] = datetime.utcnow().isoformat()
        
        return FinalReport(**json_data)
        
    except Exception as e:
        logger.error(f"Error in report generation agent: {e}")
        # Standard fallback output
        affected_resources = []
        for a in request.analysis_result.anomalies:
            src = a.get("source_ip") or a.get("resource")
            if src and src not in affected_resources:
                affected_resources.append(src)
                
        return FinalReport(
            status=status,
            summary=f"**Analysis Executive Summary**\n\n- Severity: {request.analysis_result.severity}\n- Trend: {request.analysis_result.trend}\n\nFindings: " + ", ".join(request.analysis_result.findings),
            recommendations="1. Review affected resources immediately.\n2. Verify host security settings and firewall policies.",
            affected_resources=affected_resources,
            generated_at=datetime.utcnow()
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
