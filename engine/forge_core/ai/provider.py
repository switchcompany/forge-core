"""AI provider — raw httpx calls, zero native dependencies."""

from __future__ import annotations

import os
from typing import Any

import httpx

from forge_core.models.config import AIConfig, AIProvider
from forge_core.utils import logger
from forge_core.utils.tokens import count_tokens

_TIMEOUT = httpx.Timeout(120.0, connect=10.0)
_HEAVY_PHASES = frozenset({"4", "5"})
# Number of retries for transient network errors (total attempts = _RETRY_COUNT + 1)
_RETRY_COUNT = 2


def _get_api_url(config: AIConfig) -> str:
    """Resolve the API base URL."""
    if config.base_url:
        return config.base_url.rstrip("/")
    if config.provider == AIProvider.ANTHROPIC:
        return "https://api.anthropic.com/v1"
    if config.provider == AIProvider.OLLAMA:
        return "http://localhost:11434/v1"
    if config.provider == AIProvider.AZURE:
        return (os.environ.get("AZURE_OPENAI_ENDPOINT", "")).rstrip("/")
    return "https://api.openai.com/v1"


def _get_api_key(config: AIConfig) -> str:
    """Resolve the API key."""
    if config.api_key:
        return config.api_key
    if config.provider == AIProvider.ANTHROPIC:
        return os.environ.get("ANTHROPIC_API_KEY", "")
    if config.provider == AIProvider.AZURE:
        return os.environ.get("AZURE_OPENAI_API_KEY", "")
    if config.provider == AIProvider.OLLAMA:
        return "ollama"
    return os.environ.get("OPENAI_API_KEY", "")


def _resolve_model(config: AIConfig, phase: str = "1") -> str:
    """Resolve the model name. Heavy phases (4, 5) use model_heavy (Opus)."""
    if phase in _HEAVY_PHASES and config.model_heavy:
        return config.model_heavy
    return config.model


def _call_chat_api(
    config: AIConfig,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    json_mode: bool = False,
    phase: str = "1",
    project_id: str = "",
) -> str:
    """Make a raw HTTP POST to the chat completions endpoint."""
    base_url = _get_api_url(config)
    api_key = _get_api_key(config)

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-Forge-Phase": phase,
        "X-Forge-Project-Id": project_id or "",
    }

    # Use retrying POST helper
    resp = _post_with_retries(f"{base_url}/chat/completions", body, headers)
    data = resp.json()
    return data["choices"][0]["message"]["content"] or ""


def _post_with_retries(url: str, json_body: dict[str, Any], headers: dict[str, str]):
    """POST with simple retry loop for transient errors.

    Retries _RETRY_COUNT times on exceptions (network errors, 5xx). Does not sleep
    between attempts to keep tests fast; production may add exponential backoff.
    """
    last_err = None
    attempts = _RETRY_COUNT + 1
    for attempt in range(1, attempts + 1):
        try:
            resp = httpx.post(url, json=json_body, headers=headers, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err = e
            logger.warn(f"HTTP request failed (attempt {attempt}/{attempts}): {e}")
            if attempt == attempts:
                logger.error(f"HTTP request failed after {attempts} attempts: {e}")
                raise
            # try again immediately
            continue


def complete(
    config: AIConfig,
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    max_tokens: int | None = None,
    phase: str = "1",
) -> str:
    """Send a completion request to the configured AI provider."""
    model = _resolve_model(config, phase)
    project_id = getattr(config, "_project_id", "")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    input_tokens = count_tokens(system_prompt + user_prompt, config.model)
    logger.info(f"AI call → {model} [phase {phase}] ({input_tokens} input tokens)")

    try:
        content = _call_chat_api(
            config,
            model,
            messages,
            config.temperature,
            max_tokens or config.max_tokens,
            json_mode,
            phase=phase,
            project_id=project_id,
        )
        output_tokens = count_tokens(content, config.model)
        logger.info(f"AI response ← {output_tokens} output tokens")
        return content
    except Exception as e:
        logger.error(f"AI call failed: {e}")
        raise


def complete_with_fallback(
    config: AIConfig,
    system_prompt: str,
    user_prompt: str,
    fallback_models: list[str] | None = None,
    json_mode: bool = False,
    phase: str = "1",
) -> str:
    """Try primary model, fall back to alternatives on failure."""
    primary = _resolve_model(config, phase)
    models = [primary] + (fallback_models or [])
    project_id = getattr(config, "_project_id", "")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_error = None
    for model in models:
        try:
            return _call_chat_api(
                config,
                model,
                messages,
                config.temperature,
                config.max_tokens,
                json_mode,
                phase=phase,
                project_id=project_id,
            )
        except Exception as e:
            last_error = e
            logger.warn(f"Model {model} failed, trying next: {e}")
            continue

    raise RuntimeError(f"All models failed. Last error: {last_error}")
