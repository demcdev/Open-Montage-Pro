"""Canonical repository paths — single source of truth.

The projects root is the most load-bearing path in the system: checkpoints
are written under it, tool events are attributed against it, and the Backlot
board watches it. Define it once.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Overridable for staging/screenshots/tests. Everything — checkpoint writes,
# event attribution, the Backlot board — follows the same root.
PROJECTS_DIR = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR") or (REPO_ROOT / "projects"))

# Tool output with no output_path lands here, inside gitignored output/, and never
# in whatever directory the process happens to run from.
SCRATCH_DIR = REPO_ROOT / "output" / "scratch"


def scratch_path(name: str) -> Path:
    """Return a default output path, creating its folder."""
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    return SCRATCH_DIR / name
