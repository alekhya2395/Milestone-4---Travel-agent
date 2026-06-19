from __future__ import annotations

from travel_agent.orchestrator.state import TripSpec, TransportPlan


def normalize_trip_spec(spec: TripSpec) -> TripSpec:
    """Post-process parsed trip_spec for common edge cases (EC-P01, EC-B05)."""
    assumptions = list(spec.assumptions)
    budget_amount = spec.budget_amount

    if budget_amount is not None and budget_amount <= 0:
        assumptions.append(
            f"Invalid budget amount ({budget_amount}); treating as unspecified (EC-B05)"
        )
        budget_amount = None

    assumption_blob = " ".join(assumptions).lower()
    if budget_amount is None and "no budget" not in assumption_blob:
        assumptions.append("No budget specified; using mid-range estimates (EC-P01)")

    return spec.model_copy(update={"budget_amount": budget_amount, "assumptions": assumptions})


def sanitize_transport_plan(plan: TransportPlan, destinations: list[str]) -> TransportPlan:
    """Remove fake inter-city legs for single-city trips (EC-T01)."""
    if len(destinations) > 1:
        return plan
    if not plan.inter_city_legs:
        return plan
    sanitized = plan.model_copy(deep=True)
    sanitized.inter_city_legs = []
    return sanitized
