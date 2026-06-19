"""Phase 1 agent tests with mocked LLM clients — no API quota used."""

from unittest.mock import MagicMock

import pytest

from travel_agent.agents.accommodation import AccommodationAgent
from travel_agent.agents.base import AgentContext
from travel_agent.agents.budget import BudgetAgent
from travel_agent.agents.destination_research import DestinationResearchAgent
from travel_agent.agents.itinerary_composer import ItineraryComposerAgent
from travel_agent.agents.request_parser import RequestParserAgent
from travel_agent.agents.transport import TransportAgent
from travel_agent.agents.validator import ValidatorAgent
from travel_agent.config import get_settings
from travel_agent.orchestrator.pipeline import AgentBundle, get_agents, run_pipeline
from travel_agent.orchestrator.state import (
    TripSpec,
    TripState,
    ValidationStatus,
)

JAPAN_SPEC = {
    "duration_days": 5,
    "destinations": ["Tokyo", "Kyoto"],
    "country": "Japan",
    "budget_amount": 3000,
    "budget_currency": "USD",
    "preferences": ["food", "temples"],
    "constraints": ["avoid crowds"],
    "travel_style": "mid-range",
    "party_size": 1,
    "assumptions": [],
}

JAPAN_RESEARCH = {
    "cities": [
        {
            "city": "Tokyo",
            "vibe": "bustling",
            "pois": [
                {
                    "name": "Senso-ji",
                    "category": "temple",
                    "best_time": "early morning",
                    "estimated_duration_hours": 2.0,
                    "estimated": True,
                }
            ],
            "crowd_tips": ["Visit temples before 8am"],
        }
    ]
}

JAPAN_ACCOMMODATION = {
    "cities": [
        {
            "city": "Tokyo",
            "neighborhoods": ["Asakusa"],
            "lodging_tiers": [
                {
                    "tier": "mid-range",
                    "example_type": "hotel",
                    "estimated_nightly_min": 80,
                    "estimated_nightly_max": 150,
                    "estimated": True,
                }
            ],
            "notes": "Near transit",
        }
    ]
}

JAPAN_TRANSPORT = {
    "inter_city_legs": [
        {
            "from_location": "Tokyo",
            "to_location": "Kyoto",
            "mode": "shinkansen",
            "estimated_duration": "2h30m",
            "estimated_cost": 120,
            "estimated": True,
            "notes": "",
        }
    ],
    "airport_transfers": [],
    "local_transit": [],
}

JAPAN_BUDGET = {
    "currency": "USD",
    "line_items": [
        {"category": "lodging", "amount": 600, "estimated": True, "notes": ""},
        {"category": "transport", "amount": 400, "estimated": True, "notes": ""},
        {"category": "food", "amount": 500, "estimated": True, "notes": ""},
        {"category": "activities", "amount": 300, "estimated": True, "notes": ""},
        {"category": "buffer", "amount": 200, "estimated": True, "notes": ""},
    ],
    "total_estimated": 2000,
    "budget_ceiling": 3000,
    "over_budget": False,
    "tradeoff_suggestions": [],
}

JAPAN_ITINERARY = {
    "days": [
        {
            "day": i,
            "city": "Tokyo" if i <= 2 else "Kyoto",
            "theme": "food and temples",
            "activities": ["Temple visit", "Food walk"],
            "logistics": "metro",
        }
        for i in range(1, 6)
    ],
    "summary": "5-day Japan trip",
}

JAPAN_VALIDATION = {
    "status": "pass",
    "issues": [],
    "suggestions": [],
    "checks": [
        {"rule": "duration", "passed": True, "detail": "5 days"},
        {"rule": "budget", "passed": True, "detail": "within budget"},
    ],
}


@pytest.fixture
def mock_groq():
    client = MagicMock()
    client.complete.side_effect = [
        JAPAN_SPEC,
        JAPAN_RESEARCH,
        JAPAN_ACCOMMODATION,
        JAPAN_TRANSPORT,
        JAPAN_ITINERARY,
    ]
    return client


@pytest.fixture
def mock_gemini():
    client = MagicMock()
    client.complete.side_effect = [JAPAN_BUDGET, JAPAN_VALIDATION]
    return client


def test_request_parser_parses_japan(mock_groq):
    agent = RequestParserAgent(client=mock_groq)
    state = TripState(
        raw_request="Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget."
    )
    result = agent.run(state, AgentContext())
    assert result.trip_spec.duration_days == 5
    assert "Tokyo" in result.trip_spec.destinations


def test_full_pipeline_with_mocks(mock_groq, mock_gemini, monkeypatch):
    monkeypatch.setenv("GATHER_PARALLEL", "false")
    get_settings.cache_clear()

    groq = mock_groq
    gemini = mock_gemini

    bundle = AgentBundle(
        parser=RequestParserAgent(client=groq),
        research=DestinationResearchAgent(client=groq),
        accommodation=AccommodationAgent(client=groq),
        transport=TransportAgent(client=groq),
        budget=BudgetAgent(client=gemini),
        composer=ItineraryComposerAgent(client=groq),
        validator=ValidatorAgent(client=gemini),
    )

    from travel_agent.config import get_settings as _gs
    from travel_agent.orchestrator.pipeline import run_orchestrated_pipeline

    state = TripState(
        raw_request="Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget."
    )
    result = run_orchestrated_pipeline(state, bundle, settings=_gs())
    assert result.trip_spec is not None
    assert result.validation_report.status == ValidationStatus.PASS
    assert len(result.draft_itinerary.days) == 5
    _gs.cache_clear()


def test_get_agents_count():
    assert len(get_agents()) == 7
