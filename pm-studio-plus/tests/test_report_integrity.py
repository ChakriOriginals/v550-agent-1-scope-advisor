"""Authenticated report-byte and one-page integrity acceptance tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from support import REPORT_VALIDATOR


KEYRING_ENV = "V550_REPORT_HMAC_KEYS_JSON"
KEY_V1 = "synthetic-v550-hmac-key-v1-at-least-32-characters"
KEY_V2 = "synthetic-v550-hmac-key-v2-at-least-32-characters"


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def minimal_pdf(
    *,
    generation: int = 1,
    report_id: str = "rpt_test_0001",
    font_size: int = 9,
) -> bytes:
    label = (
        "Generation 1 — ORIGINAL"
        if generation == 1
        else f"REGENERATED COPY — GENERATION {generation} — PREVIOUS ISSUANCE EXISTS"
    )
    visible = f"{label} Report {report_id} Attempt 1"
    return (
        "%PDF-1.4\n"
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
        "4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        f"5 0 obj\n<< /Length 160 >>\nstream\nBT /F1 {font_size} Tf 36 740 Td "
        f"({visible}) Tj ET\nendstream\nendobj\n"
        "trailer\n<< /Root 1 0 R >>\n%%EOF\n"
    ).encode("cp1252")


def signed_receipt(
    pdf: bytes,
    *,
    generation: int = 1,
    report_id: str = "rpt_test_0001",
    key_version: str = "v1",
    key: str = KEY_V1,
) -> dict[str, Any]:
    unsigned: dict[str, Any] = {
        "reportId": report_id,
        "stageAttempt": 1,
        "generation": generation,
        "issuedAt": "2026-08-07T18:00:00Z",
        "schemaVersion": "2.0.0",
        "templateVersion": "2.0.0",
        "byteHash": hashlib.sha256(pdf).hexdigest(),
        "byteLength": len(pdf),
        "keyVersion": key_version,
        "priorReportId": None if generation == 1 else "rpt_test_0000",
        "reportStatus": "ORIGINAL" if generation == 1 else "REGENERATED",
    }
    signature = hmac.new(key.encode("utf-8"), canonical_json(unsigned), hashlib.sha256)
    return {**unsigned, "receiptSignature": signature.hexdigest()}


def run_validator(
    pdf: bytes,
    receipt: dict[str, Any],
    *,
    keyring: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    if not REPORT_VALIDATOR.is_file():
        raise AssertionError(f"Missing report validator: {REPORT_VALIDATOR}")
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment[KEYRING_ENV] = json.dumps(keyring or {"v1": KEY_V1, "v2": KEY_V2})
    with tempfile.TemporaryDirectory() as directory:
        report_path = Path(directory) / "report.pdf"
        receipt_path = Path(directory) / "receipt.json"
        report_path.write_bytes(pdf)
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        process = subprocess.run(
            [
                sys.executable,
                str(REPORT_VALIDATOR),
                str(report_path),
                "--receipt",
                str(receipt_path),
            ],
            capture_output=True,
            text=True,
            env=environment,
        )
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Report validator returned non-JSON output: {process.stdout!r} {process.stderr!r}"
        ) from exc
    if not isinstance(result, dict):
        raise AssertionError("Report validator JSON root must be an object")
    return process, result


class ReportIntegrityTests(unittest.TestCase):
    def test_valid_original_has_exact_status(self) -> None:
        pdf = minimal_pdf()
        process, result = run_validator(pdf, signed_receipt(pdf))
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertTrue(result.get("valid"), result)
        self.assertEqual(result.get("status"), "VALID ORIGINAL")
        self.assertEqual(result.get("pageCount"), 1)

    def test_valid_regenerated_copy_has_exact_generation_status(self) -> None:
        pdf = minimal_pdf(generation=2, report_id="rpt_test_0002")
        receipt = signed_receipt(pdf, generation=2, report_id="rpt_test_0002")
        process, result = run_validator(pdf, receipt)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertTrue(result.get("valid"), result)
        self.assertEqual(result.get("status"), "VALID REGENERATED COPY — GENERATION 2")

    def test_manual_pdf_edit_fails(self) -> None:
        pdf = minimal_pdf()
        receipt = signed_receipt(pdf)
        process, result = run_validator(pdf + b"manual edit", receipt)
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(result.get("valid"), result)
        self.assertEqual(
            result.get("status"),
            "VERIFICATION FAILED — FILE MAY HAVE BEEN MODIFIED",
        )

    def test_edited_pdf_and_matching_edited_receipt_hash_still_fail_hmac(self) -> None:
        original = minimal_pdf()
        receipt = signed_receipt(original)
        edited = original + b"manual edit"
        receipt["byteHash"] = hashlib.sha256(edited).hexdigest()
        receipt["byteLength"] = len(edited)
        process, result = run_validator(edited, receipt)
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(result.get("valid"), result)
        self.assertEqual(
            result.get("status"),
            "VERIFICATION FAILED — FILE MAY HAVE BEEN MODIFIED",
        )

    def test_copied_report_id_with_different_bytes_fails(self) -> None:
        original = minimal_pdf(report_id="rpt_copied_0001")
        receipt = signed_receipt(original, report_id="rpt_copied_0001")
        substituted = minimal_pdf(report_id="rpt_copied_0001", font_size=10)
        process, result = run_validator(substituted, receipt)
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(result.get("valid"), result)

    def test_unknown_key_version_and_wrong_key_fail_closed(self) -> None:
        pdf = minimal_pdf()
        unknown = signed_receipt(
            pdf,
            key_version="retired-without-history",
            key="unknown-key-material-at-least-32-characters",
        )
        process, result = run_validator(pdf, unknown)
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(result.get("valid"), result)

        wrong = signed_receipt(pdf, key="wrong-key-material-at-least-32-characters")
        process, result = run_validator(pdf, wrong)
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(result.get("valid"), result)

    def test_key_rotation_preserves_historical_verification(self) -> None:
        original_pdf = minimal_pdf(report_id="rpt_historical_0001")
        original_receipt = signed_receipt(
            original_pdf,
            report_id="rpt_historical_0001",
            key_version="v1",
            key=KEY_V1,
        )
        process, original_result = run_validator(
            original_pdf,
            original_receipt,
            keyring={"v1": KEY_V1, "v2": KEY_V2},
        )
        self.assertEqual(process.returncode, 0, original_result)

        current_pdf = minimal_pdf(report_id="rpt_current_0001")
        current_receipt = signed_receipt(
            current_pdf,
            report_id="rpt_current_0001",
            key_version="v2",
            key=KEY_V2,
        )
        process, current_result = run_validator(
            current_pdf,
            current_receipt,
            keyring={"v1": KEY_V1, "v2": KEY_V2},
        )
        self.assertEqual(process.returncode, 0, current_result)

    def test_receipt_attempt_generation_status_and_prior_link_are_consistent(self) -> None:
        pdf = minimal_pdf()
        receipt = signed_receipt(pdf)
        for field, invalid in (
            ("stageAttempt", 0),
            ("generation", 2),
            ("reportStatus", "REGENERATED"),
            ("priorReportId", "rpt_prior_should_be_null"),
        ):
            with self.subTest(field=field):
                mutated = dict(receipt)
                mutated[field] = invalid
                # Even a validly recomputed signature must not make inconsistent metadata valid.
                unsigned = {key: value for key, value in mutated.items() if key != "receiptSignature"}
                mutated["receiptSignature"] = hmac.new(
                    KEY_V1.encode("utf-8"), canonical_json(unsigned), hashlib.sha256
                ).hexdigest()
                process, result = run_validator(pdf, mutated)
                self.assertNotEqual(process.returncode, 0)
                self.assertFalse(result.get("valid"), result)

    def test_report_must_be_single_us_letter_flattened_and_readable(self) -> None:
        two_pages = minimal_pdf().replace(b"/Count 1", b"/Count 2").replace(
            b"/Kids [3 0 R]", b"/Kids [3 0 R 3 0 R]"
        )
        process, result = run_validator(two_pages, signed_receipt(two_pages))
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(result.get("valid"), result)

        low_font = minimal_pdf(font_size=5)
        process, result = run_validator(low_font, signed_receipt(low_font))
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(result.get("valid"), result)

        annotated = minimal_pdf().replace(b"/Contents 5 0 R", b"/Annots [6 0 R] /Contents 5 0 R")
        process, result = run_validator(annotated, signed_receipt(annotated))
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(result.get("valid"), result)


if __name__ == "__main__":
    unittest.main()
