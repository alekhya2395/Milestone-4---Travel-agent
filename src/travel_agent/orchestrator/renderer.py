from __future__ import annotations

from travel_agent.orchestrator.state import TripState, ValidationStatus

AGENT_CONTRIBUTIONS = [
    ("request_parser", "Request Parser", "Groq", "trip_spec"),
    ("destination_research", "Destination Research", "Groq", "destination_research"),
    ("accommodation", "Accommodation", "Groq", "accommodation_options"),
    ("transport", "Transport", "Groq", "transport_plan"),
    ("budget", "Budget", "Gemini", "budget_breakdown"),
    ("itinerary_composer", "Itinerary Composer", "Groq", "draft_itinerary"),
    ("validator", "Validator", "Gemini", "validation_report"),
]


def _fmt_money(amount: float | None, currency: str = "USD") -> str:
    if amount is None:
        return "N/A"
    symbol = "₹" if currency == "INR" else "$" if currency == "USD" else f"{currency} "
    if currency in ("USD", "INR"):
        return f"{symbol}{amount:,.0f}"
    return f"{currency} {amount:,.0f}"


def _section_overview(state: TripState) -> str:
    lines = ["## Overview", ""]
    if state.trip_spec:
        spec = state.trip_spec
        lines.extend(
            [
                f"- **Request:** {state.raw_request}",
                f"- **Duration:** {spec.duration_days} days",
                f"- **Destinations:** {', '.join(spec.destinations)}",
                f"- **Country:** {spec.country or 'N/A'}",
                f"- **Budget:** {_fmt_money(spec.budget_amount, spec.budget_currency)}",
                f"- **Preferences:** {', '.join(spec.preferences) or 'None'}",
                f"- **Constraints:** {', '.join(spec.constraints) or 'None'}",
                f"- **Travel style:** {spec.travel_style}",
                f"- **Party size:** {spec.party_size}",
            ]
        )
        if spec.assumptions:
            lines.append(f"- **Assumptions:** {'; '.join(spec.assumptions)}")
    else:
        lines.append(f"- **Request:** {state.raw_request}")
        lines.append("- **Note:** Trip could not be fully parsed.")
    lines.append("")
    return "\n".join(lines)


def _section_day_by_day(state: TripState) -> str:
    lines = ["## Day-by-day plan", ""]
    if not state.draft_itinerary or not state.draft_itinerary.days:
        lines.append("*Itinerary not available.*")
        lines.append("")
        return "\n".join(lines)

    if state.draft_itinerary.summary:
        lines.append(state.draft_itinerary.summary)
        lines.append("")

    for day in state.draft_itinerary.days:
        lines.append(f"### Day {day.day} — {day.city}: {day.theme}")
        lines.append("")
        for activity in day.activities:
            lines.append(f"- {activity}")
        if day.logistics:
            lines.append(f"- **Logistics:** {day.logistics}")
        lines.append("")
    return "\n".join(lines)


def _section_accommodation(state: TripState) -> str:
    lines = ["## Where to stay", ""]
    if not state.accommodation_options or not state.accommodation_options.cities:
        lines.append("*Accommodation recommendations not available.*")
        lines.append("")
        return "\n".join(lines)

    for city in state.accommodation_options.cities:
        lines.append(f"### {city.city}")
        if city.neighborhoods:
            lines.append(f"- **Neighborhoods:** {', '.join(city.neighborhoods)}")
        for tier in city.lodging_tiers:
            est = " (estimated)" if tier.estimated else ""
            lines.append(
                f"- **{tier.tier.title()}** — {tier.example_type}: "
                f"{_fmt_money(tier.estimated_nightly_min, state.trip_spec.budget_currency if state.trip_spec else 'USD')}–"
                f"{_fmt_money(tier.estimated_nightly_max, state.trip_spec.budget_currency if state.trip_spec else 'USD')}/night{est}"
            )
        if city.notes:
            lines.append(f"- {city.notes}")
        lines.append("")
    return "\n".join(lines)


def _section_transport(state: TripState) -> str:
    lines = ["## Transport", ""]
    if not state.transport_plan:
        lines.append("*Transport plan not available.*")
        lines.append("")
        return "\n".join(lines)

    plan = state.transport_plan
    currency = state.trip_spec.budget_currency if state.trip_spec else "USD"

    if plan.inter_city_legs:
        lines.append("### Inter-city")
        for leg in plan.inter_city_legs:
            est = " (estimated)" if leg.estimated else ""
            lines.append(
                f"- **{leg.from_location} → {leg.to_location}** via {leg.mode}, "
                f"{leg.estimated_duration}, {_fmt_money(leg.estimated_cost, currency)}{est}"
            )
            if leg.notes:
                lines.append(f"  - {leg.notes}")
        lines.append("")

    if plan.airport_transfers:
        lines.append("### Airport transfers")
        for leg in plan.airport_transfers:
            est = " (estimated)" if leg.estimated else ""
            lines.append(
                f"- **{leg.from_location} → {leg.to_location}** via {leg.mode}, "
                f"{leg.estimated_duration}, {_fmt_money(leg.estimated_cost, currency)}{est}"
            )
        lines.append("")

    if plan.local_transit:
        lines.append("### Local transit")
        for note in plan.local_transit:
            lines.append(f"**{note.city}**")
            for item in note.notes:
                lines.append(f"- {item}")
            for pas in note.pass_suggestions:
                lines.append(f"- Pass: {pas}")
            lines.append("")
    return "\n".join(lines)


