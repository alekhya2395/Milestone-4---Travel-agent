from __future__ import annotations

import json
from typing import Any

from groq import Groq
from pydantic import BaseModel

from travel_agent.config import Settings, get_settings
from travel_agent.llm.base import (
    build_schema_prompt,
    parse_json_response,
    validate_against_schema,
)
from travel_agent.llm.rate_limiter import get_groq_limiter


class GroqClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        self._client = Groq(api_key=self.settings.groq_api_key)
        self._limiter = get_groq_limiter(
            rpm=self.settings.groq_rpm,
            rpd=self.settings.groq_rpd,
            tpm=self.settings.groq_tpm,
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
        messages = [
            {"role": "system", "content": f"{system}\n\n{schema_hint}"},
            {"role": "user", "content": user},
        ]

        last_error: Exception | None = None
        for attempt in range(self.settings.json_repair_retries + 1):
            try:
                if self.settings.rate_limit_enabled:
                    self._limiter.acquire()

                response = self._client.chat.completions.create(
                    model=self.settings.groq_model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                    max_tokens=self.settings.groq_max_tokens,
                )
                content = response.choices[0].message.content or "{}"
                data = parse_json_response(content)
                return validate_against_schema(data, schema)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                if attempt < self.settings.json_repair_retries:
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Your previous response was not valid JSON. "
                                "Return only valid JSON with no markdown fences."
                            ),
                        }
                    )
                    continue
                raise ValueError(f"Groq JSON parse failed after retries: {exc}") from exc

        raise ValueError(f"Groq completion failed: {last_error}")

    def ping(self) -> dict[str, Any]:
        return self.complete(
            system="You are a helpful assistant.",
            user='Return JSON: {"status": "ok", "provider": "groq"}',
        )
