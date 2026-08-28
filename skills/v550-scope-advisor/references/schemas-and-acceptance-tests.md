# Schemas and Acceptance Tests

## Contents

- Frozen schema boundary
- Canonical synchronization
- Validator contracts
- Acceptance groups
- Completion evidence

## Frozen schema boundary

Preserve the six existing JSON Schema files and their field meanings. Do not add, remove, rename, or repurpose student artifact fields, telemetry columns, event types, protocol roles, or GPT Action operations for the Waldron scenario.

Map new labels into existing notes/metadata:

- Gate 2 source/type/evidence/status live within existing requirement text/notes/metadata.
- Gate 6 `time_window`, `people_hours`, and resource-vector labels live within existing WBS dictionary notes/metadata.
- Gate 6B lives in the existing assumption log, Gate 5 artifacts, WBS, revision ledger, and Gate 6 history.
- Student-facing `OPEN` serializes to the existing passing outcome and `CLOSED` to the existing revision/incomplete outcome.
- Server-derived stage attempt uses the existing `attempt_number` storage field.

Schema validation fails closed. Never guess or repair identity, grade, outcome, attempt, generation, or hash.

Known authority conflict: the unchanged evaluator schema's `gate_result` `PASS` conditional requires legacy advisory flags such as `minimum_average_met`, `no_dimension_score_of_one`, and `learning_checks_complete` to be true. The consolidated six-gate policy explicitly makes those signals non-blocking. Do not falsify the booleans and do not change the locked schema. Keep this production-certification blocker visible until the instructor/schema owner authorizes a narrow schema correction or a documented compatibility interpretation.

## Canonical synchronization

`canonical-source-manifest.json` declares the three canonical frozen references plus the canonical legacy Gate 1 comparison-example file, every generated destination, and expected SHA-256. The manifest never lists itself. Runtime copies and demo fixtures are generated products, not authoring surfaces.

`sync_runtime_knowledge.py` must copy exact bytes atomically and update digests. `verify_canonical_knowledge.py` must fail on wrong source hashes, missing destinations, byte drift, undeclared destinations within protected generated roots, invalid paths, or any Gate 1 registry other than exactly one complete, source-verified, accurately labeled instructor-approved comparison example. Missing, malformed, or multiple examples are `INSTRUCTOR MATERIAL NEEDED`, never a student failure. Run verification before tests, packaging, deployment, and completion.

## Validator contracts

- `validate_frozen_gate_submission.py INPUT.json` preserves and merges draft updates, emits no formal status without an explicit ready signal, and returns a companion-first student response plus a private deterministic trace on formal evaluation. An explicitly submitted no-attempt returns diagnostic `INCOMPLETE` with no hard-check run or recorded attempt. The corrected/expanded answer and one improvement reason may span post-closure messages; issue restatement is not required, and a missing reason alone returns the exact pending one-question reflection state. Exit 0 for `OPEN`, 1 for any non-open interaction/result, and 2 for malformed input or instructor-material failure.
- `validate_scope_artifacts.py INPUT.json` validates the existing Scope schema and applies frozen package invariants by default. `--schema-only` is reserved for intentional non-Waldron schema checks. The validator must not impose evaluator/criteria thresholds, and provenance ledger entries may record observed AI suggestions without turning those suggestions into assessed artifact drafts.
- `validate_telemetry_payload.py INPUT.json` rejects unknown fields, direct/sensitive content, client-derived server fields, role/event mismatch, unapproved endpoint payloads, missing/ambiguous gate identity codes, and reason-code/outcome contradictions.
- `validate_report_integrity.py PDF --receipt RECEIPT.json` verifies byte hash, length, issuance consistency, and an authenticated receipt using the server key/keyring. A matching edited PDF plus edited receipt must fail.
- `verify_canonical_knowledge.py` returns nonzero for any drift.

## Acceptance groups

Run automated tests that cover:

1. every explicit hard check with an isolated failing fixture;
2. at least one weak-criteria/all-hard-checks-pass fixture for every gate;
3. multiple failures reported together;
4. contradiction not passing through lexical mention;
5. the two post-closure revision elements only after prior closure, with no issue restatement, exact labels, or complete re-paste;
6. ordinary cross-gate inconsistency remaining feedback;
7. Gate 6 deliverable trace and Gate 6B reconciliation as the only explicit blocking cross-gate cases;
8. no-answer/direct-answer/model-answer withholding;
9. canonical byte equality and drift detection;
10. schema and telemetry fail-closed behavior;
11. consent-before-write, idempotency, one-tab, controlled gate identities, affected-gate attempt activation, and ordered downstream re-evaluation;
12. Gate 6-only report authorization, schema-shaped authoritative server model, server rendering/storage/hash/signature, byte-identical redownload, visible regeneration, key rotation, and four verifier statuses;
13. single-page readable report layout and no sensitive/transcript content;
14. eight-dimension evaluator calibration within ±1;
15. exact six-gate ordering with internal 6B and no Stage 2 output.
16. all 36 companion regressions: the original drafting/usability/burden behaviors plus six-gate focus paths, source correction, no override, injection resistance, isolated test mode, grounding, acceptable approximations, fixed facts, and exact hard boundaries.
17. byte equality for the private course-concept source map and explicit `PMBOK SOURCE NOT PROVIDED` status.

The consolidated demo in `frozen-demo-script.md` is mandatory: deficient Gate 1 and Gate 2 submissions close, a compliant Gate 1 opens, and a Gate 2 cross-gate disconnect remains feedback while the gate opens.

## Completion evidence

Before declaring done, record:

- resolved skill-creator helper and install target;
- `quick_validate.py` result and generated `agents/openai.yaml` result;
- architecture summary and requirements traceability;
- privacy/data-flow review;
- evaluator calibration;
- canonical manifest/equality result;
- report lifecycle and verifier results;
- acceptance and pedagogical forward tests;
- instructor-editable settings;
- only decisions that genuinely require instructor authority.

Do not weaken a locked requirement to make a test pass. If a platform integration cannot be executed locally, keep its deterministic/state tests and document the precise deployment-only check.
