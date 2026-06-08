"""Tests for forge_core/core/coverage.py — report parsers and test count extraction."""
import csv
import io
import pytest
import xml.etree.ElementTree as ET
from pathlib import Path

from forge_core.core.coverage import (
    _parse_jacoco_csv,
    _parse_jacoco_xml,
    _try_parse_cobertura,
    _try_parse_go_cover,
    _try_parse_lcov,
    _try_parse_pytest_cov,
    _try_parse_generic,
    _parse_test_counts,
)
from forge_core.models.test_result import CoverageReport


def empty_report():
    return CoverageReport()


# ── _try_parse_pytest_cov ─────────────────────────────────────────────────────

def test_pytest_cov_extracts_total_line():
    output = (
        "Name                      Stmts   Miss  Cover\n"
        "---------------------------------------------------\n"
        "app/service.py               50     10    80%\n"
        "TOTAL                       150     30    80%\n"
    )
    report = _try_parse_pytest_cov(output, empty_report())
    assert report.line_coverage == 80.0


def test_pytest_cov_no_total_unchanged():
    report = _try_parse_pytest_cov("no coverage info here", empty_report())
    assert report.line_coverage == 0.0


def test_pytest_cov_100_percent():
    output = "TOTAL                       50      0   100%\n"
    report = _try_parse_pytest_cov(output, empty_report())
    assert report.line_coverage == 100.0


# ── _try_parse_go_cover ───────────────────────────────────────────────────────

def test_go_cover_extracts_percentage():
    output = "ok  \tgithub.com/example/app\t0.453s\ncoverage: 73.2% of statements\n"
    report = _try_parse_go_cover(output, empty_report())
    assert report.line_coverage == 73.2


def test_go_cover_no_match_unchanged():
    report = _try_parse_go_cover("FAIL\tgithub.com/example/app", empty_report())
    assert report.line_coverage == 0.0


# ── _try_parse_generic ────────────────────────────────────────────────────────

@pytest.mark.parametrize("output,expected", [
    ("line coverage: 65.3%", 65.3),
    ("statement coverage: 70.0%", 70.0),
    ("code coverage: 88%", 88.0),
    ("Total: 91.5%", 91.5),
    ("55.2% line coverage", 55.2),
])
def test_generic_parser_various_formats(output, expected):
    report = _try_parse_generic(output, empty_report())
    assert report.line_coverage == expected


def test_generic_parser_no_match_unchanged():
    report = _try_parse_generic("Build successful", empty_report())
    assert report.line_coverage == 0.0


# ── _parse_jacoco_csv ─────────────────────────────────────────────────────────

def test_parse_jacoco_csv_basic(tmp_path):
    csv_file = tmp_path / "jacoco.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["GROUP", "PACKAGE", "CLASS", "LINE_MISSED", "LINE_COVERED"])
        writer.writeheader()
        writer.writerow({"GROUP": "g", "PACKAGE": "com/example", "CLASS": "Service", "LINE_MISSED": "20", "LINE_COVERED": "80"})
        writer.writerow({"GROUP": "g", "PACKAGE": "com/example", "CLASS": "Repo", "LINE_MISSED": "10", "LINE_COVERED": "40"})

    report = _parse_jacoco_csv(csv_file, empty_report())
    assert report.total_lines == 150  # 20+80+10+40
    assert report.total_lines_covered == 120  # 80+40
    assert report.line_coverage == 80.0


def test_parse_jacoco_csv_zero_lines(tmp_path):
    csv_file = tmp_path / "jacoco.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["GROUP", "PACKAGE", "CLASS", "LINE_MISSED", "LINE_COVERED"])
        writer.writeheader()
        writer.writerow({"GROUP": "g", "PACKAGE": "x", "CLASS": "Empty", "LINE_MISSED": "0", "LINE_COVERED": "0"})

    report = _parse_jacoco_csv(csv_file, empty_report())
    assert report.line_coverage == 0.0


def test_parse_jacoco_csv_builds_file_entries(tmp_path):
    csv_file = tmp_path / "jacoco.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["GROUP", "PACKAGE", "CLASS", "LINE_MISSED", "LINE_COVERED"])
        writer.writeheader()
        writer.writerow({"GROUP": "g", "PACKAGE": "com/app", "CLASS": "Svc", "LINE_MISSED": "5", "LINE_COVERED": "45"})

    report = _parse_jacoco_csv(csv_file, empty_report())
    assert len(report.files) == 1
    assert report.files[0].line_coverage == 90.0


