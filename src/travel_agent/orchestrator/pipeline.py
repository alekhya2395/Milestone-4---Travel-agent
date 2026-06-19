from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone

from travel_agent.agents.accommodation import AccommodationAgent
from travel_agent.agents.base import AgentContext
from travel_agent.agents.budget import BudgetAgent
from travel_agent.agents.destination_research import DestinationResearchAgent
from travel_agent.agents.itinerary_composer import ItineraryComposerAgent
from travel_agent.agents.request_parser import RequestParserAgent
from travel_agent.agents.stubs import (
    AccommodationStub,
    BudgetStub,
    DestinationResearchStub,
    ItineraryComposerStub,
    RequestParserStub,
    TransportStub,
    ValidatorStub,
)
from travel_agent.agents.transport import TransportAgent
from travel_agent.agents.validator import ValidatorAgent
from travel_agent.config import Settings, get_settings
from travel_agent.orchestrator.runner import run_agent
from travel_agent.orchestrator.state import TripState, ValidationStatus


@dataclass
class AgentBundle:
    parser: RequestParserAgent | RequestParserStub
    research: DestinationResearchAgent | DestinationResearchStub
    accommodation: AccommodationAgent | AccommodationStub
    transport: TransportAgent | TransportStub
    budget: BudgetAgent | BudgetStub
    composer: ItineraryComposerAgent | ItineraryComposerStub
    validator: ValidatorAgent | ValidatorStub


def get_stub_bundle() -> AgentBundle:
    return AgentBundle(
        parser=RequestParserStub(),
        research=DestinationResearchStub(),
        accommodation=AccommodationStub(),
        transport=TransportStub(),
        budget=BudgetStub(),
        composer=ItineraryComposerStub(),
        validator=ValidatorStub(),
    )


def get_agent_bundle() -> AgentBundle:
    """Phase 1+ agents (LLM-driven)."""
    return AgentBundle(
        parser=RequestParserAgent(),
        research=DestinationResearchAgent(),
        accommodation=AccommodationAgent(),
        transport=TransportAgent(),
        budget=BudgetAgent(),
        composer=ItineraryComposerAgent(),
        validator=ValidatorAgent(),
    )


# Backward compatibility
def get_stub_agents():
    b = get_stub_bundle()
    return [b.parser, b.research, b.accommodation, b.transport, b.budget, b.composer, b.validator]


def get_agents():
    b = get_agent_bundle()
    return [b.parser, b.research, b.accommodation, b.transport, b.budget, b.composer, b.validator]


def run_stub_pipeline(state: TripState) -> TripState:
    """Phase 0: orchestrated pipeline with stub agents (no LLM calls)."""
    return run_orchestrated_pipeline(state, get_stub_bundle())


def run_pipeline(state: TripState) -> TripState:
    """Phase 2: orchestrated LLM pipeline with parallel gather and validation retries."""
    return run_orchestrated_pipeline(state, get_agent_bundle())


def run_orchestrated_pipeline(
    state: TripState,
    bundle: AgentBundle,
    settings: Settings | None = None,
) -> TripState:
    settings = settings or get_settings()
    context = AgentContext()

    # Phase 1 — Understand
    state.metadata.current_phase = 1
    state = run_agent(bundle.parser, state, context, phase=1, settings=settings)
    if state.trip_spec is None:
        parser_failed = any(
            entry.agent == "request_parser" and not entry.success
            for entry in state.metadata.agent_trace
        )
        if parser_failed:
            state.metadata.warnings.append(
                "Pipeline stopped: request parsing failed (EC-O03/O04)"
            )
            state.metadata.completed_at = datetime.now(timezone.utc)
            return state

    # Phase 2 — Gather (parallel or sequential)
    state.metadata.current_phase = 2
    state = _run_gather(state, bundle, context, settings)

    # Phase 3 — Constrain
    state.metadata.current_phase = 3
    state = run_agent(bundle.budget, state, context, phase=3, settings=settings)

    # Phase 4 — Synthesize
    state.metadata.current_phase = 4
    state = run_agent(bundle.composer, state, context, phase=4, settings=settings)

    # Phase 5 — Verify (+ Phase 6 remediate loop)
    state = _run_validate_with_retries(state, bundle, context, settings)

    state.metadata.completed_at = datetime.now(timezone.utc)
    return state


def _run_gather(
    state: TripState,
    bundle: AgentBundle,
    context: AgentContext,
    settings: Settings,
) -> TripState:
    gather_agents = [bundle.research, bundle.accommodation, bundle.transport]

    if settings.gather_parallel:
        return _run_gather_parallel(state, gather_agents, context, settings)
    for agent in gather_agents:
        state = run_agent(agent, state, context, phase=2, settings=settings)
    return state


def _run_gather_parallel(
    state: TripState,
    gather_agents,
    context: AgentContext,
    settings: Settings,
) -> TripState:
    """Run gather agents concurrently; each starts from the same pre-gather snapshot."""
    snapshot = state.model_copy(deep=True)
    results: dict[str, TripState] = {}

    def _run_one(agent):
        return agent.name, run_agent(
            agent,
            snapshot,
            context,
            phase=2,
            settings=settings,
            parallel_group="gather",
        )

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_run_one, agent): agent.name for agent in gather_agents}
        for future in as_completed(futures):
            name, result_state = future.result()
            results[name] = result_state

    return _merge_gather_results(state, results)


def _merge_gather_results(state: TripState, results: dict[str, TripState]) -> TripState:
    for name, partial in results.items():
        if name == "destination_research" and partial.destination_research is not None:
            state.destination_research = partial.destination_research
        elif name == "accommodation" and partial.accommodation_options is not None:
            state.accommodation_options = partial.accommodation_options
        elif name == "transport" and partial.transport_plan is not None:
            state.transport_plan = partial.transport_plan

        for entry in partial.metadata.agent_trace:
            if entry.agent == name and entry.parallel_group == "gather":
                state.metadata.agent_trace.append(entry)
        state.metadata.warnings.extend(partial.metadata.warnings)

    return state


def _run_validate_with_retries(
    state: TripState,
    bundle: AgentBundle,
    context: AgentContext,
    settings: Settings,
) -> TripState:
    state.metadata.current_phase = 5
    state = run_agent(bundle.validator, state, context, phase=5, settings=settings)

    while (
        state.validation_report is not None
        and state.validation_report.status == ValidationStatus.FAIL
        and state.metadata.validation_retry_count < settings.max_validation_retries
    ):
        state.metadata.validation_retry_count += 1
        report = state.validation_report
        context.validation_feedback = report.issues + report.suggestions
        context.retry_attempt = state.metadata.validation_retry_count

        state.metadata.current_phase = 6
        state = run_agent(bundle.budget, state, context, phase=6, settings=settings)
        state = run_agent(bundle.composer, state, context, phase=6, settings=settings)
        state = run_agent(bundle.validator, state, context, phase=5, settings=settings)

    if (
        state.validation_report is not None
        and state.validation_report.status == ValidationStatus.FAIL
    ):
        state.metadata.warnings.append(
            "Validation did not pass after retries; returning best-effort itinerary."
        )

    return state
