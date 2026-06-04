"""Phase 2 — Analyze project architecture and build project graph.

Smart approach: Static analysis first (0 AI calls), then 1 AI enrichment call.
Old approach sent ALL source code in 100+ batches (100+ AI calls).
Now we parse imports/classes/methods with regex (free), classify layers from
naming conventions, and send a compact summary to AI for validation (1 call).

Result: 106 AI calls → 1 AI call. Same graph quality.
"""

from __future__ import annotations

import json
from pathlib import Path

from forge_core.ai.prompts import load_prompt
from forge_core.ai.provider import complete
from forge_core.core.file_manager import FileManager
from forge_core.core.static_analyzer import (
    FileInfo,
    analyze_statically,
    build_summary_for_ai,
)
from forge_core.models.config import ForgeConfig
from forge_core.models.project import Component, Layer, Module, ProjectGraph, TechStack
from forge_core.utils import logger


def run(
    config: ForgeConfig,
    file_manager: FileManager,
    prompts_dir: Path,
    tech_stack: TechStack,
    learnings: str = "",
) -> ProjectGraph:
    """Analyze the project and build the 4-Level DAG."""
    # Read all source files
    source_root = tech_stack.source_root or "src"
    source_files = file_manager.read_files(f"{source_root}/**/*")
    test_files = file_manager.read_files(f"{tech_stack.test_root or 'src/test'}/**/*")

    # Filter to code files only
    code_extensions = _get_code_extensions(tech_stack.language)
    source_files = {
        k: v for k, v in source_files.items()
        if any(k.endswith(ext) for ext in code_extensions)
    }

    graph = ProjectGraph(
        name=config.project_path.name,
        root_path=str(config.project_path),
        tech_stack=tech_stack,
        total_source_files=len(source_files),
        total_test_files=len(test_files),
    )

    if not source_files:
        logger.warn("No source files found — returning empty graph")
        return graph

    # ── Step 1: Static analysis (0 AI calls) ──
    logger.info(f"Static analysis: parsing {len(source_files)} files...")
    file_infos = analyze_statically(source_files, source_root)
    modules_found = len(set(fi.module for fi in file_infos))
    layers_found = len(set(fi.layer for fi in file_infos))
    logger.info(f"Parsed {len(file_infos)} files → {modules_found} modules, {layers_found} layers")

    graph.file_infos = {fi.path: fi for fi in file_infos}

    # Build graph from static analysis
    all_modules = _build_graph_from_static(file_infos)

    # ── Step 2: AI enrichment (1 call) ──
    summary = build_summary_for_ai(file_infos)
    token_estimate = len(summary) // 4
    logger.info(f"AI enrichment: sending compact summary (~{token_estimate} tokens, 1 call)")

    try:
        enriched = _ai_enrich(config, prompts_dir, tech_stack, summary, learnings)
        if enriched:
            corrections = len(enriched.get("corrections", []))
            _merge_ai_enrichment(all_modules, enriched)
            logger.info(f"AI enrichment applied ({corrections} corrections)")
    except Exception as e:
        logger.warn(f"AI enrichment failed (static analysis is sufficient): {e}")

    graph.modules = list(all_modules.values())
    return graph


def _build_graph_from_static(file_infos: list[FileInfo]) -> dict[str, Module]:
    """Build module/layer/component graph from static analysis results."""
    modules: dict[str, Module] = {}

    for fi in file_infos:
        if fi.module not in modules:
            modules[fi.module] = Module(name=fi.module, path=fi.module)

        mod = modules[fi.module]

        # Find or create layer
        layer = None
        for existing in mod.layers:
            if existing.name == fi.layer:
                layer = existing
                break
        if layer is None:
            layer = Layer(name=fi.layer)
            mod.layers.append(layer)

        # Add component
        comp_name = fi.classes[0] if fi.classes else Path(fi.path).stem
        method_classification = ""
        if fi.not_implemented_methods:
            method_classification = "not_implemented"
        elif fi.method_classifications:
            method_classification = next(iter(fi.method_classifications.values()))

        layer.components.append(
            Component(
                name=comp_name,
                file_path=fi.path,
                layer=fi.layer,
                dependencies=[imp.split(".")[-1] for imp in fi.imports[:20]],
                method_classification=method_classification,
                koin_dependencies=list(fi.koin_dependencies),
                has_inline_reified=fi.has_inline_reified,
                not_implemented_count=len(fi.not_implemented_methods),
                requires_complex_mocking=fi.has_inline_reified,
            )
        )

    return modules


