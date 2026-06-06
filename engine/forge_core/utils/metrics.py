"""Simple in-process metrics for Forge Core used in unit tests and telemetry.

This is intentionally lightweight: a thread-safe counter registry that can be
queried by unit tests. Production SaaS should replace this with Prometheus or
another metrics backend and call `emit()` to push metrics.
"""
from __future__ import annotations

from collections import Counter
import threading
from typing import Dict, Any

_lock = threading.Lock()
_counters: Counter = Counter()
_last_error: Dict[str, Any] = {}


def incr(metric: str, amount: int = 1, tags: dict | None = None) -> None:
    key = metric
    if tags:
        # simple tag encoding for in-process keying
        tag_str = ";".join([f"{k}={v}" for k, v in sorted(tags.items())])
        key = f"{metric}|{tag_str}"
    with _lock:
        _counters[key] += amount
    try:
        # best-effort: mirror to Prometheus exporter if available
        from forge_core.utils.metrics_exporter import increment as _prom_inc

        # convert tags to string-keys for Prometheus labels
        _prom_inc(metric, amount, labels=tags)
    except Exception:
        pass


def set_last_error(context: str, error_type: str) -> None:
    with _lock:
        _last_error[context] = error_type


def get_counters() -> Dict[str, int]:
    with _lock:
        return dict(_counters)


def get_last_errors() -> Dict[str, str]:
    with _lock:
        return dict(_last_error)


def reset():
    """Reset all metrics (for tests)."""
    with _lock:
        _counters.clear()
        _last_error.clear()
