"""Canonical-source manifest, byte-equality, drift, and synchronization tests."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from support import CANONICAL_VERIFIER, REPO, SKILL, load_module


MANIFEST = SKILL / "references" / "canonical-source-manifest.json"
SYNC = SKILL / "scripts" / "sync_runtime_knowledge.py"
COURSE_MATERIALS = SKILL / "scripts" / "canonical_course_materials.py"
EXPECTED_CANONICAL_NAMES = {
    "frozen-waldron-scenario.md",
    "frozen-six-gates.md",
    "frozen-demo-script.md",
    "gate-1-precedent-cards.md",
}


def canonical_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError("canonical-source-manifest.json must contain an object")
    return value


def run(script: Path, root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(script), str(root)],
        capture_output=True,
        text=True,
        env=environment,
    )


class CanonicalKnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not MANIFEST.is_file():
            raise AssertionError(f"Missing canonical manifest: {MANIFEST}")
        if not CANONICAL_VERIFIER.is_file():
            raise AssertionError(f"Missing canonical verifier: {CANONICAL_VERIFIER}")
        if not SYNC.is_file():
            raise AssertionError(f"Missing canonical sync helper: {SYNC}")
        cls.manifest = canonical_json(MANIFEST)

    def entries(self) -> list[dict[str, Any]]:
        entries = self.manifest.get("canonical_sources")
        self.assertIsInstance(entries, list)
        return entries

    def test_manifest_declares_exactly_four_canonical_sources(self) -> None:
        entries = self.entries()
        self.assertEqual(len(entries), 4)
        names = {Path(entry["source"]).name for entry in entries}
        self.assertEqual(names, EXPECTED_CANONICAL_NAMES)
        self.assertNotIn(MANIFEST.name, names)

    def test_invalid_comparison_example_registry_fails_as_instructor_material_needed(self) -> None:
        course_materials = load_module("canonical_course_materials_test", COURSE_MATERIALS)
        approved = course_materials.load_precedent_cards()
        self.assertEqual(len(approved), 1)
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "cards.md"
            invalid.write_text(
                "<!-- GATE_1_PRECEDENT_CARDS_JSON_BEGIN -->\n"
                "```json\n{\"cards\": []}\n```\n"
                "<!-- GATE_1_PRECEDENT_CARDS_JSON_END -->\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                course_materials.InstructorMaterialError,
                "INSTRUCTOR MATERIAL NEEDED",
            ):
                course_materials.load_precedent_cards(invalid)

            duplicate = dict(approved[0])
            duplicate["card_id"] = "CARD-02_UNAPPROVED_EXTRA"
            invalid.write_text(
                "<!-- GATE_1_PRECEDENT_CARDS_JSON_BEGIN -->\n"
                "```json\n"
                + json.dumps({"cards": [approved[0], duplicate]}, indent=2)
                + "\n```\n"
                "<!-- GATE_1_PRECEDENT_CARDS_JSON_END -->\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                course_materials.InstructorMaterialError,
                "exactly one approved Gate 1 comparison example",
            ):
                course_materials.load_precedent_cards(invalid)

    def test_manifest_paths_are_repo_relative_unique_and_complete(self) -> None:
        sources: set[str] = set()
        destinations: set[str] = set()
        for entry in self.entries():
            self.assertEqual(set(entry), {"source", "sha256", "destinations"})
            source = entry["source"]
            digest = entry["sha256"]
            declared_destinations = entry["destinations"]
            self.assertIsInstance(source, str)
            self.assertFalse(Path(source).is_absolute())
            self.assertNotIn("..", Path(source).parts)
            self.assertNotIn(source, sources)
            sources.add(source)
            self.assertRegex(digest, r"^[a-f0-9]{64}$")
            self.assertIsInstance(declared_destinations, list)
            self.assertTrue(declared_destinations)
            for destination in declared_destinations:
                self.assertIsInstance(destination, str)
                self.assertFalse(Path(destination).is_absolute())
                self.assertNotIn("..", Path(destination).parts)
                self.assertNotIn(destination, destinations)
                destinations.add(destination)

    def test_manifest_hashes_and_every_destination_match_canonical_bytes(self) -> None:
        for entry in self.entries():
            source = REPO / entry["source"]
            self.assertTrue(source.is_file(), source)
            source_bytes = source.read_bytes()
            self.assertEqual(hashlib.sha256(source_bytes).hexdigest(), entry["sha256"])
            for relative_destination in entry["destinations"]:
                destination = REPO / relative_destination
                self.assertTrue(destination.is_file(), destination)
                self.assertEqual(
                    destination.read_bytes(),
                    source_bytes,
                    f"Generated destination drifted: {destination}",
                )

    def test_canonical_verifier_passes_clean_repository(self) -> None:
        process = run(CANONICAL_VERIFIER, REPO)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertTrue(result.get("valid"), result)

    def test_one_byte_drift_fails_then_deterministic_sync_restores(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary_repo = Path(directory) / "repo"
            temporary_repo.mkdir()

            paths_to_copy = {MANIFEST.relative_to(REPO), SYNC.relative_to(REPO)}
            for entry in self.entries():
                paths_to_copy.add(Path(entry["source"]))
                paths_to_copy.update(Path(item) for item in entry["destinations"])
            for relative in paths_to_copy:
                source = REPO / relative
                destination = temporary_repo / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

            first_entry = self.entries()[0]
            drifted = temporary_repo / first_entry["destinations"][0]
            drifted.write_bytes(drifted.read_bytes() + b"\nDRIFT")

            failed = run(CANONICAL_VERIFIER, temporary_repo)
            self.assertEqual(failed.returncode, 1, failed.stdout + failed.stderr)
            failed_result = json.loads(failed.stdout)
            self.assertFalse(failed_result.get("valid"), failed_result)

            synchronized = run(SYNC, temporary_repo)
            self.assertEqual(
                synchronized.returncode,
                0,
                synchronized.stdout + synchronized.stderr,
            )
            restored = run(CANONICAL_VERIFIER, temporary_repo)
            self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)
            self.assertEqual(
                drifted.read_bytes(),
                (temporary_repo / first_entry["source"]).read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
