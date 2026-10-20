"""Mirror Layer 3 skills from .agents/skills/ into .claude/skills/.

`.agents/skills/` is the source of truth. Claude Code only discovers skills
under `.claude/skills/`, and this checkout stores that directory as plain
copies (core.symlinks=false on Windows), so the two drift apart whenever a
skill is added or edited. Run this after touching `.agents/skills/`.

    python scripts/sync_claude_skills.py           # copy/refresh
    python scripts/sync_claude_skills.py --check   # report drift, exit 1 if any

Only directories that contain a SKILL.md are mirrored (e.g. `gsap/` is a
README-only navigation map and is skipped on purpose). Mirror directories
whose source no longer exists are reported but never deleted automatically.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / ".agents" / "skills"
MIRROR = ROOT / ".claude" / "skills"

# Mirror names that intentionally differ from the source directory name.
RENAMES = {"video-toolkit": "video_toolkit"}


def _differs(a: Path, b: Path) -> bool:
    if not b.exists():
        return True
    cmp = filecmp.dircmp(a, b)
    stack = [cmp]
    while stack:
        c = stack.pop()
        if c.left_only or c.right_only or c.funny_files:
            return True
        _, mismatch, errors = filecmp.cmpfiles(c.left, c.right, c.common_files, shallow=False)
        if mismatch or errors:
            return True
        stack.extend(c.subdirs.values())
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only report drift")
    args = parser.parse_args()

    drift: list[str] = []
    sources = sorted(p for p in SOURCE.iterdir() if (p / "SKILL.md").is_file())
    for src in sources:
        dst = MIRROR / RENAMES.get(src.name, src.name)
        if not _differs(src, dst):
            continue
        drift.append(dst.name)
        if not args.check:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    expected = {RENAMES.get(p.name, p.name) for p in sources}
    orphans = sorted(p.name for p in MIRROR.iterdir() if p.is_dir() and p.name not in expected)

    verb = "drifted" if args.check else "synced"
    print(f"{len(drift)} skill(s) {verb}: {', '.join(drift) or '-'}")
    if orphans:
        print(f"mirror-only (source missing, not deleted): {', '.join(orphans)}")
    return 1 if args.check and drift else 0


if __name__ == "__main__":
    sys.exit(main())
