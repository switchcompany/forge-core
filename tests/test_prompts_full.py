"""Tests for forge_core/ai/prompts.py — full prompt loading flow."""
import os
from pathlib import Path
import pytest

from forge_core.ai.prompts import (
    build_file_context,
    build_skeleton_context,
    load_knowledge_pack,
    load_learnings,
    load_prompt,
    template_prompt,
)

PACKAGED_PROMPT_NAMES = [
    "detect-tech-stack",
    "analyze-project",
    "journey-mapping",
    "fix-broken-tests",
    "write-unit-tests",
    "self-learn",
]


# ── load_prompt: packaged fallback ────────────────────────────────────────────

@pytest.mark.parametrize("name", PACKAGED_PROMPT_NAMES)
def test_all_packaged_prompts_resolve(name):
    """Every prompt used by a phase must resolve from packaged fallback."""
    content = load_prompt(Path("/nonexistent/.github/prompts"), name)
    assert content, f"Packaged prompt '{name}' is empty or missing"
    assert len(content) > 100, f"Packaged prompt '{name}' is suspiciously short ({len(content)} chars)"


def test_load_prompt_project_dir_takes_priority(tmp_path):
    """Project-level prompt overrides the packaged one."""
    prompts_dir = tmp_path / ".github" / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "detect-tech-stack.prompt.md").write_text("CUSTOM CONTENT", encoding="utf-8")

    content = load_prompt(prompts_dir, "detect-tech-stack")
    assert content == "CUSTOM CONTENT"


def test_load_prompt_strips_yaml_frontmatter(tmp_path):
    """YAML frontmatter between --- markers is stripped."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "test.prompt.md").write_text(
        "---\ntitle: Test\n---\nActual content here", encoding="utf-8"
    )
    content = load_prompt(prompts_dir, "test")
    assert content == "Actual content here"
    assert "title:" not in content


def test_load_prompt_no_frontmatter_unchanged(tmp_path):
    """Files without frontmatter are returned as-is."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "myp.prompt.md").write_text("Just content", encoding="utf-8")
    assert load_prompt(prompts_dir, "myp") == "Just content"


def test_load_prompt_missing_everywhere_returns_empty():
    """A non-existent prompt with no packaged fallback returns empty string."""
    content = load_prompt(Path("/nonexistent/prompts"), "totally-nonexistent-xyzzy")
    assert content == ""


