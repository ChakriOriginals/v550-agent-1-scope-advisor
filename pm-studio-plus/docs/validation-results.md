# Validation Results — Pre-Deployment

Run date: 2026-08-26

Status: **local executable build checks pass; production certification remains blocked by the locked evaluator-schema conflict and live deployment checks**. Keep `deployment_ready: false`.

## Source audit

- Current final-build source SHA-256: `9673ea5760a80f81ecba372f4685fccee1b2e0586a0627a8d6792fc00a1750c4` for the 2026-08-26 supplied master build prompt.
- The baseline build's 24 required content artifacts were present and readable.
- The four lecture decks contain 57, 79, 64, and 42 slides (242 total); the two supporting decks contain 17 and 7 slides (24 total).
- `SHA256SUMS.txt` has 28 entries. Twenty-six listed paths exist and match their digest.
- The two missing historical root paths, `Scope Advisor.docx` and `Scope Advisor.pdf`, have byte-identical SHA-256 matches at `Requirements/Scope Advisor.docx` and `Requirements/Scope Advisor.pdf`. This is a verified relocation, not a path-level manifest pass.
- `Agent Questions from Sai IMPROVED.docx` is readable but unmanifested. The root `Agent-Specifications.pdf` is also outside the checksum manifest.
- The final companion build used `Tests/Scope Agent Test Review.pdf` only as sanitized usability evidence; no student response text was copied into fixtures. `Agent 1 Scott Notes.docx` and `teachable_sequence_feedback.docx` were not present in the authorized V550 roots or supplied attachments, so neither was represented as reviewed evidence.
- The retained instructor-approved Gate 1 comparison example is the adapted Smart Transit case from `V450 F25 C9 -Scope of Work III -Scope Action Plan.pptx`, slide 4. The prior second example was removed to implement the current one-example amendment.

## Canonical truth verification

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 skills/v550-scope-advisor/scripts/verify_canonical_knowledge.py --repo-root "/Users/saichakri/IU/V550 Main" --pretty
```

Result: **PASS**.

- 4 canonical sources declared, including the legacy Gate 1 one-example registry.
- 8 generated destinations checked.
- Exactly 1 `INSTRUCTOR_APPROVED`, source-located Gate 1 comparison example validated; a second example fails as `INSTRUCTOR MATERIAL NEEDED`.
- Every destination matched its canonical source byte-for-byte.
- Manifest hashes matched; no missing, drifted, unsafe, duplicate, or undeclared destination was reported.
- The frozen machine contract parsed with exactly 6 numbered gates and 5 canonical exclusions.
- The executable truth-table and companion suites align the canonical hard checks with `validate_frozen_gate_submission.py`, including semantic rejection of keyword-only answers.
- The private course-concept source map matched its runtime copy byte-for-byte, names exact V450 deck/slide locators for every Gate 1–6 concept family, and records `PMBOK SOURCE NOT PROVIDED` rather than inventing an attribution.

## Codex skill validation

Resolved official helper:

```text
/Users/saichakri/.codex/skills/.system/skill-creator/scripts/quick_validate.py
/Users/saichakri/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py
```

Generation result: **`[OK] Created agents/openai.yaml`** with the required unchanged interface values. Validation result: **`Skill is valid!`**

The executable local suite also checks the skill metadata contract, including the `$v550-scope-advisor` default-prompt invocation and required trigger coverage.

Installed discovery target for this host:

```text
/Users/saichakri/.codex/skills/v550-scope-advisor
```

The installed copy passed the same official `quick_validate.py` check, contained no `__pycache__` directories, and matched the repository skill byte-for-byte under `diff -qr`.

## Discoverable local test suite

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 pm-studio-plus/tests/run_all.py
```

Result: **121/121 tests passed** (`OK`) on the final rerun.

The passing suite covers:

