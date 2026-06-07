"""Load and template .md prompt files for AI consumption."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json

from forge_core.utils import logger


def load_prompt(prompts_dir: Path, prompt_name: str) -> str:
    """Load a prompt .md file from the prompts directory.

    Falls back to packaged prompts bundled with the CLI when the project
    prompts directory does not contain the requested prompt. Does not use
    checksum verification per project preference.

    Args:
        prompts_dir: Path to the prompts directory.
        prompt_name: Name of the prompt file (e.g., 'detect-tech-stack').

    Returns:
        The prompt content as a string, or empty string if not found.
    """
    file_path = prompts_dir / f"{prompt_name}.prompt.md"

    def _load(path: Path) -> str:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warn(f"Failed to read prompt {path}: {e}")
            return ""
        # Strip YAML frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        return content

    if file_path.exists():
        return _load(file_path)

    # Not found in project prompts dir: try packaged prompts bundled with the CLI
    packaged_dir = Path(__file__).parent / "resources" / "prompts"
    packaged_file = packaged_dir / f"{prompt_name}.prompt.md"
    if packaged_file.exists():
        logger.info(f"Prompt {prompt_name} not found in project; using packaged fallback.")
        return _load(packaged_file)

    logger.warn(f"Prompt not found: {file_path} and no packaged fallback available")
    return ""

def template_prompt(prompt: str, variables: dict[str, str]) -> str:
    """Replace template variables in a prompt.

    Variables use {{variable_name}} syntax.
    """
    result = prompt
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def build_file_context(files: dict[str, str], max_files: int = 50) -> str:
    """Build a file context string from a dict of {path: content}.

    Formats each file with clear separators for the AI to parse.
    """
    parts: list[str] = []
    for i, (path, content) in enumerate(files.items()):
        if i >= max_files:
            parts.append(f"\n... and {len(files) - max_files} more files (truncated)")
            break
        parts.append(f"--- {path} ---\n{content}")

    return "\n\n".join(parts)


def build_skeleton_context(file_infos: dict) -> str:
    """Build compressed skeleton context from FileInfo objects.

    Sends only class names + method signatures (~8k tokens) instead of full
    source files (~120k tokens) — 93% token reduction for Phase 2.5 journey mapping.

    Args:
        file_infos: dict of {file_path: FileInfo} from ProjectGraph.file_infos

    Returns:
        Compact skeleton string suitable for journey mapping context.
    """
    parts: list[str] = []
    for file_path, info in file_infos.items():
        lines: list[str] = [f"// {file_path}"]

        for class_name in (getattr(info, "classes", None) or []):
            lines.append(f"class {class_name}")

        for method in (getattr(info, "methods", None) or []):
            lines.append(f"  fun {method}()")

        if getattr(info, "has_inline_reified", False):
            lines.append("  // has inline reified")
        if getattr(info, "has_serializable_dtos", False):
            lines.append("  // has @Serializable DTOs")
        not_impl = getattr(info, "not_implemented_methods", None) or []
        if not_impl:
            lines.append(f"  // NotImplemented: {', '.join(not_impl[:3])}")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def load_learnings(central_path: str | None, local_path: Path | None) -> str:
    """Load LEARNINGS.md from central hub and/or local project."""
    learnings_parts: list[str] = []

    if central_path:
        central_file = Path(central_path) / "LEARNINGS.md"
        if central_file.exists():
            learnings_parts.append(
                f"=== Central Learnings ===\n{central_file.read_text(encoding='utf-8')}"
            )

    if local_path:
        local_file = local_path / "LEARNINGS.md"
        if local_file.exists():
            learnings_parts.append(
                f"=== Project Learnings ===\n{local_file.read_text(encoding='utf-8')}"
            )

    return "\n\n".join(learnings_parts)


def load_knowledge_pack(central_path: str, pack_name: str) -> str:
    """Load a specific knowledge pack (e.g., kotlin-ktor.md)."""
    pack_path = Path(central_path) / "knowledge-packs" / f"{pack_name}.md"
    if pack_path.exists():
        return pack_path.read_text(encoding="utf-8")
    return ""
