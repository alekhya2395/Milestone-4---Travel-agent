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
    LocalTransitNote,
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


def _parse_preferences(raw: str) -> list[str]:
    prefs: list[str] = []
    lower = raw.lower()
    for keyword in (
        "food",
        "temples",
        "culture",
        "nature",
        "photography",
        "hiking",
        "coastal",
        "shopping",
        "anime",
        "onsen",
    ):
        if keyword in lower:
            prefs.append(keyword)
    return prefs or ["culture"]


# Destination-specific demo content so each card produces a distinct itinerary.
DESTINATION_PROFILES: dict[str, dict] = {
    "Tokyo": {
        "focus": "neon districts, temples, and world-class food",
        "vibe": "Electric megacity — shrines by day, Shinjuku and Shibuya by night",
        "crowd_tips": ["Visit Senso-ji before 8am", "Book teamLab slots weeks ahead"],
        "neighborhoods": ["Shinjuku", "Shibuya", "Asakusa", "Ginza"],
        "lodging_notes": "Stay near a JR Yamanote Line station for easy cross-city hops.",
        "local_transit": ["Suica/PASMO IC card", "JR Yamanote Line day pass"],
        "activity_cost_note": "Museums, Skytree, teamLab",
        "days": [
            ("Arrival & Asakusa", ["Senso-ji Temple", "Nakamise shopping street", "Sumida River sunset walk"]),
            ("Modern Tokyo", ["Meiji Shrine morning visit", "Harajuku & Omotesando", "Shibuya Crossing at night"]),
            ("Culture & views", ["Tokyo National Museum", "Ueno Park stroll", "Tokyo Skytree observation deck"]),
            ("Food & neighborhoods", ["Tsukiji Outer Market breakfast", "Ginza depachika tasting", "Golden Gai izakaya crawl"]),
            ("Departure day", ["Imperial Palace East Gardens", "Last-minute souvenirs in Akihabara", "Airport express transfer"]),
        ],
    },
    "Kyoto": {
        "focus": "temples, geisha districts, and kaiseki cuisine",
        "vibe": "Timeless capital — bamboo groves, golden pavilions, and tea houses",
        "crowd_tips": ["Fushimi Inari at 6am", "Book kaiseki dinner in Gion early"],
        "neighborhoods": ["Gion", "Higashiyama", "Arashiyama", "Kawaramachi"],
        "lodging_notes": "Machiya guesthouses in Higashiyama put you steps from temples.",
        "local_transit": ["Kyoto bus one-day pass", "Randen tram to Arashiyama"],
        "activity_cost_note": "Temple entries, tea ceremony",
        "days": [
            ("Fushimi & southern Kyoto", ["Fushimi Inari torii hike (early)", "Tofuku-ji gardens", "Fushimi sake district tasting"]),
            ("Eastern temples", ["Kiyomizu-dera", "Ninenzaka & Sannenzaka lanes", "Gion evening walk"]),
            ("Arashiyama day", ["Bamboo Grove at dawn", "Tenryu-ji Temple", "Togetsukyo Bridge & river café"]),
            ("Golden Kyoto", ["Kinkaku-ji (Golden Pavilion)", "Ryoan-ji rock garden", "Nishiki Market dinner crawl"]),
            ("Departure day", ["Fushimi Inari revisit or Nijo Castle", "Kyoto Station shopping", "Shinkansen transfer"]),
        ],
    },
    "Osaka": {
        "focus": "street food, castle history, and neon nightlife",
        "vibe": "Japan's kitchen — bold flavors, friendly locals, and canal-side neon",
        "crowd_tips": ["Dotonbori after 7pm for full atmosphere", "Universal Studios needs full-day booking"],
        "neighborhoods": ["Namba", "Dotonbori", "Umeda", "Tennoji"],
        "lodging_notes": "Namba or Umeda keeps you near food alleys and JR loops.",
        "local_transit": ["Osaka Amazing Pass", "Midosuji subway line"],
        "activity_cost_note": "Street food, castle, USJ optional",
        "days": [
            ("Arrival & Dotonbori", ["Kuromon Ichiba Market lunch", "Dotonbori canal walk", "Takoyaki & okonomiyaki dinner crawl"]),
            ("Castle & history", ["Osaka Castle & museum", "Osaka Museum of History", "Tenmangu Shrine visit"]),
            ("Neon & neighborhoods", ["Shinsekai retro district", "Tsutenkaku Tower views", "Kushikatsu alley dinner"]),
            ("Departure day", ["Umeda Sky Building", "Last ramen in Namba", "Kansai Airport transfer"]),
        ],
    },
    "Biei": {
        "focus": "Hokkaido scenery, blue pond, and landscape photography",
        "vibe": "Quiet farmland hills — patchwork fields, misty ponds, and wide open skies",
        "crowd_tips": ["Blue Pond best at dawn with mist", "Rent a car for Patchwork Road loops"],
        "neighborhoods": ["Biei town center", "Near Biei Station", "Furano day-trip base"],
        "lodging_notes": "Book a pension or lodge with onsen — rural taxis are limited.",
        "local_transit": ["Rental car recommended", "Seasonal tourist bus to Blue Pond"],
        "activity_cost_note": "Car rental, farm café stops",
        "days": [
            ("Blue Pond & Shirogane", ["Shirogane Blue Pond sunrise shoot", "Shirahige Waterfall", "Biei town lunch & camera shop"]),
            ("Patchwork Road", ["Patchwork Road scenic drive", "Sanai-no-Oka viewpoint", "Farm café & soft-serve stop"]),
            ("Furano extension", ["Farm Tomita lavender fields (seasonal)", "Biei hill viewpoints", "Return via Asahikawa ramen dinner"]),
        ],
    },
    "Nakasendo": {
        "focus": "Edo-period trail hiking between post towns",
        "vibe": "Forest stone paths — Magome, Tsumago, and mountain ryokan stays",
        "crowd_tips": ["Start Magome→Tsumago downhill for easier hiking", "Book ryokan with half-board in Tsumago"],
        "neighborhoods": ["Magome-juku", "Tsumago-juku", "Narai-juku"],
        "lodging_notes": "Stay in a traditional minshuku in Tsumago for the full trail experience.",
        "local_transit": ["Bus to Magome trailhead", "Local bus between post towns"],
        "activity_cost_note": "Ryokan stays, trail lunch boxes",
        "days": [
            ("Magome post town", ["Magome-juku cobblestone walk", "Honjin & Waki-honjin museums", "Mountain ryokan check-in"]),
            ("Magome → Tsumago hike", ["Nakasendo trail hike (7.8 km)", "Rest at Tateba tea house", "Tsumago-juku evening lanterns"]),
            ("Tsumago & Narai", ["Tsumago morning without cars", "Bus to Narai-juku", "Narai 'Narai of a Thousand Houses' stroll"]),
            ("Departure day", ["Kiso Valley souvenir shopping", "Matsumoto side-trip option", "Train to Nagoya or Tokyo"]),
        ],
    },
    "Oarai": {
        "focus": "coastal shrines, Pacific views, and seafood",
        "vibe": "Seaside Ibaraki — torii gates in the surf and fresh morning markets",
        "crowd_tips": ["Isosaki Shrine torii at sunrise for photos", "Weekend seafood queues — go early"],
        "neighborhoods": ["Oarai town", "Near Oarai Station", "Coastal promenade"],
        "lodging_notes": "Small seaside hotels walkable to the torii and fish market.",
        "local_transit": ["Walk coastal promenade", "Local bus from Mito if day-tripping"],
        "activity_cost_note": "Seafood meals, shrine offerings",
        "days": [
            ("Torii & coast", ["Oarai Isosaki Shrine sunrise torii", "Coastal promenade walk", "Grilled clams & sashimi lunch"]),
            ("Markets & departure", ["Oarai fish market breakfast", "Aquaworld aquarium visit", "Train back to Tokyo"]),
        ],
    },
}

