"""Structured AI outputs using JSON mode + dataclass parsing."""

from __future__ import annotations

import dataclasses
import json
from typing import Any, TypeVar, get_type_hints

from forge_core.models.config import AIConfig
from forge_core.ai.provider import complete
from forge_core.utils import logger

T = TypeVar("T")


def _schema_from_dataclass(cls: type) -> dict[str, Any]:
    """Generate a minimal JSON schema from a dataclass."""
    hints = get_type_hints(cls)
    properties: dict[str, Any] = {}
    for f in dataclasses.fields(cls):
        hint = hints.get(f.name, str)
        hint_str = str(hint)
        if hint_str.startswith("list") or "list[" in hint_str.lower():
            properties[f.name] = {"type": "array"}
        elif hint_str.startswith("dict") or "dict[" in hint_str.lower():
            properties[f.name] = {"type": "object"}
        elif hint in (int,) or "int" in hint_str:
            properties[f.name] = {"type": "integer"}
        elif hint in (float,):
            properties[f.name] = {"type": "number"}
        elif hint in (bool,):
            properties[f.name] = {"type": "boolean"}
        else:
            properties[f.name] = {"type": "string"}
    return {"type": "object", "properties": properties}


def _dict_to_dataclass(cls: type[T], data: dict[str, Any]) -> T:
    """Recursively convert a dict to a dataclass, handling nested dataclasses."""
    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for f in dataclasses.fields(cls):
        if f.name not in data:
            continue
        val = data[f.name]
        hint = hints.get(f.name)
        # Check if the hint is itself a dataclass
        if dataclasses.is_dataclass(hint) and isinstance(val, dict):
            kwargs[f.name] = _dict_to_dataclass(hint, val)
        elif isinstance(val, list) and val:
            # Try to detect nested dataclass in list
            inner = getattr(hint, "__args__", [None])[0] if hasattr(hint, "__args__") else None
            if inner and dataclasses.is_dataclass(inner):
                kwargs[f.name] = [_dict_to_dataclass(inner, item) if isinstance(item, dict) else item for item in val]
            else:
                kwargs[f.name] = val
        else:
            kwargs[f.name] = val
    return cls(**kwargs)


def extract(
    config: AIConfig,
    system_prompt: str,
    user_prompt: str,
    response_model: type[T],
    max_retries: int = 2,
) -> T:
    """Extract structured data from AI using JSON mode + dataclass.

    Forces the AI to return data matching a dataclass schema.
    Retries on validation failure.
    """
    schema = _schema_from_dataclass(response_model)
    structured_prompt = (
        f"{system_prompt}\n\n"
        f"You MUST respond with valid JSON matching this schema:\n"
        f"```json\n{json.dumps(schema, indent=2)}\n```\n"
        f"Respond ONLY with the JSON object, no other text."
    )

    logger.info(f"Structured extraction → {config.model} → {response_model.__name__}")

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            raw = complete(config, structured_prompt, user_prompt, json_mode=True, phase="1")
            # Strip markdown code fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

            data = json.loads(cleaned)
            result = _dict_to_dataclass(response_model, data)
            logger.success(f"Extracted {response_model.__name__} successfully")
            return result
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warn(f"Extraction attempt {attempt + 1} failed: {e}, retrying...")
            continue

    raise RuntimeError(
        f"Structured extraction failed after {max_retries + 1} attempts: {last_error}"
    )
