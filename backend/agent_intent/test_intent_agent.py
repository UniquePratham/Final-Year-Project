import os
import sys
import pytest
from fastapi.testclient import TestClient

# Adjust path to find backend and modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.agent_intent.main import app
from backend.shared.ai_adapter import AIAdapter

client = TestClient(app)

def test_analyze_intent_success(monkeypatch):
    # Mock AIAdapter.generate to return a valid JSON string
    mock_json = """
    {
      "intent_class": "Security",
      "entities": {
        "ip_address": "192.168.1.100",
        "user": "admin",
        "resource": "firewall"
      },
      "conditions": {
        "threshold": 10,
        "time_window": "10m"
      },
      "raw_prompt": "Detect login failures from 192.168.1.100"
    }
    """
    monkeypatch.setattr(AIAdapter, "generate", lambda *args, **kwargs: mock_json)

    response = client.post(
        "/analyze-intent",
        json={"prompt": "Detect login failures from 192.168.1.100"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent_class"] == "Security"
    assert data["entities"]["ip_address"] == "192.168.1.100"
    assert data["conditions"]["threshold"] == 10

def test_analyze_intent_invalid_json_fallback(monkeypatch):
    # Mock AIAdapter.generate to return non-JSON output
    # The new regex fallback should still produce a valid intent
    monkeypatch.setattr(AIAdapter, "generate", lambda *args, **kwargs: "Internal server error or generic text")

    response = client.post(
        "/analyze-intent",
        json={"prompt": "Some query"}
    )
    # With regex fallback, the agent returns 200 with a default intent
    assert response.status_code == 200
    data = response.json()
    assert data["intent_class"] == "Security"  # default fallback
    assert data["raw_prompt"] == "Some query"


def test_analyze_intent_fallback_detects_class(monkeypatch):
    # Mock returns non-JSON but mentions "Performance"
    monkeypatch.setattr(AIAdapter, "generate", lambda *args, **kwargs: "The intent is Performance related to CPU spikes")

    response = client.post(
        "/analyze-intent",
        json={"prompt": "Check CPU spikes"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent_class"] == "Performance"


def test_analyze_intent_multilingual_translation(monkeypatch):
    calls = []
    def mock_generate(self, prompt, **kwargs):
        calls.append(prompt)
        if "Query to translate" in prompt:
            return "Detect login failures from IP 185.220.101.44"
        return """
        {
          "intent_class": "Security",
          "entities": {"ip_address": "185.220.101.44", "user": null, "resource": null},
          "conditions": {"threshold": 5, "time_window": "5m"},
          "raw_prompt": "Detect login failures from IP 185.220.101.44"
        }
        """

    monkeypatch.setattr(AIAdapter, "generate", mock_generate)

    # Hinglish prompt that starts with a non-English verb, triggering translation
    response = client.post(
        "/analyze-intent",
        json={"prompt": "bruteforce attack detect karo 185.220.101.44 se"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent_class"] == "Security"
    assert len(calls) == 2
    assert "Query to translate" in calls[0]


