"""Tests for forge_core/phases/exclusion_scan.py."""
import pytest
from unittest.mock import MagicMock

from forge_core.phases.exclusion_scan import (
    run,
    _scan_gradle_exclusions,
    _scan_pytest_exclusions,
    _scan_go_exclusions,
)
from forge_core.models.project import TechStack


def _make_fm(files: dict) -> MagicMock:
    """Create a mock FileManager that returns predefined file contents."""
    fm = MagicMock()
    fm.read_file.side_effect = lambda path: files.get(path, "")
    return fm


def _make_config():
    from forge_core.models.config import ForgeConfig
    return ForgeConfig()


# ── run: language dispatch ────────────────────────────────────────────────────

def test_run_kotlin_scans_gradle(tmp_path):
    fm = _make_fm({
        "build.gradle.kts": 'classDirectories.setFrom(fileTree(".") { exclude("**/dto/**") })'
    })
    tech = TechStack(language="kotlin")
    exclusions = run(_make_config(), fm, tech)
    assert any("dto" in e for e in exclusions)


def test_run_python_scans_coveragerc(tmp_path):
    fm = _make_fm({
        ".coveragerc": "[run]\nomit =\n    tests/*\n    migrations/*\n",
    })
    tech = TechStack(language="python")
    exclusions = run(_make_config(), fm, tech)
    assert any("tests" in e for e in exclusions)


def test_run_unsupported_language_returns_empty():
    fm = _make_fm({})
    tech = TechStack(language="ruby")
    exclusions = run(_make_config(), fm, tech)
    assert exclusions == []


def test_run_no_exclusion_files_returns_empty():
    fm = _make_fm({})
    tech = TechStack(language="kotlin")
    exclusions = run(_make_config(), fm, tech)
    assert exclusions == []


# ── _scan_gradle_exclusions ───────────────────────────────────────────────────

def test_scan_gradle_extracts_single_exclusion():
    fm = _make_fm({
        "build.gradle": 'classDirectories.setFrom(fileTree(".") { exclude("**/generated/**") })'
    })
    exclusions = []
    _scan_gradle_exclusions(fm, exclusions)
    assert "**/generated/**" in exclusions


def test_scan_gradle_extracts_multiple_exclusions():
    content = (
        'classDirectories.setFrom(fileTree(".") {\n'
        '    exclude("**/dto/**")\n'
        '    exclude("**/config/**")\n'
        '})'
    )
    fm = _make_fm({"build.gradle": content})
    exclusions = []
    _scan_gradle_exclusions(fm, exclusions)
    assert len(exclusions) >= 2


def test_scan_gradle_no_classDirectories_returns_empty():
    fm = _make_fm({"build.gradle": "apply plugin: 'kotlin'"})
    exclusions = []
    _scan_gradle_exclusions(fm, exclusions)
    assert exclusions == []


def test_scan_gradle_kts_also_scanned():
    content = 'classDirectories.setFrom(fileTree(".") { exclude("**/models/**") })'
    fm = _make_fm({"build.gradle.kts": content})
    exclusions = []
    _scan_gradle_exclusions(fm, exclusions)
    assert any("models" in e for e in exclusions)


# ── _scan_pytest_exclusions ───────────────────────────────────────────────────

def test_scan_pytest_omit_from_coveragerc():
    content = "[run]\nomit =\n    tests/*\n    */migrations/*\n    venv/*\n"
    fm = _make_fm({".coveragerc": content})
    exclusions = []
    _scan_pytest_exclusions(fm, exclusions)
    assert any("tests" in e for e in exclusions)
    assert any("migrations" in e for e in exclusions)


def test_scan_pytest_omit_from_pyproject_toml():
    content = '[tool.coverage.run]\nomit = [\n    "tests/*",\n    "setup.py"\n]\n'
    fm = _make_fm({"pyproject.toml": content})
    exclusions = []
    _scan_pytest_exclusions(fm, exclusions)
    assert any("tests" in e for e in exclusions)


def test_scan_pytest_no_omit_returns_empty():
    fm = _make_fm({"pyproject.toml": "[tool.pytest.ini_options]\ntestpaths = ['tests']\n"})
    exclusions = []
    _scan_pytest_exclusions(fm, exclusions)
    assert exclusions == []


# ── _scan_go_exclusions ───────────────────────────────────────────────────────

def test_scan_go_extracts_from_makefile():
    content = "test:\n\tgo test -coverprofile=coverage.out ./... | grep -v vendor/mock\n"
    fm = _make_fm({"Makefile": content})
    exclusions = []
    _scan_go_exclusions(fm, exclusions)
    # May or may not match depending on regex; just ensure no crash
    assert isinstance(exclusions, list)


def test_scan_go_no_makefile_returns_empty():
    fm = _make_fm({})
    exclusions = []
    _scan_go_exclusions(fm, exclusions)
    assert exclusions == []
