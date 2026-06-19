from __future__ import annotations

import sys

from travel_agent.config import Settings, get_settings
from travel_agent.llm.rate_limiter import estimate_calls_per_run


def print_quota_preflight(settings: Settings | None = None, *, file=None) -> None:
    """Log expected API usage vs configured limits before a pipeline run."""
    if file is None:
        file = sys.stderr
    settings = settings or get_settings()
    est = estimate_calls_per_run(
        validation_retries=settings.max_validation_retries,
        json_repair_retries=settings.json_repair_retries,
    )

    lines = [
        "API quota preflight:",
        f"  Groq  ({settings.groq_model}): "
        f"{est['groq_min']}–{est['groq_max']} calls/run | "
        f"limits {settings.groq_rpm} RPM, {settings.groq_rpd} RPD, "
        f"{settings.groq_tpm} TPM, {settings.groq_tpd} TPD",
        f"  Gemini ({settings.gemini_model}): "
        f"{est['gemini_min']}–{est['gemini_max']} calls/run | "
        f"limits {settings.gemini_rpm} RPM, {settings.gemini_rpd} RPD, "
        f"{settings.gemini_tpm} TPM",
    ]

    max_runs_happy = settings.gemini_rpd // max(est["gemini_min"], 1)
    max_runs_worst = settings.gemini_rpd // max(est["gemini_max"], 1)
    lines.append(
        f"  Estimated full runs/day (Gemini-bound): ~{max_runs_happy} happy path, "
        f"~{max_runs_worst} worst case"
    )

    if settings.gemini_rpd <= 20:
        lines.append(
            "  Warning: Gemini RPD is very low — keep MAX_VALIDATION_RETRIES=1 "
            "and avoid JSON repair loops during development."
        )

    print("\n".join(lines), file=file)
