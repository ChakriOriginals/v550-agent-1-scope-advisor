# Instructor Configuration

## Final-build teaching and integrity defaults

Keep the focus-question, source-recheck, untrusted-content, semantic-validation, and numerical-policy feature flags at their shipped values unless a later instructor-controlled source package explicitly changes them. Focus prompts do not add hard checks. Numerical tolerance defaults to ±5 percent for genuine estimates only; fixed scenario facts and hard boundaries remain exact.

`PMBOK SOURCE NOT PROVIDED` is the current authorized-source state. Do not enable PMBOK attribution until an authorized local edition or excerpt and exact locator are added to the private course-concept source map.

## Instructor test-mode setup and teardown

Never enable test mode in the production deployment. For pre-rollout testing, clone the deployment into an authenticated instructor-only test environment, set `environment: test`, assign a non-production storage namespace, use synthetic student keys, isolate Sheets/Drive/report-registry state, and mark test reports. Then enable test mode. Run both passing and closing fixtures with unchanged gate truth.

After testing, disable test mode, retain or destroy isolated fixtures under instructor policy, and verify the production configuration still has `enabled: false`. Deployment must stop before any write if test mode is enabled outside the test environment or if the test namespace is missing, non-isolated, or equal to production.

Use `config/instructor-config.yaml` as the centralized, versioned policy file. Keep `deployment_ready: false` until every instructor decision, secret, tenant check, and deployment validation below is complete. Do not scatter course term, feature flags, rubric anchors, report policy, or retention values through prompts and code.

## Values to set before deployment

In `config/instructor-config.yaml`:

- set `course.term`;
- replace `course.retention_days_after_term_end` with the IU-approved period;
- set the report capability lifetime within the backend-supported range;
- confirm the course timezone and report template/schema versions;
- review every locked default and record any instructor-authorized exception before changing it.

In the Custom GPT Action configuration:

- replace the placeholder deployment URL with the approved Apps Script web-app URL;
- confirm the visible Action permission disclosure;
- expose exactly `startSession`, `logEvent`, `closeSession`, and `issueReport`.

In Apps Script Script Properties:

| Property | Purpose |
|---|---|
| `CLASS_DEPLOYMENT_TOKEN` | Term-scoped server deployment token. |
| `ACTIVE_STUDENT_KEYS_JSON` | Allowlist keyed by the course-issued opaque student key. |
| `WORKBOOK_ID` | Instructor-owned IU workbook. |
| `REPORT_DRIVE_FOLDER_ID` | Dedicated restricted folder for immutable issued PDF objects. |
| `REPORT_HMAC_KEYS_JSON` | Versioned report-signing key map. |
| `REPORT_HMAC_ACTIVE_KEY_VERSION` | Active signing-key version; retain old keys for historical verification. |
| `REPORT_TEMPLATE_VERSION` | Deployed server renderer/template version. |
| `REPORT_SCHEMA_VERSION` | Deployed report schema version. |
| `REPORT_CAPABILITY_TTL_SECONDS` | Optional short-lived capability lifetime; backend default is 900 seconds. |
| `INSTRUCTOR_VERIFIER_TOKEN` | Instructor-only verifier authorization. |

Use `REPORT_HMAC_SECRET` only for the documented development-compatibility path, never as the production key-rotation design. Do not put any property value in prompts, knowledge files, schemas, source control, the workbook, the report body, or student-visible logs.

## Locked defaults

- Stage 1 Scope Advisor only; later advisors are interface references, not runnable workflows.
- Exactly six numbered gates in the canonical order. Deliverables and the Scope Action Plan live inside Gate 5; the Assumption / Scope-Creep Audit and Revision lives inside Gate 6.
- Guided coaching is the default, Independent mode remains available, Guided gate introductions stay at or below 120 words, default student checklists stay at or below six bullets, and partial messages accumulate in one preserved working draft.
- A student-authored attempt and explicit ready signal precede formal evaluation. No AI-authored preliminary or assignment-ready Waldron artifact.
- Gate 1 Part C uses exactly one instructor-provided canonical comparison example; students are not assigned outside research, source discovery, citation verification, or another example.
- Applicable canonical hard checks alone determine `OPEN` or `CLOSED`; after a prior closure, only the corrected/expanded answer and one brief improvement reason are required and may be recognized naturally across messages without issue restatement, exact labels, or a full re-paste.
- Criteria, rubric scores, learning signals, critique depth, and ordinary cross-gate consistency are advisory and non-blocking.
- Legacy presentation maps `OPEN` to `PASS`, `CLOSED` to `REVISE`, and no meaningful work or repeated refusal to diagnostic `INCOMPLETE`. The diagnostic outcome records no gate attempt or closure and does not activate the post-closure revision requirement.
- The existing seven protocol roles, six schema files, event vocabulary, and four Action operations stay unchanged.
- WBS depth and the 100% rule are feedback criteria. The canonical Gate 6 traceability, ownership, time/hour, resource-vector, resource-summary, effort-ceiling, and Gate 6B checks remain blocking.
- One course-issued pseudonymous key is the only student-entered check-in value; visible consent precedes the first Action.
- Telemetry is write-only, minimized, and contains no transcripts, full drafts, evidence excerpts, direct identifiers, sensitive information, secrets, or actual grades.
- Distress and product-error turns pause evaluation, preserve completed work, and create no gate attempt; emotional wording is never persisted, while the only permitted operational note is `student requested slower pacing`.
- The instructor backend renders and stores authoritative report bytes. ChatGPT never renders, hashes, or registers the authoritative PDF.
- Canvas LMS and instructor judgment remain authoritative for grading.

## Instructor-authority decisions still open

1. Confirm the term, course-day cutoff, late-session rollup behavior, and retention/appeal period.
2. Approve opaque key issuance, replacement, revocation, and roster-mapping procedures.
3. Confirm the IU ChatGPT Edu tenant supports private chats, private Canvas/Living Project File behavior, and Actions as designed.
4. Approve the versioned Markdown checkpoint fallback when ChatGPT Canvas export is unavailable.
5. Supply professor-scored, synthetic or fully anonymized calibration fixtures.
6. Approve the one-page report's minimum readable font and final evaluator-facing language.
7. Create and approve the restricted report folder, named-person sharing, immutable-object policy, and orphan cleanup procedure.
8. Set capability TTL, signing-key rotation and historical-key retention, and report template/schema version policy.
9. Define instructor/TA verifier access, token rotation, and audit procedure.
10. Confirm workbook/dashboard sharing and the Canvas submission/verification workflow.
11. Resolve the locked `evaluator.schema.json` gate-result `PASS` conditional conflict: authorize either a narrow schema correction or a documented compatibility interpretation that does not falsify advisory booleans.

Record each decision with an owner, date, and approved value. Do not mark the deployment ready based only on local tests.
