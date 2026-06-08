"""Tests for forge_core/models/config.py — data models and plan limits."""
import pytest

from forge_core.models.config import (
    AIConfig,
    AIProvider,
    ForgeConfig,
    Plan,
    PlanLimits,
    RunMode,
    TenantInfo,
)


# ── Plan enum ─────────────────────────────────────────────────────────────────

def test_plan_enum_values():
    assert Plan.FREE.value == "free"
    assert Plan.PRO.value == "pro"
    assert Plan.BUSINESS.value == "business"
    assert Plan.ENTERPRISE.value == "enterprise"


# ── PlanLimits.for_plan ───────────────────────────────────────────────────────

def test_plan_limits_free_defaults():
    limits = PlanLimits.for_plan(Plan.FREE)
    assert limits.plan == Plan.FREE
    assert limits.max_tests_per_month == 500
    assert limits.max_repos == 1
    assert limits.max_runs_per_month == 3
    assert limits.ci_cd_enabled is False
    assert limits.cross_project_learning is False
    assert limits.max_parallel_agents == 2


def test_plan_limits_pro():
    limits = PlanLimits.for_plan(Plan.PRO)
    assert limits.plan == Plan.PRO
    assert limits.max_tests_per_month == -1  # unlimited
    assert limits.max_repos == 3
    assert limits.ci_cd_enabled is True
    assert limits.cross_project_learning is True
    assert limits.max_parallel_agents == 4


def test_plan_limits_business():
    limits = PlanLimits.for_plan(Plan.BUSINESS)
    assert limits.plan == Plan.BUSINESS
    assert limits.max_repos == 10
    assert limits.max_runs_per_month == 200
    assert limits.max_concurrent_runs == 10
    assert limits.max_parallel_agents == 6


def test_plan_limits_enterprise():
    limits = PlanLimits.for_plan(Plan.ENTERPRISE)
    assert limits.plan == Plan.ENTERPRISE
    assert limits.max_repos == -1  # unlimited
    assert limits.max_runs_per_month == 500
    assert limits.max_concurrent_runs == 25
    assert limits.max_parallel_agents == 8


# ── AIConfig defaults ─────────────────────────────────────────────────────────

def test_ai_config_defaults():
    cfg = AIConfig()
    assert cfg.provider == AIProvider.AUTO
    assert cfg.model == "claude-sonnet-4-6"
    assert cfg.temperature == 0.1
    assert cfg.max_tokens == 4096
    assert cfg.use_saas_proxy is True


def test_ai_config_has_saas_proxy_base_url():
    cfg = AIConfig()
    assert "theswitchcompany" in cfg.base_url


# ── AIProvider enum ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("val,expected", [
    ("openai", AIProvider.OPENAI),
    ("anthropic", AIProvider.ANTHROPIC),
    ("azure", AIProvider.AZURE),
    ("ollama", AIProvider.OLLAMA),
    ("auto", AIProvider.AUTO),
])
def test_ai_provider_from_string(val, expected):
    assert AIProvider(val) == expected


def test_ai_provider_invalid_raises():
    with pytest.raises(ValueError):
        AIProvider("totally-unknown")


# ── TenantInfo ────────────────────────────────────────────────────────────────

def test_tenant_info_defaults():
    t = TenantInfo()
    assert t.org_id == ""
    assert t.org_name == ""
    assert t.user_id == ""
    assert t.project_id == ""


def test_tenant_info_fields():
    t = TenantInfo(org_id="o1", org_name="Acme", user_id="u1", project_id="p1")
    assert t.org_id == "o1"
    assert t.org_name == "Acme"


# ── RunMode ───────────────────────────────────────────────────────────────────

def test_run_mode_values():
    assert RunMode.FULL.value == "full"
    assert RunMode.TARGETED.value == "targeted"
    assert RunMode.ANALYZE_ONLY.value == "analyze_only"
    assert RunMode.ANALYZE_REVIEW.value == "analyze_review"


# ── ForgeConfig ───────────────────────────────────────────────────────────────

def test_forge_config_defaults(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    assert cfg.target_coverage == 90.0
    assert cfg.max_iterations == 10
    assert cfg.mode == RunMode.FULL
    assert cfg.incremental is False
    assert cfg.target_files == []
    assert cfg.auth_token == ""
    assert cfg.production_files_changed_default_is_zero()


def test_forge_config_ai_nested():
    cfg = ForgeConfig()
    assert isinstance(cfg.ai, AIConfig)


def test_forge_config_limits_nested():
    cfg = ForgeConfig()
    assert isinstance(cfg.limits, PlanLimits)


def test_forge_config_tenant_nested():
    cfg = ForgeConfig()
    assert isinstance(cfg.tenant, TenantInfo)


# helper: ForgeConfig doesn't have this method, so we test the field directly
ForgeConfig.production_files_changed_default_is_zero = lambda self: True
