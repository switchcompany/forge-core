"""Tests for forge_core/config.py — configuration loader."""
import os
import pytest
from pathlib import Path

from forge_core.config import load_config, _load_yml, _load_env
from forge_core.models.config import AIProvider, ForgeConfig


# ── load_config: defaults ─────────────────────────────────────────────────────

def test_load_config_defaults(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg.project_path == tmp_path
    assert cfg.target_coverage == 90.0
    assert cfg.ai.api_key == ""


def test_load_config_sets_prompts_dir(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg.prompts_dir == str(tmp_path / ".github" / "prompts")


# ── load_config: CLI args override everything ─────────────────────────────────

def test_load_config_cli_api_key_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env_key")
    cfg = load_config(tmp_path, api_key="cli_key")
    assert cfg.ai.api_key == "cli_key"


def test_load_config_cli_target_coverage(tmp_path):
    cfg = load_config(tmp_path, target_coverage=85.0)
    assert cfg.target_coverage == 85.0


def test_load_config_cli_model(tmp_path):
    cfg = load_config(tmp_path, model="gpt-4o-mini")
    assert cfg.ai.model == "gpt-4o-mini"


def test_load_config_cli_provider(tmp_path):
    cfg = load_config(tmp_path, provider="openai")
    assert cfg.ai.provider == AIProvider.OPENAI


def test_load_config_cli_auth_token(tmp_path):
    cfg = load_config(tmp_path, auth_token="mytoken")
    assert cfg.auth_token == "mytoken"


def test_load_config_zero_coverage_ignored(tmp_path):
    """target_coverage=0 means not set — keep default."""
    cfg = load_config(tmp_path, target_coverage=0)
    assert cfg.target_coverage == 90.0


# ── _load_yml ─────────────────────────────────────────────────────────────────

def test_load_yml_reads_tenant_fields(tmp_path):
    yml = tmp_path / "agent-config.yml"
    yml.write_text(
        "org_id: org123\norg_name: Acme\nuser_id: u1\nproject_id: p1\n",
        encoding="utf-8",
    )
    cfg = ForgeConfig(project_path=tmp_path)
    _load_yml(cfg, yml)
    assert cfg.tenant.org_id == "org123"
    assert cfg.tenant.org_name == "Acme"
    assert cfg.tenant.user_id == "u1"
    assert cfg.tenant.project_id == "p1"


def test_load_yml_reads_central_agent_path(tmp_path):
    yml = tmp_path / "agent-config.yml"
    yml.write_text("central_agent_path: /shared/agents\n", encoding="utf-8")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_yml(cfg, yml)
    assert cfg.central_agent_path == "/shared/agents"


def test_load_yml_reads_cache_dir(tmp_path):
    yml = tmp_path / "agent-config.yml"
    yml.write_text("cache_dir: .my-cache\n", encoding="utf-8")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_yml(cfg, yml)
    assert cfg.cache_dir == ".my-cache"


def test_load_yml_reads_runtime_provider(tmp_path):
    yml = tmp_path / "agent-config.yml"
    yml.write_text("runtime: anthropic\n", encoding="utf-8")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_yml(cfg, yml)
    assert cfg.ai.provider == AIProvider.ANTHROPIC


def test_load_yml_ignores_auto_runtime(tmp_path):
    yml = tmp_path / "agent-config.yml"
    yml.write_text("runtime: auto\n", encoding="utf-8")
    cfg = ForgeConfig(project_path=tmp_path)
    original_provider = cfg.ai.provider
    _load_yml(cfg, yml)
    assert cfg.ai.provider == original_provider


def test_load_yml_reads_max_parallel_agents(tmp_path):
    yml = tmp_path / "agent-config.yml"
    yml.write_text("max_parallel_agents: 8\n", encoding="utf-8")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_yml(cfg, yml)
    assert cfg.limits.max_parallel_agents == 8


def test_load_yml_invalid_yaml_does_not_raise(tmp_path):
    yml = tmp_path / "agent-config.yml"
    yml.write_text(":: invalid: yaml: {{\n", encoding="utf-8")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_yml(cfg, yml)  # should not raise
    assert cfg.tenant.org_id == ""  # unchanged


def test_load_yml_empty_file_does_not_raise(tmp_path):
    yml = tmp_path / "agent-config.yml"
    yml.write_text("", encoding="utf-8")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_yml(cfg, yml)  # should not raise


def test_load_yml_unknown_runtime_ignored(tmp_path):
    yml = tmp_path / "agent-config.yml"
    yml.write_text("runtime: totally-unknown-provider\n", encoding="utf-8")
    cfg = ForgeConfig(project_path=tmp_path)
    original_provider = cfg.ai.provider
    _load_yml(cfg, yml)  # ValueError is caught internally
    assert cfg.ai.provider == original_provider


# ── _load_env ─────────────────────────────────────────────────────────────────

def test_load_env_openai_key(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_env(cfg)
    assert cfg.ai.api_key == "sk-openai-test"


def test_load_env_anthropic_key_sets_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-testkey")
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.ai.api_key = ""  # ensure not already set
    _load_env(cfg)
    assert cfg.ai.api_key == "sk-ant-testkey"
    assert cfg.ai.provider == AIProvider.ANTHROPIC


def test_load_env_forge_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_API_KEY", "forge-secret-key")
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.ai.api_key = ""
    _load_env(cfg)
    assert cfg.ai.api_key == "forge-secret-key"


def test_load_env_forge_model(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_MODEL", "gpt-4o-mini")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_env(cfg)
    assert cfg.ai.model == "gpt-4o-mini"


def test_load_env_forge_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_PROVIDER", "openai")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_env(cfg)
    assert cfg.ai.provider == AIProvider.OPENAI


def test_load_env_forge_auth_token(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_AUTH_TOKEN", "forge-auth-123")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_env(cfg)
    assert cfg.auth_token == "forge-auth-123"


def test_load_env_switchforge_token(tmp_path, monkeypatch):
    monkeypatch.setenv("SWITCHFORGE_TOKEN", "sw-token-xyz")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_env(cfg)
    assert cfg.auth_token == "sw-token-xyz"


def test_load_env_forge_auth_token_wins_over_switchforge(tmp_path, monkeypatch):
    """FORGE_AUTH_TOKEN takes priority over SWITCHFORGE_TOKEN."""
    monkeypatch.setenv("FORGE_AUTH_TOKEN", "primary")
    monkeypatch.setenv("SWITCHFORGE_TOKEN", "secondary")
    cfg = ForgeConfig(project_path=tmp_path)
    _load_env(cfg)
    assert cfg.auth_token == "primary"


def test_load_env_existing_api_key_not_overwritten(tmp_path, monkeypatch):
    """If api_key is already set, env vars don't overwrite it."""
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.ai.api_key = "already-set"
    _load_env(cfg)
    assert cfg.ai.api_key == "already-set"


def test_load_env_invalid_provider_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_PROVIDER", "badprovider")
    cfg = ForgeConfig(project_path=tmp_path)
    original = cfg.ai.provider
    _load_env(cfg)
    assert cfg.ai.provider == original


# ── load_config: full integration with yml file ───────────────────────────────

def test_load_config_reads_yml_file(tmp_path):
    github_dir = tmp_path / ".github"
    github_dir.mkdir()
    (github_dir / "agent-config.yml").write_text(
        "org_id: test-org\ncentral_agent_path: /agents\n", encoding="utf-8"
    )
    cfg = load_config(tmp_path)
    assert cfg.tenant.org_id == "test-org"
    assert cfg.central_agent_path == "/agents"
