import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.shared.json_utils import extract_json


def test_extract_raw_json():
    text = '{"intent_class": "Security", "entities": {}}'
    result = extract_json(text)
    assert result["intent_class"] == "Security"


def test_extract_fenced_json():
    text = '```json\n{"status": "Bad", "summary": "test"}\n```'
    result = extract_json(text)
    assert result["status"] == "Bad"


def test_extract_fenced_no_lang():
    text = '```\n{"status": "Good"}\n```'
    result = extract_json(text)
    assert result["status"] == "Good"


def test_extract_json_with_leading_text():
    text = 'Here is the analysis:\n{"severity": "HIGH", "confidence_score": 0.9}'
    result = extract_json(text)
    assert result["severity"] == "HIGH"


def test_extract_json_with_trailing_text():
    text = '{"trend": "degrading"}\n\nLet me know if you need more info.'
    result = extract_json(text)
    assert result["trend"] == "degrading"


def test_extract_empty_raises():
    with pytest.raises(ValueError):
        extract_json("")


def test_extract_garbage_raises():
    with pytest.raises(ValueError):
        extract_json("This is just plain text with no JSON at all")


def test_extract_nested_json():
    text = '{"anomalies": [{"description": "test", "severity": "HIGH"}], "trend": "stable"}'
    result = extract_json(text)
    assert len(result["anomalies"]) == 1
    assert result["anomalies"][0]["severity"] == "HIGH"
