"""Phase 4 golden-shape and fixture tests — no live API calls."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.fixtures import FIX_JP, FIX_SINGLE, FIXTURES
from travel_agent.agents.base import AgentContext
from travel_agent.agents.transport import TransportAgent
from travel_agent.orchestrator.export import export_run_artifacts, render_trace
from travel_agent.orchestrator.pipeline import run_stub_pipeline
from travel_agent.orchestrator.renderer import render_itinerary
from travel_agent.orchestrator.safety import sanitize_for_export
from travel_agent.orchestrator.state import TripSpec, TripState, ValidationStatus


REQUIRED_SECTIONS = [
    "## Overview",
    "## Day-by-day plan",
    "## Where to stay",
    "## Transport",
    "## Budget",
    "## Validation",
    "## How this plan was built",
]


@pytest.mark.parametrize("fixture_id", ["FIX-JP", "FIX-IN", "FIX-NB", "FIX-SINGLE", "FIX-MANY"])
def test_stub_pipeline_renders_all_sections(fixture_id: str):
    request = FIXTURES[fixture_id]
    state = run_stub_pipeline(TripState(raw_request=request))
    md = render_itinerary(state)
    for section in REQUIRED_SECTIONS:
        assert section in md, f"{fixture_id} missing {section}"


def test_fix_single_transport_sanitized():
    client = MagicMock()
    client.complete.return_value = {
        "inter_city_legs": [
            {
                "from_location": "Kyoto",
                "to_location": "Osaka",
                "mode": "train",
                "estimated_duration": "30m",
                "estimated_cost": 20,
                "estimated": True,
                "notes": "",
            }
        ],
        "airport_transfers": [],
        "local_transit": [{"city": "Kyoto", "notes": ["bus"], "pass_suggestions": []}],
    }
    agent = TransportAgent(client=client)
    state = TripState(
        raw_request=FIX_SINGLE,
        trip_spec=TripSpec(duration_days=5, destinations=["Kyoto"], budget_amount=1500),
    )
    result = agent.run(state, AgentContext())
    assert result.transport_plan.inter_city_legs == []
    assert any("EC-T01" in warning for warning in result.metadata.warnings)


def test_trace_redacts_pii_and_secrets():
    state = run_stub_pipeline(
        TripState(raw_request="Trip for alice@example.com call +1-555-123-4567")
    )
    trace = render_trace(state)
    assert "alice@example.com" not in trace
    assert "[REDACTED EMAIL]" in trace
    assert "[REDACTED PHONE]" in trace
    assert "sk-" not in trace.lower() or "[REDACTED KEY]" in trace


def test_sanitize_for_export_redacts_api_key_pattern():
    text = "Error with key sk-proj-abcdefghijklmnopqrstuvwxyz1234567890"
    sanitized = sanitize_for_export(text)
    assert "sk-proj" not in sanitized
    assert "[REDACTED KEY]" in sanitized


def test_stub_cli_prints_markdown_with_export_warning(monkeypatch, capsys):
    """EC-R04: export failure should not block itinerary output."""

    def _fail_export(_state, outputs_dir=None):
        raise OSError("disk full")

    monkeypatch.setattr("travel_agent.main.export_run_artifacts", _fail_export)
    monkeypatch.setattr(sys, "argv", ["plan", "--stub", FIX_JP])

    from travel_agent.main import main

    main()
    captured = capsys.readouterr()
    assert "# Travel Itinerary" in captured.out
    assert "could not write outputs" in captured.err


def test_empty_cli_input_rejected():
    result = subprocess.run(
        [sys.executable, "-m", "travel_agent.main", "--stub"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert result.returncode != 0


def test_failed_validation_still_renders(tmp_path: Path):
    from travel_agent.agents.stubs import ValidatorStub
    from travel_agent.orchestrator.pipeline import AgentBundle, run_orchestrated_pipeline
    from travel_agent.agents.stubs import (
        AccommodationStub,
        BudgetStub,
        DestinationResearchStub,
        ItineraryComposerStub,
        RequestParserStub,
        TransportStub,
    )
    from travel_agent.orchestrator.state import ValidationReport

    class FailValidator(ValidatorStub):
        def run(self, state, context):
            state.validation_report = ValidationReport(status=ValidationStatus.FAIL, issues=["test"])
            return state

    bundle = AgentBundle(
        parser=RequestParserStub(),
        research=DestinationResearchStub(),
        accommodation=AccommodationStub(),
        transport=TransportStub(),
        budget=BudgetStub(),
        composer=ItineraryComposerStub(),
        validator=FailValidator(),
    )
    state = run_orchestrated_pipeline(TripState(raw_request=FIX_JP), bundle)
    md = render_itinerary(state)
    assert "## Validation" in md
    assert "FAIL" in md
    run_dir = export_run_artifacts(state, outputs_dir=tmp_path)
    assert (run_dir / "itinerary.md").exists()
