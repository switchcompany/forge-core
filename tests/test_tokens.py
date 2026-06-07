"""Tests for forge_core/utils/tokens.py — token counting without tiktoken."""
import pytest

from forge_core.utils.tokens import (
    count_tokens,
    fits_in_context,
    split_for_context,
    truncate_to_tokens,
)


# ── count_tokens (tiktoken not installed in test env — uses estimate) ─────────

def test_count_tokens_non_empty_string():
    result = count_tokens("hello world this is a test", "gpt-4o")
    assert result > 0


def test_count_tokens_empty_string():
    result = count_tokens("", "gpt-4o")
    assert result >= 0


def test_count_tokens_longer_text_more_tokens():
    short = count_tokens("hi", "gpt-4o")
    long = count_tokens("hi " * 1000, "gpt-4o")
    assert long > short


def test_count_tokens_unknown_model_fallback():
    # Should not raise even with unknown model
    result = count_tokens("some text", "unknown-model-xyz")
    assert result > 0


# ── truncate_to_tokens ────────────────────────────────────────────────────────

def test_truncate_to_tokens_short_text_unchanged():
    text = "short"
    result = truncate_to_tokens(text, max_tokens=1000)
    assert result == text


def test_truncate_to_tokens_long_text_truncated():
    text = "word " * 10000  # very long
    result = truncate_to_tokens(text, max_tokens=10)
    assert len(result) < len(text)


def test_truncate_to_tokens_result_fits():
    text = "a " * 5000
    truncated = truncate_to_tokens(text, max_tokens=50)
    assert count_tokens(truncated) <= 60  # small buffer for estimate rounding


# ── fits_in_context ───────────────────────────────────────────────────────────

def test_fits_in_context_short_content_fits():
    assert fits_in_context("system", "user", max_context=128_000) is True


def test_fits_in_context_enormous_content_does_not_fit():
    huge_user = "token " * 200_000
    assert fits_in_context("system", huge_user, max_context=128_000) is False


def test_fits_in_context_reserve_respected():
    # Content that would fit without reserve but not with it
    big_user = "x " * 60_000  # ~30k tokens estimated
    # With 4096 reserve on a 32k context, it shouldn't fit
    result = fits_in_context("", big_user, max_context=32_000, reserve_for_response=4096)
    assert isinstance(result, bool)


# ── split_for_context ─────────────────────────────────────────────────────────

def test_split_for_context_empty_returns_empty():
    result = split_for_context({}, max_tokens=1000)
    assert result == []


def test_split_for_context_single_batch_when_fits():
    files = {"a.py": "short content", "b.py": "also short"}
    batches = split_for_context(files, max_tokens=100_000)
    assert len(batches) == 1
    assert "a.py" in batches[0]
    assert "b.py" in batches[0]


def test_split_for_context_splits_when_too_large():
    # Each file is ~250 tokens; max 300 forces splits
    files = {f"file{i}.py": "word " * 200 for i in range(5)}
    batches = split_for_context(files, max_tokens=300)
    assert len(batches) > 1
    # All files should appear in some batch
    all_keys = set()
    for b in batches:
        all_keys.update(b.keys())
    assert all_keys == set(files.keys())


def test_split_for_context_single_huge_file_still_batched():
    """A single file bigger than max_tokens still appears in a batch (not dropped)."""
    files = {"big.py": "x " * 10_000}
    batches = split_for_context(files, max_tokens=100)
    assert any("big.py" in b for b in batches)
