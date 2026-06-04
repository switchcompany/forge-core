"""Phase 4 — Fix broken tests."""

from __future__ import annotations

from pathlib import Path

from forge_core.ai.prompts import build_file_context, load_prompt
from forge_core.ai.provider import complete
from forge_core.core.file_manager import FileManager
from forge_core.models.config import ForgeConfig
from forge_core.models.project import ProjectGraph
from forge_core.models.test_result import CoverageReport
from forge_core.utils import logger
from forge_core.utils.shell import run as shell_run


def run(
    config: ForgeConfig,
    file_manager: FileManager,
    prompts_dir: Path,
    project_graph: ProjectGraph,
    baseline: CoverageReport,
    learnings: str = "",
) -> int:
    """Fix broken tests. Returns count of tests fixed."""
    tech = project_graph.tech_stack

    # Run tests to get failure output
    result = shell_run(tech.test_command, cwd=config.project_path, timeout=300)
    if result.success:
        return 0  # No broken tests

    # Read failing test files
    test_root = tech.test_root or "src/test"
    test_files = file_manager.read_files(f"{test_root}/**/*")

    prompt = load_prompt(prompts_dir, "fix-broken-tests")
    system_prompt = prompt or (
        "You are a test repair specialist. Fix the broken tests based on the error output.\n"
        "Rules: never modify production code, never delete passing tests.\n"
        "Return JSON with fixed_files: [{path, content}]."
    )

    if learnings:
        system_prompt += f"\n\nPast learnings:\n{learnings[:2000]}"

    file_context = build_file_context(test_files, max_files=30)

    response = complete(
        config=config.ai,
        system_prompt=system_prompt,
        user_prompt=(
            f"Fix the broken tests. Here is the error output:\n\n"
            f"```\n{result.output[:5000]}\n```\n\n"
            f"Test files:\n{file_context}"
        ),
        json_mode=True,
        phase="4",    # Routes to Opus 4.8 via X-Forge-Phase header
    )

    # Parse and write fixed files
    import json

    fixed_count = 0
    try:
        data = json.loads(response)
        for fix in data.get("fixed_files", []):
            path = fix.get("path", "")
            content = fix.get("content", "")
            if path and content:
                file_manager.write_file(path, content)
                fixed_count += 1
    except json.JSONDecodeError:
        logger.warn("Failed to parse fix response")

    # Verify fixes don't break more tests
    verify = shell_run(tech.test_command, cwd=config.project_path, timeout=300)
    if not verify.success:
        logger.warn("Fixes introduced new failures — rolling back")
        file_manager.rollback()
        return 0

    file_manager.checkpoint()
    return fixed_count
