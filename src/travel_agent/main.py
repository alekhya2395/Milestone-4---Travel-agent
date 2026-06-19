from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

from travel_agent.config import get_settings
from travel_agent.orchestrator.safety import validate_api_keys
from travel_agent.llm.preflight import print_quota_preflight
from travel_agent.orchestrator.export import export_run_artifacts
from travel_agent.orchestrator.pipeline import run_pipeline, run_stub_pipeline
from travel_agent.orchestrator.renderer import render_itinerary
from travel_agent.orchestrator.state import TripState


def main() -> None:
    load_dotenv()
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Travel Planning Multi-Agent System")
    parser.add_argument("request", nargs="*", help="Natural-language travel request")
    parser.add_argument(
        "--stub",
        action="store_true",
        help="Run stub pipeline (no LLM calls, saves API quota)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON state instead of markdown itinerary",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Skip writing outputs/{run_id}/ artifacts",
    )
    args = parser.parse_args()

    if not args.request:
        parser.print_usage()
        sys.exit(1)

    request = " ".join(args.request).strip()
    if not request:
        print("Error: travel request cannot be empty.")
        sys.exit(1)

    use_stub = args.stub
    if not use_stub:
        validate_api_keys(settings)
    if settings.rate_limit_enabled and not use_stub:
        print_quota_preflight(settings, file=sys.stderr)

    state = TripState(raw_request=request)
    state = run_stub_pipeline(state) if use_stub else run_pipeline(state)

    if not args.no_save:
        try:
            run_dir = export_run_artifacts(state)
            print(f"Saved to {run_dir}/", file=sys.stderr)
        except OSError as exc:
            print(f"Warning: could not write outputs: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(state.model_dump(mode="json"), indent=2))
    else:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        print(render_itinerary(state))


if __name__ == "__main__":
    main()
