"""Pattern library cache — stores proven test patterns per language/framework.

READ at Phase 5 start → enriches generation context with proven patterns.
WRITTEN at Phase 7 end → self-learn saves new patterns.
Each org/project owns their own cache — never shared across orgs.
Language-isolated: patterns only matched for exact language+framework combo.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from forge_core.utils import logger


@dataclass
class CachedPattern:
    """A reusable test pattern discovered from previous runs."""

    trigger: str
    language: str
    framework: str
    test_pattern: str
    success_count: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PatternCache:
    """Language-isolated pattern library.

    IMPORTANT: get_relevant_patterns() ONLY returns patterns matching
    exact language + framework. Never mixes patterns across languages.
    """

    CACHE_FILE = ".switchforge_patterns.json"

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._patterns: list[CachedPattern] = []
        self._loaded = False

    def load(self) -> list[CachedPattern]:
        """Load patterns from disk."""
        cache_path = self.project_root / self.CACHE_FILE
        if not cache_path.exists():
            self._loaded = True
            return []
        try:
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
            self._patterns = [CachedPattern(**p) for p in raw]
            logger.info(f"Loaded {len(self._patterns)} cached patterns")
        except Exception as e:
            logger.warn(f"Failed to load pattern cache: {e}")
            self._patterns = []
        self._loaded = True
        return self._patterns

    def get_relevant_patterns(self, language: str, framework: str) -> list[CachedPattern]:
        """Return patterns for exact language+framework ONLY. Never cross-contaminates."""
        if not self._loaded:
            self.load()
        lang = language.lower()
        fw = framework.lower()
        return [
            p
            for p in self._patterns
            if p.language.lower() == lang and p.framework.lower() == fw
        ]

    def add_patterns(self, new_patterns: list[dict], language: str, framework: str) -> int:
        """Add new patterns from self-learn. Returns count added."""
        if not self._loaded:
            self.load()

        added = 0
        existing_triggers = {p.trigger.lower() for p in self._patterns}

        for p_data in new_patterns:
            trigger = p_data.get("name", p_data.get("trigger", ""))
            if not trigger or trigger.lower() in existing_triggers:
                continue
            pattern = CachedPattern(
                trigger=trigger,
                language=language.lower(),
                framework=framework.lower(),
                test_pattern=p_data.get("description", p_data.get("example", "")),
            )
            self._patterns.append(pattern)
            existing_triggers.add(trigger.lower())
            added += 1

        if added > 0:
            self.save()
            logger.info(f"Saved {added} new patterns to cache")

        return added

    def save(self) -> None:
        """Save patterns to disk."""
        cache_path = self.project_root / self.CACHE_FILE
        try:
            cache_path.write_text(
                json.dumps([asdict(p) for p in self._patterns], indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warn(f"Failed to save pattern cache: {e}")

    def build_context_string(self, language: str, framework: str) -> str:
        """Build a compact context string for the Phase 5 system prompt."""
        patterns = self.get_relevant_patterns(language, framework)
        if not patterns:
            return ""

        lines = [f"Proven patterns for {language}/{framework} (use these, don't reinvent):"]
        for p in patterns[:10]:
            lines.append(f"- {p.trigger}: {p.test_pattern[:200]}")
        return "\n".join(lines)
