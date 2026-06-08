"""Tests for forge_core/utils/reporter.py — upload_report and check_license."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from forge_core.models.config import ForgeConfig
from forge_core.utils.reporter import check_license, upload_report


# ── upload_report ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_report_no_token_returns_false(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = ""
    result = await upload_report(cfg, {"coverage": 85.0})
    assert result is False


@pytest.mark.asyncio
async def test_upload_report_success_returns_true(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "test-token"
    cfg.saas_api_url = "https://example.com"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"url": "https://example.com/runs/123"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("forge_core.utils.reporter.httpx.AsyncClient", return_value=mock_client):
        result = await upload_report(cfg, {"coverage": 90.0})

    assert result is True


@pytest.mark.asyncio
async def test_upload_report_non_200_returns_false(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "tok"

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("forge_core.utils.reporter.httpx.AsyncClient", return_value=mock_client):
        result = await upload_report(cfg, {})

    assert result is False


@pytest.mark.asyncio
async def test_upload_report_network_error_returns_false(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "tok"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=Exception("connection refused"))

    with patch("forge_core.utils.reporter.httpx.AsyncClient", return_value=mock_client):
        result = await upload_report(cfg, {})

    assert result is False


@pytest.mark.asyncio
async def test_upload_report_sends_correct_payload(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "tok"
    cfg.tenant.org_id = "org-1"
    cfg.tenant.user_id = "user-1"
    cfg.tenant.project_id = "proj-1"

    captured = {}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"url": "https://x.com/r/1"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    async def capture_post(url, json=None, headers=None):
        captured["json"] = json
        return mock_response

    mock_client.post = capture_post

    with patch("forge_core.utils.reporter.httpx.AsyncClient", return_value=mock_client):
        await upload_report(cfg, {"coverage": 75.0})

    assert captured["json"]["org_id"] == "org-1"
    assert captured["json"]["user_id"] == "user-1"
    assert captured["json"]["report"]["coverage"] == 75.0


# ── check_license ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_license_no_token_returns_empty(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = ""
    result = await check_license(cfg)
    assert result == {}


@pytest.mark.asyncio
async def test_check_license_success_returns_plan_data(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "tok"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"plan": "pro", "org_id": "o1"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("forge_core.utils.reporter.httpx.AsyncClient", return_value=mock_client):
        result = await check_license(cfg)

    assert result["plan"] == "pro"
    assert result["org_id"] == "o1"


@pytest.mark.asyncio
async def test_check_license_non_200_returns_empty(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "tok"

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("forge_core.utils.reporter.httpx.AsyncClient", return_value=mock_client):
        result = await check_license(cfg)

    assert result == {}


@pytest.mark.asyncio
async def test_check_license_network_error_returns_empty(tmp_path):
    cfg = ForgeConfig(project_path=tmp_path)
    cfg.auth_token = "tok"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=Exception("timeout"))

    with patch("forge_core.utils.reporter.httpx.AsyncClient", return_value=mock_client):
        result = await check_license(cfg)

    assert result == {}