def _section_budget(state: TripState) -> str:
    lines = ["## Budget", ""]
    if not state.budget_breakdown:
        lines.append("*Budget breakdown not available.*")
        lines.append("")
        return "\n".join(lines)

    b = state.budget_breakdown
    lines.append(f"- **Total estimated:** {_fmt_money(b.total_estimated, b.currency)}")
    if b.budget_ceiling is not None:
        lines.append(f"- **Budget ceiling:** {_fmt_money(b.budget_ceiling, b.currency)}")
    lines.append(f"- **Over budget:** {'Yes' if b.over_budget else 'No'}")
    lines.append("")
    lines.append("| Category | Amount | Notes |")
    lines.append("|----------|--------|-------|")
    for item in b.line_items:
        est = " (est.)" if item.estimated else ""
        notes = (item.notes or "").replace("|", "\\|")
        lines.append(f"| {item.category} | {_fmt_money(item.amount, b.currency)}{est} | {notes} |")
    lines.append("")

    if b.tradeoff_suggestions:
        lines.append("### Budget-friendly suggestions")
        for tip in b.tradeoff_suggestions:
            lines.append(f"- {tip}")
        lines.append("")
    return "\n".join(lines)


def _section_preferences_evidence(state: TripState) -> str:
    lines = ["## Preferences & constraints", ""]
    if state.trip_spec:
        if state.trip_spec.preferences:
            lines.append("**Preferences reflected:**")
            for pref in state.trip_spec.preferences:
                lines.append(f"- {pref}")
            lines.append("")
        if state.trip_spec.constraints:
            lines.append("**Constraints addressed:**")
            for c in state.trip_spec.constraints:
                lines.append(f"- {c}")
            lines.append("")

    if state.destination_research:
        lines.append("**Crowd-avoidance tips:**")
        for city in state.destination_research.cities:
            for tip in city.crowd_tips:
                lines.append(f"- {city.city}: {tip}")
        lines.append("")
    return "\n".join(lines)


def _section_validation(state: TripState) -> str:
    lines = ["## Validation", ""]
    if not state.validation_report:
        lines.append("*Validation report not available.*")
        lines.append("")
        return "\n".join(lines)

    report = state.validation_report
    status = "PASS" if report.status == ValidationStatus.PASS else "FAIL"
    lines.append(f"**Status:** {status}")
    lines.append("")

    if report.checks:
        lines.append("| Rule | Result | Detail |")
        lines.append("|------|--------|--------|")
        for check in report.checks:
            result = "Pass" if check.passed else "Fail"
            detail = check.detail.replace("|", "\\|")
            rule = check.rule.replace("|", "\\|")
            lines.append(f"| {rule} | {result} | {detail} |")
        lines.append("")

    if report.issues:
        lines.append("**Issues:**")
        for issue in report.issues:
            lines.append(f"- {issue}")
        lines.append("")

    if report.suggestions:
        lines.append("**Suggestions:**")
        for suggestion in report.suggestions:
            lines.append(f"- {suggestion}")
        lines.append("")
    return "\n".join(lines)


def _section_how_built(state: TripState) -> str:
    lines = ["## How this plan was built", ""]
    lines.append(f"- **Run ID:** `{state.metadata.run_id}`")
    lines.append(f"- **Data source:** LLM-only (all estimates labeled)")
    lines.append(f"- **Validation retries:** {state.metadata.validation_retry_count}")
    if state.metadata.warnings:
        lines.append("- **Warnings:**")
        for w in state.metadata.warnings:
            lines.append(f"  - {w}")
    lines.append("")
    lines.append("### Parsed constraints")
    lines.append("")
    if state.trip_spec:
        spec = state.trip_spec
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| Duration | {spec.duration_days} days |")
        lines.append(f"| Destinations | {', '.join(spec.destinations)} |")
        lines.append(f"| Budget | {_fmt_money(spec.budget_amount, spec.budget_currency)} |")
        lines.append(f"| Preferences | {', '.join(spec.preferences)} |")
        lines.append(f"| Constraints | {', '.join(spec.constraints)} |")
        lines.append("")

    lines.append("### Agent contributions")
    lines.append("")
    lines.append("| Agent | Provider | Artifact |")
    lines.append("|-------|----------|----------|")
    trace_by_agent = {t.agent: t for t in state.metadata.agent_trace}
    for agent_id, label, provider, artifact in AGENT_CONTRIBUTIONS:
        trace = trace_by_agent.get(agent_id)
        status = "OK" if trace and trace.success else "FAIL" if trace else "-"
        lines.append(f"| {label} | {provider} | `{artifact}` {status} |")
    lines.append("")
    lines.append(f"Full trace: `outputs/{state.metadata.run_id}/trace.md`")
    lines.append("")
    return "\n".join(lines)


def render_itinerary(state: TripState) -> str:
    """Render final markdown itinerary from TripState."""
    title = "# Travel Itinerary"
    if state.trip_spec and state.trip_spec.destinations:
        title = f"# Travel Itinerary — {' & '.join(state.trip_spec.destinations)}"

    sections = [
        title,
        "",
        _section_overview(state),
        _section_day_by_day(state),
        _section_accommodation(state),
        _section_transport(state),
        _section_budget(state),
        _section_preferences_evidence(state),
        _section_validation(state),
        _section_how_built(state),
    ]
    return "\n".join(sections)
