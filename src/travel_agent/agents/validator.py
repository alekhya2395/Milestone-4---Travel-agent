from __future__ import annotations

from travel_agent.agents.base import AgentContext
from travel_agent.agents.utils import dumps_payload, trip_spec_dict
from travel_agent.agents.validator_checks import merge_validation_reports, run_deterministic_checks
from travel_agent.llm.gemini_client import GeminiClient
from travel_agent.orchestrator.state import TripState, ValidationReport
from travel_agent.prompts.loader import load_prompt


class ValidatorAgent:
    name = "validator"

    def __init__(self, client: GeminiClient | None = None) -> None:
        self._client = client

    def _gemini(self) -> GeminiClient:
        if self._client is None:
            self._client = GeminiClient()
        return self._client

    def run(self, state: TripState, context: AgentContext) -> TripState:
        if state.trip_spec is None or state.draft_itinerary is None:
            raise ValueError("validator requires trip_spec and draft_itinerary")

        det_checks, det_issues, det_pass = run_deterministic_checks(state)

        data = self._gemini().complete(
            system=load_prompt("validator"),
            user=dumps_payload(
                raw_request=state.raw_request,
                trip_spec=trip_spec_dict(state),
                draft_itinerary=state.draft_itinerary.model_dump(mode="json"),
                budget_breakdown=(
                    state.budget_breakdown.model_dump(mode="json")
                    if state.budget_breakdown
                    else None
                ),
            ),
            schema=ValidationReport,
        )
        llm_report = ValidationReport.model_validate(data)

        status, merged_checks, merged_issues, suggestions = merge_validation_reports(
            det_checks, det_issues, det_pass, llm_report
        )
        state.validation_report = ValidationReport(
            status=status,
            issues=merged_issues,
            suggestions=suggestions,
            checks=merged_checks,
        )
        return state
