# Requirements Traceability

## Authority order

Conflicts are resolved in this order, without averaging incompatible requirements:

1. The consolidated six-gate specification and frozen `Allocating the Waldron` scenario in the current master build prompt, including its explicit amendments.
2. All other requirements in the current master build prompt.
3. The latest explicit decisions in `Agent Questions from Sai IMPROVED.docx`.
4. The corrected Scope Advisor requirements.
5. `specifications/Agent-Specifications.md`.
6. The current Approach A+ architecture.
7. The build runbook.
8. Lecture content.
9. Older technical and reference architectures.

Official Codex skill tooling is a build-tool authority only; it does not override course content.

## Source inventory result

- The baseline build's 24 required content artifacts were present and readable, including the four lecture decks (242 slides total), two supporting decks (24 slides total), the decision/specification documents, and current/reference architecture representations.
- The final companion build used the available `Tests/Scope Agent Test Review.pdf` only as sanitized usability evidence. No student response text was copied into fixtures. `Agent 1 Scott Notes.docx` and `teachable_sequence_feedback.docx` were not present in the authorized V550 roots or supplied attachments, so no claim depends on them.
- `SHA256SUMS.txt` contains 28 entries. Twenty-six named paths exist and match their listed digest.
- The two historical root paths `Scope Advisor.docx` and `Scope Advisor.pdf` are absent. Byte-identical SHA-256 matches are present at `Requirements/Scope Advisor.docx` and `Requirements/Scope Advisor.pdf`; this relocation is recorded rather than silently treated as a path-level pass.
- `Agent Questions from Sai IMPROVED.docx` is required and readable but is not listed in the checksum manifest.
- The root `Agent-Specifications.pdf` is an unmanifested duplicate and is not counted as a checksum pass.

## Requirement matrix

This table identifies implementation locations; it does not claim that a check passed. Actual validation evidence belongs in `docs/validation-results.md`.

