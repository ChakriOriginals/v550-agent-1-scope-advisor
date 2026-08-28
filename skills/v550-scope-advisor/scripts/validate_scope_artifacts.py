#!/usr/bin/env python3
"""Validate V550 artifacts against the unchanged repository JSON Schemas."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


SCHEMA_FILES = {
    "scope-artifacts": "scope-artifacts.schema.json",
    "living-project-file": "living-project-file.schema.json",
    "evaluator": "evaluator.schema.json",
    "insights": "insights.schema.json",
    "report": "report.schema.json",
    "telemetry-event": "telemetry-event.schema.json",
}
OCEAN_KEYS = {"openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism", "ocean"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def pointer(parts: Iterable[Any]) -> str:
    encoded = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "$" + ("/" + "/".join(encoded) if encoded else "")


def iter_nodes(value: Any, path: tuple[Any, ...] = ()) -> Iterable[tuple[tuple[Any, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_nodes(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_nodes(child, path + (index,))


def frozen_policy_errors(document: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for path, node in iter_nodes(document):
        if isinstance(node, dict):
            lowered = {str(key).lower() for key in node}
            forbidden = lowered & OCEAN_KEYS
            if forbidden:
                errors.append({"path": pointer(path), "code": "OCEAN_FORBIDDEN", "message": "OCEAN personality fields are not part of Stage 1 Scope work."})
            for gate_key in ("gate_number", "gateNumber", "gate"):
                gate = node.get(gate_key)
                if isinstance(gate, int) and not isinstance(gate, bool) and gate not in range(1, 7):
                    errors.append({"path": pointer(path + (gate_key,)), "code": "GATE_RANGE", "message": "Frozen workflow permits only Gates 1 through 6; Gate 6B stays inside Gate 6."})
            origin = node.get("content_origin", node.get("contentOrigin"))
            label = node.get("ai_draft_label", node.get("aiDraftLabel"))
            # The unchanged schema deliberately uses content_origin in two
            # different records. AI-originated assessed artifact metadata is
            # prohibited in the frozen workflow, while a ledger entry must be
            # able to record that an observed suggestion came from AI so the
            # student's critique/disposition remains auditable.
            is_lineage_entry = "ledger_entry_id" in node or "ledgerEntryId" in node
            if (
                not is_lineage_entry
                and (
                    origin in {"ai_suggested", "mixed", "AI_SUGGESTION", "AI_AUTHORED"}
                    or label
                )
            ):
                errors.append({"path": pointer(path), "code": "FROZEN_AI_DRAFT", "message": "The frozen assessed artifact must be student-authored; an AI preliminary/corrected draft is prohibited."})
        if isinstance(node, str) and re.search(r"\bGate\s+7\b", node, re.I):
            errors.append({"path": pointer(path), "code": "GATE_7_FORBIDDEN", "message": "Gate 6B may not be represented as Gate 7."})
    return errors


def validate(document: Any, schema_path: Path, *, frozen: bool = False) -> list[dict[str, str]]:
    try:
        import jsonschema
        from referencing import Registry, Resource
        from referencing.exceptions import NoSuchResource
    except ImportError as exc:
        raise RuntimeError("The `jsonschema` package and its `referencing` dependency are required to validate repository schemas.") from exc
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read schema {schema_path}: {exc}") from exc

    def reject_remote(uri: str) -> Resource[Any]:
        raise NoSuchResource(ref=uri)

    registry = Registry(retrieve=reject_remote)
    try:
        for candidate in sorted(schema_path.parent.glob("*.json")):
            candidate_schema = json.loads(candidate.read_text(encoding="utf-8"))
            resource = Resource.from_contents(candidate_schema)
            registry = registry.with_resource(candidate.resolve().as_uri(), resource)
            schema_id = candidate_schema.get("$id")
            if isinstance(schema_id, str) and schema_id:
                registry = registry.with_resource(schema_id, resource)
        validator = jsonschema.Draft202012Validator(
            schema,
            registry=registry,
            format_checker=jsonschema.FormatChecker(),
        )
        raw_errors = sorted(
            validator.iter_errors(document),
            key=lambda item: [str(part) for part in item.absolute_path],
        )
    except Exception as exc:
        raise RuntimeError(f"Cannot resolve the bundled schema set locally: {exc}") from exc
    errors = [
        {
            "path": pointer(error.absolute_path),
            "schemaPath": pointer(error.absolute_schema_path),
            "code": "SCHEMA",
            "message": error.message,
        }
        for error in raw_errors
    ]
    if frozen:
        errors.extend(frozen_policy_errors(document))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--schema", choices=sorted(SCHEMA_FILES), default="scope-artifacts")
    parser.add_argument("--schema-path", type=Path, help="Explicit local schema path")
    policy = parser.add_mutually_exclusive_group()
    policy.add_argument(
        "--frozen",
        dest="frozen",
        action="store_true",
        help="Apply frozen Waldron authorship/gate boundaries (default for Scope and Living Project File schemas)",
    )
    policy.add_argument(
        "--schema-only",
        dest="frozen",
        action="store_false",
        help="Run only JSON Schema validation and skip frozen Waldron policy checks",
    )
    parser.set_defaults(frozen=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    schema_path = args.schema_path or repo_root() / "pm-studio-plus/schemas" / SCHEMA_FILES[args.schema]
    try:
        document = json.loads(args.document.read_text(encoding="utf-8"))
        frozen = args.frozen
        if frozen is None:
            frozen = args.schema in {"scope-artifacts", "living-project-file"}
        errors = validate(document, schema_path, frozen=frozen)
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(json.dumps({"valid": False, "errors": [{"path": "$", "code": "READ_OR_ENVIRONMENT", "message": str(exc)}]}))
        return 2
    result = {"valid": not errors, "schema": str(schema_path), "errorCount": len(errors), "errors": errors}
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
