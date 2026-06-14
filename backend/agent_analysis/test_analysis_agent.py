import os
import sys
import pytest
from fastapi.testclient import TestClient

# Adjust path to find backend and modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.agent_analysis.main import app
from backend.shared.ai_adapter import AIAdapter

client = TestClient(app)

def test_analyze_metrics_empty_logs():
    payload = {
        "intent": {
            "intent_class": "Security",
            "entities": {},
            "conditions": {},
            "raw_prompt": "Check logs"
        },
        "logs": [],
        "metrics": {
            "total_records": 0,
            "filtered_records": 0
        }
    }
    response = client.post("/analyze-metrics", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["anomalies"]) == 0
    assert data["severity"] == "LOW"
    assert "No relevant log entries" in data["findings"][0]

def test_analyze_metrics_success_with_mock(monkeypatch):
    mock_json = """
    {
      "anomalies": [
        {
          "description": "Brute force attempt detected",
          "timestamp": "2026-06-12T15:45:20Z",
          "source_ip": "192.168.1.105",
          "severity": "HIGH"
        }
      ],
      "trend": "degrading",
      "severity": "HIGH",
      "confidence_score": 0.9,
      "findings": [
        "Multiple failed login attempts observed on host"
      ]
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
        "logs": [
            {"timestamp": "2026-06-12T15:45:20Z", "level": "ERROR", "message": "Failed login", "source_ip": "192.168.1.105", "raw": "..."}
        ],
        "metrics": {
            "total_records": 1,
            "filtered_records": 1,
            "error_count": 3,
            "warning_count": 0,
            "top_ips": [["192.168.1.105", 3]],
            "level_distribution": {"ERROR": 3},
            "user_distribution": {}
        }
    }

    response = client.post("/analyze-metrics", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Rule engine escalates to CRITICAL (IP 192.168.1.105 has 3 hits ≥ threshold=3)
    assert data["severity"] in ("HIGH", "CRITICAL")
    assert data["trend"] == "degrading"
    # Rule-based findings should be present
    assert any("authentication failures" in f.lower() or "brute" in f.lower() or "attack" in f.lower() for f in data["findings"])


def test_ddos_heuristics_rule_engine():
    payload = {
        "intent": {
            "intent_class": "Security",
            "entities": {"resource": "ddos"},
            "conditions": {"threshold": 3},
            "raw_prompt": "Check DDoS traffic"
        },
        "logs": [
            {"timestamp": "2026-06-12T15:45:20Z", "level": "INFO", "message": "GET / HTTP/1.1", "source_ip": "192.168.1.1", "raw": "..."},
            {"timestamp": "2026-06-12T15:45:21Z", "level": "INFO", "message": "GET / HTTP/1.1", "source_ip": "192.168.1.2", "raw": "..."},
            {"timestamp": "2026-06-12T15:45:22Z", "level": "INFO", "message": "GET / HTTP/1.1", "source_ip": "192.168.1.3", "raw": "..."},
        ],
        "metrics": {
            "total_records": 12,
            "filtered_records": 12,
            "error_count": 0,
            "warning_count": 0,
            "top_ips": [
                ["192.168.1.1", 4],
                ["192.168.1.2", 4],
                ["192.168.1.3", 4]
            ],
            "level_distribution": {"INFO": 12},
            "user_distribution": {}
        }
    }

    response = client.post("/analyze-metrics", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["severity"] == "CRITICAL"
    assert data["confidence_score"] == 0.98
    assert any("DDoS" in f for f in data["findings"])
    assert len(data["anomalies"]) == 3

