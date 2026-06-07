"""Tests for forge_core/utils/graph_cache.py — incremental analysis cache."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from forge_core.utils.graph_cache import FileCacheEntry, GraphCache


@pytest.fixture
def cache(tmp_path):
    return GraphCache(tmp_path)


# ── load ──────────────────────────────────────────────────────────────────────

def test_load_no_cache_file_returns_empty(cache):
    result = cache.load()
    assert result == {}
    assert cache._loaded is True


def test_load_valid_cache(tmp_path):
    data = {
        "src/Service.kt": {
            "path": "src/Service.kt",
            "git_hash": "abc123",
            "last_analyzed_at": "2024-01-01T00:00:00",
            "coverage_pct": 85.0,
            "tests_count": 10,
        }
    }
    (tmp_path / GraphCache.CACHE_FILE).write_text(json.dumps(data), encoding="utf-8")
    gc = GraphCache(tmp_path)
    result = gc.load()
    assert "src/Service.kt" in result
    assert result["src/Service.kt"].git_hash == "abc123"
    assert result["src/Service.kt"].coverage_pct == 85.0


def test_load_corrupted_cache_returns_empty(tmp_path):
    (tmp_path / GraphCache.CACHE_FILE).write_text("not valid json {{{", encoding="utf-8")
    gc = GraphCache(tmp_path)
    result = gc.load()
    assert result == {}
    assert gc._loaded is True


def test_load_missing_fields_raises_gracefully(tmp_path):
    data = {"src/A.kt": {"path": "src/A.kt"}}  # missing required fields
    (tmp_path / GraphCache.CACHE_FILE).write_text(json.dumps(data), encoding="utf-8")
    gc = GraphCache(tmp_path)
    result = gc.load()
    # corrupted entry should not crash — returns empty
    assert isinstance(result, dict)


# ── save ──────────────────────────────────────────────────────────────────────

def test_save_writes_json(tmp_path):
    gc = GraphCache(tmp_path)
    entry = FileCacheEntry(
        path="src/A.kt",
        git_hash="deadbeef",
        last_analyzed_at="2024-06-01T00:00:00",
        coverage_pct=72.0,
        tests_count=5,
    )
    gc._cache["src/A.kt"] = entry
    gc.save()

    data = json.loads((tmp_path / GraphCache.CACHE_FILE).read_text())
    assert "src/A.kt" in data
    assert data["src/A.kt"]["git_hash"] == "deadbeef"


def test_save_roundtrip(tmp_path):
    gc = GraphCache(tmp_path)
    entry = FileCacheEntry(
        path="src/B.kt",
        git_hash="cafebabe",
        last_analyzed_at="2024-06-01T12:00:00",
        coverage_pct=90.0,
        tests_count=20,
    )
    gc._cache["src/B.kt"] = entry
    gc.save()

    gc2 = GraphCache(tmp_path)
    gc2.load()
    assert "src/B.kt" in gc2._cache
    assert gc2._cache["src/B.kt"].coverage_pct == 90.0


def test_save_with_explicit_entries(tmp_path):
    gc = GraphCache(tmp_path)
    entries = {
        "file.py": FileCacheEntry(
            path="file.py", git_hash="h1",
            last_analyzed_at="2024-01-01T00:00:00"
        )
    }
    gc.save(entries)
    data = json.loads((tmp_path / GraphCache.CACHE_FILE).read_text())
    assert "file.py" in data


# ── get_changed_files ─────────────────────────────────────────────────────────

def test_get_changed_files_new_file_always_changed(cache):
    """A file not in cache is always considered changed."""
    with patch.object(cache, "_get_git_hash", return_value="newhash"):
        changed = cache.get_changed_files(["src/NewFile.kt"])
    assert "src/NewFile.kt" in changed


def test_get_changed_files_same_hash_not_changed(tmp_path):
    gc = GraphCache(tmp_path)
    gc._cache["src/Same.kt"] = FileCacheEntry(
        path="src/Same.kt", git_hash="aabbcc",
        last_analyzed_at="2024-01-01T00:00:00"
    )
    gc._loaded = True
    with patch.object(gc, "_get_git_hash", return_value="aabbcc"):
        changed = gc.get_changed_files(["src/Same.kt"])
    assert "src/Same.kt" not in changed


def test_get_changed_files_different_hash_is_changed(tmp_path):
    gc = GraphCache(tmp_path)
    gc._cache["src/Changed.kt"] = FileCacheEntry(
        path="src/Changed.kt", git_hash="old",
        last_analyzed_at="2024-01-01T00:00:00"
    )
    gc._loaded = True
    with patch.object(gc, "_get_git_hash", return_value="new"):
        changed = gc.get_changed_files(["src/Changed.kt"])
    assert "src/Changed.kt" in changed


def test_get_changed_files_no_git_hash_treated_as_changed(cache):
    cache._loaded = True
    with patch.object(cache, "_get_git_hash", return_value=""):
        changed = cache.get_changed_files(["src/NoGit.kt"])
    assert "src/NoGit.kt" in changed


def test_get_changed_files_auto_loads_if_not_loaded(cache):
    """get_changed_files calls load() if cache not yet loaded."""
    with patch.object(cache, "load", wraps=cache.load) as mock_load, \
         patch.object(cache, "_get_git_hash", return_value="h"):
        cache.get_changed_files(["any.py"])
    mock_load.assert_called_once()


# ── update_entry ──────────────────────────────────────────────────────────────

def test_update_entry_adds_to_cache(cache):
    with patch.object(cache, "_get_git_hash", return_value="myhash"):
        cache.update_entry("src/A.py", coverage_pct=75.0, tests_count=8)
    assert "src/A.py" in cache._cache
    assert cache._cache["src/A.py"].coverage_pct == 75.0
    assert cache._cache["src/A.py"].tests_count == 8
    assert cache._cache["src/A.py"].git_hash == "myhash"


def test_update_entry_no_git_uses_unknown(cache):
    with patch.object(cache, "_get_git_hash", return_value=""):
        cache.update_entry("src/B.py")
    assert cache._cache["src/B.py"].git_hash == "unknown"


def test_update_entry_sets_timestamp(cache):
    with patch.object(cache, "_get_git_hash", return_value="h"):
        cache.update_entry("src/C.py")
    assert cache._cache["src/C.py"].last_analyzed_at != ""
