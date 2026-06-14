import os
import sys
import json
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Adjust Python Path to find backend shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.shared.types import AnalysisResult, ResponseObject, MitigationAction
from backend.shared.ai_adapter import AIAdapter
from backend.shared.json_utils import extract_json
from backend.shared.utils import get_logger, get_config

logger = get_logger("ResponseAgent")

app = FastAPI(title="Sentinel Forge - Response Agent Service")

# IP regex for extracting IPs from free-text
IP_REGEX = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')

class ResponseRequest(BaseModel):
    analysis_result: AnalysisResult
    metrics: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None

SYSTEM_INSTRUCTION = """You are the Response & Mitigation Agent for Sentinel Forge: AI Log Analyzer.
Your task is to analyze the log analysis findings and produce a structured list of actionable mitigation steps.

Available action types:
1. "Block IP" -> Recommend dropping traffic from malicious/offending source IPs (e.g., using iptables, ufw).
2. "Restart Service" -> Recommend restarting crashed/failing services or containers (e.g., docker restart, systemctl restart).
3. "Adjust Firewall" -> Adjust ingress/egress rules for security or compliance.
4. "Send Notification" -> Send admin notifications/webhooks for manual intervention.
5. "Capacity Increase" -> Reallocate resource thresholds (e.g., CPU, Memory) or scale containers.

IMPORTANT: If the analysis severity is "HIGH" or "CRITICAL" and offending IPs are identified, you MUST include "Block IP" actions for those IPs.
IMPORTANT: Always include at least one "Send Notification" action for HIGH/CRITICAL/MEDIUM severity.

Response Schema (Strict JSON):
{
  "mitigation_actions": [
    {
      "action_type": "Block IP | Restart Service | Adjust Firewall | Send Notification | Capacity Increase",
      "command": "Actual command line instruction (e.g., 'iptables -A INPUT -s 192.168.1.105 -j DROP' or 'systemctl restart nginx') or null",
      "description": "Short explanation of the mitigation action.",
      "target": "IP address, host, or service name targeted",
      "status": "PENDING"
    }
  ],
  "alert_triggered": true,
  "response_summary": "Summary of incident response recommendations in Markdown format."
}

Output ONLY raw JSON. Do not include markdown fences, comments, or extra text.
"""

def extract_ips_from_text(text: str) -> List[str]:
    """Extract unique IP addresses from free-text."""
    return list(set(IP_REGEX.findall(text)))


@app.post("/mitigate-incident", response_model=ResponseObject)
async def mitigate_incident(request: ResponseRequest):
    logger.info(f"Generating mitigation response recommendations for severity: {request.analysis_result.severity}")

    provider = request.provider or get_config("DEFAULT_PROVIDER", "ollama")
    model = request.model or get_config("DEFAULT_MODEL", "llama3")

    # Check if severity requires alert
    severity = request.analysis_result.severity.upper()
    alert_triggered = severity in ["WARNING", "MEDIUM", "HIGH", "CRITICAL"]

    # Gather affected resources from anomalies
    affected_resources = []
    for a in request.analysis_result.anomalies:
        src = a.get("source_ip") or a.get("resource")
        if src and src not in affected_resources:
            affected_resources.append(src)

    if severity == "LOW" and not affected_resources:
        return ResponseObject(
            mitigation_actions=[],
            alert_triggered=False,
            response_summary="### Incident Response Idle\n\nNo anomalies or threat indicators detected. System operating normally. No response actions required.",
            generated_at=datetime.utcnow()
        )

    # Collect all known IPs from findings, anomalies, and metrics
    all_ips = set()
    for anomaly in request.analysis_result.anomalies:
        ip = anomaly.get("source_ip")
        if ip and ip.count(".") == 3:
            all_ips.add(ip)

    for finding in request.analysis_result.findings:
        all_ips.update(extract_ips_from_text(finding))

    # Add top offending IPs from metrics
    if request.metrics:
        for ip_entry in request.metrics.get("top_ips", [])[:5]:
            ip = ip_entry[0] if isinstance(ip_entry, (list, tuple)) else ip_entry
            if ip and str(ip).count(".") == 3:
                all_ips.add(str(ip))

    try:
        adapter = AIAdapter(provider=provider, model=model, api_key=request.api_key, base_url=request.api_base_url)

        # Build metrics section for context
        metrics_section = ""
        if request.metrics:
            m = request.metrics
            metrics_section = f"""
        === Raw Metrics ===
        - Error Count: {m.get('error_count', 0)}
        - Top Offending IPs: {json.dumps(m.get('top_ips', [])[:5])}
        - User Distribution: {json.dumps(m.get('user_distribution', {}))}"""

        prompt = f"""
        Analysis Severity: {request.analysis_result.severity}
        Trend: {request.analysis_result.trend}
        Confidence Score: {request.analysis_result.confidence_score}

        Findings:
        {json.dumps(request.analysis_result.findings, indent=2)}

        Anomalies:
        {json.dumps(request.analysis_result.anomalies, indent=2)}

        Known Offending IPs (from analysis): {json.dumps(list(all_ips))}
{metrics_section}
        """

        response_text = adapter.generate(prompt=prompt, system_instruction=SYSTEM_INSTRUCTION, temperature=0.3)

        json_data = extract_json(response_text)

        # Validate alert triggered
        json_data["alert_triggered"] = alert_triggered
        json_data["generated_at"] = datetime.utcnow().isoformat()

        # Ensure Block IP actions exist for known offending IPs
        existing_targets = set()
        for action in json_data.get("mitigation_actions", []):
            if action.get("action_type") == "Block IP":
                existing_targets.add(action.get("target"))

        for ip in all_ips:
            if ip not in existing_targets:
                json_data.setdefault("mitigation_actions", []).append({
                    "action_type": "Block IP",
                    "command": f"iptables -A INPUT -s {ip} -j DROP",
                    "description": f"Block offending source IP {ip} identified in analysis.",
                    "target": ip,
                    "status": "PENDING"
                })

        return ResponseObject(**json_data)

    except Exception as e:
        logger.error(f"Error in response mitigation agent: {e}")
        # Comprehensive fallback
        actions = []

        # Block all known offending IPs
        for ip in all_ips:
            actions.append(MitigationAction(
                action_type="Block IP",
                command=f"iptables -A INPUT -s {ip} -j DROP",
                description=f"Auto-mitigation: Block offending source IP address {ip}.",
                target=ip,
                status="PENDING"
            ))

        # Restart affected services
        for resource in affected_resources:
            if resource.count(".") != 3 and ":" not in resource:
                actions.append(MitigationAction(
                    action_type="Restart Service",
                    command=f"systemctl restart {resource}",
                    description=f"Auto-mitigation: Restart suspected service: {resource}.",
                    target=resource,
                    status="PENDING"
                ))

        # Always send notification
        actions.append(MitigationAction(
            action_type="Send Notification",
            command=None,
            description="Auto-mitigation: Notify system administrators for forensic audit.",
            target="SecOps Admin Team",
            status="PENDING"
        ))

        return ResponseObject(
            mitigation_actions=actions,
            alert_triggered=alert_triggered,
            response_summary=(
                f"### Fallback Incident Response\n\n"
                f"- Detected {len(all_ips)} offending IP(s): {', '.join(all_ips) if all_ips else 'none identified'}\n"
                f"- Affected resources: {', '.join(affected_resources) or 'none'}\n"
                f"- Recommending IP isolation, service restarts, and admin notification."
            ),
            generated_at=datetime.utcnow()
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