_DEFAULT_PROFILE = DESTINATION_PROFILES["Tokyo"]


def _profile_for(city: str) -> dict:
    return DESTINATION_PROFILES.get(city, _DEFAULT_PROFILE)


def _primary_city(cities: list[str]) -> str:
    return cities[0] if cities else "Tokyo"


def _day_plan(city: str, day_num: int, duration: int) -> tuple[str, list[str], str]:
    profile = _profile_for(city)
    templates = profile["days"]
    if day_num <= len(templates):
        theme, activities = templates[day_num - 1]
        return theme, activities, profile["local_transit"][0]
    if day_num == duration:
        return (
            "Departure day",
            ["Flexible morning activity", "Pack & transit to airport or next city"],
            profile["local_transit"][0],
        )
    last_theme, last_activities = templates[-1]
    return last_theme, last_activities, profile["local_transit"][0]


def _summary_for(cities: list[str], duration: int, preferences: list[str]) -> str:
    primary = _primary_city(cities)
    profile = _profile_for(primary)
    pref_text = ", ".join(preferences[:3]) if preferences else "local highlights"
    if len(cities) == 1:
        return (
            f"A {duration}-day {primary} trip focused on {profile['focus']}. "
            f"Highlights: {pref_text}."
        )
    return (
        f"A {duration}-day journey through {' → '.join(cities)}. "
        f"Starting in {primary} with {profile['focus']}; themes: {pref_text}."
    )


