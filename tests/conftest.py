"""Ensure engine/ is on sys.path for all tests."""
import sys
from pathlib import Path

engine_dir = Path(__file__).parent.parent / "engine"
if str(engine_dir) not in sys.path:
    sys.path.insert(0, str(engine_dir))
