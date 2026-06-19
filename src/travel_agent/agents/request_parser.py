from __future__ import annotations

from travel_agent.agents.base import AgentContext
from travel_agent.agents.utils import dumps_payload
from travel_agent.agents.normalize import normalize_trip_spec
from travel_agent.llm.groq_client import GroqClient
from travel_agent.orchestrator.state import TripSpec, TripState
from travel_agent.prompts.loader import load_prompt


class RequestParserAgent:
    name = "request_parser"

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client

    def _groq(self) -> GroqClient:
        if self._client is None:
            self._client = GroqClient()
        return self._client

    def run(self, state: TripState, context: AgentContext) -> TripState:
        data = self._groq().complete(
            system=load_prompt("request_parser"),
            user=dumps_payload(raw_request=state.raw_request),
            schema=TripSpec,
        )
        state.trip_spec = normalize_trip_spec(TripSpec.model_validate(data))
        return state
