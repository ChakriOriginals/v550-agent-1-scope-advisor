# V550 AI Usage & Learning Report

## Authority and trigger

The instructor-controlled Apps Script backend is the only authoritative issuer. Gate 6 must be `OPEN` after its internal Gate 6B audit for the current server-derived Stage 1 attempt. Gates 1–5 and a closed Gate 6 never issue a final report.

ChatGPT and the student client may request issuance but may not render or upload the authoritative PDF, choose final prose, attempt, generation, report ID, issuance time/status, hash, signature, storage object, template version, or schema version.

## Server transaction

Run the complete issuance under a server lock:

1. Authorize the allowlisted pseudonymous key/session and read current server-held gate/revision state.
2. Verify Gate 6 `OPEN` after `assumption_audit_completed`, the final revision record, and downstream re-evaluation required for the attempt.
3. Derive the monotonic stage attempt, generation, report ID, issuance time, and status.
4. Freeze an immutable snapshot of structured metrics, reason codes, dimension scores, and sanitized summary lines.
5. Build analysis prose and a render-only view with the versioned deterministic rules in `ReportRenderer.gs`; never accept final prose or transcript/draft text from the client.
6. Render one flattened US Letter page once.
7. Store the exact bytes as a new object in the restricted instructor-owned folder. Never overwrite an earlier issuance.
8. Re-read the stored object bytes, calculate byte length and SHA-256, then build the authoritative snake-case internal model with the truthful receipt fields and validate every unchanged report-schema field, enum, range, privacy assertion, and issuance relation server-side.
9. Hash the validated model and HMAC-sign the canonical registry fields with the active Script Properties key version while preserving historical keys for verification.
10. Return only `reportId`, `generationNumber`, `issuedAtServer`, and `verificationToken`. The last field is a short-lived capability URL bound to this key/session/object.

The registry is security infrastructure, not a student artifact, telemetry extension, or GPT Action response. It stores the object ID, byte length/hash, report/session/attempt/generation data, prior issuance link, template/schema versions, HMAC, and key version.

## Visible one-page content

Title the document `V550 AI Usage & Learning Report`. Use a 612 × 792 point US Letter page, readable body text of at least 9 points, no form fields, annotations, JavaScript, or embedded files, and no second page.

Include:

- course and Stage 1;
- pseudonymous key and sanitized project title;
- session ID and server-derived attempt;
- report ID, issuance time, schema/template version, and generation;
- critique depth 0–3 and plain-language interpretation;
- accepted-verbatim, challenged/modified, and rejected counts plus AI-reliance index or `N/A`;
- substantive iteration and gate-attempt counts;
- latest gate outcome and misconception codes, if any;
- short `What the evidence shows` and `Where AI reliance is helping or hurting` paragraphs produced by deterministic rules;
- one concrete next behavior;
- a plain-language logging/non-logging note;
- report ID, non-secret verification receipt/QR, and instructor-verification instructions.

Exclude transcripts, draft fragments, evaluator quotations, direct identifiers, sensitive data, unrelated history, actual grades, rank, named comparisons, motives, accusations, emotional/psychological profiles, download capability, Drive/object IDs, and signing secrets.

## Evidence language

Describe observed counts and revision patterns candidly. Do not default to praise and do not accuse the student of misconduct or infer why they regenerated. A high AI-reliance value is a learning signal, not proof of intent.

Calculate:

`accepted_verbatim / (accepted_verbatim + challenged_or_modified + rejected) × 100`

Return `N/A` when the denominator is zero. Critique depth and all evaluator dimensions remain advisory; the report is not a Canvas grade.

## Download and regeneration

- Normal download, redownload, or capability refresh streams the exact stored bytes. It never calls the renderer and never increments generation.
- The first report for an attempt is `Generation 1 — ORIGINAL`.
- An explicit create-again request with no qualifying new student work creates a new immutable object, increments generation, links the prior issuance, and displays `REGENERATED COPY — GENERATION N — PREVIOUS ISSUANCE EXISTS`.
- A report request alone never changes the stage attempt.
- A later attempt requires a post-issuance artifact version plus `revision_submitted`, affected `gate_attempt`/`gate_result`, every downstream re-evaluation, and Gate 6 reopening after Gate 6B.
- Preserve every earlier report, metric snapshot, and event.

## Instructor verification

The verifier is authenticated and outside the student GPT Action. It finds the report ID in the private registry, verifies the stored registry HMAC with its historical key version, hashes the submitted bytes, and compares byte length/hash in constant time.

Return only one exact status and minimal receipt metadata:

- `VALID ORIGINAL`
- `VALID REGENERATED COPY — GENERATION N`
- `VERIFICATION FAILED — FILE MAY HAVE BEEN MODIFIED`
- `UNKNOWN REPORT ID`

A student- or client-provided hash never establishes validity. Matching bytes without a valid signed registry row also fail.

## Local tools

`reports/templates/report-model.example.json` is a schema-valid example of the backend's authoritative internal report model. Its receipt fields are private server/registry data; the visible-page rules above determine which fields the renderer may print.

`reports/templates/report-preview-input.example.json` is the privacy-safe input for `reports/tools/generate_report.py --qa-preview`:

```bash
python3 pm-studio-plus/reports/tools/generate_report.py \
  pm-studio-plus/reports/templates/report-preview-input.example.json \
  /tmp/v550-report-preview.pdf \
  --qa-preview
```

The tool creates a conspicuously non-authoritative layout preview only. It rejects the authoritative model and any other input containing server-owned issuance fields; do not weaken that boundary. It cannot produce a receipt or submission artifact. Authoritative rendering is implemented in the backend.

`reports/tools/verify_report.py` delegates to the skill’s HMAC-aware byte validator. Production instructor verification additionally performs the private registry lookup and authentication implemented in Apps Script.