# ── _parse_jacoco_xml ─────────────────────────────────────────────────────────

def test_parse_jacoco_xml_extracts_line_counter(tmp_path):
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE report PUBLIC "-//JACOCO//DTD Report 1.1//EN" "report.dtd">
<report name="test">
  <counter type="INSTRUCTION" missed="10" covered="90"/>
  <counter type="LINE" missed="15" covered="85"/>
  <counter type="BRANCH" missed="5" covered="15"/>
</report>"""
    xml_file = tmp_path / "jacoco.xml"
    xml_file.write_text(xml_content, encoding="utf-8")

    report = _parse_jacoco_xml(xml_file, empty_report())
    assert report.total_lines == 100
    assert report.total_lines_covered == 85
    assert report.line_coverage == 85.0


def test_parse_jacoco_xml_no_line_counter_unchanged(tmp_path):
    xml_content = '<report name="test"><counter type="INSTRUCTION" missed="5" covered="95"/></report>'
    xml_file = tmp_path / "jacoco.xml"
    xml_file.write_text(xml_content, encoding="utf-8")

    report = _parse_jacoco_xml(xml_file, empty_report())
    assert report.line_coverage == 0.0


# ── _try_parse_cobertura ──────────────────────────────────────────────────────

def test_try_parse_cobertura_extracts_line_rate(tmp_path):
    xml_content = '<coverage line-rate="0.875" branch-rate="0.5" version="1.0"></coverage>'
    (tmp_path / "coverage.xml").write_text(xml_content, encoding="utf-8")

    report = _try_parse_cobertura(tmp_path, empty_report())
    assert report.line_coverage == 87.5


def test_try_parse_cobertura_missing_file_unchanged(tmp_path):
    report = _try_parse_cobertura(tmp_path, empty_report())
    assert report.line_coverage == 0.0


# ── _try_parse_lcov ───────────────────────────────────────────────────────────

def test_try_parse_lcov_extracts_lf_lh(tmp_path):
    lcov_content = (
        "SF:src/app.js\n"
        "LF:100\n"
        "LH:75\n"
        "end_of_record\n"
        "SF:src/util.js\n"
        "LF:50\n"
        "LH:50\n"
        "end_of_record\n"
    )
    coverage_dir = tmp_path / "coverage"
    coverage_dir.mkdir()
    (coverage_dir / "lcov.info").write_text(lcov_content, encoding="utf-8")

    report = _try_parse_lcov(tmp_path, empty_report())
    assert report.total_lines == 150
    assert report.total_lines_covered == 125
    assert report.line_coverage == pytest.approx(83.3, abs=0.1)


def test_try_parse_lcov_missing_file_unchanged(tmp_path):
    report = _try_parse_lcov(tmp_path, empty_report())
    assert report.line_coverage == 0.0


# ── _parse_test_counts ────────────────────────────────────────────────────────

def test_parse_test_counts_gradle_style():
    output = "27 tests completed, 3 failed"
    counts = _parse_test_counts(output)
    assert counts["total"] == 27
    assert counts["failed"] == 3
    assert counts["passed"] == 24


def test_parse_test_counts_pytest_style():
    output = "15 passed, 2 failed, 1 error in 3.2s"
    counts = _parse_test_counts(output)
    assert counts["passed"] == 15
    assert counts["failed"] == 2


def test_parse_test_counts_pytest_passed_only():
    output = "42 passed in 1.3s"
    counts = _parse_test_counts(output)
    assert counts["passed"] == 42
    assert counts["failed"] == 0
    assert counts["total"] == 42


def test_parse_test_counts_go_style():
    output = "--- PASS: TestGetUser (0.01s)\n--- PASS: TestCreate (0.02s)\n--- FAIL: TestDelete (0.01s)\nok  \tapp/handlers\t0.05s\n"
    counts = _parse_test_counts(output)
    assert counts["passed"] == 2
    assert counts["failed"] == 1


def test_parse_test_counts_empty_output():
    counts = _parse_test_counts("")
    assert counts == {"total": 0, "passed": 0, "failed": 0}
