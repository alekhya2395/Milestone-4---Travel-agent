from travel_agent.agents.base import AgentContext
from travel_agent.orchestrator.state import (
    AccommodationOptions,
    BudgetBreakdown,
    DestinationResearch,
    DraftItinerary,
    TransportPlan,
    TripSpec,
    TripState,
    ValidationReport,
    ValidationStatus,
)


class RequestParserStub:
    name = "request_parser"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        state.trip_spec = TripSpec(
            duration_days=1,
            destinations=["placeholder"],
            assumptions=["Phase 0 stub"],
        )
        return state


class DestinationResearchStub:
    name = "destination_research"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        cities = state.trip_spec.destinations if state.trip_spec else ["placeholder"]
        from travel_agent.orchestrator.state import CityResearch, DestinationResearch

        state.destination_research = DestinationResearch(
            cities=[CityResearch(city=c, vibe="stub", crowd_tips=[]) for c in cities]
        )
        return state


class AccommodationStub:
    name = "accommodation"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        cities = state.trip_spec.destinations if state.trip_spec else ["placeholder"]
        from travel_agent.orchestrator.state import AccommodationOptions, CityAccommodation

        state.accommodation_options = AccommodationOptions(
            cities=[CityAccommodation(city=c, neighborhoods=["stub"]) for c in cities]
        )
        return state


class TransportStub:
    name = "transport"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        state.transport_plan = TransportPlan()
        return state


class BudgetStub:
    name = "budget"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        state.budget_breakdown = BudgetBreakdown(
            currency=state.trip_spec.budget_currency if state.trip_spec else "USD",
            budget_ceiling=state.trip_spec.budget_amount if state.trip_spec else None,
        )
        return state


class ItineraryComposerStub:
    name = "itinerary_composer"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        from travel_agent.orchestrator.state import DraftItinerary, ItineraryDay

        duration = state.trip_spec.duration_days if state.trip_spec else 1
        city = (
            state.trip_spec.destinations[0]
            if state.trip_spec and state.trip_spec.destinations
            else "placeholder"
        )
        state.draft_itinerary = DraftItinerary(
            days=[
                ItineraryDay(day=d, city=city, theme="stub", activities=["stub"])
                for d in range(1, duration + 1)
            ]
        )
        return state


class ValidatorStub:
    name = "validator"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        from travel_agent.orchestrator.state import ValidationCheck

        state.validation_report = ValidationReport(
            status=ValidationStatus.PASS,
            checks=[ValidationCheck(rule="stub", passed=True, detail="stub")],
        )
        return state
