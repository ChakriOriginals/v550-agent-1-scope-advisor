#!/usr/bin/env python3
"""Create a visibly non-authoritative one-page report layout preview for local QA."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PREVIEW_LABEL = "NON-AUTHORITATIVE QA PREVIEW — NOT FOR SUBMISSION"
SERVER_ONLY = {
    "session_id", "attempt", "attempt_number", "stage_attempt", "generation", "generation_number",
    "report_id", "issued_at", "status", "byte_hash", "signature", "key_version", "storage_object_id",
    "verification_token", "final_report_prose",
}


def pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def sanitized_line(value: Any, maximum: int = 92) -> str:
    candidate = re.sub(r"[\r\n\t]+", " ", str(value)).strip()
    candidate = re.sub(r"\s+", " ", candidate)
    return candidate[:maximum]


def validate_model(model: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(model, dict):
        return ["model root must be an object"]
    forbidden = SERVER_ONLY & set(model)
    if forbidden:
        errors.append("preview input may not contain server-owned issuance fields: " + ", ".join(sorted(forbidden)))
    for key in ("course", "stage", "student_key", "project_title", "metrics", "sanitized_summary"):
        if key not in model or model[key] in (None, "", [], {}):
            errors.append(f"missing required preview field: {key}")
    metrics = model.get("metrics", {})
    if isinstance(metrics, dict):
        for key in ("critique_depth", "accepted_verbatim_count", "challenged_or_modified_count", "rejected_count", "substantive_iteration_count", "gate_attempt_count", "gate_outcome"):
            if key not in metrics:
                errors.append(f"missing metrics field: {key}")
    return errors


def reliance(metrics: dict[str, Any]) -> str:
    accepted = int(metrics.get("accepted_verbatim_count", 0))
    challenged = int(metrics.get("challenged_or_modified_count", 0))
    rejected = int(metrics.get("rejected_count", 0))
    denominator = accepted + challenged + rejected
    return "N/A" if denominator == 0 else f"{accepted / denominator * 100:.2f}%"


def build_pdf(model: dict[str, Any]) -> bytes:
    metrics = model["metrics"]
    summary = model["sanitized_summary"]
    lines = [
        PREVIEW_LABEL,
        "V550 AI Usage & Learning Report — layout preview",
        f"Course/stage: {sanitized_line(model['course'])} | {sanitized_line(model['stage'])}",
        f"Pseudonymous key: {sanitized_line(model['student_key'])}",
        f"Sanitized project: {sanitized_line(model['project_title'])}",
        f"Critique depth: {metrics['critique_depth']} | AI-reliance index: {reliance(metrics)}",
        f"Accepted verbatim: {metrics['accepted_verbatim_count']} | Challenged/modified: {metrics['challenged_or_modified_count']} | Rejected: {metrics['rejected_count']}",
        f"Substantive iterations: {metrics['substantive_iteration_count']} | Gate attempts: {metrics['gate_attempt_count']} | Outcome: {metrics['gate_outcome']}",
        f"Working on: {sanitized_line(summary.get('working_on', ''))}",
        f"AI use: {sanitized_line(summary.get('ai_use', ''))}",
        f"Decided/revised: {sanitized_line(summary.get('decided_or_revised', ''))}",
        f"Stuck/next: {sanitized_line(summary.get('stuck_or_next', ''))}",
        "Preview excludes server IDs, final prose, receipt, registry data, capability, and signature.",
        "The instructor-controlled Apps Script backend is the sole authoritative issuer.",
    ]
    commands = ["BT", "/F1 9 Tf", "42 748 Td", "12 TL"]
    for index, line in enumerate(lines):
        if index:
            commands.append("T*")
        commands.append(f"({pdf_escape(line)}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("cp1252", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--qa-preview", action="store_true", required=True, help="Acknowledge that the output is not authoritative")
    args = parser.parse_args()
    try:
        model = json.loads(args.model.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}))
        return 2
    errors = validate_model(model)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}))
        return 1
    args.output.write_bytes(build_pdf(model))
    print(json.dumps({"valid": True, "authoritative": False, "label": PREVIEW_LABEL, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
