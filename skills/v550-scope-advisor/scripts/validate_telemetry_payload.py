#!/usr/bin/env python3
"""Fail-closed validation for the four V550 GPT Action request payloads."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


OPERATIONS = {"startSession", "logEvent", "closeSession", "issueReport"}
EVENTS = {
    "consent_recorded", "session_started", "role_framing_submitted", "requirements_submitted",
    "expectations_submitted", "moscow_submitted", "goals_objectives_submitted", "smart_check_completed",
    "deliverables_submitted", "project_statement_submitted", "scope_boundaries_submitted",
    "scope_action_plan_submitted", "wbs_submitted", "assumption_audit_completed", "draft_submitted",
    "critique_given", "critique_answered", "revision_submitted", "justification_submitted",
    "scope_creep_flagged", "misconception_flagged", "gate_attempt", "gate_result", "report_issued",
    "report_regenerated", "session_closed", "daily_summary_written",
}
CLIENT_LOGGABLE_EVENTS = EVENTS - {
    "consent_recorded", "session_started", "report_issued", "report_regenerated", "session_closed",
}
ROLES = {
    "main_scope_advisor", "auto_grader", "insights", "summarizer",
    "wbs_decomposer_action_plan", "assumption_auditor", "scope_review_board",
}
EVENT_ROLES = {
    "role_framing_submitted": {"main_scope_advisor"},
    "requirements_submitted": {"main_scope_advisor"},
    "expectations_submitted": {"main_scope_advisor"},
    "moscow_submitted": {"main_scope_advisor"},
    "goals_objectives_submitted": {"main_scope_advisor"},
    "smart_check_completed": {"auto_grader"},
    "deliverables_submitted": {"main_scope_advisor", "wbs_decomposer_action_plan"},
    "project_statement_submitted": {"main_scope_advisor"},
    "scope_boundaries_submitted": {"main_scope_advisor", "assumption_auditor"},
    "scope_action_plan_submitted": {"wbs_decomposer_action_plan"},
    "wbs_submitted": {"wbs_decomposer_action_plan"},
    "assumption_audit_completed": {"assumption_auditor"},
    "revision_submitted": {"main_scope_advisor", "wbs_decomposer_action_plan", "assumption_auditor"},
    "misconception_flagged": {"insights", "auto_grader", "scope_review_board"},
    "gate_attempt": {"scope_review_board"},
    "gate_result": {"scope_review_board"},
    "scope_creep_flagged": {"assumption_auditor"},
    "daily_summary_written": {"summarizer"},
}
COMMON_FIELDS = {"operation", "classToken", "studentKey", "requestId", "schemaVersion"}
ALLOWED_FIELDS = {
    "startSession": COMMON_FIELDS | {"consent"},
    "logEvent": COMMON_FIELDS | {
        "sessionId", "eventId", "eventType", "stage", "role", "artifactVersionId", "metrics",
        "reasonCodes", "oneLineNote", "misconceptionFlags", "digest", "gateOutcome", "dimensionScores",
    },
    "closeSession": COMMON_FIELDS | {
        "sessionId", "stage", "role", "metrics", "reasonCodes", "oneLineNote", "misconceptionFlags",
        "digest", "gateOutcome",
    },
    "issueReport": COMMON_FIELDS | {"sessionId", "regenerate"},
}
REQUIRED_FIELDS = {
    "startSession": COMMON_FIELDS | {"consent"},
    "logEvent": COMMON_FIELDS | {"sessionId", "eventId", "eventType", "stage", "role"},
    "closeSession": COMMON_FIELDS | {"sessionId", "stage", "role", "digest"},
    "issueReport": COMMON_FIELDS | {"sessionId"},
}
SERVER_OWNED_KEYS = {
    "attempt", "attemptnumber", "attempt_number", "stageattempt", "stage_attempt", "generation",
    "generationnumber", "generation_number", "reportid", "report_id", "issuedat", "issued_at",
    "servertimestamp", "server_timestamp", "pdf", "pdfbytes", "pdf_bytes", "pdfsha256", "pdf_sha256",
    "bytehash", "byte_hash", "signature", "receiptsignature", "receipt_signature", "storageid",
    "storage_id", "storageobjectid", "storage_object_id", "fileurl", "file_url", "finalreportprose",
    "final_report_prose", "templateversion", "template_version", "reportstatus", "report_status",
}
DENIED_CONTENT_KEYS = {
    "name", "email", "phone", "address", "studentid", "student_id", "rosterid", "roster_id",
    "transcript", "chat", "chatlog", "chat_log", "draft", "fulldraft", "full_draft", "upload",
    "evidenceexcerpt", "evidence_excerpt", "reasoning", "chainofthought", "chain_of_thought", "password",
    "pin", "secret", "accesstoken", "access_token", "grade", "medical", "immigration", "disciplinary",
}
MISCONCEPTIONS = {
    "requirements_expectations_conflated", "goal_objective_conflated", "solution_chosen_before_requirements",
    "activity_mislabeled_as_deliverable", "success_criterion_not_measurable", "missing_exclusion",
    "assumption_presented_as_fact", "ownerless_action", "vague_wbs_work_package", "wbs_overlap_or_gap",
    "scope_creep_unacknowledged", "stage2_scheduling_pulled_into_stage1",
}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")
SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
URL_RE = re.compile(r"https?://|www\.", re.I)
SENSITIVE_RE = re.compile(r"\b(medical|health condition|accommodation details|financial account|immigration|disciplinary|authentication credential|password|social security|overwhelmed|frustrated|tearful|ready to cry|crying|emotional distress)\b", re.I)
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{11,63}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
FORMULA_PREFIXES = ("=", "+", "-", "@")
GATE_IDENTITY_RE = re.compile(r"^GATE_([1-6])(?:_(ATTEMPT_RECORDED|RESULT|OPEN|CLOSED))?$")
GATE_EVENT_QUALIFIERS = {
    "revision_submitted": {None},
    "assumption_audit_completed": {None},
    "gate_attempt": {"ATTEMPT_RECORDED"},
    "gate_result": {"RESULT", "OPEN", "CLOSED"},
}


def normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(value).lower())


def add(errors: list[dict[str, str]], path: str, code: str, message: str) -> None:
    errors.append({"path": path, "code": code, "message": message})


def walk(value: Any, path: str, errors: list[dict[str, str]]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = normalized_key(key)
            if normalized in SERVER_OWNED_KEYS:
                add(errors, f"{path}.{key}", "SERVER_OWNED", "The client may not choose this server-derived field.")
            if normalized in DENIED_CONTENT_KEYS:
                add(errors, f"{path}.{key}", "PROHIBITED_FIELD", "This content category is prohibited in telemetry.")
            walk(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            walk(item, f"{path}[{index}]", errors)
    elif isinstance(value, str):
        if len(value) > 500:
            add(errors, path, "TOO_LONG", "Telemetry strings may not exceed 500 characters.")
        if value.startswith(FORMULA_PREFIXES):
            add(errors, path, "FORMULA_PREFIX", "Neutralize spreadsheet formula prefixes before logging.")
        if EMAIL_RE.search(value) or PHONE_RE.search(value) or SSN_RE.search(value):
            add(errors, path, "DIRECT_IDENTIFIER", "Possible direct identifier detected.")
        if SENSITIVE_RE.search(value):
            add(errors, path, "SENSITIVE_CONTENT", "Sensitive personal content is prohibited in telemetry.")


def validate_iso_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 40:
        return False
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_reliance(metrics: Any, errors: list[dict[str, str]]) -> None:
    if metrics is None:
        return
    if not isinstance(metrics, dict):
        add(errors, "$.metrics", "TYPE", "Metrics must be an object.")
        return
    allowed = {"critiqueDepth", "acceptedVerbatim", "challengedOrModified", "rejected", "aiRelianceStatus", "aiRelianceIndex", "substantiveIterations", "gateAttempts"}
    for key in metrics.keys() - allowed:
        add(errors, f"$.metrics.{key}", "UNKNOWN_FIELD", "Unknown metrics field.")
    if "critiqueDepth" in metrics and (not isinstance(metrics["critiqueDepth"], int) or isinstance(metrics["critiqueDepth"], bool) or not 0 <= metrics["critiqueDepth"] <= 3):
        add(errors, "$.metrics.critiqueDepth", "RANGE", "Critique depth must be an integer from 0 through 3.")
    for key in ("substantiveIterations", "gateAttempts"):
        if key in metrics and (not isinstance(metrics[key], int) or isinstance(metrics[key], bool) or metrics[key] < 0):
            add(errors, f"$.metrics.{key}", "RANGE", "Metric must be a non-negative integer.")
    counts = ("acceptedVerbatim", "challengedOrModified", "rejected")
    reliance_present = any(key in metrics for key in counts + ("aiRelianceStatus", "aiRelianceIndex"))
    if reliance_present and not all(key in metrics for key in counts + ("aiRelianceStatus", "aiRelianceIndex")):
        add(errors, "$.metrics", "RELIANCE_FIELDS", "Reliance reporting requires all counts, status, and index.")
        return
    if not reliance_present:
        return
    values = [metrics[key] for key in counts]
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
        add(errors, "$.metrics", "RELIANCE_COUNTS", "Reliance counts must be non-negative integers.")
        return
    denominator = sum(values)
    if denominator == 0:
        if metrics["aiRelianceStatus"] != "not_applicable" or metrics["aiRelianceIndex"] is not None:
            add(errors, "$.metrics", "RELIANCE_NA", "A zero denominator requires not_applicable and a null index.")
        return
    expected = round(values[0] / denominator * 100, 2)
    index = metrics["aiRelianceIndex"]
    if metrics["aiRelianceStatus"] != "calculated" or not isinstance(index, (int, float)) or isinstance(index, bool) or abs(float(index) - expected) > 0.01:
        add(errors, "$.metrics", "RELIANCE_FORMULA", f"The AI-reliance index must equal {expected:.2f}.")


def validate_digest(digest: Any, errors: list[dict[str, str]]) -> None:
    if digest is None:
        return
    if not isinstance(digest, dict):
        add(errors, "$.digest", "TYPE", "Digest must be an object.")
        return
    allowed = {"workingOn", "aiUse", "decidedOrRevised", "stuckOrNext"}
    required = {"workingOn", "aiUse", "decidedOrRevised"}
    for key in digest.keys() - allowed:
        add(errors, f"$.digest.{key}", "UNKNOWN_FIELD", "Unknown digest field.")
    for key in required:
        if not isinstance(digest.get(key), str) or not digest[key].strip():
            add(errors, f"$.digest.{key}", "REQUIRED", "Digest line is required.")
    prefixes = {"workingOn": "Working on:", "aiUse": "AI use:", "decidedOrRevised": "Decided/revised:", "stuckOrNext": "Stuck/next:"}
    for key, value in digest.items():
        if value is not None and (not isinstance(value, str) or not value.startswith(prefixes[key]) or "\n" in value or len(value) > 240 or URL_RE.search(value)):
            add(errors, f"$.digest.{key}", "DIGEST_LINE", "Digest line has an invalid label, length, URL, or newline.")


def validate_dimension_scores(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    expected = {
        "projectStatement", "objectivesAndSuccessCriteria", "scopeOfWork", "deliverables",
        "scopeActionPlan", "constraintsAndUncertainties", "exclusions", "doYouDeliver",
    }
    if not isinstance(value, dict):
        add(errors, "$.dimensionScores", "TYPE", "Dimension scores must be an object.")
        return
    if set(value) != expected:
        add(errors, "$.dimensionScores", "DIMENSION_FIELDS", "All and only the eight advisory dimensions are required when scores are sent.")
    for key, score in value.items():
        if key in expected and (not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5):
            add(errors, f"$.dimensionScores.{key}", "RANGE", "Advisory dimension score must be an integer from 1 through 5.")


def validate_gate_identity(data: dict[str, Any], errors: list[dict[str, str]]) -> None:
    event_type = data.get("eventType")
    expected = GATE_EVENT_QUALIFIERS.get(event_type)
    if expected is None:
        return
    reason_codes = data.get("reasonCodes")
    if not isinstance(reason_codes, list):
        add(errors, "$.reasonCodes", "GATE_IDENTITY_REQUIRED", f"{event_type} requires exactly one canonical gate identity reason code.")
        return
    gate_like = [code for code in reason_codes if isinstance(code, str) and code.upper().startswith("GATE_")]
    parsed = [GATE_IDENTITY_RE.fullmatch(code) for code in gate_like]
    parsed = [match for match in parsed if match]
    if len(gate_like) != 1 or len(parsed) != 1 or parsed[0].group(2) not in expected:
        add(errors, "$.reasonCodes", "GATE_IDENTITY_REQUIRED", f"{event_type} requires exactly one canonical gate identity reason code.")
        return
    gate_number = int(parsed[0].group(1))
    qualifier = parsed[0].group(2)
    if event_type == "assumption_audit_completed" and gate_number != 6:
        add(errors, "$.reasonCodes", "GATE_IDENTITY_INVALID", "The final assumption audit is internal to Gate 6.")
    gate_outcome = data.get("gateOutcome")
    if event_type == "gate_result" and (
        (qualifier == "OPEN" and gate_outcome != "PASS")
        or (qualifier == "CLOSED" and gate_outcome != "REVISE")
    ):
        add(errors, "$.reasonCodes", "GATE_RESULT_CONTRADICTION", "The gate identity reason code contradicts gateOutcome.")


def validate_reason_codes(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        add(errors, "$.reasonCodes", "REASON_CODES", "Reason codes must be a unique array of at most 20 controlled code strings.")
        return
    strings_valid = all(
        isinstance(code, str)
        and len(code) <= 80
        and re.fullmatch(r"[A-Za-z0-9_:-]+", code) is not None
        for code in value
    )
    if len(value) > 20 or not strings_valid or len(value) != len(set(value)):
        add(errors, "$.reasonCodes", "REASON_CODES", "Reason codes must be a unique array of at most 20 controlled code strings.")


def validate(data: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(data, dict):
        return [{"path": "$", "code": "TYPE", "message": "Payload must be an object."}]
    operation = data.get("operation")
    if operation not in OPERATIONS:
        add(errors, "$.operation", "OPERATION", "Exactly one of the four allowed operations is required.")
        walk(data, "$", errors)
        return errors
    for key in data.keys() - ALLOWED_FIELDS[operation]:
        add(errors, f"$.{key}", "UNKNOWN_FIELD", "Unknown field for this operation.")
    for key in REQUIRED_FIELDS[operation]:
        if key not in data or data[key] in (None, ""):
            add(errors, f"$.{key}", "REQUIRED", "Required field is missing.")
    if not isinstance(data.get("classToken"), str) or not 16 <= len(data.get("classToken", "")) <= 512:
        add(errors, "$.classToken", "CLASS_TOKEN", "Class token length is invalid.")
    if not isinstance(data.get("studentKey"), str) or not KEY_RE.fullmatch(data.get("studentKey", "")):
        add(errors, "$.studentKey", "STUDENT_KEY", "Student key format is invalid.")
    if not isinstance(data.get("requestId"), str) or not ID_RE.fullmatch(data.get("requestId", "")):
        add(errors, "$.requestId", "REQUEST_ID", "Request ID format is invalid.")
    if not isinstance(data.get("schemaVersion"), str) or not VERSION_RE.fullmatch(data.get("schemaVersion", "")):
        add(errors, "$.schemaVersion", "SCHEMA_VERSION", "Schema version must be semantic numeric form.")
    if operation == "startSession":
        consent = data.get("consent")
        if not isinstance(consent, dict):
            add(errors, "$.consent", "CONSENT_REQUIRED", "A structured consent assertion is required before any write.")
        else:
            for key in consent.keys() - {"asserted", "version", "clientObservedAt"}:
                add(errors, f"$.consent.{key}", "UNKNOWN_FIELD", "Unknown consent field.")
            if consent.get("asserted") is not True:
                add(errors, "$.consent.asserted", "CONSENT_REQUIRED", "A true consent assertion is required before any write.")
            consent_version = consent.get("version")
            if not isinstance(consent_version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,31}", consent_version):
                add(errors, "$.consent.version", "CONSENT_VERSION", "A versioned consent identifier is required.")
            if not validate_iso_timestamp(consent.get("clientObservedAt")):
                add(errors, "$.consent.clientObservedAt", "CONSENT_TIMESTAMP", "Client-observed consent time must be a valid timestamp.")
    else:
        if not isinstance(data.get("sessionId"), str) or not ID_RE.fullmatch(data.get("sessionId", "")):
            add(errors, "$.sessionId", "SESSION_ID", "A server-issued session ID is required.")
    if operation == "logEvent":
        event_type = data.get("eventType")
        role = data.get("role")
        if data.get("stage") != "stage_1_scope":
            add(errors, "$.stage", "STAGE", "The unchanged telemetry schema permits only stage_1_scope.")
        if event_type not in CLIENT_LOGGABLE_EVENTS:
            add(errors, "$.eventType", "EVENT", "Event type is unsupported or server-owned.")
        if role not in ROLES:
            add(errors, "$.role", "ROLE", "Protocol role is unsupported.")
        elif event_type in EVENT_ROLES and role not in EVENT_ROLES[event_type]:
            add(errors, "$.role", "ROLE_EVENT_MISMATCH", "Protocol role cannot emit this event type.")
        if not isinstance(data.get("eventId"), str) or not ID_RE.fullmatch(data.get("eventId", "")):
            add(errors, "$.eventId", "EVENT_ID", "Event ID format is invalid.")
        if data.get("gateOutcome") not in (None, "PASS", "REVISE", "INCOMPLETE"):
            add(errors, "$.gateOutcome", "GATE_OUTCOME", "Stored gate outcome must use the unchanged schema vocabulary.")
        if event_type == "gate_result" and data.get("gateOutcome") in (None, ""):
            add(errors, "$.gateOutcome", "REQUIRED", "gate_result requires gateOutcome.")
        if event_type == "gate_result" and data.get("gateOutcome") == "INCOMPLETE":
            add(errors, "$.gateOutcome", "NO_ATTEMPT_NOT_LOGGABLE", "Diagnostic INCOMPLETE is not a recorded gate result.")
        if event_type == "revision_submitted" and (
            not isinstance(data.get("artifactVersionId"), str)
            or not ID_RE.fullmatch(data.get("artifactVersionId", ""))
        ):
            add(errors, "$.artifactVersionId", "REQUIRED", "revision_submitted requires artifactVersionId.")
        validate_gate_identity(data, errors)
        flags = data.get("misconceptionFlags")
        if flags is not None and (not isinstance(flags, list) or len(flags) != len(set(flags)) or any(flag not in MISCONCEPTIONS for flag in flags)):
            add(errors, "$.misconceptionFlags", "MISCONCEPTION_FLAGS", "Misconception flags must use unique existing codes.")
    if operation == "closeSession":
        if data.get("stage") != "stage_1_scope":
            add(errors, "$.stage", "STAGE", "The unchanged telemetry schema permits only stage_1_scope.")
        if data.get("role") != "summarizer":
            add(errors, "$.role", "ROLE_EVENT_MISMATCH", "Only the summarizer protocol may close a session.")
    if operation == "issueReport" and "regenerate" in data and not isinstance(data["regenerate"], bool):
        add(errors, "$.regenerate", "TYPE", "regenerate must be boolean when supplied.")
    validate_reliance(data.get("metrics"), errors)
    validate_reason_codes(data.get("reasonCodes"), errors)
    validate_digest(data.get("digest"), errors)
    validate_dimension_scores(data.get("dimensionScores"), errors)
    walk(data, "$", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.payload.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [{"path": "$", "code": "READ", "message": str(exc)}]}))
        return 2
    errors = validate(data)
    print(json.dumps({"valid": not errors, "errorCount": len(errors), "errors": errors}, indent=2 if args.pretty else None))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
