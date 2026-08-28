"""Validate that every acceptance-manifest claim resolves to executable evidence."""

from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path

from support import TESTS


MANIFEST = TESTS / "acceptance" / "acceptance-manifest.json"


class AcceptanceManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_is_versioned_and_uses_discoverable_runner(self) -> None:
        self.assertEqual(self.manifest.get("schema_version"), "2.0.0")
        runner = self.manifest.get("runner", "")
        self.assertIn("python3 -m unittest discover", runner)
        self.assertIn("-p 'test_*.py'", runner)

    def test_ids_are_unique_and_consecutive(self) -> None:
        cases = self.manifest.get("cases")
        self.assertIsInstance(cases, list)
        ids = [case["id"] for case in cases]
        self.assertEqual(ids, [f"AC-{index:03d}" for index in range(1, len(ids) + 1)])
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_evidence_pointer_resolves_to_a_test_method(self) -> None:
        for case in self.manifest["cases"]:
            self.assertTrue(case["requirement"].strip(), case)
            self.assertIn(case["mode"], {"automated", "automated-static", "automated-contract"})
            self.assertIsInstance(case["evidence"], list)
            self.assertTrue(case["evidence"], case)
            for pointer in case["evidence"]:
                with self.subTest(case=case["id"], evidence=pointer):
                    module_name, class_name, method_name = pointer.split(".")
                    module = importlib.import_module(module_name)
                    test_class = getattr(module, class_name)
                    method = getattr(test_class, method_name)
                    self.assertTrue(callable(method))
                    self.assertTrue(method_name.startswith("test_"))

    def test_manifest_covers_every_required_risk_domain(self) -> None:
        categories = {case["category"] for case in self.manifest["cases"]}
        required = {
            "frozen-gates",
            "gate-1",
            "gate-2",
            "gate-3",
            "gate-4",
            "gate-5",
            "gate-6",
            "gate-6b",
            "post-closure-revision",
            "canonical",
            "pedagogy",
            "forward",
            "companion-experience",
            "telemetry",
            "consent",
            "privacy",
            "server-state",
            "report-authorization",
            "report-issuer",
            "report-download",
            "report-integrity",
            "report-verifier",
            "report-layout",
        }
        self.assertTrue(required.issubset(categories), sorted(required - categories))

    def test_stale_acceptance_contracts_are_absent(self) -> None:
        serialized = json.dumps(self.manifest, ensure_ascii=False).lower()
        for stale in (
            "meaningful draft allows labeled preliminary alternative",
            "unmeasurable success criterion blocks gate",
            "action-plan item requires verb and owner",
            "gate requires critique justification artifacts evidence and learning check",
        ):
            self.assertNotIn(stale, serialized)


if __name__ == "__main__":
    unittest.main()
