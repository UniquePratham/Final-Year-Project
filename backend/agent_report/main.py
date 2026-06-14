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
from backend.shared.json_utils import extract_json
from backend.shared.utils import get_logger, get_config

logger = get_logger("ReportAgent")

app = FastAPI(title="Sentinel Forge - Report Agent Service")

class ReportRequest(BaseModel):
    intent: IntentObject
    analysis_result: AnalysisResult
    metrics: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None

SYSTEM_INSTRUCTION = """You are the Report Agent for Sentinel Forge: AI Log Analyzer.
Your task is to compile technical log analysis findings into an executive report.

You will receive analysis findings, anomalies, AND raw metrics (error counts, IP distributions, user distributions).
Use ALL of this data to produce an accurate, evidence-based report.

Classify the overall system health state as:
- "Good": System normal. No anomalies or only minor low-severity indicators.
- "Warning": Non-critical alerts, pattern matches, or moderate-severity metrics.
- "Bad": Security breaches, active brute-force indicators, system crash, or critical errors.

IMPORTANT: If severity is HIGH or CRITICAL, the status MUST be "Bad". Do not contradict the analysis severity.
IMPORTANT: Include specific numbers (error counts, IP addresses, affected users) in the summary.

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

    # Heuristically map severity to state — this acts as a floor for the LLM
    severity = request.analysis_result.severity.upper()
    status = "Good"
    if severity in ("CRITICAL", "HIGH"):
        status = "Bad"
    elif severity == "MEDIUM":
        status = "Warning"

    # Build affected_resources from metrics and anomalies
    affected_resources = []
    for a in request.analysis_result.anomalies:
        src = a.get("source_ip") or a.get("resource")
        if src and src not in affected_resources:
            affected_resources.append(src)

    # Add top offending IPs from metrics
    if request.metrics:
        for ip_entry in request.metrics.get("top_ips", [])[:5]:
            ip = ip_entry[0] if isinstance(ip_entry, (list, tuple)) else ip_entry
            if ip and str(ip) not in affected_resources:
                affected_resources.append(str(ip))

    try:
        adapter = AIAdapter(provider=provider, model=model, api_key=request.api_key, base_url=request.api_base_url)

        # Build metrics section
        metrics_section = "  No metrics available."
        if request.metrics:
            m = request.metrics
            metrics_section = f"""  - Total Log Records: {m.get('total_records', 'N/A')}
  - Filtered Records: {m.get('filtered_records', 'N/A')}
  - Error Count: {m.get('error_count', 0)}
  - Warning Count: {m.get('warning_count', 0)}
  - Unique Source IPs: {m.get('unique_ips_count', 0)}
  - Top Source IPs: {json.dumps(m.get('top_ips', []))}
  - Level Distribution: {json.dumps(m.get('level_distribution', {}))}
  - User Distribution: {json.dumps(m.get('user_distribution', {}))}"""

        prompt = f"""
        User Intent Class: {request.intent.intent_class}
        Original Prompt: {request.intent.raw_prompt}

        Analysis Severity: {request.analysis_result.severity}
        Confidence Score: {request.analysis_result.confidence_score}

        === Raw Metrics ===
{metrics_section}

        === Findings ===
        {json.dumps(request.analysis_result.findings, indent=2)}

        === Anomalies ===
        {json.dumps(request.analysis_result.anomalies, indent=2)}

        Heuristic Calculated Status: {status}
        Pre-Identified Affected Resources: {json.dumps(affected_resources)}
        """

        response_text = adapter.generate(prompt=prompt, system_instruction=SYSTEM_INSTRUCTION, temperature=0.3)

        json_data = extract_json(response_text)

        # Enforce severity-status consistency — LLM must not downgrade
        llm_status = json_data.get("status", status)
        if severity in ("CRITICAL", "HIGH") and llm_status == "Good":
            json_data["status"] = "Bad"
        elif severity == "MEDIUM" and llm_status == "Good":
            json_data["status"] = "Warning"

        # Merge affected_resources
        llm_resources = json_data.get("affected_resources", [])
        merged_resources = list(set(affected_resources + llm_resources))
        json_data["affected_resources"] = merged_resources

        # Ensure timestamp field is set
        json_data["generated_at"] = datetime.utcnow().isoformat()

        return FinalReport(**json_data)

    except Exception as e:
        logger.error(f"Error in report generation agent: {e}")
        # Comprehensive rule-based fallback report
        findings_text = "\n".join(f"- {f}" for f in request.analysis_result.findings)
        metrics_text = ""
        if request.metrics:
            metrics_text = (
                f"\n- Error Count: {request.metrics.get('error_count', 0)}"
                f"\n- Warning Count: {request.metrics.get('warning_count', 0)}"
                f"\n- Unique IPs: {request.metrics.get('unique_ips_count', 0)}"
            )

        return FinalReport(
            status=status,
            summary=(
                f"**Analysis Executive Summary**\n\n"
                f"- Severity: **{request.analysis_result.severity}**\n"
                f"- Trend: {request.analysis_result.trend}\n"
                f"- Confidence: {request.analysis_result.confidence_score}\n"
                f"{metrics_text}\n\n"
                f"**Findings:**\n{findings_text}"
            ),
            recommendations=(
                "1. Review affected resources and IPs immediately.\n"
                "2. Verify host security settings and firewall policies.\n"
                "3. Consider blocking offending IP addresses.\n"
                "4. Enable enhanced monitoring for targeted accounts."
            ),
            affected_resources=affected_resources,
            generated_at=datetime.utcnow()
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
