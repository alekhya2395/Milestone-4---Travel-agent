from __future__ import annotations

from travel_agent.agents.base import AgentContext
from travel_agent.agents.utils import dumps_payload, trip_spec_dict
from travel_agent.llm.groq_client import GroqClient
from travel_agent.orchestrator.state import DestinationResearch, TripState
from travel_agent.prompts.loader import load_prompt


class DestinationResearchAgent:
    name = "destination_research"

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client

    def _groq(self) -> GroqClient:
        if self._client is None:
            self._client = GroqClient()
        return self._client

    def run(self, state: TripState, context: AgentContext) -> TripState:
        if state.trip_spec is None:
            raise ValueError("destination_research requires trip_spec")

        data = self._groq().complete(
            system=load_prompt("destination_research"),
            user=dumps_payload(trip_spec=trip_spec_dict(state)),
            schema=DestinationResearch,
        )
        state.destination_research = DestinationResearch.model_validate(data)
        return state
