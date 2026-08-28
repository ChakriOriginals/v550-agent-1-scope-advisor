#!/usr/bin/env python3
"""Compatibility entry point for the discoverable V550 acceptance suite."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


def main() -> int:
    tests = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(tests),
        pattern="test_*.py",
        top_level_dir=str(tests),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
