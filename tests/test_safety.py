"""Safety and config edge-case tests — EC-S01, EC-S02, EC-P09."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from travel_agent.config import Settings, get_settings
from travel_agent.orchestrator.safety import redact_pii, validate_api_keys


def test_validate_api_keys_exits_when_missing(capsys):
    settings = Settings(groq_api_key="", gemini_api_key="")
    with pytest.raises(SystemExit) as exc:
        validate_api_keys(settings)
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "GROQ_API_KEY" in captured.err
    assert "GEMINI_API_KEY" in captured.err


def test_redact_pii_email_and_phone():
    text = "Contact me at user@test.com or +44 20 7946 0958"
    redacted = redact_pii(text)
    assert "user@test.com" not in redacted
    assert "[REDACTED EMAIL]" in redacted
    assert "[REDACTED PHONE]" in redacted


def test_live_run_without_keys_fails_fast():
    env = os.environ.copy()
    env["GROQ_API_KEY"] = ""
    env["GEMINI_API_KEY"] = ""

    result = subprocess.run(
        [sys.executable, "-m", "travel_agent.main", "test trip"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
    )
    assert result.returncode == 1
    assert "Missing required API keys" in result.stderr
