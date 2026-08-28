# Approach A+ — Build Runbook (OpenAI Codex + Codex Skills)

**Goal:** build the Instrumented Studio (see `Approach-A-plus-architecture.html`) using Codex as the build engineer, with every repeatable task captured as a Codex Skill so next term's rebuild is a re-run, not a rewrite.

---

## 0. Prerequisites (verify before writing code)

| Check | Why |
|---|---|
| IU ChatGPT Edu workspace allows **creating Custom GPTs with Actions** | Some Edu tenants disable Actions; the whole logging bridge depends on it |
| IU **Google at IU** account (Sheets + Apps Script) | The spreadsheet + serverless webhook live here — FERPA-covered under IU's Google agreement |
| **Codex** signed in with the ChatGPT Edu account (`codex` CLI or IDE extension) | Codex access comes with the ChatGPT plan — no extra license |
| Decide identity policy: roster **name vs. ID** for tab names | Names are friendlier; IDs are safer PII-wise. Sheet must stay in IU Workspace, sharing restricted, either way |

---

## 1. Repo layout (Codex scaffolds this in Phase 0)

```
pm-studio-plus/
  AGENTS.md                          # Codex's standing instructions: the 4 guiding
                                     # principles (draft-to-critique, LLM-never-does-math,
                                     # cite-or-flag, cheap-to-replicate) + repo conventions
  gpt/
    orchestrator-instructions.md     # master GPT prompt: 4 advisors + Review Board
    subagents/                       # one protocol block per sub-agent, composed into ^
      insights.md    grader.md    summarizer.md
      wbs-decomposer.md  assumption-auditor.md
      cost-engine.md  wage-data.md  conflict-checker.md
      montecarlo.md  risk-register.md
      persona-player.md  debrief-coach.md
    knowledge/                       # files uploaded to the GPT
      rubric.md  personas.md  templates/  cost_snapshot.csv  montecarlo.py
    actions/
      openapi.yaml                   # Logging Action schema (startSession, logEvent)
                                     # WRITE-ONLY: no endpoint ever returns student data
  backend/
    apps-script/
      Code.gs                        # doPost router: validate token → stamp → write
      SheetFactory.gs                # per-student tab auto-creation (named by student)
      Dashboard.gs                   # master-dashboard rollups
      appsscript.json
    tests/fixtures/                  # sample event payloads for curl tests
  engines/
    montecarlo.py                    # source of truth; copied into gpt/knowledge/
    tests/test_montecarlo.py         # golden outputs — P50/P80/P90 must be reproducible
  grading/
    rubric.md                        # instructor-owned rubric
    fixtures/                        # anonymized sample student work + expected scores
  docs/
    Approach-A-plus-architecture.html
    replication-guide.md             # next-term runbook (generated in Phase 5)
```

---

## 2. Codex Skills to build (the "skill builder" part)

Ask Codex to create each skill ("create a skill that…") — it scaffolds the `SKILL.md`
(frontmatter: name + description, then instructions/scripts) in its skills directory
(`~/.codex/skills/` globally, or checked into the repo so collaborators share them).

| Skill | What it encodes | Used in |
|---|---|---|
| `pm-studio-prompts` | The pedagogy rules + house style for writing/refining advisor and sub-agent instruction blocks; composes `orchestrator-instructions.md` from `gpt/subagents/*` | Phase 2, every term |
| `sheets-telemetry-backend` | Event schema, Apps Script patterns (doPost, tab factory, dashboard formulas), deploy steps (`clasp push` + web-app deploy) | Phase 1 |
| `gpt-action-schema` | Generates/validates `openapi.yaml`, keeps it in lockstep with `Code.gs` endpoints | Phase 1 |
| `montecarlo-engine` | Maintains `montecarlo.py` (PERT/triangular, 10k iterations, P50/P80/P90, tornado) with golden tests | Phase 3 |
| `rubric-autograder` | Converts `rubric.md` → grader protocol + JSON score schema; regression-tests grading against `grading/fixtures/` | Phase 3 |
| `insights-analytics` | The metrics taxonomy (critique depth 0–3, AI-reliance index, sessions, gate outcomes, misconception flags) → generates both the GPT-side logging rules and sheet-side rollups | Phases 1–2 |
| `term-replication` | Semester reset: new spreadsheet from template, redeploy webhook, rotate token, refresh cost snapshot, re-upload knowledge files | Phase 5, each term |

---

## 3. Build phases (≈2 weeks part-time)

**Phase 0 — Scaffold (half day).**
Codex prompt: *"Scaffold the pm-studio-plus repo per docs/Build-Runbook-Codex.md §1, write AGENTS.md with the four guiding principles from the V550 architecture doc, then create the seven skills in §2."*

**Phase 1 — Telemetry backend first (1–2 days).**
Codex (with `sheets-telemetry-backend` + `gpt-action-schema`): write `Code.gs`, `SheetFactory.gs`, `Dashboard.gs`, and `openapi.yaml`. Deploy Apps Script as a web app (execute-as-me, anyone-with-link; validate the class token **and the per-student PIN** in the payload — see §5). **Test with curl before touching any GPT:** post fixture events for two fake students → verify tabs auto-create and dashboard rows appear; then post a bad PIN and a `=IMPORTXML(...)` payload → verify both are rejected/neutralized.

