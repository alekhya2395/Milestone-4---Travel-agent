from travel_agent.agents.base import AgentContext
from travel_agent.orchestrator.pipeline import get_stub_agents, run_stub_pipeline
from travel_agent.orchestrator.state import TripState, ValidationStatus


def test_stub_pipeline_runs_end_to_end():
    state = TripState(raw_request="test")
    result = run_stub_pipeline(state)

    assert result.trip_spec is not None
    assert result.destination_research is not None
    assert result.accommodation_options is not None
    assert result.transport_plan is not None
    assert result.budget_breakdown is not None
    assert result.draft_itinerary is not None
    assert result.validation_report is not None
    assert result.validation_report.status == ValidationStatus.PASS
    assert result.metadata.completed_at is not None


def test_all_stub_agents_have_names():
    agents = get_stub_agents()
    assert len(agents) == 7
    names = {agent.name for agent in agents}
    assert names == {
        "request_parser",
        "destination_research",
        "accommodation",
        "transport",
        "budget",
        "itinerary_composer",
        "validator",
    }


def test_stub_agents_accept_context():
    state = TripState(raw_request="weekend in Kyoto")
    context = AgentContext(validation_feedback=["fix budget"])
    for agent in get_stub_agents():
        state = agent.run(state, context)
    assert state.draft_itinerary is not None
