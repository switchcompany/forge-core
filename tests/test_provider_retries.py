import pytest

from forge_core.ai import provider
from forge_core.models.config import AIConfig


class DummyResponse:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def test_post_retries_then_succeed(monkeypatch):
    calls = {"count": 0}

    def flaky_post(url, json=None, headers=None, timeout=None):
        calls["count"] += 1
        if calls["count"] < 3:
            raise Exception("connect error")
        return DummyResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(provider.httpx, "post", flaky_post)
    # Avoid sleeping in tests
    monkeypatch.setattr(provider.time, "sleep", lambda s: None)

    cfg = AIConfig(api_key="k", base_url="https://example.com/api/v1/ai")
    res = provider.complete(cfg, "s", "u", phase="1")
    assert res == "ok"
    assert calls["count"] == 3


def test_post_all_fail_raises(monkeypatch):
    def always_fail(url, json=None, headers=None, timeout=None):
        raise Exception("boom")

    monkeypatch.setattr(provider.httpx, "post", always_fail)
    monkeypatch.setattr(provider.time, "sleep", lambda s: None)

    cfg = AIConfig(api_key="k", base_url="https://example.com/api/v1/ai")
    with pytest.raises(Exception):
        provider.complete(cfg, "s", "u", phase="1")


def test_complete_with_fallback_uses_next_model(monkeypatch):
    called = {"models": []}

    def fake_call(config, model, messages, temperature, max_tokens, json_mode, phase, project_id):
        called["models"].append(model)
        if model == "bad-model":
            raise Exception("model failed")
        return "ok"

    monkeypatch.setattr(provider, "_call_chat_api", fake_call)

    cfg = AIConfig(api_key="k", model="bad-model", model_heavy="good-model")
    res = provider.complete_with_fallback(cfg, "s", "u", fallback_models=["good-model"], phase="1")
    assert res == "ok"
    assert "bad-model" in called["models"] and "good-model" in called["models"]
