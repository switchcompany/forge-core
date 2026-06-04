"""Configuration loader — merges agent-config.yml, env vars, and CLI args."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from forge_core.models.config import AIProvider, ForgeConfig, TenantInfo
from forge_core.utils import logger


def load_config(
    project_path: Path,
    api_key: str = "",
    provider: str = "",
    model: str = "",
    target_coverage: float = 0,
    auth_token: str = "",
) -> ForgeConfig:
    """Load configuration from agent-config.yml, env vars, and CLI overrides.

    Priority: CLI args > env vars > agent-config.yml > defaults.
    """
    config = ForgeConfig(project_path=project_path)

    yml_path = project_path / ".github" / "agent-config.yml"
    if yml_path.exists():
        _load_yml(config, yml_path)

    _load_env(config)

    if api_key:
        config.ai.api_key = api_key
    if provider:
        config.ai.provider = AIProvider(provider)
    if model:
        config.ai.model = model
    if target_coverage > 0:
        config.target_coverage = target_coverage
    if auth_token:
        config.auth_token = auth_token

    config.prompts_dir = str(project_path / ".github" / "prompts")

    return config


def _load_yml(config: ForgeConfig, yml_path: Path) -> None:
    """Load settings from agent-config.yml."""
    try:
        data = yaml.safe_load(yml_path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.warn(f"Failed to parse {yml_path}: {e}")
        return

    if "central_agent_path" in data:
        config.central_agent_path = data["central_agent_path"]
    if "knowledge_packs_dir" in data:
        config.knowledge_packs_dir = data["knowledge_packs_dir"]
    if "cache_dir" in data:
        config.cache_dir = data["cache_dir"]

    config.tenant = TenantInfo(
        org_id=data.get("org_id", ""),
        org_name=data.get("org_name", ""),
        user_id=data.get("user_id", ""),
        project_id=data.get("project_id", ""),
    )

    if "runtime" in data and data["runtime"] != "auto":
        try:
            config.ai.provider = AIProvider(data["runtime"])
        except ValueError:
            pass
    if "max_parallel_agents" in data:
        config.limits.max_parallel_agents = int(data["max_parallel_agents"])


def _load_env(config: ForgeConfig) -> None:
    """Load settings from environment variables."""
    env_map = {
        "FORGE_API_KEY": "api_key",
        "OPENAI_API_KEY": "api_key",
        "ANTHROPIC_API_KEY": "api_key",
        "FORGE_MODEL": "model",
        "FORGE_PROVIDER": "provider",
        "FORGE_AUTH_TOKEN": "auth_token",
    }

    for env_var, field in env_map.items():
        value = os.environ.get(env_var, "")
        if not value:
            continue

        if field == "api_key" and not config.ai.api_key:
            config.ai.api_key = value
            # Auto-detect provider from key prefix
            if env_var == "ANTHROPIC_API_KEY" or value.startswith("sk-ant-"):
                config.ai.provider = AIProvider.ANTHROPIC
                if config.ai.model == "claude-sonnet-4-6":
                    pass
                elif config.ai.model in ("gpt-4o", ""):
                    config.ai.model = "claude-sonnet-4-6"
                    config.ai.model_heavy = "claude-opus-4-8"
        elif field == "model":
            config.ai.model = value
        elif field == "provider":
            try:
                config.ai.provider = AIProvider(value)
            except ValueError:
                pass
        elif field == "auth_token":
            config.auth_token = value

    # SwitchForge auth token
    switchforge_token = os.environ.get("SWITCHFORGE_TOKEN", "")
    if switchforge_token and not config.auth_token:
        config.auth_token = switchforge_token
