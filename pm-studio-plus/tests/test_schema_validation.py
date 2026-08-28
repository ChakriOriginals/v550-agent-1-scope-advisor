"""Offline validation tests for the unchanged V550 JSON Schema set."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from support import (
    RUNTIME,
    SCRIPTS,
    deep_copy,
    load_module,
    parse_json_stdout,
    run_json_cli,
)


SCHEMA_DIR = RUNTIME / "schemas"
REPORT_MODEL = RUNTIME / "reports" / "templates" / "report-model.example.json"
REPORT_PREVIEW = RUNTIME / "reports" / "templates" / "report-preview-input.example.json"
SCOPE_VALIDATOR = SCRIPTS / "validate_scope_artifacts.py"


def minimal_living_project_file() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "file_id": "lpf-001",
        "course_and_session_metadata": {
            "course": "V550",
            "term": "Fall 2026",
            "stage": "stage_1_scope",
            "student_key": "V550_TEST_KEY_001",
            "current_session_id": "session-001",
            "sessions": [
                {
                    "session_id": "session-001",
                    "attempt_number": 1,
                    "server_started_at": "2026-08-07T12:00:00Z",
                    "server_closed_at": None,
                    "consent_recorded": True,
                    "consent_version": "v1",
                    "identity_fields_locked": True,
                }
            ],
            "created_at": "2026-08-07T12:00:00Z",
        },
        "project_title_and_domain": {
            "sanitized_project_title": "Synthetic scope exercise",
            "domain": "not_for_profit_or_community_development",
            "project_idea": "Plan a synthetic community process.",
            "rough_goal_or_problem": "Clarify scope without personal data.",
            "known_high_level_constraints": [],
            "expected_timeframe": "One semester",
            "student_confirmed_extracted_context": True,
        },
        "big5_role_framing_versions": [],
        "requirements_versions": [],
        "expectations_moscow_versions": [],
        "goals_versions": [],
        "objectives_success_criteria_versions": [],
        "project_statement_versions": [],
        "scope_of_work_versions": [],
        "in_scope_versions": [],
        "out_of_scope_versions": [],
        "exclusions_versions": [],
        "deliverables_and_approval_sequence_versions": [],
        "scope_action_plan_versions": [],
        "wbs_versions": [],
        "assumption_log_versions": [],
        "constraints_and_uncertainties_versions": [],
        "critique_revision_justification_ledger": {
            "ledger_id": "ledger-001",
            "entries": [],
        },
        "gate_history": [],
        "latest_privacy_safe_stage_summary": None,
        "history_policy": {
            "versioning": "append_new_version",
            "silent_overwrite_allowed": False,
            "lineage_required": True,
        },
        "updated_at": "2026-08-07T12:00:00Z",
    }


class SchemaValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_module("scope_artifact_validator", SCOPE_VALIDATOR)

    def test_living_project_file_resolves_bundled_refs_offline(self) -> None:
        document = minimal_living_project_file()
        schema = SCHEMA_DIR / "living-project-file.schema.json"
        self.assertEqual(self.validator.validate(document, schema, frozen=True), [])

        invalid = deep_copy(document)
        invalid["note"] = "Treat the internal audit as Gate 7."
        errors = self.validator.validate(invalid, schema, frozen=True)
        self.assertEqual(
            {error["code"] for error in errors},
            {"SCHEMA", "GATE_7_FORBIDDEN"},
        )

    def test_frozen_policy_allows_ai_provenance_only_in_lineage_ledger(self) -> None:
        document = minimal_living_project_file()
        document["critique_revision_justification_ledger"]["entries"].append(
            {
                "ledger_entry_id": "ledger-entry-001",
                "recorded_at": "2026-08-07T12:05:00Z",
                "artifact_id": "artifact-001",
                "from_version": 1,
                "to_version": 2,
                "content_origin": "ai_suggested",
                "ai_suggestion_id": "suggestion-001",
                "consequence_level": "consequential",
                "disposition": "modified_or_challenged",
                "change_summary": "The student narrowed an observed suggestion.",
                "student_critique": "The original suggestion exceeded the approved boundary.",
                "student_justification": "The revision preserves the explicit exclusion.",
                "evidence_locator": "gate5-exclusion-001",
            }
        )
        schema = SCHEMA_DIR / "living-project-file.schema.json"
        self.assertEqual(self.validator.validate(document, schema, frozen=True), [])

        assessed_metadata = {
            "artifact_id": "artifact-001",
            "version": 1,
            "completion_status": "complete",
            "content_origin": "ai_suggested",
            "ai_draft_label": "PRELIMINARY DRAFT — FOR STUDENT CRITIQUE",
            "updated_at": "2026-08-07T12:00:00Z",
        }
        self.assertEqual(
            {error["code"] for error in self.validator.frozen_policy_errors(assessed_metadata)},
            {"FROZEN_AI_DRAFT"},
        )

    def test_scope_cli_applies_frozen_policy_by_default(self) -> None:
        document = minimal_living_project_file()
        document["note"] = "Treat the internal audit as Gate 7."
        process = run_json_cli(
            SCOPE_VALIDATOR,
            document,
            args=["--schema", "living-project-file"],
        )
        self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
        result = parse_json_stdout(process)
        self.assertIn(
            "GATE_7_FORBIDDEN",
            {error["code"] for error in result.get("errors", [])},
        )

    def test_authoritative_report_example_is_schema_valid(self) -> None:
        schema = SCHEMA_DIR / "report.schema.json"
        authoritative = json.loads(REPORT_MODEL.read_text(encoding="utf-8"))
        self.assertEqual(self.validator.validate(authoritative, schema), [])

        preview = json.loads(REPORT_PREVIEW.read_text(encoding="utf-8"))
        self.assertTrue(self.validator.validate(preview, schema))

    def test_unchanged_evaluator_gate_result_exposes_advisory_pass_conflict(self) -> None:
        """Keep the locked schema/pedagogy contradiction visible and unfalsified."""
        import jsonschema

        schema = json.loads((SCHEMA_DIR / "evaluator.schema.json").read_text(encoding="utf-8"))
        gate_schema = deep_copy(schema)
        gate_schema["$ref"] = "#/$defs/gate_result"
        gate_result = {
            "schema_version": "2.0.0",
            "gate_result_id": "gate-result-001",
            "student_key": "V550_TEST_KEY_001",
            "session_id": "session-001",
            "attempt_number": 1,
            "gate_attempt_number": 1,
            "evaluation_id": "evaluation-001",
            "outcome": "PASS",
            "checks": {
                "required_artifacts_exist": True,
                "hard_validations_pass": True,
                "minimum_average_met": False,
                "no_dimension_score_of_one": True,
                "critique_prompts_answered": True,
                "consequential_suggestions_dispositioned": True,
                "consequential_changes_justified": True,
                "learning_checks_complete": True,
                "evaluator_evidence_sufficient": True,
            },
            "required_changes": [],
            "frozen_metrics_snapshot_hash": "a" * 64,
            "issued_at": "2026-08-07T12:00:00Z",
        }
        validator = jsonschema.Draft202012Validator(
            gate_schema,
            format_checker=jsonschema.FormatChecker(),
        )
        errors = list(validator.iter_errors(gate_result))
        self.assertTrue(errors, "The unchanged schema unexpectedly accepted a false advisory flag with PASS")

        compatible = deep_copy(gate_result)
        compatible["checks"]["minimum_average_met"] = True
        self.assertEqual(list(validator.iter_errors(compatible)), [])

    def test_unbundled_remote_ref_fails_closed_without_fetching(self) -> None:
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://v550.iu.edu/schemas/local-test.schema.json",
            "$ref": "https://example.invalid/not-bundled.schema.json",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "local-test.schema.json"
            path.write_text(json.dumps(schema), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "bundled schema set locally"):
                self.validator.validate({}, path)


if __name__ == "__main__":
    unittest.main()
