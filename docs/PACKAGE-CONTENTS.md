# Agent 1 package contents

This reference defines what belongs in the staff-test repository and why.

## Runtime surfaces

| Path | Purpose | Editing rule |
|---|---|---|
| `skills/v550-scope-advisor/` | Codex skill, canonical course truth, source map, deterministic validators, and templates | Follow `SKILL.md`; edit canonical truth only in its declared reference source. |
| `pm-studio-plus/gpt/` | Custom GPT instructions, protocol hats, knowledge, and four-operation Action description | Preserve one orchestrating advisor and the existing seven protocol roles. |
| `pm-studio-plus/backend/` | Apps Script source for consent, telemetry, report issuance, storage, and verification | Never put Script Property values in Git. |
| `pm-studio-plus/config/` | Centralized instructor defaults and deployment placeholders | Keep `deployment_ready: false` until live certification completes. |
| `pm-studio-plus/schemas/` | Six locked JSON Schemas | Do not change without instructor/schema-owner authority. |
| `pm-studio-plus/tests/` | 121-test acceptance suite and synthetic instructor fixtures | Use fictional data; never copy student transcripts into fixtures. |
| `pm-studio-plus/reports/` | Report specification, examples, generator, and verifier | Backend remains authoritative for issued bytes, hash, and signature. |
| `pm-studio-plus/docs/` | Deployment, privacy, configuration, traceability, and validation evidence | Update actual results after every release. |

## Source material

| Path | Contents | Handling |
|---|---|---|
| `source-material/MASTER-BUILD-PROMPT.txt` | Final 2026-08-26 build specification | Highest current build requirement after platform rules. |
| `source-material/specifications/` | Agent specification and corrected Scope Advisor requirements in Markdown/DOCX/PDF | Instructor/build reference. |
| `source-material/Scenario 1 After the Merger.docx` | Latest scenario/instruction source with lower-authority conflicting wording | Mixed-content reference, never executable authority. |
| `source-material/course-decks/` | V450 C7–C10 lecture decks | Course-method authority through the private source map. |
| `source-material/Agent Questions from Sai IMPROVED.docx` | Instructor decisions and clarifications | Lower than the final build specification and canonical frozen truth. |
| `source-material/architecture-context/` | Current Approach A+ visual/context files | Context only; final Agent 1 runtime and skill govern executable behavior. |
| `source-material/planning-context/` | Historical build runbook | Context only when it conflicts with final runtime requirements. |
| `source-material/instructor-only-evidence/` | Sanitized usability transcript used as evidence, not as a fixture | Private teaching staff only. Do not publish or copy its text into tests. |

## Deliberately excluded

- Agent 2 Resource & Cost files and decision records.
- Agent 3 Risk and Agent 4 Stakeholder implementation work.
- Stage 2 scheduling, detailed costing, critical path, resource leveling, and Monte Carlo output.
- Deployment secrets, Apps Script properties, student keys, rosters, access URLs, signing keys, and verifier tokens.
- Caches, temporary renders, generated scratch PDFs, the workspace ZIP, and duplicate course-deck copies.
- Real student submissions, chat transcripts, emotional disclosures, and private report artifacts.

## Stable boundaries

- Six numbered gates only; Gate 6B remains internal to Gate 6.
- Seven existing protocol roles only.
- Six locked schemas.
- Four public Action operations: `startSession`, `logEvent`, `closeSession`, and `issueReport`.
- One instructor-provided Gate 1 comparison example.
- Canvas LMS and instructor judgment remain grade authority.

## Related

- [README](../README.md)
- [Staff testing tutorial](STAFF-TESTING-TUTORIAL.md)
- [Git sharing guide](HOW-TO-SHARE-WITH-GIT.md)
- `pm-studio-plus/docs/requirements-traceability.md`
- `pm-studio-plus/docs/validation-results.md`
