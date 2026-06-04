"""Incremental mode — git-hash cache for changed file detection."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from forge_core.utils import logger


@dataclass
class FileCacheEntry:
    """Cache entry for a single source file."""

    path: str
    git_hash: str
    last_analyzed_at: str
    coverage_pct: float = 0.0
    tests_count: int = 0


class GraphCache:
    """Git-hash based incremental analysis cache.

    READ at pipeline start → identifies changed files → skips unchanged.
    WRITTEN at pipeline end → stores hashes for next run.

    Cache file: .switchforge_cache.json in project root.
    """

    CACHE_FILE = ".switchforge_cache.json"

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._cache: dict[str, FileCacheEntry] = {}
        self._loaded = False

    def load(self) -> dict[str, FileCacheEntry]:
        """Load cache from disk. Returns empty dict if no cache exists."""
        cache_path = self.project_root / self.CACHE_FILE
        if not cache_path.exists():
            self._loaded = True
            return {}
        try:
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
            self._cache = {k: FileCacheEntry(**v) for k, v in raw.items()}
            logger.info(f"Loaded incremental cache: {len(self._cache)} entries")
        except Exception as e:
            logger.warn(f"Failed to load cache: {e} — falling back to full run")
            self._cache = {}
        self._loaded = True
        return self._cache

    def save(self, entries: dict[str, FileCacheEntry] | None = None) -> None:
        """Save cache to disk."""
        to_save = entries or self._cache
        cache_path = self.project_root / self.CACHE_FILE
        try:
            cache_path.write_text(
                json.dumps({k: asdict(v) for k, v in to_save.items()}, indent=2),
                encoding="utf-8",
            )
            logger.info(f"Saved incremental cache: {len(to_save)} entries")
        except Exception as e:
            logger.warn(f"Failed to save cache: {e}")

    def get_changed_files(self, source_files: list[str]) -> list[str]:
        """Return files whose git hash differs from cached version.

        Files not in cache (new files) are always returned as changed.
        Falls back to returning all files if git is unavailable.
        """
        if not self._loaded:
            self.load()

        changed: list[str] = []
        for file_path in source_files:
            current_hash = self._get_git_hash(file_path)
            if not current_hash:
                changed.append(file_path)
                continue
            cached = self._cache.get(file_path)
            if cached is None or cached.git_hash != current_hash:
                changed.append(file_path)

        logger.info(f"Incremental: {len(changed)}/{len(source_files)} files changed")
        return changed

    def update_entry(
        self, file_path: str, coverage_pct: float = 0.0, tests_count: int = 0
    ) -> None:
        """Update cache entry for a file after successful analysis."""
        git_hash = self._get_git_hash(file_path) or "unknown"
        self._cache[file_path] = FileCacheEntry(
            path=file_path,
            git_hash=git_hash,
            last_analyzed_at=datetime.now().isoformat(),
            coverage_pct=coverage_pct,
            tests_count=tests_count,
        )

    def _get_git_hash(self, file_path: str) -> str:
        """Get git object hash for a file. Returns empty string if unavailable."""
        try:
            rel_path = file_path
            if file_path.startswith(str(self.project_root)):
                rel_path = file_path[len(str(self.project_root)) :].lstrip("/\\")

            result = subprocess.run(
                ["git", "hash-object", rel_path],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return ""
