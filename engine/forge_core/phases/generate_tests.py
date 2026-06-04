"""Phase 5 — Iterative test generation with journey-weighted prioritization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from forge_core.ai.prompts import build_file_context, load_prompt
from forge_core.ai.provider import complete
from forge_core.core.agent_manager import AgentManager
from forge_core.core.coverage import run_coverage
from forge_core.core.file_manager import FileManager
from forge_core.models.config import ForgeConfig
from forge_core.models.dto import DTORegistry
from forge_core.models.project import Component, ProjectGraph
from forge_core.models.test_result import IterationResult, TestFileResult
from forge_core.templates.template_engine import TemplateEngine, TemplateTest
from forge_core.utils import logger
from forge_core.utils.pattern_cache import PatternCache


@dataclass
class GenerationResult:
    """Aggregate result of the generation loop."""

    iterations: list[IterationResult] = field(default_factory=list)
    total_tests_generated: int = 0
    template_tests_generated: int = 0


def run(
    config: ForgeConfig,
    file_manager: FileManager,
    prompts_dir: Path,
    project_graph: ProjectGraph,
    dto_registry: DTORegistry,
    agent_manager: AgentManager,
    baseline_coverage: float,
    learnings: str = "",
) -> GenerationResult:
    """Run the iterative test generation loop (Phase 5A + 5B)."""
    result = GenerationResult()
    tech = project_graph.tech_stack

    all_targets = _prioritize_targets(project_graph)
    if not all_targets:
        logger.warn("No generation targets found")
        return result

    simple_targets = [t for t in all_targets if not t.requires_complex_mocking]
    complex_targets = [t for t in all_targets if t.requires_complex_mocking]
    logger.info(
        f"Targets: {len(all_targets)} total "
        f"({len(simple_targets)} simple [5A], {len(complex_targets)} complex [5B])"
    )

    write_prompt = load_prompt(prompts_dir, "write-unit-tests")
    system_prompt = write_prompt or (
        "You are a backend test engineer. Write unit tests for the given source code.\n"
        "Rules: idiomatic tests, proper mocking, no production code changes.\n"
        "Return JSON with test_files: [{path, content}]."
    )

    if learnings:
        system_prompt += f"\n\nPast learnings:\n{learnings[:2000]}"

    if dto_registry.count > 0:
        dto_context = _build_dto_context(dto_registry)
        system_prompt += f"\n\nDTO Registry (use these exact constructors):\n{dto_context}"

    pattern_cache = PatternCache(config.project_path)
    pattern_context = pattern_cache.build_context_string(tech.language, tech.framework)
    if pattern_context:
        system_prompt += f"\n\n{pattern_context}"
        logger.info("Pattern cache: loaded proven patterns into context")

    template_engine = TemplateEngine()

    current_coverage = baseline_coverage
    best_coverage = baseline_coverage

    logger.info("Phase 5A: Generating tests for simple targets")
    current_coverage = _run_generation_loop(
        targets=simple_targets,
        phase_label="5A",
        config=config,
        file_manager=file_manager,
        agent_manager=agent_manager,
        tech=tech,
        system_prompt=system_prompt,
        template_engine=template_engine,
        dto_registry=dto_registry,
        result=result,
        current_coverage=current_coverage,
        best_coverage=best_coverage,
    )
    best_coverage = max(best_coverage, current_coverage)

    if current_coverage >= config.target_coverage:
        logger.success(
            f"Phase 5A hit target {config.target_coverage}% — skipping Phase 5B "
            f"(saving ~$0.50/run)"
        )
    elif complex_targets:
        logger.info("Phase 5B: Generating tests for complex targets (MockEngine)")
        current_coverage = _run_generation_loop(
            targets=complex_targets,
            phase_label="5B",
            config=config,
            file_manager=file_manager,
            agent_manager=agent_manager,
            tech=tech,
            system_prompt=system_prompt,
            template_engine=template_engine,
            dto_registry=dto_registry,
            result=result,
            current_coverage=current_coverage,
            best_coverage=best_coverage,
        )
    else:
        logger.info("Phase 5B: No complex targets")

    return result


def _run_generation_loop(
    targets: list,
    phase_label: str,
    config: ForgeConfig,
    file_manager: FileManager,
    agent_manager: AgentManager,
    tech,
    system_prompt: str,
    template_engine: TemplateEngine,
    dto_registry: DTORegistry,
    result: GenerationResult,
    current_coverage: float,
    best_coverage: float,
) -> float:
    """Inner generation loop shared by Phase 5A and 5B. Returns final coverage."""
    stall_count = 0
    batch_size = 5

    for iteration in range(1, config.max_iterations + 1):
        batch_start = (iteration - 1) * batch_size
        batch_targets = targets[batch_start : batch_start + batch_size]
        if not batch_targets:
            logger.info(
                f"Phase {phase_label}: all targets processed after {iteration - 1} iterations"
            )
            break

        logger.info(
            f"Phase {phase_label} iteration {iteration}: {len(batch_targets)} targets"
        )

        scope_id = f"gen-{phase_label}-iter-{iteration}"
        agent_manager.register(scope_id, [t.file_path for t in batch_targets])

        template_written = 0
        ai_targets = []
        tests_written = 0
        for target in batch_targets:
            if template_engine.can_generate(target):
                tmpl: TemplateTest | None = template_engine.generate(
                    target, dto_registry, tech.language, tech.test_framework
                )
                if tmpl:
                    file_manager.write_file(tmpl.file_path, tmpl.test_code)
                    template_written += 1
                    result.template_tests_generated += 1
                    logger.info(
                        f"Template: {target.name} ({tmpl.pattern_used.value}) — no AI call"
                    )
                    continue
            ai_targets.append(target)

        if template_written:
            logger.info(
                f"Template engine: {template_written} tests written (0 AI tokens)"
            )

        if ai_targets:
            batch_files: dict[str, str] = {}
            for target in ai_targets:
                content = file_manager.read_file(target.file_path)
                if content:
                    batch_files[target.file_path] = content

            file_context = build_file_context(batch_files)

            response = complete(
                config=config.ai,
                system_prompt=system_prompt,
                user_prompt=(
                    f"Write unit tests for these source files.\n\n"
                    f"Language: {tech.language}\n"
                    f"Framework: {tech.framework}\n"
                    f"Test framework: {tech.test_framework}\n"
                    f"Mock library: {tech.mock_library}\n\n"
                    f"{file_context}"
                ),
                json_mode=True,
                max_tokens=8192,
                phase="5",
            )

            iter_result = IterationResult(
                iteration=iteration, coverage_before=current_coverage
            )
            tests_written = _write_generated_tests(response, file_manager, iter_result)

            if tests_written == 0 and template_written == 0:
                agent_manager.record_error(scope_id, "no_tests_generated")
                action = agent_manager.heartbeat(scope_id)
                if action in ("split", "terminate"):
                    logger.warn(f"Agent {scope_id}: {action} — moving to next batch")
                    continue
        else:
            iter_result = IterationResult(
                iteration=iteration, coverage_before=current_coverage
            )

        if template_written > 0 or (ai_targets and tests_written > 0):
            coverage = run_coverage(config.project_path, tech.coverage_command)
            iter_result.coverage_after = coverage.line_coverage
            iter_result.coverage_delta = coverage.line_coverage - current_coverage

            if coverage.line_coverage < best_coverage:
                logger.warn(
                    f"Coverage dropped {best_coverage:.1f}% → {coverage.line_coverage:.1f}% — rolling back"
                )
                file_manager.rollback()
                iter_result.rolled_back = True
            else:
                file_manager.checkpoint()
                agent_manager.record_progress(scope_id)
                if coverage.line_coverage > best_coverage:
                    best_coverage = coverage.line_coverage
                current_coverage = coverage.line_coverage

        agent_manager.complete(scope_id)
        result.iterations.append(iter_result)

        if current_coverage >= config.target_coverage:
            logger.success(
                f"Phase {phase_label}: target {config.target_coverage}% reached!"
            )
            break

        if iter_result.coverage_delta < 0.5:
            stall_count += 1
            if stall_count >= 3:
                logger.warn(f"Phase {phase_label}: coverage stalled — stopping")
                break
        else:
            stall_count = 0

    return current_coverage


def _prioritize_targets(graph: ProjectGraph) -> list[Component]:
    """Build ROI-weighted priority list of components to test.

    ROI scoring (lines coverable per test / complexity):
    - NotImplemented methods: ROI=10 (1-2 lines/test, trivial complexity)
    - Pure logic (mappers/processors): ROI=8 (10-20 lines/test, low complexity)
    - Service delegates: ROI=5 (5-10 lines/test, medium complexity)
    - HTTP-dependent (adapter try/catch): ROI=3 (3-5 lines/test, medium complexity)
    - HTTP-dependent (MockEngine deep): ROI=4 (15-30 lines/test, high complexity)

    Two-phase strategy:
    - Phase A (shallow): Cover method entry points first (quick coverage gains)
    - Phase B (deep): Cover lambda/inner class bodies (requires MockEngine)
    """
    all_components: list[Component] = []

    for module in graph.modules:
        journey_components = set()
        for journey in module.journeys:
            journey_components.update(journey.components)

        for layer in module.layers:
            for comp in layer.components:
                if not comp.is_tested:
                    comp.roi_score = _calculate_roi(comp, layer.name)

                    if comp.name in journey_components:
                        comp.roi_score *= 1.5

                    all_components.append(comp)

    all_components.sort(key=lambda c: c.roi_score, reverse=True)

    return all_components


def _calculate_roi(comp: Component, layer_name: str) -> float:
    """Calculate ROI score for a component based on its characteristics.

    Higher ROI = more lines covered per unit of test-writing effort.
    """
    layer_roi = {
        "repository": 8.0,
        "util": 7.0,
        "service": 5.0,
        "controller": 4.0,
        "middleware": 3.0,
        "config": 1.0,
        "model": 1.0,
    }
    roi = layer_roi.get(layer_name, 4.0)

    if comp.not_implemented_count > 0:
        roi += comp.not_implemented_count * 0.5

    if comp.method_classification == "pure_logic":
        roi *= 1.3
    elif comp.method_classification == "not_implemented":
        roi *= 1.5

    if comp.has_inline_reified:
        roi *= 0.7

    if comp.lambda_lines > 50:
        roi *= 0.8

    return round(roi, 2)


def _build_dto_context(registry: DTORegistry) -> str:
    """Build a compact DTO reference for the system prompt.

    Includes:
    - Construction strategy (@Serializable → Json.decodeFromString)
    - Namespace collision warnings with import aliases
    - Required vs optional params
    """
    lines: list[str] = []

    serializable = registry.serializable_dtos()
    if serializable:
        lines.append(
            f"⚠ {len(serializable)} @Serializable DTOs detected. "
            "Use Json.decodeFromString<Type>(jsonString) instead of direct constructors. "
            "Direct construction causes 'seen0/serializationConstructorMarker' compile errors."
        )
        lines.append("")

    collisions = registry.get_collisions()
    if collisions:
        lines.append("⚠ Namespace collisions — use import aliases:")
        for name, entries in collisions.items():
            for entry in entries:
                alias = (
                    entry.package.replace(".", "_").replace("model_dto_", "")
                    + "_"
                    + name
                )
                lines.append(f"  - {entry.fully_qualified_name} as {alias}")
        lines.append("")

    for entry in list(registry.entries.values())[:50]:
        required = [p for p in entry.params if not p.nullable and not p.default]
        optional = [p for p in entry.params if p.nullable or p.default]

        req_str = ", ".join(f"{p.name}: {p.type}" for p in required)
        opt_count = len(optional)

        strategy = ""
        if entry.construction_strategy == "json_decode":
            strategy = " [USE Json.decodeFromString]"
        elif entry.has_builder:
            strategy = " [USE builder]"

        lines.append(f"- {entry.class_name}({req_str}){strategy}")
        if opt_count:
            lines.append(f"  + {opt_count} optional params")

    return "\n".join(lines)


def _write_generated_tests(
    response: str, file_manager: FileManager, iter_result: IterationResult
) -> int:
    """Parse AI response and write test files. Returns count written."""
    count = 0
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        logger.warn("Failed to parse test generation JSON")
        return 0

    for test in data.get("test_files", []):
        path = test.get("path", "")
        content = test.get("content", "")
        if path and content:
            file_manager.write_file(path, content)
            iter_result.tests_generated.append(
                TestFileResult(
                    file_path=path,
                    test_count=content.count("@Test")
                    + content.count("def test_")
                    + content.count("func Test"),
                )
            )
            count += 1

    return count
