"""Tests for forge_core/utils/pattern_cache.py."""
import json
import pytest
from pathlib import Path

from forge_core.utils.pattern_cache import CachedPattern, PatternCache


@pytest.fixture
def cache(tmp_path):
    return PatternCache(tmp_path)


# ── load ──────────────────────────────────────────────────────────────────────

def test_load_no_file_returns_empty(cache):
    result = cache.load()
    assert result == []
    assert cache._loaded is True


def test_load_valid_cache(tmp_path):
    patterns = [
        {
            "trigger": "mock_repo",
            "language": "python",
            "framework": "fastapi",
            "test_pattern": "Use MagicMock for repos",
            "success_count": 3,
            "created_at": "2024-01-01T00:00:00",
            "last_used_at": "2024-01-02T00:00:00",
        }
    ]
    (tmp_path / PatternCache.CACHE_FILE).write_text(json.dumps(patterns), encoding="utf-8")
    pc = PatternCache(tmp_path)
    result = pc.load()
    assert len(result) == 1
    assert result[0].trigger == "mock_repo"
    assert result[0].language == "python"


def test_load_corrupted_file_returns_empty(tmp_path):
    (tmp_path / PatternCache.CACHE_FILE).write_text("{{not json}}", encoding="utf-8")
    pc = PatternCache(tmp_path)
    result = pc.load()
    assert result == []


# ── get_relevant_patterns ─────────────────────────────────────────────────────

def test_get_relevant_patterns_exact_match(cache):
    cache._patterns = [
        CachedPattern("p1", "python", "fastapi", "pattern A"),
        CachedPattern("p2", "kotlin", "ktor", "pattern B"),
    ]
    cache._loaded = True
    result = cache.get_relevant_patterns("python", "fastapi")
    assert len(result) == 1
    assert result[0].trigger == "p1"


def test_get_relevant_patterns_no_cross_language_contamination(cache):
    cache._patterns = [
        CachedPattern("p1", "kotlin", "ktor", "Kotlin pattern"),
    ]
    cache._loaded = True
    result = cache.get_relevant_patterns("python", "fastapi")
    assert result == []


def test_get_relevant_patterns_case_insensitive(cache):
    cache._patterns = [
        CachedPattern("p1", "Python", "FastAPI", "pattern"),
    ]
    cache._loaded = True
    result = cache.get_relevant_patterns("python", "fastapi")
    assert len(result) == 1


def test_get_relevant_patterns_auto_loads_if_not_loaded(cache):
    """First call should trigger load()."""
    result = cache.get_relevant_patterns("go", "gin")
    assert isinstance(result, list)
    assert cache._loaded is True


def test_get_relevant_patterns_empty_cache_returns_empty(cache):
    cache._loaded = True
    assert cache.get_relevant_patterns("java", "spring") == []


# ── add_patterns ──────────────────────────────────────────────────────────────

def test_add_patterns_adds_new(tmp_path):
    pc = PatternCache(tmp_path)
    pc._loaded = True
    new_patterns = [{"name": "mock_http", "description": "Use httpx.MockTransport"}]
    count = pc.add_patterns(new_patterns, "python", "fastapi")
    assert count == 1
    assert any(p.trigger == "mock_http" for p in pc._patterns)


def test_add_patterns_deduplicates_by_trigger(tmp_path):
    pc = PatternCache(tmp_path)
    pc._loaded = True
    pc._patterns = [CachedPattern("mock_http", "python", "fastapi", "existing")]
    new_patterns = [{"name": "mock_http", "description": "duplicate"}]
    count = pc.add_patterns(new_patterns, "python", "fastapi")
    assert count == 0


def test_add_patterns_dedup_is_case_insensitive(tmp_path):
    pc = PatternCache(tmp_path)
    pc._loaded = True
    pc._patterns = [CachedPattern("Mock_Http", "python", "fastapi", "existing")]
    new_patterns = [{"name": "mock_http", "description": "duplicate"}]
    count = pc.add_patterns(new_patterns, "python", "fastapi")
    assert count == 0


def test_add_patterns_skips_missing_name(tmp_path):
    pc = PatternCache(tmp_path)
    pc._loaded = True
    count = pc.add_patterns([{"description": "no name here"}], "python", "fastapi")
    assert count == 0


def test_add_patterns_saves_to_disk(tmp_path):
    pc = PatternCache(tmp_path)
    pc._loaded = True
    pc.add_patterns([{"name": "new_pattern", "description": "desc"}], "go", "gin")
    saved = json.loads((tmp_path / PatternCache.CACHE_FILE).read_text())
    assert any(p["trigger"] == "new_pattern" for p in saved)


def test_add_patterns_accepts_trigger_key_instead_of_name(tmp_path):
    pc = PatternCache(tmp_path)
    pc._loaded = True
    count = pc.add_patterns([{"trigger": "alt_key", "description": "uses trigger key"}], "python", "django")
    assert count == 1


# ── build_context_string ──────────────────────────────────────────────────────

def test_build_context_string_returns_empty_if_no_patterns(cache):
    cache._loaded = True
    result = cache.build_context_string("go", "echo")
    assert result == ""


def test_build_context_string_includes_patterns(cache):
    cache._patterns = [
        CachedPattern("async_mock", "python", "fastapi", "Use AsyncMock for coroutines"),
    ]
    cache._loaded = True
    result = cache.build_context_string("python", "fastapi")
    assert "async_mock" in result
    assert "python/fastapi" in result


def test_build_context_string_caps_at_ten(cache):
    cache._patterns = [
        CachedPattern(f"p{i}", "python", "fastapi", f"pattern {i}")
        for i in range(20)
    ]
    cache._loaded = True
    result = cache.build_context_string("python", "fastapi")
    # Should only show first 10
    assert result.count("- p") <= 10


# ── save ─────────────────────────────────────────────────────────────────────

def test_save_persists_patterns(tmp_path):
    pc = PatternCache(tmp_path)
    pc._patterns = [CachedPattern("t1", "kotlin", "ktor", "test pattern")]
    pc.save()
    data = json.loads((tmp_path / PatternCache.CACHE_FILE).read_text())
    assert len(data) == 1
    assert data[0]["trigger"] == "t1"


def test_save_roundtrip(tmp_path):
    pc = PatternCache(tmp_path)
    pc._patterns = [
        CachedPattern("p1", "go", "gin", "pattern1"),
        CachedPattern("p2", "go", "gin", "pattern2"),
    ]
    pc.save()

    pc2 = PatternCache(tmp_path)
    pc2.load()
    assert len(pc2._patterns) == 2
