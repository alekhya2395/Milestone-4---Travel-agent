from __future__ import annotations

from travel_agent.agents.base import AgentContext
from travel_agent.agents.utils import dumps_payload, trip_spec_dict
from travel_agent.llm.groq_client import GroqClient
from travel_agent.orchestrator.state import DraftItinerary, TripState
from travel_agent.prompts.loader import load_prompt


class ItineraryComposerAgent:
    name = "itinerary_composer"

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client

    def _groq(self) -> GroqClient:
        if self._client is None:
            self._client = GroqClient()
        return self._client

    def run(self, state: TripState, context: AgentContext) -> TripState:
        if state.trip_spec is None:
            raise ValueError("itinerary_composer requires trip_spec")

        payload: dict = {
            "trip_spec": trip_spec_dict(state),
            "destination_research": (
                state.destination_research.model_dump(mode="json")
                if state.destination_research
                else None
            ),
            "accommodation_options": (
                state.accommodation_options.model_dump(mode="json")
                if state.accommodation_options
                else None
            ),
            "transport_plan": (
                state.transport_plan.model_dump(mode="json")
                if state.transport_plan
                else None
            ),
            "budget_breakdown": (
                state.budget_breakdown.model_dump(mode="json")
                if state.budget_breakdown
                else None
            ),
        }
        if context.validation_feedback:
            payload["validation_feedback"] = context.validation_feedback

        data = self._groq().complete(
            system=load_prompt("itinerary_composer"),
            user=dumps_payload(**payload),
            schema=DraftItinerary,
        )
        state.draft_itinerary = DraftItinerary.model_validate(data)
        return state
