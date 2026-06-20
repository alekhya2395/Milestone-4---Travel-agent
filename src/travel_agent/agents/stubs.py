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


# Canonical city names detected in free-form requests (voice + typed).
KNOWN_CITIES: dict[str, str] = {
    "tokyo": "Tokyo",
    "kyoto": "Kyoto",
    "osaka": "Osaka",
    "biei": "Biei",
    "nakasendo": "Nakasendo",
    "oarai": "Oarai",
    "hiroshima": "Hiroshima",
    "nara": "Nara",
    "sapporo": "Sapporo",
    "jaipur": "Jaipur",
    "udaipur": "Udaipur",
    "delhi": "Delhi",
    "mumbai": "Mumbai",
    "agra": "Agra",
    "goa": "Goa",
    "barcelona": "Barcelona",
    "paris": "Paris",
    "london": "London",
    "rome": "Rome",
    "amsterdam": "Amsterdam",
    "bali": "Bali",
    "bangkok": "Bangkok",
    "singapore": "Singapore",
    "dubai": "Dubai",
    "new york": "New York",
    "san francisco": "San Francisco",
    "los angeles": "Los Angeles",
}

_CITY_WORD = (
    r"(?!and\b|or\b|with\b|for\b|the\b|to\b|in\b|of\b|a\b|an\b|"
    r"love\b|hate\b|street\b|food\b|forts\b|crowds\b|trip\b|plan\b|day\b|days\b)"
    r"[A-Za-z][A-Za-z\-']+"
)
_CITY_TOKEN = rf"{_CITY_WORD}(?:\s+{_CITY_WORD})?"


def _planning_slice(raw: str) -> str:
    """Drop preference/constraint tails so they are not parsed as cities."""
    match = re.search(r"\b(?:love|hate|budget)\b", raw, re.I)
    return raw[: match.start()].strip(".") if match else raw


