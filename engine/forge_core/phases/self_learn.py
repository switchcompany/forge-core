"""Phase 7 — Self-learning: record patterns to LEARNINGS.md."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from forge_core.ai.prompts import load_prompt
from forge_core.ai.provider import complete
from forge_core.core.file_manager import FileManager
from forge_core.models.config import ForgeConfig
from forge_core.models.project import ProjectGraph
from forge_core.models.test_result import RunReport
from forge_core.utils import logger
from forge_core.utils.pattern_cache import PatternCache


def run(
    config: ForgeConfig,
    file_manager: FileManager,
    prompts_dir: Path,
    project_graph: ProjectGraph,
    report: RunReport,
    learnings: str = "",
) -> int:
    """Record patterns learned from this run. Returns count of new patterns."""
    prompt = load_prompt(prompts_dir, "self-learn")
    system_prompt = prompt or (
        "You are a learning engine. Analyze the test generation run and extract reusable patterns.\n"
        "Focus on: mocking patterns, assertion styles, framework quirks, error patterns.\n"
        "Return JSON with patterns: [{name, description, language, example}]."
    )

    run_summary = (
        f"Project: {report.project_name}\n"
        f"Language: {report.language}, Framework: {report.framework}\n"
        f"Coverage: {report.coverage_before:.1f}% → {report.coverage_after:.1f}%\n"
        f"Tests generated: {report.tests_generated}, Fixed: {report.tests_fixed}\n"
        f"Iterations: {report.total_iterations}, Rollbacks: {report.rollbacks}\n"
        f"Journeys mapped: {report.journeys_mapped}, DTOs: {report.dtos_registered}\n"
    )

    if learnings:
        run_summary += f"\nExisting learnings (don't duplicate):\n{learnings[:3000]}"

    response = complete(
        config=config.ai,
        system_prompt=system_prompt,
        user_prompt=f"Extract patterns from this run:\n\n{run_summary}",
        json_mode=True,
        phase="7",
    )

    new_patterns: list[dict] = []
    try:
        data = json.loads(response)
        new_patterns = data.get("patterns", [])
    except json.JSONDecodeError:
        logger.warn("Failed to parse self-learn response")
        return 0

    if not new_patterns:
        return 0

    # Save patterns to structured cache (for Phase 5 context enrichment)
    pattern_cache = PatternCache(config.project_path)
    cache_added = pattern_cache.add_patterns(
        new_patterns, report.language, report.framework
    )
    logger.info(f"Pattern cache: {cache_added} new patterns saved")

    learnings_path = config.project_path / "LEARNINGS.md"
    _append_learnings(learnings_path, report, new_patterns)

    if config.central_agent_path:
        central_path = Path(config.central_agent_path) / "LEARNINGS.md"
        _append_learnings(central_path, report, new_patterns)

    return len(new_patterns)


def _append_learnings(
    path: Path, report: RunReport, patterns: list[dict]
) -> None:
    """Append new patterns to a LEARNINGS.md file."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""

    section = f"\n\n## Run: {report.project_name} ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n"
    section += f"- Coverage: {report.coverage_before:.1f}% → {report.coverage_after:.1f}%\n"
    section += f"- Language: {report.language}/{report.framework}\n\n"

    for p in patterns:
        name = p.get("name", "Pattern")
        desc = p.get("description", "")
        section += f"### {name}\n{desc}\n\n"

    path.write_text(existing + section, encoding="utf-8")
