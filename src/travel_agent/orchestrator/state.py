from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class TripSpec(BaseModel):
    duration_days: int
    destinations: list[str]
    country: str | None = None
    budget_amount: float | None = None
    budget_currency: str = "USD"
    preferences: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    travel_style: str = "mid-range"
    party_size: int = 1
    assumptions: list[str] = Field(default_factory=list)


class POI(BaseModel):
    name: str
    category: str
    best_time: str
    estimated_duration_hours: float
    estimated: bool = True


class CityResearch(BaseModel):
    city: str
    vibe: str
    pois: list[POI] = Field(default_factory=list)
    crowd_tips: list[str] = Field(default_factory=list)


class DestinationResearch(BaseModel):
    cities: list[CityResearch] = Field(default_factory=list)


class LodgingTier(BaseModel):
    tier: Literal["budget", "mid-range", "upscale"]
    example_type: str
    estimated_nightly_min: float
    estimated_nightly_max: float
    estimated: bool = True


class CityAccommodation(BaseModel):
    city: str
    neighborhoods: list[str] = Field(default_factory=list)
    lodging_tiers: list[LodgingTier] = Field(default_factory=list)
    notes: str = ""


class AccommodationOptions(BaseModel):
    cities: list[CityAccommodation] = Field(default_factory=list)


class TransportLeg(BaseModel):
    from_location: str
    to_location: str
    mode: str
    estimated_duration: str
    estimated_cost: float
    estimated: bool = True
    notes: str = ""


class LocalTransitNote(BaseModel):
    city: str
    notes: list[str] = Field(default_factory=list)
    pass_suggestions: list[str] = Field(default_factory=list)


class TransportPlan(BaseModel):
    inter_city_legs: list[TransportLeg] = Field(default_factory=list)
    airport_transfers: list[TransportLeg] = Field(default_factory=list)
    local_transit: list[LocalTransitNote] = Field(default_factory=list)


class BudgetLineItem(BaseModel):
    category: Literal["lodging", "transport", "food", "activities", "buffer"]
    amount: float
    estimated: bool = True
    notes: str = ""


class BudgetBreakdown(BaseModel):
    currency: str = "USD"
    line_items: list[BudgetLineItem] = Field(default_factory=list)
    total_estimated: float = 0.0
    budget_ceiling: float | None = None
    over_budget: bool = False
    tradeoff_suggestions: list[str] = Field(default_factory=list)


class ItineraryDay(BaseModel):
    day: int
    city: str
    theme: str
    activities: list[str] = Field(default_factory=list)
    logistics: str = ""


class DraftItinerary(BaseModel):
    days: list[ItineraryDay] = Field(default_factory=list)
    summary: str = ""


class ValidationCheck(BaseModel):
    rule: str
    passed: bool
    detail: str


class ValidationReport(BaseModel):
    status: ValidationStatus = ValidationStatus.FAIL
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    checks: list[ValidationCheck] = Field(default_factory=list)


class AgentTraceEntry(BaseModel):
    agent: str
    phase: int
    started_at: datetime
    completed_at: datetime | None = None
    success: bool = True
    error: str | None = None
    parallel_group: str | None = None


class RunMetadata(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    current_phase: int = 0
    validation_retry_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    agent_trace: list[AgentTraceEntry] = Field(default_factory=list)


class TripState(BaseModel):
    raw_request: str = ""
    trip_spec: TripSpec | None = None
    destination_research: DestinationResearch | None = None
    accommodation_options: AccommodationOptions | None = None
    transport_plan: TransportPlan | None = None
    budget_breakdown: BudgetBreakdown | None = None
    draft_itinerary: DraftItinerary | None = None
    validation_report: ValidationReport | None = None
    metadata: RunMetadata = Field(default_factory=RunMetadata)