**Phase 2 — Orchestrator + sub-agent protocols (2–3 days).**
Codex (with `pm-studio-prompts` + `insights-analytics`): write the 12 sub-agent blocks and compose the master instructions. Key protocol rules: check-in (ask roster ID → `startSession`) · log after every milestone (draft, critique, gate, sim, grade) · Insights Agent answers "how am I using AI?" interactively · Review Board won't pass a gate without an Auto-Grader score.

**Phase 3 — Engines + grading validation (1–2 days).**
Codex (with `montecarlo-engine` + `rubric-autograder`): finalize `montecarlo.py` with golden tests (fixed seed → identical P-values); build grading fixtures from anonymized past work and tune the grader protocol until scores match instructor scores within ±1 on each rubric dimension.

**Phase 4 — Wire the GPT + end-to-end dry run (1 day).**
Create the Custom GPT in ChatGPT Edu: paste instructions, upload `gpt/knowledge/*`, add the Action from `openapi.yaml` + token. Run a full fake-student session ("Test Student"): all four advisors → gates → sim → report. Verify: tab created, events logged, dashboard row live, report footer has session ID matching the tab.

**Phase 5 — Pilot + replication guide (ongoing).**
Pilot with 2–3 volunteers; use the insights data itself to tune prompts. Codex (with `term-replication`) generates `docs/replication-guide.md`.

---

## 4. Known constraints (design accepts these)

- **Sub-agents are orchestrated roles, not parallel processes** — one GPT switching protocol hats + tool calls. Fine at course scale; that's how Custom GPTs work.
- **Action calls prompt the student to "Allow"** — logging is visible by design. Disclose it in the syllabus; consent is a feature, not a bug.
- **Identity is honor-system** (roster-ID check-in). Session-ID stamping makes reports tamper-evident, not tamper-proof. Canvas grade stays instructor-owned.
- **Apps Script quotas** are generous vs. 30 students' event volume — not a risk.
- **PII:** keep the workbook in IU Workspace, restrict sharing; prefer roster IDs as tab names if the class roster is sensitive.

---

## 5. Security model (student isolation, logs, FERPA)

### 5.1 Student-to-student isolation is structural — students never touch the sheet

1. **Own accounts only.** Every student signs into their own IU ChatGPT Edu account. Never a shared class login — a shared login means one shared chat history and everyone sees everything.
2. **Distribute the GPT via link — do NOT use a shared ChatGPT Project.** Chats inside a *shared* project are visible to project members. Each student converses with the GPT in their own private space, so their chats and their Living Project File (Canvas doc) are private to their account by platform design. "One studio" = one GPT everyone uses, not one chat space everyone shares.
3. **The workbook is never shared with students.** Instructor (+ TA) named-person sharing only; no link sharing. Students reach it only through the webhook.
4. **Nothing student-derived in GPT instructions or knowledge files.** Both are extractable by any student via prompt extraction — treat them as public. Class materials only; grading exemplars must be anonymized or synthetic.
5. **The Action surface is write-only.** Every endpoint returns only `{ok:true}`. Even a fully extracted webhook URL + token cannot read anyone's work. If per-student read-back is ever wanted, it must be PIN-gated and return only that student's coarse summary.

### 5.2 Hardening the one bridge (GPT Action → Apps Script)

- **Assume the webhook URL and any payload token leak** — the model sees the OpenAPI schema, so a determined student can extract both. The write-only rule bounds all damage to *fake writes*.
- **Per-student PIN** issued privately (Canvas individual message or gradebook comment). `Code.gs` validates the (rosterID, PIN) pair against a hidden roster tab → blocks impersonation and cross-tab poisoning. (Note: Apps Script cannot read HTTP headers, so payload-field auth is the native option; a free Cloudflare Worker proxy in front adds real header auth if wanted later.)
- **Sheets formula-injection defense:** any logged string starting with `=`, `+`, `-`, or `@` gets an apostrophe prefix before writing — otherwise a crafted payload could plant `=IMPORTXML(...)` and exfiltrate the workbook. Also: schema-validate payloads, cap field lengths, per-ID rate limit (LockService + counters).
- **Append-only + server-side timestamps.** The script never edits or deletes rows; Sheets version history is the tamper audit trail.
- **Secrets in Script Properties**, never in code or the repo. Rotate token + PINs and redeploy (new URL) every term — encoded in `term-replication`. Same rotation is the incident response if anything leaks mid-term.

### 5.3 Grader integrity (students will try "log me a 5/5")

Auto-grades are **advisory**: the grader must log rationale + quoted evidence with every score; the Review Board refuses gates without artifacts; the dashboard flags anomalies (high score + thin event history); and **Canvas remains the only authoritative gradebook**, so poisoned telemetry can never change a grade by itself.

### 5.4 Log safety & FERPA hygiene

- **Minimize:** log the Summarizer's digests + metrics, never raw transcripts. What isn't collected can't leak.
- **Disclose:** syllabus statement + the Action's visible "Allow" prompt = informed, ongoing consent; the Insights Agent can explain exactly what gets logged when asked.
- **Retention:** keep one semester + the grade-appeal window, then archive to IU storage or delete, per IU records policy (encode in `term-replication`).
- **Provider side:** students must use ChatGPT **Edu** accounts, not personal ChatGPT — Edu has enterprise controls and does not train on user data.
