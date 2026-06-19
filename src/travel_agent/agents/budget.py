from __future__ import annotations

from travel_agent.agents.base import AgentContext
from travel_agent.agents.utils import dumps_payload, trip_spec_dict
from travel_agent.llm.gemini_client import GeminiClient
from travel_agent.orchestrator.state import BudgetBreakdown, TripState
from travel_agent.prompts.loader import load_prompt


class BudgetAgent:
    name = "budget"

    def __init__(self, client: GeminiClient | None = None) -> None:
        self._client = client

    def _gemini(self) -> GeminiClient:
        if self._client is None:
            self._client = GeminiClient()
        return self._client

    def run(self, state: TripState, context: AgentContext) -> TripState:
        if state.trip_spec is None:
            raise ValueError("budget requires trip_spec")

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
        }
        if context.validation_feedback:
            payload["validation_feedback"] = context.validation_feedback

        data = self._gemini().complete(
            system=load_prompt("budget"),
            user=dumps_payload(**payload),
            schema=BudgetBreakdown,
        )
        breakdown = BudgetBreakdown.model_validate(data)

        gaps: list[str] = []
        if state.destination_research is None:
            gaps.append("destination_research")
        if state.accommodation_options is None:
            gaps.append("accommodation_options")
        if state.transport_plan is None:
            gaps.append("transport_plan")
        if gaps:
            note = f"Budget computed with partial inputs; missing: {', '.join(gaps)} (EC-B06)"
            state.metadata.warnings.append(note)
            if not breakdown.tradeoff_suggestions:
                breakdown.tradeoff_suggestions = [note]
            else:
                breakdown.tradeoff_suggestions = [note, *breakdown.tradeoff_suggestions]

        if state.trip_spec.budget_amount is None and breakdown.budget_ceiling is None:
            note = "No budget ceiling in request; budget check will be skipped (EC-B02)"
            if note not in breakdown.tradeoff_suggestions:
                breakdown.tradeoff_suggestions = [*breakdown.tradeoff_suggestions, note]

        if breakdown.budget_ceiling is None and state.trip_spec.budget_amount is not None:
            breakdown.budget_ceiling = state.trip_spec.budget_amount
        if breakdown.currency == "USD" and state.trip_spec.budget_currency:
            breakdown.currency = state.trip_spec.budget_currency
        if breakdown.budget_ceiling is not None:
            breakdown.over_budget = breakdown.total_estimated > breakdown.budget_ceiling

        state.budget_breakdown = breakdown
        return state
