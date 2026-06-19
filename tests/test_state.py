import json
from pathlib import Path

import pytest

from travel_agent.orchestrator.state import (
    AccommodationOptions,
    BudgetBreakdown,
    DestinationResearch,
    DraftItinerary,
    RunMetadata,
    TransportPlan,
    TripSpec,
    TripState,
    ValidationReport,
    ValidationStatus,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_trip_spec_from_fixture():
    data = json.loads((FIXTURES / "sample_japan.json").read_text(encoding="utf-8"))
    spec = TripSpec.model_validate(data["trip_spec"])
    assert spec.duration_days == 5
    assert spec.destinations == ["Tokyo", "Kyoto"]
    assert spec.budget_amount == 3000


def test_validation_report_from_fixture():
    data = json.loads((FIXTURES / "sample_japan.json").read_text(encoding="utf-8"))
    report = ValidationReport.model_validate(data["validation_report"])
    assert report.status == ValidationStatus.PASS
    assert report.checks[0].rule == "duration"


def test_trip_state_round_trip():
    state = TripState(
        raw_request="test",
        trip_spec=TripSpec(duration_days=3, destinations=["Jaipur"]),
        destination_research=DestinationResearch(),
        accommodation_options=AccommodationOptions(),
        transport_plan=TransportPlan(),
        budget_breakdown=BudgetBreakdown(),
        draft_itinerary=DraftItinerary(),
        validation_report=ValidationReport(),
        metadata=RunMetadata(),
    )
    restored = TripState.model_validate(state.model_dump())
    assert restored.raw_request == "test"
    assert restored.trip_spec.destinations == ["Jaipur"]
