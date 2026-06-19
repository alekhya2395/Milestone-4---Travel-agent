from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from typing import Any

from travel_agent.agents.base import AgentContext
from travel_agent.config import Settings, get_settings
from travel_agent.orchestrator.state import AgentTraceEntry, TripState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def run_agent(
    agent: Any,
    state: TripState,
    context: AgentContext,
    *,
    phase: int,
    settings: Settings | None = None,
    parallel_group: str | None = None,
) -> TripState:
    """Run one agent with timeout, single API retry, and trace logging."""
    settings = settings or get_settings()
    trace_entry = AgentTraceEntry(
        agent=agent.name,
        phase=phase,
        started_at=_utcnow(),
        parallel_group=parallel_group,
    )

    last_error: Exception | None = None
    max_attempts = 1 + settings.agent_api_retries

    for attempt in range(max_attempts):
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(agent.run, state.model_copy(deep=True), context)
                state = future.result(timeout=settings.agent_timeout_s)

            trace_entry.completed_at = _utcnow()
            trace_entry.success = True
            state.metadata.agent_trace.append(trace_entry)
            return state

        except FuturesTimeoutError:
            last_error = TimeoutError(
                f"{agent.name} exceeded {settings.agent_timeout_s}s timeout"
            )
        except Exception as exc:
            last_error = exc

        if attempt < max_attempts - 1:
            time.sleep(settings.agent_retry_backoff_s)

    trace_entry.completed_at = _utcnow()
    trace_entry.success = False
    trace_entry.error = str(last_error)
    state.metadata.agent_trace.append(trace_entry)
    state.metadata.warnings.append(
        f"{agent.name} failed after {max_attempts} attempt(s): {last_error}"
    )
    return state
