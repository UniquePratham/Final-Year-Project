import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Adjust Python Path to find backend shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.shared.types import IntentObject, AnalysisResult, FinalReport, MitigationAction
from backend.shared.ai_adapter import AIAdapter
from backend.shared.json_utils import extract_json
from backend.shared.utils import get_logger, get_config

logger = get_logger("ReportAgent")

app = FastAPI(title="Sentinel Forge - Report Agent Service")

class ReportRequest(BaseModel):
    intent: IntentObject
    analysis_result: AnalysisResult
    mitigation_actions: List[MitigationAction] = []
    metrics: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None

SYSTEM_INSTRUCTION = """You are the Report Agent for Sentinel Forge: AI Log Analyzer.
Your task is to compile technical log analysis findings and response mitigation actions into a premium, detailed executive intelligence report.

You will receive:
1. Analysis findings, anomalies, and trend severity.
2. Raw metrics (log count, error levels, target users, log recency).
3. Structured mitigation actions containing commands (like iptables, systemctl restart).

Your summary MUST be highly detailed, structured, and formal. It must include:
- A "Log Recency & Context" section clarifying whether the logs are "recent (real-time stream)" or "historical (past logs archive)".
- A detailed "Threat / Anomaly Analysis" section explaining the findings with exact statistics (such as failure counts, user targeting, top IPs).
- A clean, detailed "Incident Mitigation Playbook" section detailing the exact actions and CLI commands recommended by the Response Agent to resolve the incidents (rendered in markdown code blocks).

IMPORTANT: If severity is HIGH or CRITICAL, the status MUST be "Bad".
IMPORTANT: Never downgrade severity or ignore the generated mitigation commands. Include the raw CLI commands exactly as provided.

Response Schema (Strict JSON):
{
  "status": "Good | Warning | Bad",
  "summary": "Executive summary of findings in detailed Markdown format (incorporate log recency, detailed findings, and the mitigation playbook with commands).",
  "recommendations": "Actionable recommendations in detailed Markdown format.",
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
    elif severity in ("LOW", "INFO"):
        if request.mitigation_actions or request.analysis_result.anomalies:
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
        recency = "unknown"
        if request.metrics:
            m = request.metrics
            recency = m.get("log_recency", "unknown")
            metrics_section = f"""  - Total Sub-log Records: {m.get('total_records', 'N/A')}
  - Filtered Sub-log Records: {m.get('filtered_records', 'N/A')}
  - Error Count: {m.get('error_count', 0)}
  - Warning Count: {m.get('warning_count', 0)}
  - Unique Source IPs: {m.get('unique_ips_count', 0)}
  - Log Recency: {recency}
  - Top Source IPs: {json.dumps(m.get('top_ips', []))}
  - Level Distribution: {json.dumps(m.get('level_distribution', {}))}
  - User Distribution: {json.dumps(m.get('user_distribution', {}))}"""

        # Serialize mitigation actions
        mitigation_section = "  No mitigation actions generated."
        if request.mitigation_actions:
            actions_list = []
            for a in request.mitigation_actions:
                cmd_str = f"Command: `{a.command}`" if a.command else "No command required"
                actions_list.append(f"- [{a.action_type}] on target '{a.target}': {a.description} ({cmd_str})")
            mitigation_section = "\n".join(actions_list)

        prompt = f"""
        User Intent Class: {request.intent.intent_class}
        Original Prompt: {request.intent.raw_prompt}

        Log Recency: {recency}

        Analysis Severity: {request.analysis_result.severity}
        Confidence Score: {request.analysis_result.confidence_score}

        === Raw Metrics ===
{metrics_section}

        === Findings ===
        {json.dumps(request.analysis_result.findings, indent=2)}

        === Anomalies ===
        {json.dumps(request.analysis_result.anomalies, indent=2)}

        === Generated Mitigation Actions & Commands ===
{mitigation_section}

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
        elif severity in ("LOW", "INFO") and llm_status == "Good" and (request.mitigation_actions or request.analysis_result.anomalies):
            json_data["status"] = "Warning"

        # Merge affected_resources
        llm_resources = json_data.get("affected_resources", [])
        merged_resources = list(set(affected_resources + llm_resources))
        json_data["affected_resources"] = merged_resources

        # Attach mitigation actions
        json_data["mitigation_actions"] = [action.dict() for action in request.mitigation_actions]

        # Ensure timestamp field is set
        json_data["generated_at"] = datetime.utcnow().isoformat()

        return FinalReport(**json_data)

    except Exception as e:
        logger.error(f"Error in report generation agent: {e}")
        # Comprehensive rule-based fallback report
        findings_text = "\n".join(f"- {f}" for f in request.analysis_result.findings)
        metrics_text = ""
        recency = "unknown"
        if request.metrics:
            metrics_text = (
                f"\n- Error Count: {request.metrics.get('error_count', 0)}"
                f"\n- Warning Count: {request.metrics.get('warning_count', 0)}"
                f"\n- Unique IPs: {request.metrics.get('unique_ips_count', 0)}"
                f"\n- Log Recency: {request.metrics.get('log_recency', 'unknown')}"
            )
            recency = request.metrics.get('log_recency', 'unknown')

        # Fallback summary with actions
        fallback_summary = (
            f"**Analysis Executive Summary**\n\n"
            f"- Severity: **{request.analysis_result.severity}**\n"
            f"- Trend: {request.analysis_result.trend}\n"
            f"- Confidence: {request.analysis_result.confidence_score}\n"
            f"- Log Recency: **{recency}**\n"
            f"{metrics_text}\n\n"
            f"**Findings:**\n{findings_text}"
        )
        if request.mitigation_actions:
            actions_summary_list = ["\n\n**Mitigation Actions:**"]
            for a in request.mitigation_actions:
                cmd_block = f"\n  ```bash\n  {a.command}\n  ```" if a.command else ""
                actions_summary_list.append(f"- **{a.action_type}** on {a.target}: {a.description}{cmd_block}")
            fallback_summary += "\n".join(actions_summary_list)

        return FinalReport(
            status=status,
            summary=fallback_summary,
            recommendations=(
                "1. Review affected resources and IPs immediately.\n"
                "2. Verify host security settings and firewall policies.\n"
                "3. Consider blocking offending IP addresses.\n"
                "4. Enable enhanced monitoring for targeted accounts."
            ),
            affected_resources=affected_resources,
            mitigation_actions=request.mitigation_actions,
            generated_at=datetime.utcnow()
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
