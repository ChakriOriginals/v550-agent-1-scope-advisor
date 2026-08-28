# V550 AI Usage & Learning Report

> Server-rendered US Letter PDF; exactly one readable page. Flatten the final PDF. The instructor-controlled backend renders once, stores the exact bytes, rereads and hashes the stored object, and signs private registry metadata. Never render the authoritative report in ChatGPT or accept client-supplied prose, bytes, attempt, generation, hash, signature, status, or storage ID.

<!-- Resolve issuance, watermark, and verifier strings from status_vocabulary in the frozen machine contract. Do not duplicate those strings in renderer code. Omit the watermark region for an original issuance. Build prose only from server-held structured metrics, reason codes, and sanitized summaries. Never include transcripts, draft fragments, evaluator quotes, inferred motives, generic praise, a download capability, verification token, signing secret, Drive path, storage-object ID, or private byte hash in the report body or QR. -->

## Course and issuance

| Field | Server-derived value |
|---|---|
| Course / stage | {{course}} / {{stage}} |
| Pseudonymous student key | {{student_key}} |
| Sanitized project title | {{sanitized_project_title}} |
| Session / Stage 1 attempt | {{session_id}} / {{stage_attempt}} |
| Report ID | {{report_id}} |
| Issued at | {{issued_at}} |
| Schema / rubric / template | {{schema_version}} / {{rubric_version}} / {{template_version}} |
| Generation | {{generation_label}} |

{{regeneration_watermark_if_required}}

## Learning signals

| Signal | Evidence-based value |
|---|---|
| Critique depth, 0-3 | {{critique_depth}} — {{critique_depth_plain_language}} |
| AI-reliance index | {{ai_reliance_index_or_na}} |
| Guidance dispositions | Accepted verbatim: {{accepted_verbatim_count}} · Challenged/modified: {{challenged_or_modified_count}} · Rejected: {{rejected_count}} |
| Substantive iterations | {{substantive_iteration_count}} |
| Gate attempts / outcome | {{gate_attempt_count}} / {{gate_outcome}} |
| Controlled misconception flags | {{misconception_flags_or_none}} |

## What the evidence shows

{{deterministic_evidence_paragraph}}

## Where AI reliance is helping or hurting

{{deterministic_reliance_paragraph}}

## One next behavior

{{one_concrete_next_behavior}}

## What was logged — and what was not

Logged: the course-issued pseudonymous key; server-created session, event, gate, attempt, and report identifiers; server timestamps; structured critique, guidance-disposition, iteration, gate, misconception, score, summary, and report-receipt fields.

Not logged: names or contact details; transcript or chat text; full drafts; evaluator evidence excerpts; hidden reasoning; sensitive information; unrelated history; inferred motives; class rank or named comparisons with other students; emotional or psychological profiles; actual grades; credentials or secrets.

## Verification

- Non-secret receipt / QR: {{non_secret_verification_receipt_or_qr}}
- Evaluator instruction: use the instructor-authenticated verifier to hash the submitted PDF bytes and compare them with the signed private Report Registry record for this report ID.

> This report is advisory evidence about observed AI-use behavior. Canvas LMS and the instructor remain authoritative for grading.
