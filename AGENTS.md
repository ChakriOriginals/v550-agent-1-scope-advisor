# Agent 1 repository instructions

This repository contains only the V550 Stage 1 Scope Advisor, also called Agent 1.

- Use `skills/v550-scope-advisor/SKILL.md` for build, maintenance, and test work.
- Preserve exactly six numbered gates and the internal Gate 6B phase.
- Do not build or import Agent 2, Agent 3, Agent 4, or Stage 2 work.
- Treat the four canonical files under `skills/v550-scope-advisor/references/` as the only editable frozen truth. Never hand-edit generated copies.
- Never commit Apps Script properties, student keys, transcripts, student work, report signing keys, access tokens, or other credentials.
- Use synthetic keys and fictional answers for testing.
- Run `python3 tools/verify_package.py` before sharing or merging changes.
- Keep `deployment_ready: false` until the evaluator-schema authority conflict and live IU tenant checks are resolved.
