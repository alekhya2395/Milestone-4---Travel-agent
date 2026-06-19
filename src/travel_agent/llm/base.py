from __future__ import annotations

import json
import re
from typing import Any, Protocol

from pydantic import BaseModel


class LLMClient(Protocol):
    def complete(
        self,
        system: str,
        user: str,
        schema: type[BaseModel] | None = None,
    ) -> dict[str, Any]:
        ...


def strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def repair_truncated_json(text: str) -> str:
    """Best-effort repair for truncated JSON responses (EC-L02)."""
    cleaned = strip_markdown_fences(text)
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError:
        pass

    stack: list[str] = []
    in_string = False
    escape = False
    for char in cleaned:
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            stack.append("}")
        elif char == "[":
            stack.append("]")
        elif char in ("}", "]") and stack and stack[-1] == char:
            stack.pop()

    repaired = cleaned.rstrip().rstrip(",")
    if in_string:
        repaired += '"'
    repaired += "".join(reversed(stack))
    return repaired


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = strip_markdown_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return json.loads(repair_truncated_json(text))


def validate_against_schema(data: dict[str, Any], schema: type[BaseModel] | None) -> dict[str, Any]:
    if schema is None:
        return data
    return schema.model_validate(data).model_dump()


def build_schema_prompt(schema: type[BaseModel] | None) -> str:
    if schema is None:
        return "Respond with valid JSON only."
    return (
        "Respond with valid JSON only matching this schema:\n"
        f"{json.dumps(schema.model_json_schema(), indent=2)}"
    )
