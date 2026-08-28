#!/usr/bin/env python3
"""Verify one-page report bytes against an authenticated server receipt.

The keyring is supplied as V550_REPORT_HMAC_KEYS_JSON, for example
{"v1":"a server-only secret of at least thirty-two characters"}.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


VALID_ORIGINAL = "VALID ORIGINAL"
VALID_REGENERATED = "VALID REGENERATED COPY — GENERATION {generation}"
VERIFICATION_FAILED = "VERIFICATION FAILED — FILE MAY HAVE BEEN MODIFIED"
UNKNOWN_REPORT_ID = "UNKNOWN REPORT ID"
REQUIRED_RECEIPT_FIELDS = {
    "reportId", "stageAttempt", "generation", "issuedAt", "schemaVersion", "templateVersion",
    "byteHash", "byteLength", "keyVersion", "priorReportId", "reportStatus", "receiptSignature",
}
HEX_64 = re.compile(r"^[a-f0-9]{64}$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def page_count(pdf_bytes: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))


def canonical_receipt_bytes(receipt: dict[str, Any]) -> bytes:
    signed = {key: value for key, value in receipt.items() if key != "receiptSignature"}
    return json.dumps(signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_keyring(raw: str | None = None) -> dict[str, str]:
    source = raw if raw is not None else os.environ.get("V550_REPORT_HMAC_KEYS_JSON")
    if not source:
        raise ValueError("V550_REPORT_HMAC_KEYS_JSON is required")
    try:
        value = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ValueError(f"V550_REPORT_HMAC_KEYS_JSON is invalid JSON: {exc}") from exc
    if not isinstance(value, dict) or not value:
        raise ValueError("V550_REPORT_HMAC_KEYS_JSON must be a non-empty object")
    keyring: dict[str, str] = {}
    for version, secret in value.items():
        if not isinstance(version, str) or not version or not isinstance(secret, str) or len(secret) < 32:
            raise ValueError("every HMAC key version needs a secret of at least 32 characters")
        keyring[version] = secret
    return keyring


def add(errors: list[dict[str, str]], code: str, message: str) -> None:
    errors.append({"code": code, "message": message})


def validate_receipt_shape(receipt: Any, errors: list[dict[str, str]]) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        add(errors, "RECEIPT_TYPE", "Receipt must be an object.")
        return {}
    missing = REQUIRED_RECEIPT_FIELDS - receipt.keys()
    unknown = receipt.keys() - REQUIRED_RECEIPT_FIELDS
    for key in sorted(missing):
        add(errors, "RECEIPT_FIELD", f"Receipt field {key} is required.")
    for key in sorted(unknown):
        add(errors, "RECEIPT_UNKNOWN_FIELD", f"Receipt field {key} is not allowed.")
    if not isinstance(receipt.get("reportId"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}", receipt.get("reportId", "")):
        add(errors, "REPORT_ID", "Report ID format is invalid.")
    for key in ("stageAttempt", "generation", "byteLength"):
        if not isinstance(receipt.get(key), int) or isinstance(receipt.get(key), bool) or receipt.get(key, 0) < 1:
            add(errors, key.upper(), f"{key} must be a positive integer.")
    if not isinstance(receipt.get("byteHash"), str) or not HEX_64.fullmatch(receipt.get("byteHash", "")):
        add(errors, "BYTE_HASH", "Receipt byteHash must be lowercase SHA-256 hex.")
    for key in ("schemaVersion", "templateVersion"):
        if not isinstance(receipt.get(key), str) or not VERSION.fullmatch(receipt.get(key, "")):
            add(errors, "VERSION", f"{key} must use numeric semantic version form.")
    try:
        if not isinstance(receipt.get("issuedAt"), str):
            raise ValueError
        dt.datetime.fromisoformat(receipt["issuedAt"].replace("Z", "+00:00"))
    except ValueError:
        add(errors, "ISSUED_AT", "issuedAt must be an ISO 8601 timestamp.")
    signature = receipt.get("receiptSignature")
    if not isinstance(signature, str) or not HEX_64.fullmatch(signature):
        add(errors, "RECEIPT_SIGNATURE", "Receipt signature must be lowercase HMAC-SHA256 hex.")
    generation = receipt.get("generation")
    status = receipt.get("reportStatus")
    prior = receipt.get("priorReportId")
    if generation == 1:
        if prior is not None:
            add(errors, "PRIOR_REPORT", "An original report must not link to a prior report.")
        if status not in {"ORIGINAL", "Generation 1 — ORIGINAL"}:
            add(errors, "REPORT_STATUS", "Generation 1 must carry original status.")
    elif isinstance(generation, int) and generation > 1:
        if not isinstance(prior, str) or not prior.strip():
            add(errors, "PRIOR_REPORT", "A regenerated report must link to its prior issuance.")
        expected_watermark = f"REGENERATED COPY — GENERATION {generation} — PREVIOUS ISSUANCE EXISTS"
        if status not in {"REGENERATED", expected_watermark}:
            add(errors, "REPORT_STATUS", "Regenerated status/watermark does not match its generation.")
    return receipt


def validate(
    report_bytes: bytes,
    receipt: Any,
    keyring: dict[str, str],
    *,
    max_bytes: int = 2_000_000,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    receipt = validate_receipt_shape(receipt, errors)
    if not report_bytes.startswith(b"%PDF-"):
        add(errors, "PDF_MAGIC", "Report is not a PDF.")
    if len(report_bytes) > max_bytes:
        add(errors, "FILE_SIZE", f"Report exceeds {max_bytes} bytes.")
    pages = page_count(report_bytes)
    if pages != 1:
        add(errors, "PAGE_COUNT", f"Expected exactly one page; found {pages}.")
    count_match = re.search(rb"/Count\s+(\d+)", report_bytes)
    if not count_match or int(count_match.group(1)) != 1:
        add(errors, "PAGE_TREE_COUNT", "PDF page tree must declare exactly one page.")
    if not re.search(rb"/MediaBox\s*\[\s*0(?:\.0+)?\s+0(?:\.0+)?\s+612(?:\.0+)?\s+792(?:\.0+)?\s*\]", report_bytes):
        add(errors, "PAGE_SIZE", "Report must use US Letter media bounds (612 × 792 points).")
    for token, code in ((b"/AcroForm", "INTERACTIVE_FORM"), (b"/Annots", "ANNOTATIONS"), (b"/JavaScript", "ACTIVE_CONTENT"), (b"/EmbeddedFile", "EMBEDDED_FILE")):
        if token in report_bytes:
            add(errors, code, "Authoritative report must be flattened and contain no active/embedded content.")
    font_sizes = [float(value) for value in re.findall(rb"(?:/[A-Za-z0-9]+\s+)?([0-9]+(?:\.[0-9]+)?)\s+Tf\b", report_bytes)]
    if not font_sizes or min(font_sizes) < 8:
        add(errors, "READABILITY", "Report text must use a readable font size of at least 8 points.")

    actual_hash = hashlib.sha256(report_bytes).hexdigest()
    if receipt and receipt.get("byteHash") != actual_hash:
        add(errors, "HASH_MISMATCH", VERIFICATION_FAILED)
    if receipt and receipt.get("byteLength") != len(report_bytes):
        add(errors, "LENGTH_MISMATCH", VERIFICATION_FAILED)

    key_version = receipt.get("keyVersion") if receipt else None
    secret = keyring.get(key_version) if isinstance(key_version, str) else None
    if secret is None:
        add(errors, "UNKNOWN_KEY_VERSION", "Receipt key version is unavailable or unknown.")
    elif isinstance(receipt.get("receiptSignature"), str):
        expected = hmac.new(secret.encode("utf-8"), canonical_receipt_bytes(receipt), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, receipt["receiptSignature"]):
            add(errors, "SIGNATURE_MISMATCH", VERIFICATION_FAILED)

    generation = receipt.get("generation") if receipt else None
    if errors:
        status = VERIFICATION_FAILED
    elif generation == 1:
        status = VALID_ORIGINAL
    else:
        status = VALID_REGENERATED.format(generation=generation)
    return {
        "valid": not errors,
        "status": status,
        "sha256": actual_hash,
        "byteLength": len(report_bytes),
        "pageCount": pages,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--keyring-json", help="Testing override; production should use the environment keyring")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        report_bytes = args.report.read_bytes()
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        keyring = load_keyring(args.keyring_json)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"valid": False, "status": VERIFICATION_FAILED, "errors": [{"code": "READ_OR_KEYRING", "message": str(exc)}]}, ensure_ascii=False))
        return 2
    result = validate(report_bytes, receipt, keyring, max_bytes=args.max_bytes)
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
