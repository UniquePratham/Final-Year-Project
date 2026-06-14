"""Robust JSON extraction from LLM responses.

Handles markdown fences, leading/trailing garbage, and partial JSON recovery.
Used by all agents to replace duplicated fence-stripping logic.
"""
import json
import re
from typing import Dict, Any

# Matches ```json ... ``` or ``` ... ``` blocks
_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)

# Matches the outermost { ... } or [ ... ] in a string
_BRACE_RE = re.compile(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", re.DOTALL)


def extract_json(text: str) -> Dict[str, Any]:
    """Extract and parse the first JSON object from an LLM response.

    Strategy (in order):
    1. Strip markdown code fences and parse the inner content.
    2. Try parsing the raw stripped text directly.
    3. Find the first { ... } block via regex and parse it.
    4. Raise ValueError if all strategies fail.
    """
    if not text or not text.strip():
        raise ValueError("Empty response text")

    cleaned = text.strip()

    # Strategy 1: Extract from markdown fences
    fence_match = _FENCE_RE.search(cleaned)
    if fence_match:
        inner = fence_match.group(1).strip()
        try:
            return json.loads(inner)
        except json.JSONDecodeError:
            pass

    # Strategy 2: Direct parse (response is raw JSON)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Find first { ... } block
    brace_match = _BRACE_RE.search(cleaned)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3b: More aggressive — find first { and last }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM response: {cleaned[:200]}")