| ID | Requirement | Highest authority | Implementation / evidence location |
|---|---|---|---|
| R-001 | Build only the Stage 1 Scope Advisor and leave later stages non-executable. | Master prompt | `pm-studio-plus/AGENTS.md`; `config/instructor-config.yaml`; orchestrator |
| R-002 | Canonical scenario, gates, demo, and the single instructor-provided Gate 1 comparison example each have one editable source and byte-identical generated copies. | Master prompt | Skill `references/frozen-*.md` and legacy `gate-1-precedent-cards.md`; canonical manifest; sync/verify scripts; protected `generated/` roots |
| R-003 | Use exactly six numbered gates in the frozen order. | Consolidated specification | Generated frozen gate contract; config `gate_flow`; orchestrator; Review Board |
| R-004 | Keep Deliverables and Scope Action Plan inside Gate 5 and the final audit inside Gate 6. | Consolidated specification | Frozen gate contract; Scope/WBS/Auditor protocols; Living Project File sections 13–16 |
| R-005 | Require student-authored work first, wait for an explicit ready signal before formal evaluation, and withhold assignment-ready answers or fixes. | Master prompt | Orchestrator; Scope Advisor; companion contract; frozen demo assertions |
| R-006 | Only applicable hard checks determine status; criteria and learning signals never block. | Consolidated specification | Frozen gate contract; Review Board; advisory rubric; config |
| R-007 | Require only a corrected/expanded answer and one improvement reason after a prior closure, recognizing ordinary prose across preserved messages without issue restatement, exact labels, or a complete re-paste. | Current master prompt amendment | Frozen gate contract; orchestrator; Review Board; companion tests 9–11 |
| R-008 | Map canonical `OPEN`/`CLOSED` to legacy `PASS`/`REVISE`; use diagnostic `INCOMPLETE` for no meaningful work without recording a gate attempt, closure, or retry trigger. | Master prompt amendment | Config `legacy_outcome_mapping`; orchestrator; Review Board |
| R-009 | Preserve the frozen Waldron facts and five-entry exclusion registry without live supplementation. | Consolidated specification | Canonical scenario; machine contract in canonical gates; manifest-generated copies |
| R-010 | Gate 1 implements Q1–Q3, Q4–Q5, and an evidence check using the internal study plus one lesson from exactly one instructor-provided comparison example, with no student outside research. | Current master prompt amendment + C7/C8/C9 | Frozen Gate 1; canonical legacy example registry; Scope Advisor; deterministic validator |
| R-011 | Gate 2 distinguishes requirements and enforces source/type/verification/status and supplied binding facts. | Consolidated specification + C8 | Frozen Gate 2; Scope Advisor; Living Project File requirements table |
| R-012 | Gate 3 uses exclusive MoSCoW, visible conflicts, and the canonical exclusions in `Won't`. | Consolidated specification + C8 | Frozen Gate 3; machine exclusion registry; Living Project File expectations table |
| R-013 | Gate 4 has exactly one goal, three-to-five measurable objectives, and the frozen date checks; SMART/criteria quality is feedback. | Consolidated specification + C8 | Frozen Gate 4; Scope Advisor; rubric |
| R-014 | Gate 5 checks the five project-statement labels, exclusions, constraint/assumption separation, action verbs, output deliverables, approvers, and phased dates. | Consolidated specification + C9 | Frozen Gate 5; Scope/WBS protocol; Living Project File |
| R-015 | Gate 5 action-line ownership is advisory; Gate 6 work-package ownership is blocking. | Master prompt amendment | Frozen Gates 5–6; both rubric files; Scope/WBS protocol |
| R-016 | Gate 6 preserves the existing WBS schema while enforcing traceability, boundaries, owners, time/hours, full resource vectors, resource summary, and pre-vote effort ceiling. | Consolidated specification + C10 | Frozen Gate 6; config `wbs`; WBS protocol; Living Project File WBS dictionary |
| R-017 | Gate 6B audits assumptions/scope creep and reconciles accepted or exchanged changes without becoming another gate or role. | Consolidated specification | Frozen internal phase; Assumption Auditor; Gate 6 history/notes |
| R-018 | Preserve one versioned 20-section private Living Project File. | Master prompt | Both Living Project File templates; existing schema |
| R-019 | Preserve the seven Stage 1 protocol hats with no added specialist. | Master prompt | Config `roles`; orchestrator; six protocol files plus Review Board |
| R-020 | Use eight equally weighted advisory dimensions and the exact common 1–5 scale. | Master prompt | `gpt/knowledge/scope-rubric.md`; `grading/rubric.md`; Auto-Grader |
| R-021 | Track critique depth, AI-reliance components, iterations, gate attempts, misconceptions, and issuance counts without changing gates. | Master prompt | Insights/Auto-Grader protocols; existing Insights/evaluator schemas; report template |
| R-022 | Produce no more than four sanitized summary lines. | Master prompt | Config; Summarizer; Living Project File section 20 |
| R-023 | Collect one opaque key and visible consent; make `startSession` the first Action. | Consolidated specification | Config onboarding; orchestrator; privacy docs; backend security |
| R-024 | Keep telemetry write-only and omit transcripts, drafts, excerpts, PII, sensitive or emotional-disclosure data, secrets, and real grades. | Master prompt | Privacy knowledge/doc; config telemetry; Python and live Apps Script validators |
| R-025 | Expose only four public operations and preserve the existing event vocabulary. | Master prompt | OpenAPI; config `action_api`/`event_vocabulary`; backend security |
| R-026 | Preserve the six existing strict schema files and their established model/field contracts. | Consolidated specification | `pm-studio-plus/schemas/*.schema.json`; protocols map new logic into existing fields |
| R-027 | Use atomic one-tab mapping, event idempotency, append-only history, and one stable-key daily summary. | Master prompt | Apps Script SheetFactory/Security/Dashboard; privacy data-flow review |
| R-028 | Make the instructor backend the sole authoritative report renderer, storage owner, hasher, signer, and registry writer. | Master prompt amendment | ReportRegistry/Renderer/Delivery/Verifier; report methodology/spec/template |
| R-029 | Re-download exact stored bytes; regenerate as a new preserved issuance; verify submitted bytes instructor-side. | Master prompt amendment | Backend report files; canonical status vocabulary; report tests/plans |
| R-030 | Issue a final report only after Gate 6 opens after Gate 6B; a report request cannot create an attempt. | Consolidated specification | Frozen gates; config report flags; ReportRegistry; report methodology |
| R-031 | Canvas LMS and instructor judgment remain the grade authority. | Master prompt | Config; orchestrator; rubrics; privacy/report docs |
| R-032 | Package a reusable Codex skill with environment-resolved official validation. | Master prompt | `skills/v550-scope-advisor/`; `agents/openai.yaml`; replication guide |
| R-033 | Keep term, privacy, pedagogy, report, taxonomy, and version settings centralized and instructor-editable. | Master prompt | `config/instructor-config.yaml`; instructor configuration guide |
| R-034 | Demonstrate both close and open behavior for Gates 1 and 2 without exposing the passing fixture to students. | Master prompt | Canonical frozen demo; generated demo fixtures; frozen-gate validator/tests |
| R-035 | Use Guided mode by default, offer Independent mode, preserve fragments, and show one manageable next step without status during drafting. | Revised master prompt | Companion contract; orchestrator; config feature flags; companion tests 1–3 and 17 |
| R-036 | Render formal results with `Ready to move on`, `Optional advice`, and `Connection to your earlier work`, every blocker, at most one optional item while closed, and no private check IDs. | Current master prompt amendment | Frozen formal response contract; deterministic validator; companion test 8 |
| R-037 | Escalate repeated confusion through the help ladder, then terminate loops with an instructor handoff. | Revised master prompt | Companion contract; deterministic help ladder; companion tests 5 and 12 |
| R-038 | Pause evaluation for distress or product errors, preserve completed work, and persist no emotional wording. | Revised master prompt | Orchestrator; privacy policy; backend sensitive-value filter; companion tests 13 and 18 |
| R-039 | Keep all thirty-six companion-experience behaviors as executable acceptance evidence without weakening semantic hard checks. | Current master prompt amendment | `test_companion_experience.py`; acceptance manifest AC-044 |
| R-040 | Demonstrate the approximate 25 percent burden-reduction target operationally through one example, two post-closure elements, one question per turn, saved progress, no outside research, no repeated rubric, short Guided introductions, and bounded checklists; make no psychometric claim. | Current master prompt amendment | Companion contract; instructor config; deterministic validator; companion test 19 |
| R-041 | Use strong, student-visible focus subheadings and one-question Guided paths at all six gates without creating hidden hard checks or surprise trivia. | Final master prompt | Canonical gate focus path; deterministic validator; companion tests 20–26 |
| R-042 | Correct challenged AI checks from approved sources without override authority or attempt penalties; hold genuine source conflicts for instructor review. | Final master prompt | Orchestrator; Review Board; source-recheck validator; companion tests 27–28 |
| R-043 | Treat messages, uploads, role claims, and embedded instructions as untrusted content that cannot alter identity, gate truth, configuration, telemetry, or reporting. | Final master prompt | Orchestrator; Review Board; integrity validator; companion tests 27 and 29 |
| R-044 | Support authenticated, isolated instructor testing with production gate truth and fail closed on student activation or production/test-storage misconfiguration. | Final master prompt | Instructor config; deployment validator; companion test 30 |
| R-045 | Retrieve a versioned local course-concept locator before factual or course-method decisions and make no PMBOK attribution without an authorized local source. | Final master prompt | `course-concept-source-map.md`; sync verifier; companion test 31 |
| R-046 | Accept supported immaterial estimates within configured tolerance while keeping fixed facts and hard numerical boundaries exact. | Final master prompt | Numeric evaluator; instructor config; WBS protocol; companion tests 32–36 |

