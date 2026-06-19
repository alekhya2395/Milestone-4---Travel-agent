from __future__ import annotations

import json
from pathlib import Path

from travel_agent.orchestrator.renderer import AGENT_CONTRIBUTIONS, render_itinerary
from travel_agent.orchestrator.safety import sanitize_for_export
from travel_agent.orchestrator.state import TripState

DEFAULT_OUTPUTS_DIR = Path("outputs")


def _duration_ms(start, end) -> str:
    if not end:
        return "N/A"
    delta = (end - start).total_seconds() * 1000
    return f"{delta:.0f}ms"


def render_trace(state: TripState) -> str:
    lines = [
        f"# Run Trace — {state.metadata.run_id}",
        "",
        f"- **Started:** {state.metadata.started_at.isoformat()}",
        f"- **Completed:** {state.metadata.completed_at.isoformat() if state.metadata.completed_at else 'N/A'}",
        f"- **Validation retries:** {state.metadata.validation_retry_count}",
        "",
        "## Agent execution",
        "",
        "| Agent | Phase | Provider | Parallel | Duration | Status |",
        "|-------|-------|----------|----------|----------|--------|",
    ]

    provider_map = {a[0]: a[2] for a in AGENT_CONTRIBUTIONS}

    for entry in state.metadata.agent_trace:
        provider = provider_map.get(entry.agent, "—")
        parallel = entry.parallel_group or "—"
        duration = _duration_ms(entry.started_at, entry.completed_at)
        status = "OK" if entry.success else f"FAIL: {sanitize_for_export(entry.error or 'unknown')}"
        lines.append(
            f"| {entry.agent} | {entry.phase} | {provider} | {parallel} | {duration} | {status} |"
        )

    lines.append("")

    if state.metadata.warnings:
        lines.append("## Warnings")
        lines.append("")
        for warning in state.metadata.warnings:
            lines.append(f"- {sanitize_for_export(warning)}")
        lines.append("")

    lines.append("## Raw request")
    lines.append("")
    lines.append(f"```\n{sanitize_for_export(state.raw_request)}\n```")
    lines.append("")

    return "\n".join(lines)


def export_run_artifacts(state: TripState, outputs_dir: Path | None = None) -> Path:
    """Write itinerary.md, trace.md, and state.json under outputs/{run_id}/."""
    base = (outputs_dir or DEFAULT_OUTPUTS_DIR) / state.metadata.run_id
    base.mkdir(parents=True, exist_ok=True)

    itinerary_path = base / "itinerary.md"
    trace_path = base / "trace.md"
    state_path = base / "state.json"

    itinerary_path.write_text(render_itinerary(state), encoding="utf-8")
    trace_path.write_text(render_trace(state), encoding="utf-8")
    state_path.write_text(
        json.dumps(state.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    return base
