from __future__ import annotations

import json
from typing import Any

from travel_agent.orchestrator.state import TripState


def dumps_payload(**kwargs: Any) -> str:
    return json.dumps(kwargs, indent=2, default=str)


def trip_spec_dict(state: TripState) -> dict[str, Any] | None:
    if state.trip_spec is None:
        return None
    return state.trip_spec.model_dump(mode="json")
