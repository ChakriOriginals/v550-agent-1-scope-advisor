#!/usr/bin/env python3
"""Delegate local PDF/receipt verification to the reusable skill validator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


VALIDATOR = Path(__file__).resolve().parents[3] / "skills/v550-scope-advisor/scripts/validate_report_integrity.py"


def main() -> int:
    if not VALIDATOR.is_file():
        print(f"Required skill validator is missing: {VALIDATOR}", file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location("v550_report_integrity", VALIDATOR)
    if spec is None or spec.loader is None:
        print(f"Cannot load skill validator: {VALIDATOR}", file=sys.stderr)
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.main())


if __name__ == "__main__":
    sys.exit(main())
