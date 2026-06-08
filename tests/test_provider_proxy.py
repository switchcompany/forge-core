import pytest

from forge_core.models.config import AIConfig, AIProvider
from forge_core.ai import provider


class DummyResponse:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def test_provider_uses_saas_proxy_and_passes_headers(monkeypatch):
    calls = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        calls['url'] = url
        calls['json'] = json
        calls['headers'] = headers
        return DummyResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(provider.httpx, 'post', fake_post)

    cfg = AIConfig(api_key='saas-token', base_url='https://theswitchcompany.online/api/v1/ai', provider=AIProvider.AUTO)
    result = provider.complete(cfg, 'SYS', 'USER', phase='1')

    assert result == 'ok'
    assert calls['url'].endswith('/chat/completions')
    assert calls['headers']['Authorization'] == 'Bearer saas-token'
    assert calls['headers']['X-Forge-Phase'] == '1'


def test_provider_routes_to_heavy_model_on_phase(monkeypatch):
    calls = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        calls['json'] = json
        return DummyResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(provider.httpx, 'post', fake_post)

    cfg = AIConfig(api_key='t', model='sonnet', model_heavy='opus')
    res = provider.complete(cfg, 's', 'u', phase='4')
    assert res == 'ok'
    assert calls['json']['model'] == 'opus'
