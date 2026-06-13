import os
import sys
import json
import pytest
import httpx
from fastapi.testclient import TestClient

# Adjust path to find backend and modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.orchestrator.main import app

# Create FastAPI test client
client = TestClient(app)

class MockAsyncResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("Error", request=None, response=None)

@pytest.fixture
def mock_subservices(monkeypatch):
    async def mock_post(self, url, json, *args, **kwargs):
        if "/analyze-intent" in url:
            return MockAsyncResponse({
                "intent_class": "Security",
                "entities": {},
                "conditions": {"threshold": 3},
                "raw_prompt": json["prompt"]
            })
        elif "/process-data" in url:
            return MockAsyncResponse({
                "logs_normalized": [
                    {"timestamp": "2026-06-12T15:45:20Z", "level": "ERROR", "message": "Failed login", "raw": "..."}
                ],
                "metrics": {"total_records": 1, "filtered_records": 1, "error_count": 1}
            })
        elif "/analyze-metrics" in url:
            return MockAsyncResponse({
                "anomalies": [],
                "trend": "stable",
                "severity": "HIGH",
                "confidence_score": 0.85,
                "findings": ["Failed login detected"]
            })
        elif "/generate-report" in url:
            return MockAsyncResponse({
                "status": "Bad",
                "summary": "Failed login brute force report summary",
                "recommendations": "Verify IP settings",
                "affected_resources": []
            })
        return MockAsyncResponse({}, 404)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

def test_orchestrator_sync_pipeline(mock_subservices):
    payload = {
        "prompt": "Check brute force login attempts",
        "logs_raw": "raw log line",
        "log_format": "Syslog"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "final_report" in data
    assert data["final_report"]["status"] == "Bad"

def test_orchestrator_stream_pipeline(mock_subservices):
    payload = {
        "prompt": "Check brute force login attempts",
        "logs_raw": "raw log line",
        "log_format": "Syslog"
    }
    # Test SSE stream endpoint
    with client.stream("POST", "/analyze/stream", json=payload) as response:
        assert response.status_code == 200
        events = []
        for line in response.iter_lines():
            if line:
                events.append(line)
        # Verify events are generated
        assert any("event: pipeline_started" in e for e in events)
        assert any("event: intent_completed" in e for e in events)
        assert any("event: report_completed" in e for e in events)
        assert any("event: pipeline_completed" in e for e in events)