def _scan_known_cities(raw: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for key, canonical in KNOWN_CITIES.items():
        for match in re.finditer(rf"\b{re.escape(key)}\b", raw, re.I):
            found.append((match.start(), canonical))
    return found


def _dedupe_ordered(found: list[tuple[int, str]]) -> list[str]:
    found.sort(key=lambda item: item[0])
    seen: set[str] = set()
    ordered: list[str] = []
    for _, name in found:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(name)
    return ordered


def _parse_destinations(raw: str) -> list[str]:
    """Extract destination cities from free-form trip requests."""
    text = _planning_slice(raw)
    found: list[tuple[int, str]] = _scan_known_cities(text)

    for match in re.finditer(
        rf"\b({_CITY_TOKEN})\s*\+\s*({_CITY_TOKEN})\b",
        text,
        re.I,
    ):
        for group in (match.group(1), match.group(2)):
            cleaned = _clean_place_name(group)
            if cleaned:
                found.append((match.start(), cleaned))

    for match in re.finditer(
        rf"\b({_CITY_TOKEN})\s+(?:and|&)\s+({_CITY_TOKEN})\b",
        text,
        re.I,
    ):
        for group in (match.group(1), match.group(2)):
            cleaned = _clean_place_name(group)
            if cleaned:
                found.append((match.start(), cleaned))

    colon_list = re.search(r":\s*([^.$\n]+)", text)
    if colon_list:
        for part in re.split(r"\s*,\s*", colon_list.group(1)):
            cleaned = _clean_place_name(part)
            if cleaned:
                idx = text.find(part, colon_list.start())
                found.append((idx if idx >= 0 else colon_list.start(), cleaned))

    if not found:
        tail = r"(?:\s*[.,]|$|\s+(?:Love|love|with|budget|for|in|₹|\$|\d))"
        for pattern in (
            rf"(?:weekend|stay|days?\s+)?in\s+({_CITY_TOKEN}){tail}",
            rf"(?:trip|travel|visit(?:ing)?)\s+(?:to|around)\s+({_CITY_TOKEN}){tail}",
            rf"Plan\s+(?:a|an)\s+[\w\s\-]*?trip\s+to\s+({_CITY_TOKEN}){tail}",
        ):
            match = re.search(pattern, text, re.I)
            if match:
                cleaned = _clean_place_name(match.group(1))
                if cleaned:
                    found.append((match.start(), cleaned))
                    break

    if found:
        return _dedupe_ordered(found)

    if re.search(r"\b(?:India|Rajasthan)\b", text, re.I):
        return ["Jaipur", "Udaipur"]
    if re.search(r"\bJapan\b", text, re.I):
        return ["Tokyo", "Kyoto"]
    return ["Tokyo"]


def _clean_place_name(text: str) -> str | None:
    name = text.strip().strip(".")
    name = re.sub(
        r"\s+(Japan|India|France|Spain|Italy|Thailand|USA|UK|Hokkaido|Rajasthan|Culture|Nature)\b.*$",
        "",
        name,
        flags=re.I,
    )
    name = re.sub(r"^(?:the\s+|a\s+|an\s+)", "", name, flags=re.I)
    name = re.sub(r"\s+(Trail|Region|Province|State)$", "", name, flags=re.I)
    name = name.strip()
    if not name or len(name) < 3:
        return None
    skip = {
        "plan", "day", "days", "trip", "budget", "weekend", "hiking", "hike",
        "love", "hate", "food", "total", "only", "focused", "trail", "on",
    }
    if name.lower() in skip:
        return None
    words = name.split()
    return " ".join(w.capitalize() if w.islower() else w for w in words)


def _parse_country(raw: str) -> str | None:
    if "₹" in raw or re.search(r"\bIndia\b|\bRajasthan\b", raw, re.I):
        return "India"
    for country in ("Japan", "France", "Spain", "Italy", "Thailand", "USA", "UK", "Germany", "Portugal"):
        if re.search(rf"\b{country}\b", raw, re.I):
            return country
    return None


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
        "architecture",
        "forts",
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

_MAJOR_JP_CITIES = frozenset({"Tokyo", "Kyoto", "Osaka", "Hiroshima", "Nara", "Sapporo", "Fukuoka", "Nagoya"})

_PLACE_TYPE_HINTS: dict[str, tuple[str, ...]] = {
    "hiking": ("hik", "trail", "trek", "mountain", "nakasendo"),
    "coastal": ("beach", "coast", "sea", "island", "ocean", "harbor", "harbour", "surf"),
    "nature": ("nature", "photography", "national park", "wildlife", "scenic", "countryside"),
    "foodie": ("food", "street food", "cuisine", "restaurant", "market"),
    "cultural": ("temple", "fort", "museum", "architecture", "heritage", "history", "culture"),
}


def _infer_place_type(city: str, preferences: list[str], raw: str) -> str:
    blob = f"{city} {raw} {' '.join(preferences)}".lower()
    for place_type, hints in _PLACE_TYPE_HINTS.items():
        if any(hint in blob for hint in hints):
            return place_type
    return "urban"


def _format_template(value: str, city: str) -> str:
    return value.format(city=city)


def _build_dynamic_profile(city: str, preferences: list[str], raw: str) -> dict:
    place_type = _infer_place_type(city, preferences, raw)
    pref_text = ", ".join(preferences[:3])

    if place_type == "hiking":
        focus = f"trails, viewpoints, and outdoor time around {city}"
        vibe = f"{city} — forest paths, scenic overlooks, and fresh-air day hikes"
        crowd_tips = [f"Start early to beat crowds on popular {city} trails", "Pack layers and trail snacks"]
        neighborhoods = [f"{city} trailhead area", f"{city} town center", "Near main station"]
        lodging_notes = f"Book lodging in {city} town center or near the trailhead — transport can be limited."
        local_transit = ["Local bus to trailheads", "Walking between town sites"]
        activity_cost_note = f"Trail fees, guides, and gear rental near {city}"
        day_templates = [
            ("Arrival & orientation", [f"Arrive in {city} and check in", f"Short walk around {city} center", f"Trail briefing and supply stop"]),
            ("Main hike day", [f"Morning hike on the signature {city} trail", "Scenic lunch stop en route", f"Evening rest in {city}"]),
            ("Landmarks & views", [f"Viewpoint or heritage stop near {city}", f"Local museum or visitor center", "Relaxed dinner downtown"]),
            ("Nature loop", [f"Second trail or nature walk around {city}", "Photography stops and cafés", "Optional onsen or spa"]),
            ("Departure day", [f"Easy morning stroll in {city}", "Souvenir stop", "Transit to airport or next city"]),
        ]
    elif place_type == "coastal":
        focus = f"coastline walks, seafood, and seaside views in {city}"
        vibe = f"{city} — ocean air, waterfront promenades, and fresh local seafood"
        crowd_tips = [f"Visit {city} waterfront at sunrise", "Book seafood restaurants ahead on weekends"]
        neighborhoods = [f"{city} waterfront", f"{city} old port", "Near beach access"]
        lodging_notes = f"Stay walkable to the coast in {city} for sunrise and sunset walks."
        local_transit = ["Walk the coastal promenade", "Local bus along the shore"]
        activity_cost_note = f"Seafood meals and boat tours in {city}"
        day_templates = [
            ("Coast & arrival", [f"Check in and explore {city} waterfront", f"Coastal promenade walk", f"Seafood dinner in {city}"]),
            ("Beach & culture", [f"Morning beach or cove near {city}", f"Local shrine, fort, or old town in {city}", "Sunset by the water"]),
            ("Markets & day trip", [f"{city} fish or farmers market", f"Nearby coastal viewpoint", "Casual harbor-side lunch"]),
            ("Departure day", [f"Final swim or coastal walk in {city}", "Pack and depart"]),
        ]
    elif place_type == "nature":
        focus = f"landscapes, viewpoints, and slow travel around {city}"
        vibe = f"{city} — open skies, scenic drives, and camera-friendly viewpoints"
        crowd_tips = [f"Check weather for {city} viewpoints", "Rent a car if public transit is sparse"]
        neighborhoods = [f"{city} town center", "Near scenic road access", "Countryside lodge area"]
        lodging_notes = f"Choose a lodge or guesthouse outside {city} center for the best scenery."
        local_transit = ["Rental car recommended", "Seasonal tourist shuttle"]
        activity_cost_note = f"Car rental, farm stops, and park entries near {city}"
        day_templates = [
            ("Scenic arrival", [f"Arrive in {city} and pick up rental car", f"First viewpoint loop around {city}", "Local farm café stop"]),
            ("Signature landscape", [f"Sunrise shoot at a famous {city} viewpoint", "Scenic drive and short walks", "Quiet dinner locally"]),
            ("Countryside day", [f"Explore rural roads near {city}", "Seasonal fields or lake stop", "Return via local specialty food"]),
            ("Departure day", [f"One last {city} lookout", "Return rental and depart"]),
        ]
    elif place_type == "foodie":
        focus = f"local markets, signature dishes, and food neighborhoods in {city}"
        vibe = f"{city} — market mornings, regional specialties, and neighborhood food crawls"
        crowd_tips = [f"Book popular {city} restaurants early", "Visit markets before noon for best selection"]
        neighborhoods = [f"{city} food market district", f"{city} old town", "Near central station"]
        lodging_notes = f"Stay central in {city} so food markets and restaurants are walkable."
        local_transit = ["Walk between food districts", "Metro or local bus day pass"]
        activity_cost_note = f"Market tastings and restaurant meals in {city}"
        day_templates = [
            ("Market & arrival", [f"Check in and explore {city} central market", f"Signature street-food tasting in {city}", "Evening food alley crawl"]),
            ("Local cuisine deep dive", [f"Cooking class or food tour in {city}", f"Historic quarter walk between meals", "Reservation-only local favorite dinner"]),
            ("Neighborhood flavors", [f"Breakfast specialty unique to {city}", f"Café and specialty shop hop", "Progressive dinner across two districts"]),
            ("Culture between meals", [f"Light sightseeing in {city}", f"Final market stop for souvenirs", "Departure meal at a classic spot"]),
            ("Departure day", [f"One must-try breakfast in {city}", "Pack and transit out"]),
        ]
    elif place_type == "cultural":
        focus = f"heritage sites, museums, and historic neighborhoods in {city}"
        vibe = f"{city} — temples, forts, museums, and old-quarter wandering"
        crowd_tips = [f"Visit major {city} sites at opening time", "Book timed-entry tickets online when available"]
        neighborhoods = [f"{city} historic center", f"{city} museum district", "Near old town"]
        lodging_notes = f"Stay in or near {city}'s historic core for easy walking access."
        local_transit = ["Walk the old town", "Metro or heritage tram where available"]
        activity_cost_note = f"Museum entries and guided heritage tours in {city}"
        day_templates = [
            ("Heritage introduction", [f"Arrive and walk {city} old town", f"Main palace, fort, or temple in {city}", "Evening cultural quarter stroll"]),
            ("Museums & history", [f"Top museum day in {city}", f"Historic neighborhood wandering", "Traditional performance or local craft shop"]),
            ("Architecture day", [f"Iconic buildings and viewpoints in {city}", f"Guided heritage walk", "Local specialty dinner"]),
            ("Day trip option", [f"Nearby heritage site from {city}", "Return for sunset in the old center", "Night market or plaza"]),
            ("Departure day", [f"Final temple or monument in {city}", "Souvenir shopping", "Departure transfer"]),
        ]
    else:
        focus = f"landmarks, neighborhoods, and local life in {city}"
        vibe = f"{city} — classic sights mixed with cafés, shops, and local neighborhoods"
        crowd_tips = [f"Use a transit pass to cross {city} efficiently", f"Explore one {city} neighborhood deeply per day"]
        neighborhoods = [f"{city} city center", f"{city} old town", "Near main station"]
        lodging_notes = f"Pick a central base in {city} with good transit links."
        local_transit = ["City transit day pass", "Walkable central districts"]
        activity_cost_note = f"Sights, museums, and experiences in {city}"
        day_templates = [
            ("Arrival & center", [f"Check in and explore downtown {city}", f"Main square or waterfront in {city}", "Welcome dinner nearby"]),
            ("Highlights day", [f"Top landmark or museum in {city}", f"Historic district walk", "Evening in a lively neighborhood"]),
            ("Local neighborhoods", [f"Café and shopping streets in {city}", f"Park or viewpoint", "Try a regional specialty dish"]),
            ("Flexible explorer day", [f"Day trip or lesser-known district near {city}", "Local market stop", "Relaxed final dinner"]),
            ("Departure day", [f"Easy morning in {city}", "Last-minute souvenirs", "Airport or station transfer"]),
        ]

    days = [
        (theme, [_format_template(activity, city) for activity in activities])
        for theme, activities in day_templates
    ]

    return {
        "focus": focus if pref_text == "culture" else f"{focus}; emphasis on {pref_text}",
        "vibe": vibe,
        "crowd_tips": crowd_tips,
        "neighborhoods": neighborhoods,
        "lodging_notes": lodging_notes,
        "local_transit": local_transit,
        "activity_cost_note": activity_cost_note,
        "days": days,
        "place_type": place_type,
    }


def _profile_for(
    city: str,
    preferences: list[str] | None = None,
    raw: str = "",
) -> dict:
    if city in DESTINATION_PROFILES:
        return DESTINATION_PROFILES[city]
    return _build_dynamic_profile(city, preferences or ["culture"], raw)


def _primary_city(cities: list[str]) -> str:
    return cities[0] if cities else "Tokyo"


def _day_plan(
    city: str,
    day_num: int,
    duration: int,
    preferences: list[str] | None = None,
    raw: str = "",
) -> tuple[str, list[str], str]:
    profile = _profile_for(city, preferences, raw)
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


def _stub_context(state: TripState) -> tuple[list[str], list[str], str]:
    spec = state.trip_spec
    cities = spec.destinations if spec else ["Tokyo"]
    preferences = spec.preferences if spec and spec.preferences else ["culture"]
    raw = state.raw_request or ""
    return cities, preferences, raw


def _summary_for(cities: list[str], duration: int, preferences: list[str], raw: str = "") -> str:
    primary = _primary_city(cities)
    profile = _profile_for(primary, preferences, raw)
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
            country=_parse_country(raw) or ("Japan" if re.search(r"Japan", raw, re.I) else None),
            budget_amount=_parse_budget(raw),
            budget_currency="USD" if "$" in raw else ("INR" if "₹" in raw else "USD"),
            preferences=_parse_preferences(raw),
            constraints=["avoid crowds"] if "crowd" in raw.lower() else [],
            assumptions=["Demo stub — no LLM calls"],
        )
        return state


