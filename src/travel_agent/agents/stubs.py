import re

from travel_agent.agents.base import AgentContext
from travel_agent.orchestrator.state import (
    AccommodationOptions,
    BudgetBreakdown,
    BudgetLineItem,
    CityAccommodation,
    CityResearch,
    DestinationResearch,
    DraftItinerary,
    ItineraryDay,
    LodgingTier,
    TransportLeg,
    TransportPlan,
    TripSpec,
    TripState,
    ValidationCheck,
    ValidationReport,
    ValidationStatus,
)


def _parse_duration(raw: str, default: int = 5) -> int:
    m = re.search(r"(\d+)\s*-?\s*day", raw, re.I)
    return int(m.group(1)) if m else default


def _parse_destinations(raw: str) -> list[str]:
    dests: list[str] = []
    for name in ("Tokyo", "Kyoto", "Osaka", "Biei", "Nakasendo", "Oarai"):
        if re.search(rf"\b{re.escape(name)}\b", raw, re.I):
            dests.append(name)
    if dests:
        return dests
    if re.search(r"\bJapan\b", raw, re.I):
        return ["Tokyo", "Kyoto"]
    return ["Tokyo"]


def _parse_budget(raw: str) -> float | None:
    m = re.search(r"\$\s*([\d,]+)", raw)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"(\d+)\s*k\b", raw, re.I)
    if m:
        return float(m.group(1)) * 1000
    return None


class RequestParserStub:
    name = "request_parser"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        raw = state.raw_request
        state.trip_spec = TripSpec(
            duration_days=_parse_duration(raw),
            destinations=_parse_destinations(raw),
            country="Japan" if re.search(r"Japan", raw, re.I) else None,
            budget_amount=_parse_budget(raw),
            budget_currency="USD",
            preferences=["food", "temples"] if "temple" in raw.lower() else [],
            constraints=["avoid crowds"] if "crowd" in raw.lower() else [],
            assumptions=["Demo stub — no LLM calls"],
        )
        return state


class DestinationResearchStub:
    name = "destination_research"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        cities = state.trip_spec.destinations if state.trip_spec else ["Tokyo"]
        state.destination_research = DestinationResearch(
            cities=[
                CityResearch(
                    city=c,
                    vibe=f"Cultural highlights and local food in {c}",
                    crowd_tips=["Visit popular sites before 9am", "Book restaurants ahead"],
                )
                for c in cities
            ]
        )
        return state


class AccommodationStub:
    name = "accommodation"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        cities = state.trip_spec.destinations if state.trip_spec else ["Tokyo"]
        state.accommodation_options = AccommodationOptions(
            cities=[
                CityAccommodation(
                    city=c,
                    neighborhoods=["Central", "Historic district", "Near transit"],
                    lodging_tiers=[
                        LodgingTier(
                            tier="mid-range",
                            example_type="Boutique hotel",
                            estimated_nightly_min=90,
                            estimated_nightly_max=160,
                        )
                    ],
                    notes=f"Stay near a major station in {c} for easy day trips.",
                )
                for c in cities
            ]
        )
        return state


class TransportStub:
    name = "transport"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        cities = state.trip_spec.destinations if state.trip_spec else ["Tokyo", "Kyoto"]
        legs: list[TransportLeg] = []
        for i in range(len(cities) - 1):
            legs.append(
                TransportLeg(
                    from_location=cities[i],
                    to_location=cities[i + 1],
                    mode="Shinkansen (bullet train)",
                    estimated_duration="2–3 hours",
                    estimated_cost=120.0,
                    notes="Reserve seats in advance during peak season",
                )
            )
        state.transport_plan = TransportPlan(
            inter_city_legs=legs,
            airport_transfers=[
                TransportLeg(
                    from_location="Airport",
                    to_location=cities[0],
                    mode="Airport express / train",
                    estimated_duration="45–60 min",
                    estimated_cost=25.0,
                )
            ],
        )
        return state


class BudgetStub:
    name = "budget"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        spec = state.trip_spec
        ceiling = spec.budget_amount if spec else 3000.0
        days = spec.duration_days if spec else 5
        lodging = days * 120
        transport = 180.0
        food = days * 55
        activities = days * 35
        buffer = 150.0
        total = lodging + transport + food + activities + buffer
        state.budget_breakdown = BudgetBreakdown(
            currency=spec.budget_currency if spec else "USD",
            budget_ceiling=ceiling,
            total_estimated=total,
            over_budget=ceiling is not None and total > ceiling,
            line_items=[
                BudgetLineItem(category="lodging", amount=lodging, notes=f"{days} nights"),
                BudgetLineItem(category="transport", amount=transport, notes="Trains + airport"),
                BudgetLineItem(category="food", amount=food, notes="Meals & snacks"),
                BudgetLineItem(category="activities", amount=activities, notes="Temples, museums"),
                BudgetLineItem(category="buffer", amount=buffer, notes="Contingency"),
            ],
        )
        return state


class ItineraryComposerStub:
    name = "itinerary_composer"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        spec = state.trip_spec
        duration = spec.duration_days if spec else 5
        cities = spec.destinations if spec else ["Tokyo", "Kyoto"]
        themes = [
            "Arrival & neighborhood exploration",
            "Temples & traditional culture",
            "Food markets & local cuisine",
            "Day trip & scenic views",
            "Departure & last-minute shopping",
        ]
        activity_pool = [
            ["Senso-ji Temple", "Asakusa street food", "Sumida River walk"],
            ["Fushimi Inari early morning", "Nishiki Market lunch", "Gion district stroll"],
            ["Osaka Dotonbori dinner", "Castle visit", "Kuromon Market"],
            ["Local café breakfast", "Museum or garden", "Souvenir shopping"],
            ["Pack & airport transfer"],
        ]
        days: list[ItineraryDay] = []
        for d in range(1, duration + 1):
            city = cities[min(d - 1, len(cities) - 1)]
            idx = min(d - 1, len(themes) - 1)
            acts = activity_pool[idx] if d <= len(activity_pool) else activity_pool[-1]
            days.append(
                ItineraryDay(
                    day=d,
                    city=city,
                    theme=themes[idx],
                    activities=acts,
                    logistics="Use IC card / day pass for local transit",
                )
            )
        state.draft_itinerary = DraftItinerary(
            summary=f"A {duration}-day journey through {', '.join(cities)} focused on food, culture, and temples.",
            days=days,
        )
        return state


class ValidatorStub:
    name = "validator"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        state.validation_report = ValidationReport(
            status=ValidationStatus.PASS,
            checks=[ValidationCheck(rule="stub_demo", passed=True, detail="Demo itinerary validated")],
        )
        return state
