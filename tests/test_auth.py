"""Tests for forge_core/auth.py — token persistence and license verification."""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from forge_core.auth import load_auth_token, save_auth_token, verify_license
from forge_core.models.config import ForgeConfig, Plan, PlanLimits


# ── save_auth_token / load_auth_token ─────────────────────────────────────────

def test_save_and_load_auth_token(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    save_auth_token("my-secret-token")
    assert load_auth_token() == "my-secret-token"


def test_save_auth_token_creates_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    save_auth_token("tok")
    assert (tmp_path / ".forge-core").is_dir()


def test_save_auth_token_sets_restrictive_permissions(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    save_auth_token("tok")
    auth_file = tmp_path / ".forge-core" / "auth"
    mode = oct(auth_file.stat().st_mode)[-3:]
    assert mode == "600"


def test_load_auth_token_missing_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = load_auth_token()
    assert result == ""


def test_load_auth_token_strips_whitespace(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    auth_dir = tmp_path / ".forge-core"
    auth_dir.mkdir()
    (auth_dir / "auth").write_text("  token-with-spaces  \n", encoding="utf-8")
    assert load_auth_token() == "token-with-spaces"


# ── verify_license: no token → free tier ─────────────────────────────────────

def test_verify_license_no_token_returns_free(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = ""
    result = verify_license(cfg)
    assert result.limits.plan == Plan.FREE


def test_verify_license_no_token_does_not_call_api(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = ""
    with patch("forge_core.auth.check_license") as mock_check:
        verify_license(cfg)
    mock_check.assert_not_called()


# ── verify_license: failed API check → free tier ─────────────────────────────

def test_verify_license_api_failure_falls_back_to_free(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "some-token"

    with patch("forge_core.auth.check_license", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {}
        result = verify_license(cfg)

    assert result.limits.plan == Plan.FREE


def test_verify_license_exception_falls_back_to_free(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "some-token"

    with patch("forge_core.auth.check_license", side_effect=Exception("network error")):
        result = verify_license(cfg)

    assert result.limits.plan == Plan.FREE


# ── verify_license: plan mapping ─────────────────────────────────────────────

@pytest.mark.parametrize("plan_str,expected_plan", [
    ("pro", Plan.PRO),
    ("business", Plan.BUSINESS),
    ("enterprise", Plan.ENTERPRISE),
    ("free", Plan.FREE),
])
def test_verify_license_applies_plan(tmp_path, plan_str, expected_plan):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "tok"

    license_data = {"plan": plan_str, "org_id": "o1", "org_name": "Acme"}
    with patch("forge_core.auth.check_license", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = license_data
        result = verify_license(cfg)

    assert result.limits.plan == expected_plan


def test_verify_license_unknown_plan_defaults_to_free(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "tok"

    with patch("forge_core.auth.check_license", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {"plan": "unknown-tier"}
        result = verify_license(cfg)

    assert result.limits.plan == Plan.FREE


def test_verify_license_populates_tenant_info(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "tok"

    with patch("forge_core.auth.check_license", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {"plan": "pro", "org_id": "org-123", "org_name": "TestCorp"}
        result = verify_license(cfg)

    assert result.tenant.org_id == "org-123"
    assert result.tenant.org_name == "TestCorp"


def test_verify_license_pro_enables_saas_proxy(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "tok"
    cfg.ai.api_key = ""

    with patch("forge_core.auth.check_license", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {"plan": "pro", "org_id": "o", "org_name": "X"}
        result = verify_license(cfg)

    assert result.ai.use_saas_proxy is True
    assert result.ai.api_key == "tok"


def test_verify_license_enterprise_enables_saas_proxy(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "enterprise-tok"
    cfg.ai.api_key = ""

    with patch("forge_core.auth.check_license", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {"plan": "enterprise", "org_id": "e", "org_name": "BigCorp"}
        result = verify_license(cfg)

    assert result.ai.use_saas_proxy is True
