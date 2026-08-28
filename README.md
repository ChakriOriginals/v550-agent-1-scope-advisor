# V550 Agent 1: Scope Advisor staff-test package

This private, Git-ready repository contains the complete final local build of the existing V550 Stage 1 Scope Advisor. It gives teaching staff one place to inspect the sources, run all automated tests, install the Codex skill, and conduct synthetic conversational testing.

Do not make this repository public. It contains instructor-controlled source material and a sanitized instructor-only usability transcript. It contains no deployment credentials or real student records.

## First result in three steps

1. Clone the private repository and enter it.

   ```bash
   git clone PRIVATE_REPOSITORY_URL
   cd Agent-1-Scope-Advisor-Staff-Test
   ```

2. Run the package verifier.

   ```bash
   python3 tools/verify_package.py
   ```

   Expected result: canonical knowledge verifies, the source map matches, and all 121 automated tests pass.

3. Install the skill in Codex and begin a synthetic test.

   ```bash
   mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/v550-scope-advisor"
   rsync -a --exclude '__pycache__' skills/v550-scope-advisor/ "${CODEX_HOME:-$HOME/.codex}/skills/v550-scope-advisor/"
   ```

   Restart or refresh Codex skill discovery, then prompt:

   ```text
   Use $v550-scope-advisor to run a synthetic staff test of Gate 1 in Guided mode. Do not call Actions or write telemetry.
   ```

## What is included

- `skills/v550-scope-advisor/`: the reusable Codex skill, canonical truth, source map, validators, and templates.
- `pm-studio-plus/`: the maintainable Agent 1 runtime, backend source, configuration, six unchanged schemas, reports, and 121-test suite.
- `source-material/`: the final build prompt, corrected Agent 1 specifications, scenario, V450 C7–C10 decks, current architecture context, and instructor-only sanitized usability evidence.
- `docs/`: staff testing, Git sharing, and package-reference documentation.
- `tools/verify_package.py`: one-command package, canonical, and regression verification.

See [Package contents](docs/PACKAGE-CONTENTS.md) for the exact boundary.

## Staff workflow

1. Read [Staff testing tutorial](docs/STAFF-TESTING-TUTORIAL.md).
2. Run `python3 tools/verify_package.py` before conversational testing.
3. Use only fictional submissions and synthetic student keys.
4. Record pass/fail observations without copying chat transcripts or emotional disclosures into Git.
5. File one Git issue per reproducible defect, naming the test case, expected behavior, actual behavior, runtime/model version, and sanitized reproduction steps.

## Sharing with Git

Yes. Git is a good way to share and version this package. Use a private GitHub, IU GitHub Enterprise, or private GitLab repository and invite only course staff. The largest included file is below GitHub's 100 MB single-file limit, so Git LFS is not required for the current snapshot. LFS is still sensible if the PowerPoint/PDF files will change frequently.

Follow [How to share Agent 1 with Git](docs/HOW-TO-SHARE-WITH-GIT.md) for exact commands and privacy checks.

## Current certification boundary

The local source package passes 121/121 tests, canonical verification, and official skill validation. It is not yet certified for production student use. Keep `deployment_ready: false` until:

- the instructor/schema owner resolves the locked evaluator-schema `PASS` conditional conflict;
- instructor settings, keys, retention, and report-verifier access are approved;
- the IU ChatGPT Edu, Canvas/Living Project File, Apps Script, Drive, and Canvas LMS flows pass live tenant tests.

The authoritative evidence is in `pm-studio-plus/docs/validation-results.md`.
