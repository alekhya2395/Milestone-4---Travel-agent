from __future__ import annotations

from travel_agent.agents.base import AgentContext
from travel_agent.agents.utils import dumps_payload, trip_spec_dict
from travel_agent.llm.groq_client import GroqClient
from travel_agent.orchestrator.state import AccommodationOptions, TripState
from travel_agent.prompts.loader import load_prompt


class AccommodationAgent:
    name = "accommodation"

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client

    def _groq(self) -> GroqClient:
        if self._client is None:
            self._client = GroqClient()
        return self._client

    def run(self, state: TripState, context: AgentContext) -> TripState:
        if state.trip_spec is None:
            raise ValueError("accommodation requires trip_spec")

        if state.destination_research is None:
            state.metadata.warnings.append(
                "accommodation: destination_research missing; using trip_spec only (EC-A03)"
            )

        destination_research = (
            state.destination_research.model_dump(mode="json")
            if state.destination_research
            else None
        )
        data = self._groq().complete(
            system=load_prompt("accommodation"),
            user=dumps_payload(
                trip_spec=trip_spec_dict(state),
                destination_research=destination_research,
            ),
            schema=AccommodationOptions,
        )
        state.accommodation_options = AccommodationOptions.model_validate(data)
        return state
