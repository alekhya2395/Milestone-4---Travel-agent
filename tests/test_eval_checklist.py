"""Automated eval checklist assertions — maps to docs/eval.md."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.fixtures import FIX_JP, FIX_LOW, FIX_MANY
from travel_agent.agents.validator_checks import run_deterministic_checks
from travel_agent.orchestrator.export import export_run_artifacts
from travel_agent.orchestrator.pipeline import run_stub_pipeline
from travel_agent.orchestrator.renderer import render_itinerary
from travel_agent.orchestrator.state import TripState, ValidationStatus

FIX_JP_STATE = Path("outputs/8c3ff70a-b7e4-48a1-9065-7a5157707ffb/state.json")
FIX_IN_STATE = Path("outputs/fdbf1948-9079-4f3b-a97a-8dd9e1205e91/state.json")
EVIDENCE_MANIFEST = Path("outputs/evidence_manifest.json")
REQUIRED_SECTIONS = [
    "## Overview",
    "## Day-by-day plan",
    "## Where to stay",
    "## Transport",
    "## Budget",
    "## Validation",
    "## How this plan was built",
]


def test_m1_cli_produces_full_markdown():
    state = run_stub_pipeline(TripState(raw_request=FIX_JP))
    md = render_itinerary(state)
    for section in REQUIRED_SECTIONS:
        assert section in md


@pytest.mark.skipif(not FIX_JP_STATE.exists(), reason="Live FIX-JP evidence not captured")
def test_m2_fix_jp_live_validation_passes():
    data = json.loads(FIX_JP_STATE.read_text(encoding="utf-8"))
    assert data["validation_report"]["status"] == "pass"
    assert data["trip_spec"]["duration_days"] == 5


@pytest.mark.skipif(not FIX_IN_STATE.exists(), reason="Live FIX-IN evidence not captured")
def test_e2e2_fix_in_live_validation_passes():
    data = json.loads(FIX_IN_STATE.read_text(encoding="utf-8"))
    assert data["validation_report"]["status"] == "pass"
    assert data["trip_spec"]["budget_currency"] == "INR"
    assert "Jaipur" in data["trip_spec"]["destinations"]


@pytest.mark.skipif(not EVIDENCE_MANIFEST.exists(), reason="Evidence manifest not captured")
def test_evidence_manifest_complete():
    manifest = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    assert len(manifest["runs"]) >= 2
    for run in manifest["runs"]:
        for path in run["artifacts"].values():
            assert Path(path).exists()
        assert run["validation_status"] == "pass"


@pytest.mark.skipif(not FIX_JP_STATE.exists(), reason="Live FIX-JP evidence not captured")
def test_vr_rules_on_live_fix_jp():
    data = json.loads(FIX_JP_STATE.read_text(encoding="utf-8"))
    state = TripState.model_validate(data)
    checks, _, passed = run_deterministic_checks(state)
    rules = {check.rule for check in checks}
    assert "duration" in rules
    assert "destinations" in rules
    assert "budget" in rules
    assert passed


def test_e2e7_over_budget_reported_not_hidden():
    from travel_agent.orchestrator.state import BudgetBreakdown, DraftItinerary, ItineraryDay, TripSpec

    state = TripState(
        raw_request=FIX_LOW,
        trip_spec=TripSpec(duration_days=3, destinations=["Tokyo"], budget_amount=400),
        budget_breakdown=BudgetBreakdown(
            currency="USD",
            line_items=[],
            total_estimated=800,
            budget_ceiling=400,
            over_budget=True,
        ),
        draft_itinerary=DraftItinerary(
            days=[
                ItineraryDay(day=i, city="Tokyo", theme="food", activities=["Eat"])
                for i in range(1, 4)
            ]
        ),
    )
    _, issues, passed = run_deterministic_checks(state)
    assert not passed
    assert any("exceeds budget" in issue for issue in issues)
    md = render_itinerary(state)
    assert "**Over budget:** Yes" in md


def test_e2e9_trace_reproducibility(tmp_path: Path):
    state = run_stub_pipeline(TripState(raw_request=FIX_MANY))
    run_dir = export_run_artifacts(state, outputs_dir=tmp_path)
    assert (run_dir / "trace.md").exists()
    assert (run_dir / "state.json").exists()
    trace = (run_dir / "trace.md").read_text(encoding="utf-8")
    assert "request_parser" in trace
