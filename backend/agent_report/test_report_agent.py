import os
import sys
import pytest
from fastapi.testclient import TestClient

# Adjust path to find backend and modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.agent_report.main import app
from backend.shared.ai_adapter import AIAdapter

client = TestClient(app)

def test_generate_report_success(monkeypatch):
    mock_json = """
    {
      "status": "Bad",
      "summary": "Executive summary: active brute-force detected",
      "recommendations": "1. Block source IP immediately.\\n2. Reset user password.",
      "affected_resources": ["192.168.1.105"]
    }
    """
    monkeypatch.setattr(AIAdapter, "generate", lambda *args, **kwargs: mock_json)
    
    payload = {
        "intent": {
            "intent_class": "Security",
            "entities": {"ip_address": "192.168.1.105"},
            "conditions": {"threshold": 3},
            "raw_prompt": "Detect logins from 192.168.1.105"
        },
        "analysis_result": {
            "anomalies": [
                {"description": "Failed password", "source_ip": "192.168.1.105", "severity": "HIGH"}
            ],
            "trend": "degrading",
            "severity": "HIGH",
            "confidence_score": 0.9,
            "findings": ["Failed password for admin"]
        }
    }
    
    response = client.post("/generate-report", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Bad"
    assert "active brute-force" in data["summary"]
    assert "192.168.1.105" in data["affected_resources"]

def test_generate_report_fallback(monkeypatch):
    # If LLM raises error, it should still return fallback FinalReport
    def mock_fail(*args, **kwargs):
        raise RuntimeError("API timeout")
        
    monkeypatch.setattr(AIAdapter, "generate", mock_fail)
    
    payload = {
        "intent": {
            "intent_class": "Security",
            "entities": {},
            "conditions": {},
            "raw_prompt": "Check logs"
        },
        "analysis_result": {
            "anomalies": [],
            "trend": "stable",
            "severity": "LOW",
            "confidence_score": 1.0,
            "findings": ["No errors found"]
        }
    }
    
    response = client.post("/generate-report", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Good"
    assert "Analysis Executive Summary" in data["summary"]


def test_generate_report_with_mitigation_actions(monkeypatch):
    mock_json = """
    {
      "status": "Bad",
      "summary": "Executive summary: brute force detected. Mitigation action: Block IP 1.1.1.1",
      "recommendations": "Verify IP settings",
      "affected_resources": ["1.1.1.1"]
    }
    """
    monkeypatch.setattr(AIAdapter, "generate", lambda *args, **kwargs: mock_json)
    
    payload = {
        "intent": {
            "intent_class": "Security",
            "entities": {},
            "conditions": {},
            "raw_prompt": "Check logs"
        },
        "analysis_result": {
            "anomalies": [],
            "trend": "stable",
            "severity": "HIGH",
            "confidence_score": 1.0,
            "findings": []
        },
        "mitigation_actions": [
            {
                "action_type": "Block IP",
                "command": "iptables -A INPUT -s 1.1.1.1 -j DROP",
                "description": "Block brute force host",
                "target": "1.1.1.1",
                "status": "PENDING"
            }
        ]
    }
    
    response = client.post("/generate-report", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Bad"
    assert len(data["mitigation_actions"]) == 1
    assert data["mitigation_actions"][0]["command"] == "iptables -A INPUT -s 1.1.1.1 -j DROP"