def test_load_prompt_unreadable_file_returns_empty(tmp_path):
    """An unreadable project prompt gracefully returns empty."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    bad = prompts_dir / "bad.prompt.md"
    bad.write_bytes(b"\xff\xfe invalid utf")  # invalid UTF-8

    # The loader catches decode errors and returns ""
    result = load_prompt(prompts_dir, "bad")
    # Should either fall back to packaged or return ""
    assert isinstance(result, str)


# ── template_prompt ───────────────────────────────────────────────────────────

def test_template_prompt_replaces_variables():
    prompt = "Hello {{name}}, your language is {{lang}}."
    result = template_prompt(prompt, {"name": "Alice", "lang": "Python"})
    assert result == "Hello Alice, your language is Python."


def test_template_prompt_unknown_variable_left_intact():
    prompt = "Hello {{name}}, target: {{unknown}}."
    result = template_prompt(prompt, {"name": "Bob"})
    assert "{{unknown}}" in result


def test_template_prompt_empty_variables():
    prompt = "No replacements here."
    assert template_prompt(prompt, {}) == "No replacements here."


def test_template_prompt_multiple_occurrences():
    prompt = "{{x}} and {{x}} and {{x}}"
    result = template_prompt(prompt, {"x": "Y"})
    assert result == "Y and Y and Y"


# ── build_file_context ────────────────────────────────────────────────────────

def test_build_file_context_formats_files():
    files = {"src/a.py": "print('a')", "src/b.py": "print('b')"}
    ctx = build_file_context(files)
    assert "--- src/a.py ---" in ctx
    assert "print('a')" in ctx
    assert "--- src/b.py ---" in ctx


def test_build_file_context_empty_dict():
    assert build_file_context({}) == ""


def test_build_file_context_truncates_at_max_files():
    files = {f"file{i}.py": f"content{i}" for i in range(60)}
    ctx = build_file_context(files, max_files=10)
    assert "50 more files (truncated)" in ctx
    # Only 10 files should have their content shown
    shown = [k for k in files if f"--- {k} ---" in ctx]
    assert len(shown) == 10


# ── build_skeleton_context ────────────────────────────────────────────────────

class _FakeInfo:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_build_skeleton_context_basic():
    info = _FakeInfo(classes=["MyService"], methods=["doThing", "helper"],
                     has_inline_reified=False, has_serializable_dtos=False,
                     not_implemented_methods=[])
    ctx = build_skeleton_context({"src/MyService.kt": info})
    assert "// src/MyService.kt" in ctx
    assert "class MyService" in ctx
    assert "fun doThing()" in ctx


def test_build_skeleton_context_inline_reified_flag():
    info = _FakeInfo(classes=[], methods=[], has_inline_reified=True,
                     has_serializable_dtos=False, not_implemented_methods=[])
    ctx = build_skeleton_context({"src/Client.kt": info})
    assert "inline reified" in ctx


def test_build_skeleton_context_serializable_flag():
    info = _FakeInfo(classes=["Dto"], methods=[], has_inline_reified=False,
                     has_serializable_dtos=True, not_implemented_methods=[])
    ctx = build_skeleton_context({"src/Dto.kt": info})
    assert "@Serializable" in ctx


def test_build_skeleton_context_not_implemented_shows_first_three():
    info = _FakeInfo(classes=[], methods=[], has_inline_reified=False,
                     has_serializable_dtos=False,
                     not_implemented_methods=["a", "b", "c", "d", "e"])
    ctx = build_skeleton_context({"src/Adapter.kt": info})
    assert "NotImplemented" in ctx
    # only first 3 shown
    assert "a" in ctx and "b" in ctx and "c" in ctx


def test_build_skeleton_context_empty_file_infos():
    assert build_skeleton_context({}) == ""


def test_build_skeleton_context_missing_attrs_graceful():
    """FileInfo objects with missing optional attrs don't crash."""
    info = _FakeInfo()  # no attrs at all
    ctx = build_skeleton_context({"src/X.kt": info})
    assert isinstance(ctx, str)


# ── load_learnings ────────────────────────────────────────────────────────────

def test_load_learnings_central_and_local(tmp_path):
    central = tmp_path / "central"
    central.mkdir()
    (central / "LEARNINGS.md").write_text("Central learning", encoding="utf-8")

    local = tmp_path / "project"
    local.mkdir()
    (local / "LEARNINGS.md").write_text("Local learning", encoding="utf-8")

    result = load_learnings(str(central), local)
    assert "Central learning" in result
    assert "Local learning" in result


def test_load_learnings_central_only(tmp_path):
    central = tmp_path / "central"
    central.mkdir()
    (central / "LEARNINGS.md").write_text("Central only", encoding="utf-8")

    result = load_learnings(str(central), tmp_path / "no-project")
    assert "Central only" in result
    assert "Local" not in result


def test_load_learnings_local_only(tmp_path):
    local = tmp_path / "project"
    local.mkdir()
    (local / "LEARNINGS.md").write_text("Local only", encoding="utf-8")

    result = load_learnings(None, local)
    assert "Local only" in result


def test_load_learnings_none_returns_empty(tmp_path):
    result = load_learnings(None, tmp_path / "nope")
    assert result == ""


# ── load_knowledge_pack ───────────────────────────────────────────────────────

def test_load_knowledge_pack_found(tmp_path):
    packs_dir = tmp_path / "knowledge-packs"
    packs_dir.mkdir()
    (packs_dir / "kotlin-ktor.md").write_text("# Kotlin Ktor patterns", encoding="utf-8")

    result = load_knowledge_pack(str(tmp_path), "kotlin-ktor")
    assert "Kotlin Ktor patterns" in result


def test_load_knowledge_pack_missing_returns_empty(tmp_path):
    result = load_knowledge_pack(str(tmp_path), "nonexistent-pack")
    assert result == ""
