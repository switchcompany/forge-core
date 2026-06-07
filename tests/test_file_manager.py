"""Tests for forge_core/core/file_manager.py."""
import pytest
from pathlib import Path

from forge_core.core.file_manager import FileManager


@pytest.fixture
def fm(tmp_path):
    return FileManager(tmp_path)


# ── read_file ─────────────────────────────────────────────────────────────────

def test_read_file_existing(fm, tmp_path):
    (tmp_path / "hello.txt").write_text("world", encoding="utf-8")
    assert fm.read_file("hello.txt") == "world"


def test_read_file_missing_returns_empty(fm):
    assert fm.read_file("nonexistent.txt") == ""


def test_read_file_nested_path(fm, tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app", encoding="utf-8")
    assert fm.read_file("src/app.py") == "# app"


# ── read_files ────────────────────────────────────────────────────────────────

def test_read_files_glob_matches(fm, tmp_path):
    (tmp_path / "a.py").write_text("aaa", encoding="utf-8")
    (tmp_path / "b.py").write_text("bbb", encoding="utf-8")
    (tmp_path / "c.txt").write_text("ccc", encoding="utf-8")

    results = fm.read_files("*.py")
    assert "a.py" in results
    assert "b.py" in results
    assert "c.txt" not in results


def test_read_files_returns_relative_paths(fm, tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("x", encoding="utf-8")
    results = fm.read_files("src/*.py")
    assert "src/service.py" in results


def test_read_files_empty_glob_returns_empty(fm):
    assert fm.read_files("*.nonexistent") == {}


def test_read_files_skips_binary_files(fm, tmp_path):
    (tmp_path / "binary.bin").write_bytes(b"\xff\xfe\x00\x01")
    # Should not raise; just skip the unreadable file
    results = fm.read_files("*.bin")
    assert isinstance(results, dict)


# ── write_file ────────────────────────────────────────────────────────────────

def test_write_file_creates_new_file(fm, tmp_path):
    fm.write_file("new_test.py", "content")
    assert (tmp_path / "new_test.py").read_text() == "content"


def test_write_file_creates_parent_dirs(fm, tmp_path):
    fm.write_file("tests/unit/test_service.py", "# test")
    assert (tmp_path / "tests" / "unit" / "test_service.py").exists()


def test_write_file_tracks_new_file_as_none_original(fm, tmp_path):
    fm.write_file("brand_new.py", "hello")
    assert fm._written_files["brand_new.py"] is None


def test_write_file_tracks_existing_file_original(fm, tmp_path):
    (tmp_path / "existing.py").write_text("original", encoding="utf-8")
    fm.write_file("existing.py", "modified")
    assert fm._written_files["existing.py"] == "original"


def test_write_file_only_stores_first_original(fm, tmp_path):
    (tmp_path / "file.py").write_text("v1", encoding="utf-8")
    fm.write_file("file.py", "v2")
    fm.write_file("file.py", "v3")  # second write should not overwrite stored original
    assert fm._written_files["file.py"] == "v1"


# ── rollback ──────────────────────────────────────────────────────────────────

def test_rollback_deletes_new_files(fm, tmp_path):
    fm.write_file("new_file.py", "content")
    assert (tmp_path / "new_file.py").exists()
    count = fm.rollback()
    assert not (tmp_path / "new_file.py").exists()
    assert count == 1


def test_rollback_restores_modified_files(fm, tmp_path):
    (tmp_path / "original.py").write_text("original content", encoding="utf-8")
    fm.write_file("original.py", "modified content")
    fm.rollback()
    assert (tmp_path / "original.py").read_text() == "original content"


def test_rollback_clears_written_files_tracking(fm, tmp_path):
    fm.write_file("temp.py", "x")
    fm.rollback()
    assert fm._written_files == {}


def test_rollback_empty_returns_zero(fm):
    assert fm.rollback() == 0


def test_rollback_handles_mixed_new_and_modified(fm, tmp_path):
    (tmp_path / "mod.py").write_text("original", encoding="utf-8")
    fm.write_file("mod.py", "changed")
    fm.write_file("new.py", "created")

    count = fm.rollback()
    assert count == 2
    assert (tmp_path / "mod.py").read_text() == "original"
    assert not (tmp_path / "new.py").exists()


# ── checkpoint ────────────────────────────────────────────────────────────────

def test_checkpoint_clears_rollback_history(fm, tmp_path):
    fm.write_file("file.py", "content")
    assert fm.pending_rollback_count == 1
    fm.checkpoint()
    assert fm.pending_rollback_count == 0


def test_checkpoint_accepts_state_so_rollback_does_nothing(fm, tmp_path):
    fm.write_file("accepted.py", "content")
    fm.checkpoint()
    count = fm.rollback()
    assert count == 0
    assert (tmp_path / "accepted.py").exists()


# ── list_source_files / list_test_files ───────────────────────────────────────

def test_list_source_files(fm, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text("x", encoding="utf-8")
    (src / "repo.py").write_text("x", encoding="utf-8")

    files = fm.list_source_files("src")
    assert any("service.py" in f for f in files)
    assert any("repo.py" in f for f in files)


def test_list_source_files_nonexistent_root_returns_empty(fm):
    assert fm.list_source_files("nonexistent_dir") == []


def test_list_source_files_excludes_hidden(fm, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / ".hidden").write_text("x", encoding="utf-8")
    (src / "visible.py").write_text("x", encoding="utf-8")

    files = fm.list_source_files("src")
    assert not any(".hidden" in f for f in files)
    assert any("visible.py" in f for f in files)


def test_list_test_files(fm, tmp_path):
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_service.py").write_text("x", encoding="utf-8")

    files = fm.list_test_files("tests")
    assert any("test_service.py" in f for f in files)


def test_list_test_files_nonexistent_returns_empty(fm):
    assert fm.list_test_files("no_tests_here") == []


# ── pending_rollback_count ────────────────────────────────────────────────────

def test_pending_rollback_count_increments(fm, tmp_path):
    assert fm.pending_rollback_count == 0
    fm.write_file("a.py", "a")
    fm.write_file("b.py", "b")
    assert fm.pending_rollback_count == 2


def test_pending_rollback_count_same_file_counted_once(fm, tmp_path):
    fm.write_file("a.py", "v1")
    fm.write_file("a.py", "v2")
    assert fm.pending_rollback_count == 1
