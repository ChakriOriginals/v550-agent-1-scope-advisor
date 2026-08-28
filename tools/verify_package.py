#!/usr/bin/env python3
"""Verify the self-contained V550 Agent 1 staff-test package."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    ROOT / "skills" / "v550-scope-advisor" / "SKILL.md",
    ROOT / "pm-studio-plus" / "AGENTS.md",
    ROOT / "pm-studio-plus" / "config" / "instructor-config.yaml",
    ROOT / "source-material" / "MASTER-BUILD-PROMPT.txt",
    ROOT / "source-material" / "Scenario 1 After the Merger.docx",
    ROOT / "docs" / "STAFF-TESTING-TUTORIAL.md",
)


def run(label: str, command: list[str]) -> None:
    print(f"\n== {label} ==")
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(command, cwd=ROOT, env=environment)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
    caches = [path for path in ROOT.rglob("__pycache__") if ".git" not in path.parts]
    if missing or caches:
        if missing:
            print("Missing required files:", *missing, sep="\n- ")
        if caches:
            print("Generated caches must not be shared:", *(str(path.relative_to(ROOT)) for path in caches), sep="\n- ")
        return 1
    print("Package structure: PASS")

    run(
        "Canonical knowledge",
        [sys.executable, "skills/v550-scope-advisor/scripts/verify_canonical_knowledge.py"],
    )
    run(
        "Course source map",
        [sys.executable, "skills/v550-scope-advisor/scripts/sync_course_source_map.py", "--verify"],
    )
    run("Automated acceptance suite", [sys.executable, "pm-studio-plus/tests/run_all.py"])
    print("\nAgent 1 staff-test package: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
