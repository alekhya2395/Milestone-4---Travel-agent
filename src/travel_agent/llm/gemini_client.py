from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from travel_agent.config import Settings, get_settings
from travel_agent.llm.base import (
    build_schema_prompt,
    parse_json_response,
    validate_against_schema,
)
from travel_agent.llm.rate_limiter import get_gemini_limiter


class GeminiClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        self._client = genai.Client(api_key=self.settings.gemini_api_key)
        self._limiter = get_gemini_limiter(
            rpm=self.settings.gemini_rpm,
            rpd=self.settings.gemini_rpd,
            tpm=self.settings.gemini_tpm,
        )

    def rate_limit_status(self):
        return self._limiter.status()

    def complete(
        self,
        system: str,
        user: str,
        schema: type[BaseModel] | None = None,
    ) -> dict[str, Any]:
        schema_hint = build_schema_prompt(schema)
        prompt = f"{system}\n\n{schema_hint}\n\nUser request:\n{user}"

        last_error: Exception | None = None
        for attempt in range(self.settings.json_repair_retries + 1):
            try:
                if self.settings.rate_limit_enabled:
                    self._limiter.acquire()

                response = self._client.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                        max_output_tokens=self.settings.gemini_max_tokens,
                    ),
                )
                content = response.text or "{}"
                data = parse_json_response(content)
                return validate_against_schema(data, schema)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                if attempt < self.settings.json_repair_retries:
                    prompt += (
                        "\n\nYour previous response was not valid JSON. "
                        "Return only valid JSON."
                    )
                    continue
                raise ValueError(f"Gemini JSON parse failed after retries: {exc}") from exc

        raise ValueError(f"Gemini completion failed: {last_error}")

    def ping(self) -> dict[str, Any]:
        return self.complete(
            system="You are a helpful assistant.",
            user='Return JSON: {"status": "ok", "provider": "gemini"}',
        )
