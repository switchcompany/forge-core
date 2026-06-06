from forge_core.utils import metrics
from forge_core.ai import provider
from forge_core.models.config import AIConfig


def test_metrics_incremented_on_retry(monkeypatch):
    metrics.reset()
    calls = {"count": 0}

    def flaky_post(url, json=None, headers=None, timeout=None):
        calls["count"] += 1
        if calls["count"] < 2:
            raise Exception("connect error")
        return type("R", (), {"status_code": 200, "json": lambda self: {"choices": [{"message": {"content": "ok"}}]}, "raise_for_status": lambda self: None})()

    monkeypatch.setattr(provider.httpx, "post", flaky_post)
    monkeypatch.setattr(provider.time, "sleep", lambda s: None)

    cfg = AIConfig(api_key="k", base_url="https://example.com/api/v1/ai")
    res = provider.complete(cfg, "s", "u", phase="1")
    assert res == "ok"

    counters = metrics.get_counters()
    # Expect at least one retry metric key
    assert any(k.startswith("ai_http_retries") for k in counters.keys())


def test_last_error_set_on_failure(monkeypatch):
    metrics.reset()

    def always_fail(url, json=None, headers=None, timeout=None):
        raise ValueError("boom")

    monkeypatch.setattr(provider.httpx, "post", always_fail)
    monkeypatch.setattr(provider.time, "sleep", lambda s: None)

    cfg = AIConfig(api_key="k", base_url="https://example.com/api/v1/ai")
    try:
        provider.complete(cfg, "s", "u", phase="1")
    except Exception:
        pass

    last_errors = metrics.get_last_errors()
    assert last_errors.get("ai_http") == "ValueError"