class DestinationResearchStub:
    name = "destination_research"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        cities, preferences, raw = _stub_context(state)
        state.destination_research = DestinationResearch(
            cities=[
                CityResearch(
                    city=c,
                    vibe=_profile_for(c, preferences, raw)["vibe"],
                    crowd_tips=_profile_for(c, preferences, raw)["crowd_tips"],
                )
                for c in cities
            ]
        )
        return state


class AccommodationStub:
    name = "accommodation"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        cities, preferences, raw = _stub_context(state)
        state.accommodation_options = AccommodationOptions(
            cities=[
                CityAccommodation(
                    city=c,
                    neighborhoods=_profile_for(c, preferences, raw)["neighborhoods"],
                    lodging_tiers=[
                        LodgingTier(
                            tier="mid-range",
                            example_type="Boutique hotel or ryokan",
                            estimated_nightly_min=90,
                            estimated_nightly_max=160,
                        )
                    ],
                    notes=_profile_for(c, preferences, raw)["lodging_notes"],
                )
                for c in cities
            ]
        )
        return state


class TransportStub:
    name = "transport"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        cities, preferences, raw = _stub_context(state)
        country = state.trip_spec.country if state.trip_spec else None
        legs: list[TransportLeg] = []
        for i in range(len(cities) - 1):
            shinkansen_ok = (
                country == "Japan"
                and cities[i] in _MAJOR_JP_CITIES
                and cities[i + 1] in _MAJOR_JP_CITIES
            )
            mode = "Shinkansen (bullet train)" if shinkansen_ok else "Train or regional bus"
            legs.append(
                TransportLeg(
                    from_location=cities[i],
                    to_location=cities[i + 1],
                    mode=mode,
                    estimated_duration="2–3 hours" if shinkansen_ok else "3–6 hours",
                    estimated_cost=120.0 if shinkansen_ok else 65.0,
                    notes="Reserve seats in advance during peak season",
                )
            )
        primary_profile = _profile_for(_primary_city(cities), preferences, raw)
        needs_car = primary_profile.get("place_type") in ("nature", "hiking") or any(
            "Rental car" in note for note in primary_profile["local_transit"]
        )
        airport_mode = "Rental car pickup" if needs_car else "Airport express / train"
        state.transport_plan = TransportPlan(
            inter_city_legs=legs,
            airport_transfers=[
                TransportLeg(
                    from_location="Airport",
                    to_location=cities[0],
                    mode=airport_mode,
                    estimated_duration="45–90 min",
                    estimated_cost=35.0 if needs_car else 25.0,
                )
            ],
            local_transit=[
                LocalTransitNote(city=c, notes=_profile_for(c, preferences, raw)["local_transit"])
                for c in cities
            ],
        )
        return state


class BudgetStub:
    name = "budget"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        spec = state.trip_spec
        cities, preferences, raw = _stub_context(state)
        ceiling = spec.budget_amount if spec else 3000.0
        days = spec.duration_days if spec else 5
        primary = _primary_city(cities)
        profile = _profile_for(primary, preferences, raw)
        lodging = days * 120
        transport = 220.0 if profile.get("place_type") in ("nature", "hiking") else 180.0
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
        cities, preferences, raw = _stub_context(state)
        city_schedule = _distribute_cities(cities, duration)

        days: list[ItineraryDay] = []
        for d in range(1, duration + 1):
            city = city_schedule[d - 1]
            theme, activities, logistics = _day_plan(city, d, duration, preferences, raw)
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
            summary=_summary_for(cities, duration, preferences, raw),
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
