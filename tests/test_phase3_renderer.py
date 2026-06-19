"""Phase 3 output & explainability tests — no live API calls."""

from __future__ import annotations

from pathlib import Path

from travel_agent.orchestrator.export import export_run_artifacts, render_trace
from travel_agent.orchestrator.pipeline import run_stub_pipeline
from travel_agent.orchestrator.renderer import render_itinerary
from travel_agent.orchestrator.state import TripState

REQUIRED_SECTIONS = [
    "## Overview",
    "## Day-by-day plan",
    "## Where to stay",
    "## Transport",
    "## Budget",
    "## Preferences & constraints",
    "## Validation",
    "## How this plan was built",
]


def test_render_itinerary_includes_all_sections():
    state = TripState(raw_request="Plan a 5-day trip to Japan")
    state = run_stub_pipeline(state)
    md = render_itinerary(state)

    for section in REQUIRED_SECTIONS:
        assert section in md, f"Missing section: {section}"

    assert "Agent contributions" in md
    assert "Parsed constraints" in md
    assert state.metadata.run_id in md


def test_render_trace_includes_agent_table():
    state = TripState(raw_request="test request")
    state = run_stub_pipeline(state)
    trace = render_trace(state)

    assert "# Run Trace" in trace
    assert "## Agent execution" in trace
    assert "request_parser" in trace
    assert state.raw_request in trace


def test_export_run_artifacts_writes_files(tmp_path: Path):
    state = TripState(raw_request="export test")
    state = run_stub_pipeline(state)

    run_dir = export_run_artifacts(state, outputs_dir=tmp_path)

    assert run_dir.exists()
    assert (run_dir / "itinerary.md").exists()
    assert (run_dir / "trace.md").exists()
    assert (run_dir / "state.json").exists()

    itinerary = (run_dir / "itinerary.md").read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert section in itinerary

    trace = (run_dir / "trace.md").read_text(encoding="utf-8")
    assert state.metadata.run_id in trace


def test_render_handles_partial_state():
    state = TripState(raw_request="incomplete trip")
    md = render_itinerary(state)

    assert "## Overview" in md
    assert "not available" in md.lower()
