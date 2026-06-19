"""Repo hygiene checks — run before git push or demo."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TRACKED = {".env"}
SECRET_PATTERNS = ("gsk_", "AIza", "AQ.", "sk-proj-")


def test_env_gitignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore


def test_outputs_gitignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "outputs/*" in gitignore or "outputs/" in gitignore


def test_env_example_has_placeholders():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "GROQ_API_KEY=your_groq_api_key_here" in example
    assert "GEMINI_API_KEY=your_gemini_api_key_here" in example
    assert "gsk_" not in example
    assert "AQ." not in example


def test_src_has_no_hardcoded_secrets():
    src = ROOT / "src" / "travel_agent"
    for path in src.rglob("*.py"):
        if path.name == "safety.py":
            continue  # contains redaction regex literals, not real keys
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            assert pattern not in text, f"Possible secret in {path}"


def test_live_evidence_has_no_secrets():
    manifest = ROOT / "outputs" / "evidence_manifest.json"
    if not manifest.exists():
        pytest.skip("No evidence manifest")
    for run_dir in (ROOT / "outputs").iterdir():
        if not run_dir.is_dir():
            continue
        for name in ("trace.md", "state.json", "itinerary.md"):
            path = run_dir / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in SECRET_PATTERNS:
                assert pattern not in text, f"Secret pattern in {path}"


def test_groq_and_gemini_keys_redacted():
    from travel_agent.orchestrator.safety import sanitize_for_export

    groq = "Error: gsk_FAKEGROQKEY012345678901234567890"
    gemini = "Error: AQ.FAKEGEMINIKEY012345678901234567890"
    assert "gsk_" not in sanitize_for_export(groq)
    assert "AQ." not in sanitize_for_export(gemini)
    assert "[REDACTED KEY]" in sanitize_for_export(groq)
    assert "[REDACTED KEY]" in sanitize_for_export(gemini)
