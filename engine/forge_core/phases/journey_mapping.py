"""Phase 2.5 — Journey mapping & DTO registry building."""

from __future__ import annotations

import json
from pathlib import Path

from forge_core.ai.prompts import build_file_context, build_skeleton_context, load_prompt
from forge_core.ai.provider import complete
from forge_core.core.file_manager import FileManager
from forge_core.models.config import ForgeConfig
from forge_core.models.dto import DTOEntry, DTOParam, DTORegistry
from forge_core.models.project import Journey, ProjectGraph
from forge_core.utils import logger


def run(
    config: ForgeConfig,
    file_manager: FileManager,
    prompts_dir: Path,
    project_graph: ProjectGraph,
    learnings: str = "",
) -> DTORegistry:
    """Map journeys and build the DTO registry."""
    registry = DTORegistry()
    tech = project_graph.tech_stack

    source_root = tech.source_root or "src"
    source_files = file_manager.read_files(f"{source_root}/**/*")
    code_exts = _code_exts(tech.language)
    source_files = {k: v for k, v in source_files.items() if any(k.endswith(e) for e in code_exts)}

    prompt = load_prompt(prompts_dir, "journey-mapping")
    system_prompt = prompt or (
        "You are a senior backend engineer. Trace all user journeys through this codebase.\n"
        "For each journey: identify entry point, trace through all layers, catalog every DTO.\n"
        "Return JSON with journeys and dto_registry."
    )

    if learnings:
        system_prompt += f"\n\nPast learnings:\n{learnings[:2000]}"

    # Use skeleton context if ProjectGraph has file_infos (93% token reduction)
    # Falls back to full file context if file_infos not yet populated
    if project_graph.file_infos:
        file_context = build_skeleton_context(project_graph.file_infos)
        logger.info(f"Using skeleton context: {len(project_graph.file_infos)} files (compressed)")
    else:
        file_context = build_file_context(source_files, max_files=80)
        logger.info(f"Using full file context: {len(source_files)} files")

    response = complete(
        config=config.ai,
        system_prompt=system_prompt,
        user_prompt=(
            f"Trace all user journeys and catalog all DTOs in this project.\n\n"
            f"Project: {config.project_path.name}\n"
            f"Language: {tech.language}\n"
            f"Framework: {tech.framework}\n\n"
            f"{file_context}"
        ),
        json_mode=True,
        max_tokens=8192,
        phase="2.5",
    )

    _parse_journey_response(response, project_graph, registry)

    return registry


def _parse_journey_response(
    response: str, graph: ProjectGraph, registry: DTORegistry
) -> None:
    """Parse AI response into journeys and DTO registry."""
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        logger.warn("Failed to parse journey mapping JSON")
        return

    for j_data in data.get("journeys", []):
        journey = Journey(
            name=j_data.get("name", ""),
            entry_point=j_data.get("entry_point", ""),
            entry_type=j_data.get("entry_type", ""),
            components=j_data.get("components", []),
            priority=j_data.get("priority", 3),
            description=j_data.get("description", ""),
        )
        if graph.modules:
            graph.modules[0].journeys.append(journey)

    for dto_data in data.get("dto_registry", data.get("dtos", [])):
        params = [
            DTOParam(
                name=p.get("name", ""),
                type=p.get("type", ""),
                default=p.get("default", ""),
                nullable=p.get("nullable", False),
            )
            for p in dto_data.get("params", dto_data.get("constructor_params", []))
        ]

        is_serializable = dto_data.get("is_serializable", False)
        construction_strategy = "direct"
        if is_serializable:
            construction_strategy = "json_decode"
        elif dto_data.get("has_builder", False):
            construction_strategy = "builder"
        elif dto_data.get("has_factory", False):
            construction_strategy = "factory"

        entry = DTOEntry(
            class_name=dto_data.get("class_name", dto_data.get("name", "")),
            package=dto_data.get("package", ""),
            file_path=dto_data.get("file_path", ""),
            params=params,
            has_builder=dto_data.get("has_builder", False),
            has_factory=dto_data.get("has_factory", False),
            is_serializable=is_serializable,
            construction_strategy=construction_strategy,
            nested_dtos=dto_data.get("nested_dtos", []),
            used_in_journeys=dto_data.get("used_in_journeys", []),
            used_in_layers=dto_data.get("used_in_layers", []),
        )
        registry.register(entry)


def _code_exts(language: str) -> list[str]:
    ext_map = {
        "kotlin": [".kt"], "java": [".java"], "python": [".py"],
        "go": [".go"], "typescript": [".ts"], "javascript": [".js"],
        "rust": [".rs"], "csharp": [".cs"], "ruby": [".rb"], "php": [".php"],
    }
    return ext_map.get(language.lower(), [".py", ".java", ".kt"])
