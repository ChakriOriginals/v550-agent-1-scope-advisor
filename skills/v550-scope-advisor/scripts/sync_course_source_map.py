#!/usr/bin/env python3
"""Synchronize the private course-source locator map into the runtime project."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[1]
SOURCE = SKILL_ROOT / "references" / "course-concept-source-map.md"
DESTINATION = REPO_ROOT / "pm-studio-plus" / "gpt" / "knowledge" / "course-concept-source-map.md"


def atomic_copy(source: Path, destination: Path) -> None:
    data = source.read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=destination.name + ".", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    finally:
        temporary = Path(temporary_name)
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="fail unless runtime bytes already match")
    args = parser.parse_args()
    if args.verify:
        if not DESTINATION.exists() or DESTINATION.read_bytes() != SOURCE.read_bytes():
            print("course source map drift detected")
            return 1
        print("course source map verified")
        return 0
    atomic_copy(SOURCE, DESTINATION)
    print(f"synchronized {SOURCE} -> {DESTINATION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