def _ai_enrich(
    config: ForgeConfig,
    prompts_dir: Path,
    tech_stack: TechStack,
    summary: str,
    learnings: str,
) -> dict | None:
    """Single AI call to validate and enrich the static analysis."""
    prompt = load_prompt(prompts_dir, "analyze-project")
    system_prompt = prompt or (
        "You are a software architect. I've already analyzed this codebase statically "
        "and extracted modules, layers, and components. Review my analysis below and:\n"
        "1. Correct any misclassified layers (e.g., a 'service' classified as 'util')\n"
        "2. Identify key dependencies I might have missed\n"
        "3. Suggest which components are highest priority for testing\n\n"
        "Return JSON with: {\"corrections\": [{\"file\": \"path\", \"layer\": \"correct_layer\"}], "
        "\"high_priority_files\": [\"path1\", \"path2\"], "
        "\"notes\": \"architectural observations\"}"
    )

    if learnings:
        system_prompt += f"\n\nPast learnings:\n{learnings[:2000]}"

    response = complete(
        config=config.ai,
        system_prompt=system_prompt,
        user_prompt=(
            f"Here is my static analysis of the project. Review and enrich it.\n\n"
            f"Project: {config.project_path.name}\n"
            f"Language: {tech_stack.language}\n"
            f"Framework: {tech_stack.framework}\n\n"
            f"{summary}"
        ),
        json_mode=True,
        phase="2",
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warn("Could not parse AI enrichment response")
        return None


def _merge_ai_enrichment(
    modules: dict[str, Module],
    enrichment: dict,
) -> None:
    """Apply AI corrections to the static analysis graph."""
    corrections = enrichment.get("corrections", [])
    if not corrections:
        return

    # Build lookup: file_path → (module_name, layer_index, component_index)
    file_lookup: dict[str, tuple[str, int, int]] = {}
    for mod_name, mod in modules.items():
        for li, layer in enumerate(mod.layers):
            for ci, comp in enumerate(layer.components):
                file_lookup[comp.file_path] = (mod_name, li, ci)

    for correction in corrections[:50]:
        file_path = correction.get("file", "")
        new_layer = correction.get("layer", "")
        if not file_path or not new_layer or file_path not in file_lookup:
            continue

        mod_name, li, ci = file_lookup[file_path]
        mod = modules[mod_name]
        comp = mod.layers[li].components[ci]
        old_layer = mod.layers[li]

        # Find or create target layer
        target_layer = None
        for layer in mod.layers:
            if layer.name == new_layer:
                target_layer = layer
                break
        if target_layer is None:
            target_layer = Layer(name=new_layer)
            mod.layers.append(target_layer)

        # Move component if layer actually changed
        if old_layer != target_layer:
            old_layer.components.remove(comp)
            comp.layer = new_layer
            target_layer.components.append(comp)

    # Clean up empty layers
    for mod in modules.values():
        mod.layers = [l for l in mod.layers if l.components]


def _get_code_extensions(language: str) -> list[str]:
    """Get relevant file extensions for a language."""
    ext_map = {
        "kotlin": [".kt", ".kts"],
        "java": [".java"],
        "python": [".py"],
        "go": [".go"],
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx"],
        "rust": [".rs"],
        "csharp": [".cs"],
        "c#": [".cs"],
        "ruby": [".rb"],
        "php": [".php"],
        "c++": [".cpp", ".hpp", ".cc", ".h"],
    }
    return ext_map.get(language.lower(), [".py", ".java", ".kt", ".go", ".ts", ".js"])