def _distribute_cities(cities: list[str], duration: int) -> list[str]:
    if len(cities) == 1:
        return [cities[0]] * duration
    schedule: list[str] = []
    for d in range(duration):
        schedule.append(cities[min(d * len(cities) // duration, len(cities) - 1)])
    return schedule


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
            preferences=_parse_preferences(raw),
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
                    vibe=_profile_for(c)["vibe"],
                    crowd_tips=_profile_for(c)["crowd_tips"],
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
                    neighborhoods=_profile_for(c)["neighborhoods"],
                    lodging_tiers=[
                        LodgingTier(
                            tier="mid-range",
                            example_type="Boutique hotel or ryokan",
                            estimated_nightly_min=90,
                            estimated_nightly_max=160,
                        )
                    ],
                    notes=_profile_for(c)["lodging_notes"],
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
            mode = (
                "Shinkansen (bullet train)"
                if cities[i] in ("Tokyo", "Kyoto", "Osaka")
                and cities[i + 1] in ("Tokyo", "Kyoto", "Osaka")
                else "Limited express train or bus"
            )
            legs.append(
                TransportLeg(
                    from_location=cities[i],
                    to_location=cities[i + 1],
                    mode=mode,
                    estimated_duration="2–3 hours" if "Shinkansen" in mode else "3–5 hours",
                    estimated_cost=120.0 if "Shinkansen" in mode else 65.0,
                    notes="Reserve seats in advance during peak season",
                )
            )
        airport_mode = (
            "Rental car pickup"
            if _primary_city(cities) in ("Biei", "Nakasendo")
            else "Airport express / train"
        )
        state.transport_plan = TransportPlan(
            inter_city_legs=legs,
            airport_transfers=[
                TransportLeg(
                    from_location="Airport",
                    to_location=cities[0],
                    mode=airport_mode,
                    estimated_duration="45–90 min",
                    estimated_cost=35.0 if airport_mode.startswith("Rental") else 25.0,
                )
            ],
            local_transit=[
                LocalTransitNote(city=c, notes=_profile_for(c)["local_transit"])
                for c in cities
            ],
        )
        return state


class BudgetStub:
    name = "budget"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        spec = state.trip_spec
        ceiling = spec.budget_amount if spec else 3000.0
        days = spec.duration_days if spec else 5
        cities = spec.destinations if spec else ["Tokyo"]
        primary = _primary_city(cities)
        profile = _profile_for(primary)
        lodging = days * 120
        transport = 220.0 if primary in ("Biei", "Nakasendo") else 180.0
        food = days * 55
        activities = days * 40
        buffer = 150.0
        total = lodging + transport + food + activities + buffer
        state.budget_breakdown = BudgetBreakdown(
            currency=spec.budget_currency if spec else "USD",
            budget_ceiling=ceiling,
            total_estimated=total,
            over_budget=ceiling is not None and total > ceiling,
            line_items=[
                BudgetLineItem(category="lodging", amount=lodging, notes=f"{days} nights in {primary}"),
                BudgetLineItem(category="transport", amount=transport, notes=profile["local_transit"][0]),
                BudgetLineItem(category="food", amount=food, notes=f"{primary} dining"),
                BudgetLineItem(
                    category="activities",
                    amount=activities,
                    notes=profile["activity_cost_note"],
                ),
                BudgetLineItem(category="buffer", amount=buffer, notes="Contingency"),
            ],
        )
        return state


class ItineraryComposerStub:
    name = "itinerary_composer"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        spec = state.trip_spec
        duration = spec.duration_days if spec else 5
        cities = spec.destinations if spec else ["Tokyo"]
        preferences = spec.preferences if spec else ["culture"]
        city_schedule = _distribute_cities(cities, duration)

        days: list[ItineraryDay] = []
        for d in range(1, duration + 1):
            city = city_schedule[d - 1]
            theme, activities, logistics = _day_plan(city, d, duration)
            days.append(
                ItineraryDay(
                    day=d,
                    city=city,
                    theme=theme,
                    activities=activities,
                    logistics=logistics,
                )
            )
        state.draft_itinerary = DraftItinerary(
            summary=_summary_for(cities, duration, preferences),
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
