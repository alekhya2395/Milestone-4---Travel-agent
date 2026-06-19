"""LLM JSON parsing edge cases — EC-L01, EC-L02."""

from __future__ import annotations

import json

import pytest

from travel_agent.llm.base import parse_json_response, repair_truncated_json, strip_markdown_fences


def test_strip_markdown_fences():
    raw = '```json\n{"status": "ok"}\n```'
    assert strip_markdown_fences(raw) == '{"status": "ok"}'


def test_parse_json_with_fences():
    raw = '```json\n{"days": 5, "city": "Tokyo"}\n```'
    data = parse_json_response(raw)
    assert data["days"] == 5


def test_repair_truncated_json_object():
    truncated = '{"duration_days": 5, "destinations": ["Tokyo"'
    repaired = repair_truncated_json(truncated)
    data = json.loads(repaired)
    assert data["duration_days"] == 5
    assert data["destinations"] == ["Tokyo"]


def test_parse_truncated_json_via_repair():
    truncated = '{"budget_amount": 3000, "line_items": [{"category": "food", "amount": 100'
    data = parse_json_response(truncated)
    assert data["budget_amount"] == 3000
    assert data["line_items"][0]["category"] == "food"


def test_invalid_json_still_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_json_response("not json at all")
