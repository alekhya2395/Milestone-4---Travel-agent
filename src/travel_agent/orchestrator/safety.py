from __future__ import annotations

import re
import sys

from travel_agent.config import Settings

EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{7,}\d")
# Groq (gsk_), OpenAI-style (sk-), Google (AIza), Gemini (AQ.)
API_KEY_RE = re.compile(
    r"(gsk_[a-zA-Z0-9]{20,}|sk-[a-zA-Z0-9_\-]{16,}|AIza[a-zA-Z0-9_\-]{16,}|AQ\.[a-zA-Z0-9_\-]{20,})"
)


def redact_pii(text: str) -> str:
    """Redact emails and phone numbers from trace output (EC-P11)."""
    text = EMAIL_RE.sub("[REDACTED EMAIL]", text)
    return PHONE_RE.sub("[REDACTED PHONE]", text)


def redact_secrets(text: str) -> str:
    """Redact API key patterns from logs (EC-S04)."""
    return API_KEY_RE.sub("[REDACTED KEY]", text)


def sanitize_for_export(text: str) -> str:
    return redact_pii(redact_secrets(text))


def validate_api_keys(settings: Settings, *, file=None) -> None:
    """Fail fast when live pipeline keys are missing (EC-S01, EC-S02)."""
    if file is None:
        file = sys.stderr
    missing: list[str] = []
    if not settings.groq_api_key:
        missing.append("GROQ_API_KEY")
    if not settings.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if missing:
        print(
            f"Error: Missing required API keys: {', '.join(missing)}. "
            "Use --stub for offline runs or add keys to .env.",
            file=file,
        )
        sys.exit(1)
