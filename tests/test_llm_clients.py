import os

import pytest

from travel_agent.config import Settings
from travel_agent.llm.gemini_client import GeminiClient
from travel_agent.llm.groq_client import GroqClient


def test_groq_missing_key_raises():
    settings = Settings(groq_api_key="")
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        GroqClient(settings=settings)


def test_gemini_missing_key_raises():
    settings = Settings(gemini_api_key="")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiClient(settings=settings)


@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set")
def test_groq_ping():
    client = GroqClient()
    result = client.ping()
    assert result.get("status") == "ok"
    assert result.get("provider") == "groq"


@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_gemini_ping():
    client = GeminiClient()
    result = client.ping()
    assert result.get("status") == "ok"
    assert result.get("provider") == "gemini"
