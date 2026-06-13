import os
import sys
import json
import concurrent.futures
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Adjust Python Path to find backend shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.shared.types import IntentObject, NormalizedLog, AnalysisResult
from backend.shared.ai_adapter import AIAdapter
from backend.shared.utils import get_logger, get_config

logger = get_logger("AnalysisAgent")

app = FastAPI(title="Sentinel Forge - Analysis Agent Service")

class AnalysisRequest(BaseModel):
    intent: IntentObject
    logs: List[NormalizedLog]
    metrics: Dict[str, Any]
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None

SYSTEM_INSTRUCTION = """You are the Analysis Agent for Sentinel Forge: AI Log Analyzer.
Your role is to perform deep log intelligence analysis using pre-computed log metrics, a sample of log records, and the user's intent.

Identify anomalies, security failures, performance bottlenecks, access violations, or availability issues.
Determine the overall severity and confidence score based on the evidence.

Response Schema (Strict JSON):
{
  "anomalies": [
    {
      "description": "string description",
      "timestamp": "string or null",
      "source_ip": "string or null",
      "severity": "LOW | MEDIUM | HIGH | CRITICAL"
    }
  ],
  "trend": "degrading | stable | improving",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "confidence_score": float,
  "findings": [
    "finding 1",
    "finding 2"
  ]
}

Provide ONLY the raw JSON block. Do not include markdown fences, comments, or extra text.
"""

def analyze_batch_with_llm(batch: List[NormalizedLog], intent: IntentObject, metrics: Dict[str, Any], provider: str, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """Helper to analyze a single batch using LLM."""
    adapter = AIAdapter(provider=provider, model=model, api_key=api_key, base_url=base_url)
    
    # Format log batch for LLM context
    log_sample = "\n".join([f"[{l.timestamp}] {l.level} | IP={l.source_ip} | User={l.user} | Service={l.service} | Msg: {l.message}" for l in batch[:10]])
    
    prompt = f"""
    Intent Class: {intent.intent_class}
    User Prompt: {intent.raw_prompt}
    
    Metrics:
    - Total Logs: {metrics.get('total_records', 0)}
    - Error Logs: {metrics.get('error_count', 0)}
    - Warning Logs: {metrics.get('warning_count', 0)}
    
    Log Records Sample:
    {log_sample}
    """
    
    response = adapter.generate(prompt=prompt, system_instruction=SYSTEM_INSTRUCTION)
    cleaned_text = response.strip()
    if cleaned_text.startswith("```"):
        lines = cleaned_text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned_text = "\n".join(lines).strip()
        
    return json.loads(cleaned_text)

@app.post("/analyze-metrics", response_model=AnalysisResult)
async def analyze_metrics(request: AnalysisRequest):
    logger.info(f"Analyzing metrics and logs. Intent Class={request.intent.intent_class}")
    
    provider = request.provider or get_config("DEFAULT_PROVIDER", "ollama")
    model = request.model or get_config("DEFAULT_MODEL", "llama3")
    
    # Check if we have logs to process
    if not request.logs:
        return AnalysisResult(
            anomalies=[],
            trend="stable",
            severity="LOW",
            confidence_score=1.0,
            findings=["No relevant log entries matching the filter criteria were found."]
        )
        
    # Spawning parallel sub-agent execution for large-scale datasets (Batch Processing)
    batch_size = 50
    batches = [request.logs[i:i + batch_size] for i in range(0, len(request.logs), batch_size)]
    
    # Rule-based validation logic (Heuristic pre-check)
    rule_findings = []
    rule_severity = "LOW"
    error_ratio = request.metrics.get("error_count", 0) / max(request.metrics.get("total_records", 1), 1)
    
    if request.intent.intent_class == "Security":
        threshold = request.intent.conditions.get("threshold")
        if threshold is not None:
            try:
                if isinstance(threshold, str) and threshold.lower() in ("null", "none", "undefined", ""):
                    threshold = 5
                else:
                    threshold = int(threshold)
            except (ValueError, TypeError):
                threshold = 5
        else:
            threshold = 5

        if request.metrics.get("error_count", 0) >= threshold:
            rule_findings.append(f"Rule Alert: Brute-force threshold exceeded. {request.metrics.get('error_count')} authentication failures detected.")
            rule_severity = "HIGH"
            
    if error_ratio > 0.5:
        rule_findings.append(f"Rule Alert: High failure rate detected. {error_ratio:.1%} of analyzed logs indicate system errors.")
        rule_severity = "CRITICAL"
        
    try:
        # Run parallel sub-agent analyses on log chunks
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(batches), 4)) as executor:
            future_to_batch = {
                executor.submit(analyze_batch_with_llm, batch, request.intent, request.metrics, provider, model, request.api_key, request.api_base_url): i 
                for i, batch in enumerate(batches[:4]) # Cap at 4 subagents for performance/cost
            }
            for future in concurrent.futures.as_completed(future_to_batch):
                try:
                    data = future.result()
                    results.append(data)
                except Exception as ex:
                    logger.error(f"Sub-agent batch analysis failed: {ex}")
                    
        # Aggregate sub-agent outputs
        if not results:
            # Fallback to rule-based analysis if LLM fails or is unconfigured
            return AnalysisResult(
                anomalies=[],
                trend="stable",
                severity=rule_severity,
                confidence_score=0.7,
                findings=rule_findings if rule_findings else ["Rule-based analysis did not detect any systemic anomalies."]
            )
            
        # Merge results (Lead Analysis Agent behavior)
        all_anomalies = []
        all_findings = list(rule_findings)
        trends = []
        severities = []
        confidence_scores = []
        
        for r in results:
            all_anomalies.extend(r.get("anomalies", []))
            all_findings.extend(r.get("findings", []))
            trends.append(r.get("trend", "stable"))
            severities.append(r.get("severity", "LOW"))
            confidence_scores.append(r.get("confidence_score", 0.5))
            
        # Determine consolidated metrics
        consolidated_trend = max(set(trends), key=trends.count) if trends else "stable"
        
        severity_hierarchy = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        highest_severity = max(severities, key=lambda s: severity_hierarchy.get(s, 1)) if severities else rule_severity
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.8
        
        return AnalysisResult(
            anomalies=all_anomalies,
            trend=consolidated_trend,
            severity=highest_severity,
            confidence_score=round(avg_confidence, 2),
            findings=list(set(all_findings))
        )
        
    except Exception as e:
        logger.error(f"Error in analysis agent: {e}")
        # Graceful fallback to rule-based metrics
        return AnalysisResult(
            anomalies=[],
            trend="stable",
            severity=rule_severity,
            confidence_score=0.6,
            findings=rule_findings if rule_findings else [f"Analysis pipeline error: {e}"]
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
