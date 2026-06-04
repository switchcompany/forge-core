"""Phase 5b — Auto compile-fix loop."""

from __future__ import annotations

from pathlib import Path

from forge_core.ai.provider import complete
from forge_core.core.file_manager import FileManager
from forge_core.models.config import ForgeConfig
from forge_core.utils import logger
from forge_core.utils.shell import run as shell_run

import json


def fix_compilation_errors(
    config: ForgeConfig,
    file_manager: FileManager,
    test_command: str,
    max_attempts: int = 3,
) -> bool:
    """Attempt to fix compilation errors in generated tests.

    Returns True if tests compile after fixes.
    """
    for attempt in range(1, max_attempts + 1):
        result = shell_run(test_command, cwd=config.project_path, timeout=300)

        if result.success:
            return True

        # Check if it's a compilation error (not a test failure)
        if not _is_compile_error(result.output):
            return True  # Tests compiled but some failed — that's okay

        logger.info(f"Compile-fix attempt {attempt}/{max_attempts}")

        # Ask AI to fix with classified error context
        classified = classify_compile_errors(result.output)
        hints = "\n".join(
            f"- [{e['type']}] {e['fix_hint']}" for e in classified[:10]
        ) if classified else "No specific error classification available."

        response = complete(
            config=config.ai,
            system_prompt=(
                "Fix the compilation errors in these test files. "
                "Return JSON with fixed_files: [{path, content}]. "
                "Only fix imports, types, and syntax — don't change test logic.\n\n"
                "Error hints:\n" + hints
            ),
            user_prompt=f"Compilation errors:\n```\n{result.output[:4000]}\n```",
            json_mode=True,
            phase="5b",  # Routes to Opus — compile debugging requires deep reasoning
        )

        try:
            data = json.loads(response)
            for fix in data.get("fixed_files", []):
                path = fix.get("path", "")
                content = fix.get("content", "")
                if path and content:
                    file_manager.write_file(path, content)
        except json.JSONDecodeError:
            logger.warn("Failed to parse compile-fix response")
            continue

    return False


def _is_compile_error(output: str) -> bool:
    """Detect if the output contains compilation errors (vs test failures)."""
    compile_indicators = [
        "Compilation failed",
        "COMPILE ERROR",
        "error: cannot find symbol",
        "Unresolved reference",
        "SyntaxError",
        "IndentationError",
        "ImportError",
        "ModuleNotFoundError",
        "error TS",
        "cannot resolve",
        "does not exist",
        # Kotlin @Serializable synthetic constructor errors
        "serializationConstructorMarker",
        "seen0",
        "None of the following candidates",
        # Kotlin DTO drift errors
        "No value passed for parameter",
        "Type mismatch: inferred type",
    ]
    return any(indicator.lower() in output.lower() for indicator in compile_indicators)


def classify_compile_errors(output: str) -> list[dict[str, str]]:
    """Classify compilation errors for targeted fixing.

    Returns a list of {type, class_name, detail} dicts to guide the AI fixer.
    Avoids wasting AI tokens on generic "fix everything" prompts.
    """
    errors: list[dict[str, str]] = []
    lines = output.split("\n")

    for line in lines:
        lower = line.lower()

        if "serializationconstructormarker" in lower or "seen0" in lower:
            # @Serializable DTO — must use Json.decodeFromString
            errors.append({
                "type": "serializable_dto",
                "detail": line.strip(),
                "fix_hint": (
                    "This DTO uses @Serializable with a synthetic constructor. "
                    "Replace direct constructor call with: "
                    'Json.decodeFromString<DtoType>("""{"field": "value"}""")'
                ),
            })

        elif "no value passed for parameter" in lower:
            # Missing required DTO parameter
            errors.append({
                "type": "missing_param",
                "detail": line.strip(),
                "fix_hint": "Add the missing required parameter to the constructor call.",
            })

        elif "unresolved reference" in lower:
            # Wrong class name or missing import
            errors.append({
                "type": "unresolved_reference",
                "detail": line.strip(),
                "fix_hint": (
                    "Check for namespace collisions (same DTO name in v1/v2/v3). "
                    "Use import alias or fully qualified name."
                ),
            })

        elif "type mismatch" in lower:
            # Wrong type (e.g., String vs Double across DTO versions)
            errors.append({
                "type": "type_mismatch",
                "detail": line.strip(),
                "fix_hint": (
                    "Check DTO version — same field may have different types in v1 vs v2. "
                    "E.g., promotionSavings is String? in v1 but Double? in v2."
                ),
            })

    return errors
