"""Deterministic validator rule tests — EC-V04, VR-1 through VR-5."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from travel_agent.agents.base import AgentContext
from travel_agent.agents.validator import ValidatorAgent
from travel_agent.agents.validator_checks import run_deterministic_checks
from travel_agent.orchestrator.state import (
    BudgetBreakdown,
    BudgetLineItem,
    CityResearch,
    DestinationResearch,
    DraftItinerary,
    ItineraryDay,
    TripSpec,
    TripState,
    ValidationStatus,
)


def _japan_state(**overrides) -> TripState:
    state = TripState(
        raw_request="Japan trip",
        trip_spec=TripSpec(
            duration_days=5,
            destinations=["Tokyo", "Kyoto"],
            budget_amount=3000,
            preferences=["food", "temples"],
            constraints=["avoid crowds"],
        ),
        destination_research=DestinationResearch(
            cities=[
                CityResearch(
                    city="Tokyo",
                    vibe="urban",
                    crowd_tips=["Visit temples before 8am"],
                )
            ]
        ),
        budget_breakdown=BudgetBreakdown(
            currency="USD",
            line_items=[
                BudgetLineItem(category="lodging", amount=600, estimated=True),
            ],
            total_estimated=2000,
            budget_ceiling=3000,
            over_budget=False,
        ),
        draft_itinerary=DraftItinerary(
            summary="Food and temples across Japan",
            days=[
                ItineraryDay(
                    day=i,
                    city="Tokyo" if i <= 2 else "Kyoto",
                    theme="food and temples",
                    activities=["Temple visit", "Food walk"],
                    logistics="metro",
                )
                for i in range(1, 6)
            ],
        ),
    )
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


def test_vr1_duration_mismatch_fails():
    state = _japan_state(
        draft_itinerary=DraftItinerary(
            days=[
                ItineraryDay(day=1, city="Tokyo", theme="food", activities=["Eat"])
            ]
        )
    )
    checks, issues, passed = run_deterministic_checks(state)
    assert not passed
    assert any(check.rule == "duration" and not check.passed for check in checks)
    assert any("Duration mismatch" in issue for issue in issues)


def test_vr2_missing_destination_fails():
    state = _japan_state(
        draft_itinerary=DraftItinerary(
            days=[
                ItineraryDay(day=i, city="Tokyo", theme="food", activities=["Eat"])
                for i in range(1, 6)
            ]
        )
    )
    _, issues, passed = run_deterministic_checks(state)
    assert not passed
    assert any("Kyoto" in issue for issue in issues)


def test_vr3_over_budget_fails():
    state = _japan_state(
        budget_breakdown=BudgetBreakdown(
            currency="USD",
            line_items=[],
            total_estimated=3500,
            budget_ceiling=3000,
            over_budget=True,
        )
    )
    _, issues, passed = run_deterministic_checks(state)
    assert not passed
    assert any("exceeds budget" in issue for issue in issues)


def test_vr3_missing_budget_skips_check():
    state = _japan_state(
        trip_spec=TripSpec(
            duration_days=5,
            destinations=["Tokyo", "Kyoto"],
            budget_amount=None,
            preferences=["food"],
            constraints=[],
        ),
        budget_breakdown=BudgetBreakdown(
            currency="USD",
            line_items=[],
            total_estimated=5000,
            over_budget=True,
        ),
    )
    checks, _, passed = run_deterministic_checks(state)
    budget_check = next(check for check in checks if check.rule == "budget")
    assert budget_check.passed
    assert "skipped" in budget_check.detail


def test_vr4_preference_not_reflected_fails():
    state = _japan_state(
        draft_itinerary=DraftItinerary(
            days=[
                ItineraryDay(
                    day=i,
                    city="Tokyo" if i <= 2 else "Kyoto",
                    theme="shopping",
                    activities=["Mall visit"],
                )
                for i in range(1, 6)
            ]
        )
    )
    _, issues, passed = run_deterministic_checks(state)
    assert not passed
    assert any("food" in issue.lower() or "temple" in issue.lower() for issue in issues)


def test_vr5_crowd_constraint_requires_tips():
    state = _japan_state(
        destination_research=DestinationResearch(
            cities=[CityResearch(city="Tokyo", vibe="urban", crowd_tips=[])]
        ),
        draft_itinerary=DraftItinerary(
            days=[
                ItineraryDay(
                    day=i,
                    city="Tokyo" if i <= 2 else "Kyoto",
                    theme="nightlife",
                    activities=["Bar crawl at peak hours"],
                )
                for i in range(1, 6)
            ]
        ),
    )
    _, issues, passed = run_deterministic_checks(state)
    assert not passed
    assert any("crowd" in issue.lower() for issue in issues)


def test_canonical_japan_passes_deterministic_checks():
    _, _, passed = run_deterministic_checks(_japan_state())
    assert passed


def test_validator_merges_llm_pass_with_deterministic_fail():
    client = MagicMock()
    client.complete.return_value = {
        "status": "pass",
        "issues": [],
        "suggestions": [],
        "checks": [{"rule": "duration", "passed": True, "detail": "ok"}],
    }
    agent = ValidatorAgent(client=client)
    state = _japan_state(
        draft_itinerary=DraftItinerary(
            days=[ItineraryDay(day=1, city="Tokyo", theme="food", activities=["Eat"])]
        )
    )
    result = agent.run(state, AgentContext())
    assert result.validation_report.status == ValidationStatus.FAIL
    assert any("Duration mismatch" in issue for issue in result.validation_report.issues)


def test_validator_passes_when_both_layers_pass():
    client = MagicMock()
    client.complete.return_value = {
        "status": "pass",
        "issues": [],
        "suggestions": [],
        "checks": [],
    }
    agent = ValidatorAgent(client=client)
    result = agent.run(_japan_state(), AgentContext())
    assert result.validation_report.status == ValidationStatus.PASS
