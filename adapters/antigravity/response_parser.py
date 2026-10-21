from __future__ import annotations

import json
from typing import Any

from .models import AntigravityResponse


def parse_response(raw_text: str) -> AntigravityResponse:
    """
    Parses the raw text response into an AntigravityResponse.
    Does not use LLMs. Does not hallucinate fields.
    """
    structured_output: dict[str, Any] | None = None

    # Try to find JSON in a code block
    json_str = None
    if "```json" in raw_text:
        parts = raw_text.split("```json")
        if len(parts) > 1:
            json_str = parts[1].split("```")[0].strip()
    elif "```" in raw_text:
        # Maybe just ``` without json
        parts = raw_text.split("```")
        if len(parts) > 1:
            possible_json = parts[1].strip()
            if possible_json.startswith("{") and possible_json.endswith("}"):
                json_str = possible_json

    if json_str:
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                structured_output = parsed
        except json.JSONDecodeError:
            pass

    # Fallback to entire text if it's pure JSON
    if (
        not structured_output
        and raw_text.strip().startswith("{")
        and raw_text.strip().endswith("}")
    ):
        try:
            parsed = json.loads(raw_text.strip())
            if isinstance(parsed, dict):
                structured_output = parsed
        except json.JSONDecodeError:
            pass

    metadata = {}
    if structured_output is None:
        metadata["warnings"] = ["No valid structured JSON output found. Retaining raw_text."]

    return AntigravityResponse(
        raw_text=raw_text,
        structured_output=structured_output,
        metadata=metadata,
    )
