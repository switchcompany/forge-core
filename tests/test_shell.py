"""Tests for forge_core/utils/shell.py — subprocess runner."""
import pytest
import sys
from pathlib import Path

from forge_core.utils.shell import ShellResult, run


# ── ShellResult properties ────────────────────────────────────────────────────

def test_shell_result_success_true_on_zero():
    r = ShellResult(command="x", returncode=0, stdout="ok", stderr="")
    assert r.success is True


def test_shell_result_success_false_on_nonzero():
    r = ShellResult(command="x", returncode=1, stdout="", stderr="err")
    assert r.success is False


def test_shell_result_output_combines_stdout_stderr():
    r = ShellResult(command="x", returncode=0, stdout="OUT", stderr="ERR")
    assert "OUT" in r.output
    assert "ERR" in r.output


def test_shell_result_output_empty_when_no_output():
    r = ShellResult(command="x", returncode=0, stdout="", stderr="")
    assert r.output == ""


# ── run ───────────────────────────────────────────────────────────────────────

def test_run_echo_command_success():
    result = run("echo hello")
    assert result.success
    assert "hello" in result.stdout


def test_run_false_command_fails():
    result = run(f"{sys.executable} -c 'import sys; sys.exit(1)'")
    assert not result.success
    assert result.returncode == 1


def test_run_returns_stdout():
    result = run(f"{sys.executable} -c \"print('forge-output')\"")
    assert "forge-output" in result.stdout


def test_run_returns_stderr():
    result = run(f"{sys.executable} -c \"import sys; sys.stderr.write('err-msg')\"")
    assert "err-msg" in result.stderr


def test_run_cwd_is_respected(tmp_path):
    (tmp_path / "marker.txt").write_text("exists", encoding="utf-8")
    result = run(f"{sys.executable} -c \"import os; print(os.listdir('.'))\"", cwd=tmp_path)
    assert "marker.txt" in result.stdout


def test_run_timeout_returns_timeout_result():
    result = run(f"{sys.executable} -c \"import time; time.sleep(60)\"", timeout=1)
    assert not result.success
    assert result.returncode == -1
    assert "TIMEOUT" in result.stderr


def test_run_invalid_command_returns_error():
    result = run("this_command_does_not_exist_at_all_xyzzy_abc")
    assert not result.success
    # Shell may return 127 (command not found) or -1 (exception); both are failures
    assert result.returncode != 0


def test_run_duration_is_set():
    result = run("echo hi")
    assert result.duration_seconds >= 0.0


def test_run_extra_env_passed_to_process():
    result = run(
        f"{sys.executable} -c \"import os; print(os.environ.get('MY_TEST_VAR', 'missing'))\"",
        env={"MY_TEST_VAR": "forge_test_value"},
    )
    assert "forge_test_value" in result.stdout
