# PM Studio Plus — Stage 1 Build Rules

This subtree implements only the V550 Scope Advisor.

- Preserve the locked sequence in `config/instructor-config.yaml`.
- Treat protocol files under `gpt/subagents/` as roles used by one orchestrating GPT, not autonomous agents.
- Run exactly six ordered gates; keep deliverables and the Scope Action Plan inside Gate 5 and the final audit inside Gate 6B, never Gate 7.
- Start in guided coaching mode, preserve short fragments in one working draft, and evaluate only after the student gives an explicit ready signal. A complete-looking draft without that signal is still coaching, not a gate attempt.
- Require the student to submit first. In the frozen scenario, evaluate that work without generating an alternative, corrected draft, model answer, answer bank, or assignment-ready text.
- Open a gate only when every applicable explicit hard check passes. Criteria, scores, Insights, and ordinary cross-gate feedback never block.
- After a prior closure, recognize the corrected or expanded answer and one brief improvement reason naturally across preserved messages; do not require issue restatement, labels, or a complete re-paste.
- For Gate 1 Part C, use exactly one canonical instructor-provided comparison example. Do not assign outside research or citation sourcing to the student.
- Keep private check IDs and implementation jargon out of student-facing messages; use the amended plain-language headings and pause formal evaluation on distress or product errors while preserving completed work.
- Never invent facts or authorities or change grades.
- Keep private content in the current chat/Living Project File.
- Keep telemetry pseudonymous, structured, write-only, and free of transcripts, drafts, evidence excerpts, PII, secrets, and actual grades.
- Keep the public Action surface limited to `startSession`, `logEvent`, `closeSession`, and `issueReport`.
- Capture visible consent before the first Action; the server records consent before session start and derives session, attempt, report, generation, bytes, hash, and signature.
- Treat generated frozen knowledge as read-only; update canonical skill references and run sync plus byte-equality verification.
- Use `additionalProperties: false` in object schemas unless a documented compatibility exception is approved.
- Add or update an acceptance case for every behavior change.
- Do not add executable Resource/Cost, Risk, or Stakeholder functionality.
- Use `VERIFY WITH THE APPROPRIATE AUTHORITY` for unverified legal or regulatory claims.
- Canvas LMS and the instructor remain authoritative for submissions and grades.
