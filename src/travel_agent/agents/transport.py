from __future__ import annotations

from travel_agent.agents.base import AgentContext
from travel_agent.agents.utils import dumps_payload, trip_spec_dict
from travel_agent.agents.normalize import sanitize_transport_plan
from travel_agent.llm.groq_client import GroqClient
from travel_agent.orchestrator.state import TransportPlan, TripState
from travel_agent.prompts.loader import load_prompt


class TransportAgent:
    name = "transport"

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client

    def _groq(self) -> GroqClient:
        if self._client is None:
            self._client = GroqClient()
        return self._client

    def run(self, state: TripState, context: AgentContext) -> TripState:
        if state.trip_spec is None:
            raise ValueError("transport requires trip_spec")

        if state.accommodation_options is None:
            state.metadata.warnings.append(
                "transport: accommodation_options missing; planning from trip_spec only (EC-T04)"
            )

        accommodation = (
            state.accommodation_options.model_dump(mode="json")
            if state.accommodation_options
            else None
        )
        data = self._groq().complete(
            system=load_prompt("transport"),
            user=dumps_payload(
                trip_spec=trip_spec_dict(state),
                accommodation_options=accommodation,
            ),
            schema=TransportPlan,
        )
        plan = TransportPlan.model_validate(data)
        removed = len(plan.inter_city_legs)
        plan = sanitize_transport_plan(plan, state.trip_spec.destinations)
        if removed and not plan.inter_city_legs and len(state.trip_spec.destinations) <= 1:
            state.metadata.warnings.append(
                "transport: removed inter-city legs for single-city trip (EC-T01)"
            )
        state.transport_plan = plan
        return state