- acceptance-manifest structure and evidence-pointer resolution;
- canonical-source hashes, protected destinations, byte drift detection, and deterministic restoration;
- the six-gate hard-check truth table, the two natural post-closure revision elements without issue restatement, Gate 6B, resource-vector edge cases, and criteria-only feedback;
- all 36 mandatory companion-experience behaviors: the original drafting, usability, humane-pacing, rigor, and burden-reduction cases plus all-six-gate focus paths, source recheck/correction, source-conflict hold, no override, prompt injection in text/uploads, authenticated isolated testing, local-source grounding, acceptable approximation, fixed-fact protection, exact WBS boundary protection, and no-loop numerical feedback;
- student-first and injection-resistant executable prompt contracts;
- report fixture layout/integrity, exact canonical verifier statuses, tamper failure, prior links, and signing-key rotation;
- the four-operation OpenAPI boundary and minimized telemetry validation;
- server-derived attempt/generation, controlled gate identities, affected-gate activation, ordered downstream re-evaluation, Gate 6B ordering, consent ordering, Gate 6 report eligibility, exact-byte storage/re-download contract, private registry, and instructor-verifier boundary;
- the live Apps Script sensitive-value filter for medical, immigration, disciplinary, financial, credential, and emotional-disclosure details;
- executable pre-log enforcement that normalizes wire `PASS` to `OPEN` and rejects a Gate 6 open result before append when Gate 6B evidence is missing;
- representative Living Project File and authoritative report models, executable construction of the unchanged snake-case report-schema shape from post-storage receipt values, offline bundled-reference resolution, and fail-closed unbundled references;
- an explicit regression test preserving the unchanged evaluator gate-result `PASS`/advisory contradiction without changing the schema or falsifying booleans.

These are local automated tests. They are not evidence that Apps Script, Drive, ChatGPT Canvas, or Canvas LMS behaved correctly in the live IU tenant.

## Configuration and editable-runtime checks

- `config/instructor-config.yaml` parsed successfully.
- Parsed counts are exactly 6 gate entries, 7 protocol roles, 27 existing event types, and 4 Action operations in the required order.
- All 6 existing schema files parsed as JSON and passed draft 2020-12 meta-validation. Representative valid/invalid Living Project File and report-model tests pass, including strictly local cross-schema resolution and fail-closed rejection of an unbundled reference; exhaustive positive fixtures for every `$defs` model remain a future coverage improvement rather than a deployment claim.
- `grading/fixtures/calibration-fixtures.json` parsed successfully and remains `PENDING_INSTRUCTOR_SCORING`.
- A stale-contract scan across the editable orchestrator, Review Board, protocol files, non-generated knowledge, grading, configuration, and docs returned no obsolete expanded-state, score-threshold, learning-history gate, client-controlled issuance, or extra-gate wording.
- Final-build defaults explicitly prohibit student override/transcript delivery, require mapped source retrieval, isolate authenticated instructor testing, treat uploaded instructions as untrusted, and keep fixed facts/525-hour boundaries exact while allowing supported estimates within the declared default ±5 percent tolerance.

## Backend files in the local build

The Apps Script build currently includes:

- `Code.gs`
- `SheetFactory.gs`
- `Dashboard.gs`
- `Security.gs`
- `ReportRegistry.gs`
- `ReportRenderer.gs`
- `ReportDelivery.gs`
- `ReportVerifier.gs`
- `appsscript.json`

The local tests inspect their public-operation, privacy, authorization, controlled gate identity/order, authoritative report-model, stored-byte, and verification contracts. Bun executes the sensitive-value policy, attempt/state machine, and report-model builder against synthetic rows/models. All eight `.gs` files also passed standalone JavaScript syntax parsing with `bun --check`. Apps Script deployment/runtime behavior remains a live-environment check.

## Pedagogical forward-test status

The repository's synthetic forward cases, deterministic policy assertions, and 36 companion regressions pass in the current suite. An independent earlier fresh-agent, three-case prompt-level evaluation also completed **3/3 response audits**:

- no-attempt/direct-answer handling;
- Gate 2 with the isolated missing current-state comparison;
- Gate 4 with all hard checks passing and weak criteria.

