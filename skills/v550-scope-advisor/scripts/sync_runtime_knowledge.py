#!/usr/bin/env python3
"""Atomically synchronize canonical V550 frozen references to declared destinations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("skills/v550-scope-advisor/references/canonical-source-manifest.json")


class ManifestError(ValueError):
    """The canonical-source manifest is unsafe or malformed."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def safe_repo_path(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{label} must be a non-empty repo-relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ManifestError(f"{label} must stay inside the repository: {value!r}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ManifestError(f"{label} escapes the repository: {value!r}") from exc
    return resolved


def load_manifest(root: Path, manifest_path: Path) -> tuple[dict[str, Any], Path]:
    path = manifest_path if manifest_path.is_absolute() else root / manifest_path
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0.0":
        raise ManifestError("manifest schema_version must be 1.0.0")
    sources = manifest.get("canonical_sources")
    roots = manifest.get("protected_generated_roots")
    if not isinstance(sources, list) or not sources:
        raise ManifestError("canonical_sources must be a non-empty array")
    if not isinstance(roots, list) or not roots:
        raise ManifestError("protected_generated_roots must be a non-empty array")
    return manifest, path


def validate_declarations(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    protected = [safe_repo_path(root, item, "protected_generated_root") for item in manifest["protected_generated_roots"]]
    declared_destinations: set[Path] = set()
    declarations: list[dict[str, Any]] = []
    for index, item in enumerate(manifest["canonical_sources"]):
        if not isinstance(item, dict):
            raise ManifestError(f"canonical_sources[{index}] must be an object")
        source = safe_repo_path(root, item.get("source"), f"canonical_sources[{index}].source")
        try:
            source.relative_to((root / "skills/v550-scope-advisor/references").resolve())
        except ValueError as exc:
            raise ManifestError(f"canonical source is outside the skill references directory: {source}") from exc
        if source.name == "canonical-source-manifest.json":
            raise ManifestError("the manifest must not list or hash itself")
        if not source.is_file():
            raise ManifestError(f"canonical source is missing: {source}")
        destinations = item.get("destinations")
        if not isinstance(destinations, list) or not destinations:
            raise ManifestError(f"canonical_sources[{index}].destinations must be non-empty")
        resolved_destinations: list[Path] = []
        for d_index, value in enumerate(destinations):
            destination = safe_repo_path(root, value, f"canonical_sources[{index}].destinations[{d_index}]")
            if not any(destination == base or destination.is_relative_to(base) for base in protected):
                raise ManifestError(f"destination is outside protected generated roots: {destination}")
            if destination in declared_destinations:
                raise ManifestError(f"destination is declared more than once: {destination}")
            declared_destinations.add(destination)
            resolved_destinations.append(destination)
        declarations.append({"item": item, "source": source, "destinations": resolved_destinations})
    return declarations


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def sync(root: Path, manifest_path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest, resolved_manifest = load_manifest(root, manifest_path)
    declarations = validate_declarations(root, manifest)
    copied: list[str] = []
    for declaration in declarations:
        data = declaration["source"].read_bytes()
        declaration["item"]["sha256"] = hashlib.sha256(data).hexdigest()
        for destination in declaration["destinations"]:
            atomic_write(destination, data)
            copied.append(destination.relative_to(root).as_posix())
    serialized = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    atomic_write(resolved_manifest, serialized)
    return {
        "valid": True,
        "manifest": resolved_manifest.relative_to(root).as_posix(),
        "canonicalSourceCount": len(declarations),
        "destinationCount": len(copied),
        "copied": copied,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_root", nargs="?", type=Path, help="Optional repository root")
    parser.add_argument("--repo-root", dest="repo_root_option", type=Path, help="Repository root")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        root = (args.repo_root_option or args.repo_root or repo_root()).resolve()
        result = sync(root, args.manifest)
    except (ManifestError, OSError) as exc:
        result = {"valid": False, "errors": [{"code": "SYNC_FAILED", "message": str(exc)}]}
        print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
