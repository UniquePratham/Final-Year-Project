import os
import sys
import json
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Adjust Python Path to find backend shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.shared.types import FinalReport, ResponseObject, MitigationAction
from backend.shared.ai_adapter import AIAdapter
from backend.shared.utils import get_logger, get_config

logger = get_logger("ResponseAgent")

app = FastAPI(title="Sentinel Forge - Response Agent Service")

class ResponseRequest(BaseModel):
    final_report: FinalReport
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None

SYSTEM_INSTRUCTION = """You are the Response & Mitigation Agent for Sentinel Forge: AI Log Analyzer.
Your task is to analyze the executive log intelligence report and produce a structured list of actionable mitigation steps.

Available action types:
1. "Block IP" -> Recommend dropping traffic from malicious/offending source IPs (e.g., using iptables, ufw).
2. "Restart Service" -> Recommend restarting crashed/failing services or containers (e.g., docker restart, systemctl restart).
3. "Adjust Firewall" -> Adjust ingress/egress rules for security or compliance.
4. "Send Notification" -> Send admin notifications/webhooks for manual intervention.
5. "Capacity Increase" -> Reallocate resource thresholds (e.g., CPU, Memory) or scale containers.

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

@app.post("/mitigate-incident", response_model=ResponseObject)
async def mitigate_incident(request: ResponseRequest):
    logger.info(f"Generating mitigation response recommendations for status: {request.final_report.status}")
    
    provider = request.provider or get_config("DEFAULT_PROVIDER", "ollama")
    model = request.model or get_config("DEFAULT_MODEL", "llama3")
    
    # Check if report has warning/bad status
    status = request.final_report.status.upper()
    alert_triggered = status in ["WARNING", "BAD"]
    
    if status == "GOOD":
        # System is fine, return no actions
        return ResponseObject(
            mitigation_actions=[],
            alert_triggered=False,
            response_summary="### Incident Response Idle\n\nNo anomalies or threat indicators detected. System operating normally. No response actions required.",
            generated_at=datetime.utcnow()
        )
        
    try:
        adapter = AIAdapter(provider=provider, model=model, api_key=request.api_key, base_url=request.api_base_url)
        
        prompt = f"""
        Final Report Status: {request.final_report.status}
        Executive Summary:
        {request.final_report.summary}
        
        Actionable Recommendations:
        {request.final_report.recommendations}
        
        Affected Resources:
        {json.dumps(request.final_report.affected_resources)}
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
        
        # Validate alert triggered
        json_data["alert_triggered"] = alert_triggered
        json_data["generated_at"] = datetime.utcnow().isoformat()
        
        return ResponseObject(**json_data)
        
    except Exception as e:
        logger.error(f"Error in response mitigation agent: {e}")
        # Standard fallback output
        actions = []
        for resource in request.final_report.affected_resources:
            # If resource is an IP address, block it
            if resource.count(".") == 3 or ":" in resource:
                actions.append(MitigationAction(
                    action_type="Block IP",
                    command=f"iptables -A INPUT -s {resource} -j DROP",
                    description=f"Auto-mitigation: Block offending source IP address {resource} from accessing ports.",
                    target=resource,
                    status="PENDING"
                ))
            else:
                actions.append(MitigationAction(
                    action_type="Restart Service",
                    command=f"systemctl restart {resource}",
                    description=f"Auto-mitigation: Restart suspected service or container: {resource}.",
                    target=resource,
                    status="PENDING"
                ))
                
        if not actions:
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
            response_summary=f"### Fallback Incident Response Recommendations\n\n- Detected anomalies for resources: {', '.join(request.final_report.affected_resources)}.\n- Recommending IP isolation and container restarts.",
            generated_at=datetime.utcnow()
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
