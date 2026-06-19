"""Phase 2 orchestration tests — no live API calls."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from travel_agent.agents.base import AgentContext
from travel_agent.agents.stubs import (
    AccommodationStub,
    BudgetStub,
    DestinationResearchStub,
    ItineraryComposerStub,
    RequestParserStub,
    TransportStub,
)
from travel_agent.config import get_settings
from travel_agent.orchestrator.pipeline import AgentBundle, run_orchestrated_pipeline
from travel_agent.orchestrator.state import (
    TripState,
    ValidationCheck,
    ValidationReport,
    ValidationStatus,
)


@pytest.fixture
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class SlowStub:
    """Stub that records timing for parallel gather tests."""

    def __init__(self, name: str, delay: float = 0.15):
        self.name = name
        self.delay = delay
        self.started_at: float | None = None
        self.ended_at: float | None = None

    def run(self, state: TripState, context: AgentContext) -> TripState:
        self.started_at = time.monotonic()
        time.sleep(self.delay)
        self.ended_at = time.monotonic()
        if self.name == "destination_research":
            return DestinationResearchStub().run(state, context)
        if self.name == "accommodation":
            return AccommodationStub().run(state, context)
        return TransportStub().run(state, context)


class FailThenPassValidator:
    name = "validator"

    def __init__(self) -> None:
        self.calls = 0

    def run(self, state: TripState, context: AgentContext) -> TripState:
        self.calls += 1
        if self.calls == 1:
            state.validation_report = ValidationReport(
                status=ValidationStatus.FAIL,
                issues=["Budget exceeds ceiling"],
                suggestions=["Reduce lodging tier"],
                checks=[
                    ValidationCheck(
                        rule="budget",
                        passed=False,
                        detail="over budget",
                    )
                ],
            )
        else:
            state.validation_report = ValidationReport(
                status=ValidationStatus.PASS,
                checks=[
                    ValidationCheck(rule="budget", passed=True, detail="within budget")
                ],
            )
        return state


class AlwaysFailValidator:
    name = "validator"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        state.validation_report = ValidationReport(
            status=ValidationStatus.FAIL,
            issues=["Still over budget"],
            suggestions=["Cut activities"],
        )
        return state


class SlowResearch(DestinationResearchStub):
    name = "destination_research"

    def run(self, state: TripState, context: AgentContext) -> TripState:
        time.sleep(2.0)
        return super().run(state, context)


def test_parallel_gather_overlaps(clear_settings_cache, monkeypatch):
    monkeypatch.setenv("GATHER_PARALLEL", "true")
    get_settings.cache_clear()

    research = SlowStub("destination_research", 0.2)
    accommodation = SlowStub("accommodation", 0.2)
    transport = SlowStub("transport", 0.2)

    bundle = AgentBundle(
        parser=RequestParserStub(),
        research=research,
        accommodation=accommodation,
        transport=transport,
        budget=BudgetStub(),
        composer=ItineraryComposerStub(),
        validator=FailThenPassValidator(),
    )

    start = time.monotonic()
    state = run_orchestrated_pipeline(
        TripState(raw_request="test trip"),
        bundle,
        settings=get_settings(),
    )
    elapsed = time.monotonic() - start

    assert elapsed < 0.55  # parallel ~0.2s vs sequential ~0.6s+
    assert research.started_at and accommodation.started_at and transport.started_at
    overlap = (
        max(research.started_at, accommodation.started_at, transport.started_at)
        < min(research.ended_at, accommodation.ended_at, transport.ended_at)
    )
    assert overlap

    gather_trace = [t for t in state.metadata.agent_trace if t.parallel_group == "gather"]
    assert len(gather_trace) == 3


def test_validation_retry_remediates(clear_settings_cache, monkeypatch):
    monkeypatch.setenv("GATHER_PARALLEL", "false")
    monkeypatch.setenv("MAX_VALIDATION_RETRIES", "1")
    get_settings.cache_clear()

    validator = FailThenPassValidator()
    bundle = AgentBundle(
        parser=RequestParserStub(),
        research=DestinationResearchStub(),
        accommodation=AccommodationStub(),
        transport=TransportStub(),
        budget=BudgetStub(),
        composer=ItineraryComposerStub(),
        validator=validator,
    )

    state = run_orchestrated_pipeline(TripState(raw_request="test"), bundle)
    assert validator.calls == 2
    assert state.validation_report.status == ValidationStatus.PASS
    assert state.metadata.validation_retry_count == 1


def test_max_retries_returns_best_effort(clear_settings_cache, monkeypatch):
    monkeypatch.setenv("GATHER_PARALLEL", "false")
    monkeypatch.setenv("MAX_VALIDATION_RETRIES", "1")
    get_settings.cache_clear()

    bundle = AgentBundle(
        parser=RequestParserStub(),
        research=DestinationResearchStub(),
        accommodation=AccommodationStub(),
        transport=TransportStub(),
        budget=BudgetStub(),
        composer=ItineraryComposerStub(),
        validator=AlwaysFailValidator(),
    )

    state = run_orchestrated_pipeline(TripState(raw_request="test"), bundle)
    assert state.validation_report.status == ValidationStatus.FAIL
    assert any("best-effort" in w for w in state.metadata.warnings)


def test_agent_timeout_degrades_gracefully(clear_settings_cache, monkeypatch):
    monkeypatch.setenv("AGENT_TIMEOUT_S", "1")
    monkeypatch.setenv("GATHER_PARALLEL", "false")
    get_settings.cache_clear()

    bundle = AgentBundle(
        parser=RequestParserStub(),
        research=SlowResearch(),
        accommodation=AccommodationStub(),
        transport=TransportStub(),
        budget=BudgetStub(),
        composer=ItineraryComposerStub(),
        validator=FailThenPassValidator(),
    )

    state = run_orchestrated_pipeline(TripState(raw_request="test"), bundle)
    assert any("destination_research" in w and "failed" in w for w in state.metadata.warnings)
    assert state.destination_research is None
    assert state.accommodation_options is not None


def test_validation_feedback_on_retry(clear_settings_cache, monkeypatch):
    monkeypatch.setenv("GATHER_PARALLEL", "false")
    monkeypatch.setenv("MAX_VALIDATION_RETRIES", "1")
    get_settings.cache_clear()

    captured: list[str] = []

    class CapturingBudget(BudgetStub):
        def run(self, state, context):
            if context.validation_feedback:
                captured.extend(context.validation_feedback)
            return super().run(state, context)

    bundle = AgentBundle(
        parser=RequestParserStub(),
        research=DestinationResearchStub(),
        accommodation=AccommodationStub(),
        transport=TransportStub(),
        budget=CapturingBudget(),
        composer=ItineraryComposerStub(),
        validator=FailThenPassValidator(),
    )

    run_orchestrated_pipeline(TripState(raw_request="test"), bundle)
    assert captured
    assert any("budget" in item.lower() for item in captured)
