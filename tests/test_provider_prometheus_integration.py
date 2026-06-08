import sys
from types import SimpleNamespace

# Fake prometheus client
class FakeCounter:
    def __init__(self, name, desc, labelnames=None):
        self.name = name
        self.labelnames = labelnames or []
        self.calls = []

    def labels(self, **kwargs):
        # return self for chaining
        self.calls.append(('labels', kwargs))
        return self

    def inc(self, amount=1):
        self.calls.append(('inc', amount))


def test_provider_emits_prometheus_metrics(monkeypatch):
    fake_prom = SimpleNamespace(Counter=FakeCounter)
    sys.modules['prometheus_client'] = fake_prom

    # reload exporter
    from importlib import reload
    from forge_core.utils import metrics_exporter
    reload(metrics_exporter)
    metrics_exporter.reset_for_tests()

    # Set up a flaky post that fails once then succeeds
    from forge_core.ai import provider
    calls = {'n': 0}

    def flaky_post(url, json=None, headers=None, timeout=None):
        calls['n'] += 1
        if calls['n'] < 2:
            raise Exception('connect')
        return type('R', (), {'status_code': 200, 'json': lambda self: {'choices': [{'message': {'content': 'ok'}}]}, 'raise_for_status': lambda self: None})()

    monkeypatch.setattr(provider.httpx, 'post', flaky_post)
    monkeypatch.setattr(provider.time, 'sleep', lambda s: None)

    from forge_core.models.config import AIConfig
    cfg = AIConfig(api_key='k', base_url='https://example.com')
    res = provider.complete(cfg, 's', 'u', phase='1')
    assert res == 'ok'

    # Verify that exporter registered a counter and inc was called
    # The exporter stores counters in its _counters dict
    cdict = metrics_exporter.__dict__['_counters']
    assert 'ai_http_retries' in cdict
    c = cdict['ai_http_retries']
    # FakeCounter should have recorded a labels call and inc call
    assert any(call[0] == 'labels' for call in c.calls)

    del sys.modules['prometheus_client']
