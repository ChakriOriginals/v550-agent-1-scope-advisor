# Replication and Deployment Guide

Run commands from the repository root. A passing local build is necessary but does not replace live IU tenant certification or instructor approval.

## 1. Synchronize canonical truth

The three frozen scenario/gate/demo files plus the legacy file `gate-1-precedent-cards.md` under `skills/v550-scope-advisor/references/` are the four editable canonical sources. Generate runtime/test copies and then verify exact bytes, the one-example registry, and manifest hashes:

```bash
python3 skills/v550-scope-advisor/scripts/sync_runtime_knowledge.py --repo-root "$PWD"
python3 skills/v550-scope-advisor/scripts/verify_canonical_knowledge.py --repo-root "$PWD" --pretty
```

Never edit a file under a protected `generated/` root. Run verification before tests, packaging, and deployment; any drift is a stop condition.

## 2. Validate the Codex skill

Resolve the installed `skill-creator` directory from the current Codex environment or available-skills catalog. Do not assume a global executable or copy a path from another machine.

```bash
SKILL_CREATOR_DIR="/absolute/path/resolved/from/this/Codex/environment"
python3 "$SKILL_CREATOR_DIR/scripts/quick_validate.py" skills/v550-scope-advisor
```

Confirm that `agents/openai.yaml` matches the final `SKILL.md`, its default prompt explicitly invokes `$v550-scope-advisor`, and its description covers build, update, run, evaluation, privacy-report, and validation requests.

Install the validated directory at the current environment's exact discovery target:

```text
${CODEX_HOME:-$HOME/.codex}/skills/v550-scope-advisor
```

Keep the repository copy at `skills/v550-scope-advisor`. Copy the complete validated directory, exclude generated caches, run `quick_validate.py` against the installed copy, and compare repository/install bytes. On this build host the resolved target was `/Users/saichakri/.codex/skills/v550-scope-advisor`; resolve it again rather than copying that private absolute path to another machine.

## 3. Run local validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 pm-studio-plus/tests/run_all.py
```

Also exercise every skill validator with representative valid and invalid inputs: frozen-gate submission, scope artifact, telemetry payload, and PDF/receipt integrity. Record commands, fixture IDs, tool/runtime versions, and actual results in `docs/validation-results.md`; never copy a previous pass count forward.

## 4. Configure the term and infrastructure

Set every deployment placeholder documented in `docs/instructor-configuration.md`. Create:

- one instructor-owned IU workbook with `Dashboard` and restricted `StudentIndex` tabs;
- exactly one opaque-key student tab on first accepted session;
- one dedicated, restricted IU Drive folder or approved equivalent for immutable issued reports;
- a versioned HMAC key map and authenticated instructor-verifier credential.

Store deployment values only in Apps Script Script Properties. Restrict the workbook, report folder, and verifier to named instructors/TAs. Rotate term-specific URL/token/student keys and follow the approved retention policy.

## 5. Deploy the backend and Action

Deploy Apps Script in the approved IU tenant and replace the OpenAPI server placeholder with that deployment URL. Verify that only these public operations exist:

- `startSession`
- `logEvent`
- `closeSession`
- `issueReport`

Confirm visible consent precedes the first Action, ordinary responses reveal no stored history, and `issueReport` returns only the current receipt plus an opaque expiring capability for one authorized stored PDF. The student Action must not expose the instructor verifier.

## 6. Build one Scope Advisor GPT

Load `gpt/orchestrator-instructions.md`, `gpt/review-board.md`, the existing protocol-role files, and the knowledge files. Include the generated frozen scenario/gate/demo copies only after canonical verification succeeds. Distribute one GPT by link; each student uses a private chat and private Living Project File.

Test tenant-specific private Canvas/Living Project File creation, update and export, Action permission disclosure, private-chat isolation, and the versioned Markdown fallback. Do not create a shared student project or enable cross-student history.

## 7. Certify pedagogy, storage, and integrity

Use synthetic term keys to test at least:

- no-attempt and direct-answer requests;
- all required frozen demo outcomes and failure-withholding behavior;
- all 36 companion-experience regressions, including the original companion behaviors plus all-six-gate focus paths, AI source correction/conflict, untrusted-content handling, isolated test mode, course-source grounding, and bounded numerical judgment;
- the two post-closure student elements across preserved messages, no issue restatement, and immediate opening when required items pass;
- automatic delivery of exactly one instructor-provided Gate 1 comparison example without student outside research;
- concurrency, idempotency, one-tab mapping, and daily-summary upsert;
- unknown/inactive key rejection with no tab creation;
- Gate 6 plus Gate 6B report eligibility;
- one-page readability at the approved font size;
- render-once storage, stored-byte reread/hash, exact-byte re-download, refreshed capability, same-attempt regeneration, and prior-issuance preservation;
- instructor-only valid, modified, and unknown-report verification outcomes;
- professor calibration within the approved tolerance.

Record the real automated case count and all remaining scripted/live checks. Keep `deployment_ready: false` until the professor decisions and live tenant checks are complete.

## 8. Pilot and operate

Pilot with synthetic keys before students. Monitor only instructor-controlled dashboards and security reason codes; never inspect or export raw student content through telemetry. Use Canvas LMS for submission and grading. At term close, revoke/rotate credentials and archive or delete data according to the approved retention schedule.