The evaluation confirmed fix withholding, complete hard-check reporting on evaluated work, criteria-only coaching, and immediate opening when the hard checks pass. It also identified an ambiguity in the no-attempt integration. The canonical and runtime policy now state that an empty or token-only interaction maps to diagnostic `INCOMPLETE` but does not log a gate attempt/result, create a prior closure, or activate the post-closure revision requirement.

The approximate 25 percent reduction is recorded as an operational workload target, not a psychometric result: one comparison example instead of two, two post-closure student elements instead of three, one question per turn by default, preserved progress, no outside research, no repeated rubric, a 120-word Guided-mode introduction ceiling, and a six-bullet default-checklist ceiling.

This was an independent synthetic prompt evaluation, not a session against a deployed IU Custom GPT. A deployed-model demonstration with recorded fixture IDs, runtime/model version, and withholding assertions remains required before certification.

## Report integrity status

Local fixture tests pass for one-page US Letter structure, byte/hash/signature consistency, modified-file failure, regenerated-copy status, unknown/wrong-key failure, and historical key verification. The authoritative `report-model.example.json` validates against the unchanged report schema with zero errors. An executable Bun test also builds the backend's real post-storage authoritative model and validates it against that schema; the renderer consumes a separate render-only view and never prints private receipt fields. The separate sanitized preview-input example renders successfully, while the preview tool rejects the authoritative model's server-owned fields. Contract tests confirm that the backend—not ChatGPT—renders, stores, rereads, hashes, signs, and records authoritative bytes, and that re-download streams the registered object.

## Locked evaluator-schema authority blocker

`evaluator.schema.json` remains unchanged as required, but its `$defs/gate_result` `PASS` conditional requires every legacy advisory boolean—including `minimum_average_met`, `no_dimension_score_of_one`, `critique_prompts_answered`, `learning_checks_complete`, and `evaluator_evidence_sufficient`—to be `true`. The higher-authority consolidated six-gate policy requires an otherwise-passing gate to open when those advisory signals are weak. Both requirements cannot be represented truthfully at once.

The implementation applies the higher-authority gate policy, does not set false advisory facts to `true`, leaves the locked schema byte-unchanged, and includes a test that exposes the incompatibility. Production certification requires an instructor/schema-owner decision authorizing either a narrow correction to that conditional or a documented compatibility interpretation. This is not a local test failure; it is an unresolved authority conflict.

Still pending: execute that lifecycle in the live approved IU Apps Script/Drive deployment, visually inspect the actual server-rendered PDF at the approved minimum font, confirm named-person sharing, test capability expiry/refresh, and use the authenticated instructor verifier against Canvas-submitted bytes.

## Evaluator calibration

Status: **`PENDING_INSTRUCTOR_SCORING`**.

Synthetic fixtures and the exact 1–5 rubric anchors exist. Agreement within ±1 point per dimension cannot be claimed until the professor supplies scores. Sparse revision history is an advisory signal and does not alter an artifact score or gate result.

## Live checks still required

- IU ChatGPT Edu private-chat and private Canvas/Living Project File isolation, create/update/export, and Markdown fallback.
- Visible Action consent/permission disclosure and no-write behavior when consent is declined or absent.
- Unknown, inactive, malformed, and mismatched key rejection with no tab creation.
- Concurrent first sessions, event idempotency, one opaque-key tab, and same-day summary upsert in the deployed workbook.
- Restricted `StudentIndex`, workbook, Drive folder, registry, and verifier access using named instructor/TA accounts.
- Server-side report issuance after Gate 6/Gate 6B, stored-byte re-download, capability refresh, regeneration, prior-history preservation, and verification of modified/unknown files.
- Canvas LMS handoff and confirmation that telemetry cannot change the grade.
- Course-day scheduled trigger, cutoff behavior, term credential rotation, retention/archive deletion, and orphaned-report cleanup.
- Professor calibration and a recorded deployed-model frozen demonstration.
- Instructor/schema-owner resolution of the locked evaluator gate-result `PASS` conditional conflict.

Do not change `deployment_ready` until every instructor-authority decision and live check is resolved with dated evidence.