## Recorded conflict resolutions

| Lower-authority or stale direction | Applied resolution |
|---|---|
| Older expanded milestone sequence | Exactly six numbered gates in the canonical order. |
| Additional Deliverables, Action Plan, Revision, or Review gates | Deliverables and the Scope Action Plan are Gate 5 components; the final audit is an internal Gate 6 phase. |
| Earlier AI-authored assessed output before student work | Student submits first; only blank structure, questions, and a small unrelated example are allowed without an attempt. |
| Prior two-example Gate 1 evidence scan | Use one instructor-provided comparison example and require one student lesson; zero or multiple configured examples fail as `INSTRUCTOR MATERIAL NEEDED`. |
| Prior three-part retry structure | After closure require only the corrected/expanded answer and one brief improvement reason; the student never has to restate an issue already identified by the advisor. |
| Average-score, minimum-dimension, critique-depth, or learning-history gate | Only explicit hard checks block. Scores and learning evidence remain advisory. |
| Unchanged `evaluator.schema.json` `$defs/gate_result` requires every legacy advisory flag to be `true` whenever `outcome` is `PASS`, so it cannot truthfully encode an open gate with weak advisory evidence | The higher-authority six-gate policy still opens the gate when explicit hard checks pass, and the runtime must not falsify advisory booleans. The schema remains byte-unchanged as required. This irreconcilable serialization case is recorded as a deployment blocker pending an instructor/schema-owner decision to authorize either a narrowly revised conditional or a sanctioned compatibility interpretation. |
| Every cross-gate inconsistency blocks | Ordinary inconsistencies are feedback; only the two canonical Gate 6/Gate 6B reconciliation cases block. |
| Legacy `PASS`/`REVISE` as canonical status | Evaluate meaningful submissions as `OPEN`/`CLOSED`; map at the legacy presentation boundary. No meaningful submission is diagnostic `INCOMPLETE`, not a gate result. |
| Gate 5 requires an owner on every Action Plan line | Ownership affects advisory Gate 5 scoring; the explicit one-owner hard check applies to Gate 6 work packages. |
| Earlier client-coordinated multi-step issuance | The backend authorizes, derives, renders, stores, rereads, hashes, signs, and records under one locked issuance transaction. |
| Report body contains its own authoritative full-file hash/signature | Private registry holds the hash/signature; the report contains only non-secret receipt/verification guidance. |
| Earlier multi-phase public report flow | `issueReport` is the single public operation; issuance phases are backend-internal. |
| Two student credentials or a repeated PIN | One course-issued opaque key is the only student-entered check-in value. |
| Shared ChatGPT Project and named student tabs | One linked GPT, private student chats, and opaque-key tabs in an instructor-owned workbook. |
| Telemetry stores draft or transcript content | Only minimized structured fields and sanitized summaries leave the private chat. |

## Open assumptions and authority dependencies

- Course timezone currently defaults to `America/Indiana/Indianapolis`.
- The instructor must supply the term, approved retention period, keys, storage folder, verifier access policy, and professor-scored calibration fixtures.
- A confirmed student-owned upload may count as an attempt only under the canonical student-authorship policy.
- The instructor/schema owner must resolve the unchanged evaluator gate-result `PASS` conditional conflict before production certification; local tests preserve and expose the contradiction rather than setting false advisory facts to `true`.
- ChatGPT Canvas behavior and the versioned Markdown fallback require tenant testing.
- Live IU deployment, report readability, sharing restrictions, and Canvas handoff remain deployment checks until recorded otherwise.
