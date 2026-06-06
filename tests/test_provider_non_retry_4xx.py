import pytest

from forge_core.ai import provider
from forge_core.models.config import AIConfig


class DummyResponse:
    def __init__(self, json_data=None, status=400):
        self._json = json_data or {"error": "bad request"}
        self.status_code = status

    def json(self):
        return self._json

    def raise_for_status(self):
        # Simulate httpx.HTTPStatusError by raising it directly
        raise provider.httpx.HTTPStatusError("error", request=None, response=self)


def test_4xx_does_not_retry(monkeypatch):
    calls = {"count": 0}

    def post_4xx(url, json=None, headers=None, timeout=None):
        calls["count"] += 1
        return DummyResponse(status=400)

    monkeypatch.setattr(provider.httpx, "post", post_4xx)
    monkeypatch.setattr(provider.time, "sleep", lambda s: None)

    cfg = AIConfig(api_key="k", base_url="https://example.com/api/v1/ai")
    with pytest.raises(Exception):
        provider.complete(cfg, "s", "u", phase="1")

    assert calls["count"] == 1
