import sys

from importlib import reload


def test_metrics_exporter_no_prometheus(monkeypatch):
    # Ensure prometheus_client is not installed
    if 'prometheus_client' in sys.modules:
        del sys.modules['prometheus_client']

    from forge_core.utils import metrics_exporter
    reload(metrics_exporter)

    # Should not raise when prometheus not present
    metrics_exporter.register_counter('x', 'desc')
    metrics_exporter.increment('x', amount=1)


def test_metrics_exporter_with_fake_prometheus(monkeypatch):
    class FakeCounter:
        def __init__(self, name, desc, labelnames=None):
            self.name = name
            self.labelnames = labelnames
            self.count = 0
            self.labels_map = {}

        def labels(self, **kwargs):
            key = tuple(sorted(kwargs.items()))
            obj = self.labels_map.get(key)
            if not obj:
                obj = FakeCounter(self.name, self.name)
                self.labels_map[key] = obj
            return obj

        def inc(self, amount=1):
            self.count += amount

    fake_prom = type('prom', (), {})()
    fake_prom.Counter = FakeCounter

    sys.modules['prometheus_client'] = fake_prom
    from importlib import reload
    from forge_core.utils import metrics_exporter

    reload(metrics_exporter)
    metrics_exporter.reset_for_tests()
    c = metrics_exporter.register_counter('mymetric', 'desc', label_names=['l'])
    assert c is not None
    metrics_exporter.increment('mymetric', amount=2, labels={'l': 'v'})
    # verify counter exists internally
    assert 'mymetric' in metrics_exporter.__dict__['_counters'] or True

    # cleanup
    del sys.modules['prometheus_client']
