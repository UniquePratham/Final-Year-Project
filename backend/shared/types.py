from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class IntentObject(BaseModel):
    intent_class: str = Field(..., description="Intent category: Security, Performance, Availability, Compliance, or Usage Analytics")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Identified entities, e.g., user, ip_address, host, resource")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Extracted conditions, e.g., error_code, threshold, time_window")
    raw_prompt: str = Field(..., description="Original user prompt")

class NormalizedLog(BaseModel):
    timestamp: datetime
    level: str
    source_ip: Optional[str] = None
    user: Optional[str] = None
    service: Optional[str] = None
    message: str
    raw: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AnalysisResult(BaseModel):
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    trend: str = Field(..., description="Trend analysis summary")
    severity: str = Field(..., description="Severity level: LOW, MEDIUM, HIGH, CRITICAL")
    confidence_score: float = Field(..., description="Confidence score between 0.0 and 1.0")
    findings: List[str] = Field(default_factory=list)

class MitigationAction(BaseModel):
    action_type: str = Field(..., description="e.g. Block IP, Restart Service, Adjust Firewall, Send Notification")
    command: Optional[str] = Field(None, description="CLI command or script execution recommendation")
    description: str = Field(..., description="Description of why this action is recommended")
    target: str = Field(..., description="Target entity, e.g. IP address or service name")
    status: str = Field("PENDING", description="Status of mitigation action: PENDING, EXECUTED, FAILED")

class FinalReport(BaseModel):
    status: str = Field(..., description="System health status: Good, Warning, or Bad")
    summary: str = Field(..., description="Summary of the analysis and findings")
    recommendations: str = Field(..., description="Actionable recommendations")
    affected_resources: List[str] = Field(default_factory=list)
    mitigation_actions: List[MitigationAction] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class ResponseObject(BaseModel):
    mitigation_actions: List[MitigationAction] = Field(default_factory=list)
    alert_triggered: bool = Field(False, description="Flag indicating if external alert is triggered")
    response_summary: str = Field(..., description="Summary of response/mitigation recommendations")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

