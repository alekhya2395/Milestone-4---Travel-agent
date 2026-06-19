from __future__ import annotations

from travel_agent.orchestrator.state import (
    TripState,
    ValidationCheck,
    ValidationStatus,
)

PREFERENCE_SYNONYMS: dict[str, list[str]] = {
    "food": ["restaurant", "cuisine", "eat", "dining", "market", "street food", "ramen", "sushi"],
    "temples": ["temple", "shrine", "senso-ji", "buddhist", "pagoda"],
    "forts": ["fort", "palace", "mahal", "amber", "haveli"],
    "architecture": ["building", "cathedral", "gaudi", "monument", "historic"],
    "street food": ["street food", "bazaar", "market", "snack", "chaat"],
}

CROWD_KEYWORDS = ["early", "off-peak", "quiet", "morning", "weekday", "crowd", "avoid peak"]


def _itinerary_text(state: TripState) -> str:
    parts: list[str] = []
    if state.draft_itinerary:
        parts.append(state.draft_itinerary.summary.lower())
        for day in state.draft_itinerary.days:
            parts.extend([day.theme.lower(), day.city.lower()])
            parts.extend(activity.lower() for activity in day.activities)
            parts.append(day.logistics.lower())
    return " ".join(parts)


def _preference_reflected(preference: str, text: str, state: TripState) -> bool:
    pref = preference.lower()
    if pref in text:
        return True
    for keyword in PREFERENCE_SYNONYMS.get(pref, []):
        if keyword in text:
            return True
    if state.destination_research:
        for city in state.destination_research.cities:
            for poi in city.pois:
                blob = f"{poi.name} {poi.category}".lower()
                if pref in blob or any(kw in blob for kw in PREFERENCE_SYNONYMS.get(pref, [])):
                    return True
    return False


def _constraint_addressed(constraint: str, state: TripState) -> bool:
    lowered = constraint.lower()
    if "crowd" in lowered:
        if state.destination_research:
            for city in state.destination_research.cities:
                if city.crowd_tips:
                    return True
        text = _itinerary_text(state)
        return any(keyword in text for keyword in CROWD_KEYWORDS)
    return lowered in _itinerary_text(state)


def run_deterministic_checks(state: TripState) -> tuple[list[ValidationCheck], list[str], bool]:
    """Deterministic validation rules (VR-1 through VR-5). EC-V04."""
    checks: list[ValidationCheck] = []
    issues: list[str] = []
    spec = state.trip_spec
    itinerary = state.draft_itinerary
    budget = state.budget_breakdown

    if spec and itinerary:
        day_count = len(itinerary.days)
        duration_ok = day_count == spec.duration_days
        duration_detail = f"{day_count} days planned vs {spec.duration_days} requested"
        checks.append(ValidationCheck(rule="duration", passed=duration_ok, detail=duration_detail))
        if not duration_ok:
            issues.append(f"Duration mismatch: {duration_detail}")

        itinerary_cities = {day.city.lower() for day in itinerary.days}
        missing = [city for city in spec.destinations if city.lower() not in itinerary_cities]
        destinations_ok = not missing
        dest_detail = (
            "all destinations present"
            if destinations_ok
            else f"missing: {', '.join(missing)}"
        )
        checks.append(
            ValidationCheck(rule="destinations", passed=destinations_ok, detail=dest_detail)
        )
        if not destinations_ok:
            issues.append(f"Itinerary missing destinations: {', '.join(missing)}")

    if budget:
        if spec and spec.budget_amount is None:
            budget_ok = True
            budget_detail = "budget check skipped (no ceiling specified)"
        else:
            budget_ok = not budget.over_budget
            ceiling = budget.budget_ceiling or (spec.budget_amount if spec else None)
            budget_detail = (
                f"total {budget.total_estimated:.0f} {budget.currency} "
                f"vs ceiling {ceiling:.0f} {budget.currency}"
                if ceiling is not None
                else f"total {budget.total_estimated:.0f} {budget.currency}"
            )
        checks.append(ValidationCheck(rule="budget", passed=budget_ok, detail=budget_detail))
        if not budget_ok:
            issues.append("Estimated total exceeds budget ceiling")

    if spec and spec.preferences and itinerary:
        text = _itinerary_text(state)
        for preference in spec.preferences:
            pref_ok = _preference_reflected(preference, text, state)
            checks.append(
                ValidationCheck(
                    rule=f"preference:{preference}",
                    passed=pref_ok,
                    detail="reflected in itinerary" if pref_ok else "not found in itinerary",
                )
            )
            if not pref_ok:
                issues.append(f"Preference '{preference}' not reflected in itinerary")

    if spec and spec.constraints:
        for constraint in spec.constraints:
            constraint_ok = _constraint_addressed(constraint, state)
            checks.append(
                ValidationCheck(
                    rule=f"constraint:{constraint}",
                    passed=constraint_ok,
                    detail="addressed" if constraint_ok else "not clearly addressed",
                )
            )
            if not constraint_ok:
                issues.append(f"Constraint '{constraint}' not clearly addressed")

    if spec and spec.budget_amount is not None:
        if spec.travel_style == "luxury" and spec.budget_amount < 1000:
            checks.append(
                ValidationCheck(
                    rule="constraint_conflict",
                    passed=False,
                    detail="luxury travel style with very low budget",
                )
            )
            issues.append("Conflicting constraints: luxury travel style with very low budget")

    all_passed = all(check.passed for check in checks)
    return checks, issues, all_passed


def merge_validation_reports(
    deterministic_checks: list[ValidationCheck],
    deterministic_issues: list[str],
    deterministic_pass: bool,
    llm_report,
) -> tuple[ValidationStatus, list[ValidationCheck], list[str], list[str]]:
    """Merge deterministic checks with LLM report; deterministic failures always fail."""
    det_rules = {check.rule for check in deterministic_checks}
    merged_checks = deterministic_checks + [
        check for check in llm_report.checks if check.rule not in det_rules
    ]
    merged_issues = list(dict.fromkeys(deterministic_issues + llm_report.issues))

    if not deterministic_pass:
        status = ValidationStatus.FAIL
    elif llm_report.status == ValidationStatus.FAIL:
        status = ValidationStatus.FAIL
    else:
        status = ValidationStatus.PASS

    return status, merged_checks, merged_issues, llm_report.suggestions
