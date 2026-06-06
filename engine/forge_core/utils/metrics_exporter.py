"""Optional Prometheus exporter adapter.

If prometheus_client is installed, expose counters to Prometheus. Otherwise, act
as a no-op to keep the core engine lightweight. Designed for testing and prod
replacement.
"""
from __future__ import annotations

import importlib
from typing import Dict, Any

_prom = None
_counters: Dict[str, Any] = {}

try:
    _prom = importlib.import_module("prometheus_client")
except Exception:
    _prom = None


def register_counter(name: str, description: str, label_names: list[str] | None = None):
    if not _prom:
        return None
    label_names = label_names or []
    if name in _counters:
        return _counters[name]
    if label_names:
        c = _prom.Counter(name, description, labelnames=label_names)
    else:
        c = _prom.Counter(name, description)
    _counters[name] = c
    return c


def increment(name: str, amount: int = 1, labels: Dict[str, str] | None = None):
    if not _prom:
        return
    c = _counters.get(name)
    # Auto-register with label names if labels provided
    if not c:
        label_names = list(labels.keys()) if labels else None
        c = register_counter(name, name, label_names)
        if not c:
            return
    if labels:
        # Ensure labels key order doesn't matter
        c.labels(**labels).inc(amount)
    else:
        c.inc(amount)


def reset_for_tests():
    """Clear registered counters — only for tests."""
    _counters.clear()
