from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from travel_agent.config import get_settings
from travel_agent.orchestrator.export import export_run_artifacts
from travel_agent.orchestrator.pipeline import run_pipeline, run_stub_pipeline
from travel_agent.orchestrator.renderer import render_itinerary
from travel_agent.orchestrator.safety import validate_api_keys
from travel_agent.orchestrator.state import TripState


def execute_plan(
    request: str,
    *,
    stub: bool = False,
    save: bool = True,
) -> TripState:
    """Run the travel pipeline and optionally persist artifacts."""
    load_dotenv()
    settings = get_settings()

    if not stub:
        validate_api_keys(settings)

    state = TripState(raw_request=request.strip())
    state = run_stub_pipeline(state) if stub else run_pipeline(state)

    if save:
        try:
            export_run_artifacts(state)
        except OSError:
            pass

    return state


def state_to_api_payload(state: TripState) -> dict:
    """Serialize TripState for the web API."""
    data = state.model_dump(mode="json")
    data["markdown"] = render_itinerary(state)
    data["validation_status"] = (
        state.validation_report.status.value if state.validation_report else None
    )
    return data


def static_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "web" / "static"
