"""Request parser unit tests — EC-P01, EC-P06, EC-B05."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from travel_agent.agents.base import AgentContext
from travel_agent.agents.normalize import normalize_trip_spec, sanitize_transport_plan
from travel_agent.agents.request_parser import RequestParserAgent
from travel_agent.orchestrator.state import TransportLeg, TransportPlan, TripSpec, TripState


def test_normalize_missing_budget_adds_assumption():
    spec = TripSpec(duration_days=3, destinations=["Barcelona"], budget_amount=None)
    normalized = normalize_trip_spec(spec)
    assert normalized.budget_amount is None
    assert any("No budget specified" in assumption for assumption in normalized.assumptions)


def test_normalize_zero_budget_treated_as_unspecified():
    spec = TripSpec(duration_days=3, destinations=["Tokyo"], budget_amount=0)
    normalized = normalize_trip_spec(spec)
    assert normalized.budget_amount is None
    assert any("Invalid budget" in assumption for assumption in normalized.assumptions)


def test_normalize_negative_budget_treated_as_unspecified():
    spec = TripSpec(duration_days=3, destinations=["Tokyo"], budget_amount=-100)
    normalized = normalize_trip_spec(spec)
    assert normalized.budget_amount is None


def test_sanitize_single_city_removes_inter_city_legs():
    plan = TransportPlan(
        inter_city_legs=[
            TransportLeg(
                from_location="Tokyo",
                to_location="Kyoto",
                mode="train",
                estimated_duration="2h",
                estimated_cost=100,
                estimated=True,
            )
        ]
    )
    sanitized = sanitize_transport_plan(plan, ["Kyoto"])
    assert sanitized.inter_city_legs == []


def test_sanitize_multi_city_keeps_inter_city_legs():
    plan = TransportPlan(
        inter_city_legs=[
            TransportLeg(
                from_location="Tokyo",
                to_location="Kyoto",
                mode="train",
                estimated_duration="2h",
                estimated_cost=100,
                estimated=True,
            )
        ]
    )
    sanitized = sanitize_transport_plan(plan, ["Tokyo", "Kyoto"])
    assert len(sanitized.inter_city_legs) == 1


def test_parser_applies_normalization(mock_groq_missing_budget):
    agent = RequestParserAgent(client=mock_groq_missing_budget)
    state = TripState(raw_request="Weekend in Barcelona. Love architecture.")
    result = agent.run(state, AgentContext())
    assert result.trip_spec.budget_amount is None
    assert any("No budget specified" in a for a in result.trip_spec.assumptions)


def test_parser_parses_inr_currency(mock_groq_inr):
    agent = RequestParserAgent(client=mock_groq_inr)
    state = TripState(
        raw_request="Plan a 4-day trip to Rajasthan. Jaipur + Udaipur. ₹60,000 budget."
    )
    result = agent.run(state, AgentContext())
    assert result.trip_spec.budget_currency == "INR"
    assert result.trip_spec.budget_amount == 60000


@pytest.fixture
def mock_groq_missing_budget():
    client = MagicMock()
    client.complete.return_value = {
        "duration_days": 2,
        "destinations": ["Barcelona"],
        "budget_amount": None,
        "budget_currency": "USD",
        "preferences": ["architecture"],
        "constraints": [],
        "assumptions": [],
    }
    return client


@pytest.fixture
def mock_groq_inr():
    client = MagicMock()
    client.complete.return_value = {
        "duration_days": 4,
        "destinations": ["Jaipur", "Udaipur"],
        "country": "India",
        "budget_amount": 60000,
        "budget_currency": "INR",
        "preferences": ["forts", "street food"],
        "constraints": ["avoid crowds"],
        "assumptions": [],
    }
    return client
