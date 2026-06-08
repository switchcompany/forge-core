"""8-Phase pipeline orchestrator — the heart of Forge Core."""

from __future__ import annotations

import time
from pathlib import Path

from forge_core.ai.prompts import load_learnings
from forge_core.core.agent_manager import AgentManager
from forge_core.core.coverage import run_coverage
from forge_core.core.file_manager import FileManager
from forge_core.models.config import ForgeConfig, RunMode
from forge_core.models.dto import DTORegistry
from forge_core.models.project import ProjectGraph
from forge_core.models.test_result import RunReport
from forge_core.phases import (
    analyze_project,
    audit_tests,
    coverage_report,
    detect_stack,
    exclusion_scan,
    fix_broken,
    generate_tests,
    journey_mapping,
    self_learn,
)
from forge_core.utils import logger
from forge_core.utils.graph_cache import GraphCache


class Orchestrator:
    """Runs the full 8-phase Forge Core pipeline."""

    def __init__(self, config: ForgeConfig):
        self.config = config

        # If an auth_token is present and SaaS proxy usage is enabled,
        # configure AIConfig to point to the central SaaS AI proxy and use
        # the auth token as the API key. This centralizes key management
        # in the SaaS proxy (theswitchcompany-website) and ensures all
        # requests include the required Authorization and phase headers.
        try:
            if getattr(self.config, "auth_token", None) and getattr(self.config, "ai", None) and self.config.ai.use_saas_proxy:
                self.config.ai.base_url = self.config.saas_api_url
                self.config.ai.api_key = self.config.auth_token
        except Exception:
            # Avoid failing construction if config shape is unexpected
            pass

        self.file_manager = FileManager(config.project_path)
        self.agent_manager = AgentManager()
        self.project_graph = ProjectGraph()
        self.dto_registry = DTORegistry()
        self.graph_cache = GraphCache(config.project_path)
        self.report = RunReport(
            project_path=str(config.project_path),
            mode=config.mode.value,
            target_coverage=config.target_coverage,
        )

    def run(self) -> RunReport:
        """Execute the full pipeline and return the run report."""
        start_time = time.time()
        self.report.started_at = __import__("datetime").datetime.now()

        logger.banner("Forge Core v2.0", "AI-Powered Backend Test Generation Engine")

        prompts_dir = Path(self.config.prompts_dir)

        logger.phase_start("-1", "Loading past learnings")
        learnings = load_learnings(
            self.config.central_agent_path or None,
            self.config.project_path,
        )
        if learnings:
            logger.phase_done("-1", f"Loaded {len(learnings)} chars of learnings")
        else:
            logger.phase_done("-1", "No prior learnings found")

        # Incremental mode: load git-hash cache
        if self.config.incremental:
            logger.phase_start("INC", "Loading incremental cache")
            self.graph_cache.load()
            logger.phase_done("INC", "Incremental mode active — only changed files will be analyzed")

        logger.phase_start("1/8", "Detecting tech stack")
        tech_stack = detect_stack.run(
            config=self.config,
            file_manager=self.file_manager,
            prompts_dir=prompts_dir,
        )
        self.project_graph.tech_stack = tech_stack
        self.report.language = tech_stack.language
        self.report.framework = tech_stack.framework
        self.report.project_name = self.config.project_path.name
        logger.phase_done("1/8", f"{tech_stack.language}/{tech_stack.framework} detected")

        logger.phase_start("1.5/8", "Scanning coverage exclusions")
        exclusions = exclusion_scan.run(
            config=self.config,
            file_manager=self.file_manager,
            tech_stack=tech_stack,
        )
        logger.phase_done("1.5/8", f"{len(exclusions)} exclusions found")

        logger.phase_start("2/8", "Analyzing architecture & building project graph")
        self.project_graph = analyze_project.run(
            config=self.config,
            file_manager=self.file_manager,
            prompts_dir=prompts_dir,
            tech_stack=tech_stack,
            learnings=learnings,
        )
        logger.phase_done(
            "2/8",
            f"{len(self.project_graph.modules)} modules, "
            f"{self.project_graph.total_source_files} source files",
        )

        # Incremental mode: filter project graph to only changed files
        if self.config.incremental and self.project_graph.file_infos:
            all_paths = list(self.project_graph.file_infos.keys())
            changed_paths = set(self.graph_cache.get_changed_files(all_paths))
            if len(changed_paths) < len(all_paths):
                # Trim file_infos to changed files only (Phase 2.5 skeleton context auto-respects this)
                self.project_graph.file_infos = {
                    k: v for k, v in self.project_graph.file_infos.items()
                    if k in changed_paths
                }
                # Mark unchanged components as already tested (skip in Phase 5)
                for module in self.project_graph.modules:
                    for layer in module.layers:
                        for comp in layer.components:
                            if comp.file_path not in changed_paths:
                                comp.is_tested = True  # excluded from generation targets
                logger.info(
                    f"Incremental: scoped to {len(changed_paths)}/{len(all_paths)} changed files"
                )

        logger.phase_start("2.5/8", "Mapping journeys & building DTO registry")
        self.dto_registry = journey_mapping.run(
            config=self.config,
            file_manager=self.file_manager,
            prompts_dir=prompts_dir,
            project_graph=self.project_graph,
            learnings=learnings,
        )
        journey_count = sum(len(m.journeys) for m in self.project_graph.modules)
        self.report.journeys_mapped = journey_count
        self.report.dtos_registered = self.dto_registry.count
        logger.phase_done(
            "2.5/8",
            f"{journey_count} journeys mapped, {self.dto_registry.count} DTOs registered",
        )

        if self.config.mode == RunMode.ANALYZE_ONLY:
            logger.success("Analysis complete (analyze-only mode)")
            self.report.duration_seconds = time.time() - start_time
            return self.report

        logger.phase_start("3/8", "Auditing existing tests")
        baseline = audit_tests.run(
            config=self.config,
            file_manager=self.file_manager,
            prompts_dir=prompts_dir,
            project_graph=self.project_graph,
        )
        self.report.coverage_before = baseline.line_coverage
        self.report.total_tests_before = baseline.total_tests
        logger.phase_done(
            "3/8",
            f"Baseline: {baseline.line_coverage:.1f}% coverage, "
            f"{baseline.total_tests} tests ({baseline.tests_failed} failing)",
        )

        if self.config.mode == RunMode.ANALYZE_REVIEW:
            logger.success("Analysis + review complete")
            self.report.duration_seconds = time.time() - start_time
            return self.report

        if baseline.tests_failed > 0:
            logger.phase_start("4/8", "Fixing broken tests")
            fixed_count = fix_broken.run(
                config=self.config,
                file_manager=self.file_manager,
                prompts_dir=prompts_dir,
                project_graph=self.project_graph,
                baseline=baseline,
                learnings=learnings,
            )
            self.report.tests_fixed = fixed_count
            logger.phase_done("4/8", f"Fixed {fixed_count} broken tests")
        else:
            logger.phase_skip("4/8", "No broken tests found")

        post_fix = run_coverage(
            self.config.project_path,
            self.project_graph.tech_stack.coverage_command,
        )
        best_coverage = max(baseline.line_coverage, post_fix.line_coverage)

        logger.phase_start("5/8", "Generating tests (journey-weighted)")

        # FC-006 Phase Gating: block Phase 5 if Phase 2 produced no components
        total_components = sum(
            len(layer.components)
            for module in self.project_graph.modules
            for layer in module.layers
        )
        if total_components == 0:
            logger.warn(
                "Phase 5 BLOCKED — Phase 2 (analyze_project) returned 0 components. "
                "Re-running Phase 2 before proceeding."
            )
            self.project_graph = analyze_project.run(
                config=self.config,
                file_manager=self.file_manager,
                prompts_dir=prompts_dir,
                tech_stack=self.project_graph.tech_stack,
                learnings=learnings,
            )
            total_components = sum(
                len(layer.components)
                for module in self.project_graph.modules
                for layer in module.layers
            )
            if total_components == 0:
                logger.error(
                    "Phase 5 ABORTED — Phase 2 retry also returned 0 components. "
                    "Check project structure and try again."
                )
                self.report.duration_seconds = time.time() - start_time
                return self.report
            logger.phase_done(
                "2/8",
                f"Phase 2 retry: {total_components} components found",
            )

        generation_result = generate_tests.run(
            config=self.config,
            file_manager=self.file_manager,
            prompts_dir=prompts_dir,
            project_graph=self.project_graph,
            dto_registry=self.dto_registry,
            agent_manager=self.agent_manager,
            baseline_coverage=best_coverage,
            learnings=learnings,
        )
        self.report.iterations = generation_result.iterations
        self.report.total_iterations = len(generation_result.iterations)
        self.report.rollbacks = sum(1 for i in generation_result.iterations if i.rolled_back)

        logger.phase_start("6/8", "Generating final coverage report")
        final = coverage_report.run(
            config=self.config,
            project_graph=self.project_graph,
        )
        self.report.coverage_after = final.line_coverage
        self.report.coverage_delta = final.line_coverage - self.report.coverage_before
        self.report.total_tests_after = final.total_tests
        self.report.tests_generated = final.total_tests - self.report.total_tests_before
        logger.phase_done("6/8", f"Final coverage: {final.line_coverage:.1f}%")

        logger.coverage_table(
            self.report.coverage_before,
            self.report.coverage_after,
            self.report.total_tests_before,
            self.report.total_tests_after,
        )

        logger.phase_start("7/8", "Self-learning")
        patterns = self_learn.run(
            config=self.config,
            file_manager=self.file_manager,
            prompts_dir=prompts_dir,
            project_graph=self.project_graph,
            report=self.report,
            learnings=learnings,
        )
        self.report.patterns_discovered = patterns
        logger.phase_done("7/8", f"{patterns} new patterns recorded")

        # Save incremental cache for next run
        for module in self.project_graph.modules:
            for layer in module.layers:
                for component in layer.components:
                    self.graph_cache.update_entry(component.file_path)
        self.graph_cache.save()

        self.report.duration_seconds = time.time() - start_time
        self.report.completed_at = __import__("datetime").datetime.now()
        self.report.production_files_changed = 0

        mins = self.report.duration_seconds / 60
        logger.banner(
            "✅ Forge Core Complete",
            f"{self.report.coverage_before:.1f}% → {self.report.coverage_after:.1f}% "
            f"in {mins:.1f} minutes | "
            f"+{self.report.tests_generated} tests | "
            f"{self.report.patterns_discovered} patterns learned",
        )

        return self.report
