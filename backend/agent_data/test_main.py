import os
import sys
import pytest
from fastapi.testclient import TestClient

# Adjust path to find backend and modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.agent_data.main import app

client = TestClient(app)

def test_process_data_syslog_success():
    intent_payload = {
        "intent_class": "Security",
        "entities": {
            "ip_address": "192.168.1.105",
            "user": None,
            "resource": None
        },
        "conditions": {
            "threshold": 3,
            "time_window": None
        },
        "raw_prompt": "Detect logins from 192.168.1.105"
    }
    
    # 2 syslog lines: one matches IP, one doesn't
    syslog_raw = (
        "Jun 12 15:45:20 myhost sshd[1234]: Failed password for invalid user admin from 192.168.1.105 port 54322\n"
        "Jun 12 15:46:10 myhost sshd[1234]: Accepted publickey for user admin from 192.168.1.10 port 54322\n"
    )
    
    payload = {
        "intent": intent_payload,
        "logs_raw": syslog_raw,
        "log_format": "Syslog"
    }
    
    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Should only return the matching line
    assert len(data["logs_normalized"]) == 1
    assert data["logs_normalized"][0]["source_ip"] == "192.168.1.105"
    assert data["metrics"]["total_records"] == 2
    assert data["metrics"]["filtered_records"] == 1
    assert data["metrics"]["error_count"] == 1

def test_process_data_json_success():
    intent_payload = {
        "intent_class": "Performance",
        "entities": {},
        "conditions": {},
        "raw_prompt": "Detect performance warnings"
    }
    
    json_raw = (
        '{"timestamp": "2026-06-12T15:45:20Z", "level": "WARNING", "message": "High CPU utilization", "service": "api"}\n'
        '{"timestamp": "2026-06-12T15:46:10Z", "level": "INFO", "message": "Service normal", "service": "api"}\n'
    )
    
    payload = {
        "intent": intent_payload,
        "logs_raw": json_raw,
        "log_format": "JSON"
    }
    
    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["logs_normalized"]) == 2
    assert data["metrics"]["warning_count"] == 1
    assert data["metrics"]["total_records"] == 2
