from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from travel_agent.orchestrator.state import TripState


@dataclass
class AgentContext:
    validation_feedback: list[str] | None = None
    retry_attempt: int = 0
    warnings: list[str] = field(default_factory=list)


class Agent(Protocol):
    name: str

    def run(self, state: TripState, context: AgentContext) -> TripState:
        ...
