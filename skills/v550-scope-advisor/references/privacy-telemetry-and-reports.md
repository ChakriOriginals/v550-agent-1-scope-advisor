# Privacy, Telemetry, and Reports

## Contents

- Data classification and isolation
- Four-operation Action boundary
- Consent and write ordering
- Workbook controls
- Authoritative report lifecycle
- Download, regeneration, and verification
- Single-page report content

## Data classification and isolation

The class workbook is pseudonymized, re-identifiable protected education data because the restricted `StudentIndex` can map the opaque key. Do not call it de-identified unless that linkage is irreversibly destroyed and re-identification risk has been assessed under applicable policy.

Use IU-controlled storage with instructor/TA named-person access. Retain data for the semester plus the approved appeal period, then archive/delete under IU policy. Canvas LMS remains grade-authoritative.

The agent may see only the current private chat, Living Project File, and approved course files. No student-facing read can browse workbook data, history, another student, Drive paths, or report history.

## Four-operation Action boundary

Expose exactly four GPT Action operations:

- `startSession`
- `logEvent`
- `closeSession`
- `issueReport`

Normal operations return minimal acknowledgement. `issueReport` returns only `reportId`, `generationNumber`, `issuedAtServer`, and `verificationToken`; the token carries the opaque, expiring object-bound download capability. A token download handler is a narrow byte delivery path, not a fifth GPT Action or telemetry event.

Reject unknown fields and all client-supplied attempts, generations, report IDs, PDF bytes, final prose, hashes, signatures, storage IDs, template/schema versions, or issuance status. Use server time, lock writes, apply length/enum/rate limits, validate allowlisted term keys and class deployment token, and neutralize strings beginning with `=`, `+`, `-`, or `@` before spreadsheet storage.

The one-key model is low-friction identification, not strong identity proof. A shared key cannot prove who is typing. Bound risk with opaque term keys, write-only telemetry, append-only history, no automatic grade changes, current-session/object-bound report capabilities, and instructor comparison with the submitted report/session ID.

## Consent and write ordering

Visible chat consent precedes any Action. `startSession` must carry a true consent assertion, consent-version identifier, and validated client-observed timestamp but no client session/attempt. Under one server lock:

1. validate deployment and allowlisted active key;
2. create the session ID and derive the stage attempt;
3. persist `consent_recorded` with server time;
4. persist `session_started` next;
5. return minimal session acknowledgement.

Missing/declined consent, malformed/inactive/mismatched key, or failed validation writes nothing and creates no tab. Identity fields are immutable within the session.

## Workbook controls

Maintain `Dashboard`, restricted `StudentIndex`, and exactly one opaque-ID student tab per key. Atomic `getOrCreateStudentTab` uses a lock and unique index. Do not delete or silently merge historical duplicate tabs; stop and flag them.

Events are append-only and idempotent by event ID. Daily summaries are unique by student key + course date + stage. Server-derived stage attempt is stored in the unchanged `attempt_number` field. Existing event vocabulary only; no transcript, full draft, evaluator quotation, identifier, sensitive detail, emotional disclosure, hidden reasoning, or secret. If slower pacing matters operationally, use only the neutral note `student requested slower pacing`.

Gate identity uses only the existing `reasonCodes` field and this controlled vocabulary:

| Event | Exactly one gate identity reason code |
|---|---|
| `revision_submitted` | `GATE_N` for the affected gate |
| `assumption_audit_completed` | `GATE_6` |
| `gate_attempt` | `GATE_N_ATTEMPT_RECORDED` |
| `gate_result` | `GATE_N_OPEN` with wire `PASS`, or `GATE_N_CLOSED` with wire `REVISE` |

Reject unknown aliases, multiple gate identities, and reason-code/outcome contradictions. After an issuance, matching revision + gate activity activates the next server attempt; reportability then requires the affected gate and every downstream gate to be attempted and opened in order, plus the Gate 6B audit, versioned Gate 6 revision, new Gate 6 attempt, and Gate 6 open result.

The structured lifecycle includes existing consent/session, artifact submission, critique/revision/justification, gate, assumption audit, misconception, report, session close, and daily summary events. `assumption_audit_completed` remains part of Gate 6; there is no Gate 7 or `stage_completed` event.

## Authoritative report lifecycle

Only the instructor-controlled backend issues the authoritative PDF. Under one lock it must:

1. verify current key/session authorization and server state showing Gate 6 `OPEN` after Gate 6B;
2. derive stage attempt, generation, report ID, issuance time, and status;
3. freeze structured metrics and sanitized summaries;
4. construct prose through versioned deterministic server templates—never client prose or transcript/draft text;
5. render one US Letter page once with identifiers, attempt, generation, and any regeneration watermark;
6. store exact bytes as a new restricted immutable object without overwriting prior objects;
7. reread stored bytes, compute byte length and SHA-256, and append a server-only registry row with object ID, metadata, prior link, and template/schema versions;
8. sign report ID, attempt, generation, byte hash, issuance metadata, and key version with a Script Properties HMAC key;
9. return only the narrow public receipt and expiring token.

ChatGPT/client never renders the authoritative report or selects integrity metadata. Report registry fields are server infrastructure, not telemetry/schema additions.

## Download, regeneration, and verification

A normal download or refreshed capability streams the same stored object bytes and does not render or increment generation. The token binds one object, key/session authorization, and short expiry; it cannot retrieve another object or any workbook/Drive listing.

Generation 1 of a server-derived attempt is `ORIGINAL`. An explicit create-again request with no qualifying new work makes a new immutable object and increments generation with this exact visible watermark:

`REGENERATED COPY — GENERATION N — PREVIOUS ISSUANCE EXISTS`

A new stage attempt is server-derived only after a post-issuance artifact/version plus `revision_submitted` and affected `gate_attempt`/`gate_result`, downstream re-evaluation, and Gate 6 reopening after Gate 6B. A report request alone never creates an attempt. Preserve all earlier objects and metrics.

The instructor-only authenticated verifier hashes submitted bytes, validates the registry signature with its historical key version, and returns only one exact status plus minimal metadata:

- `VALID ORIGINAL`
- `VALID REGENERATED COPY — GENERATION N`
- `VERIFICATION FAILED — FILE MAY HAVE BEEN MODIFIED`
- `UNKNOWN REPORT ID`

Student/client hashes are ignored. Verification requires both byte equality and authenticated registry state. Never infer why a student regenerated.

## Single-page report content

Title the flattened US Letter PDF `V550 AI Usage & Learning Report`. Include course/stage, pseudonymous key, sanitized title, session and attempt, report ID/time/schema/generation, critique depth, AI-reliance counts/index, substantive iterations, gate attempts/outcome, misconception flags, evidence-based analysis, one concrete next behavior, transparency note, and non-secret receipt/QR instructions.

Exclude transcripts, drafts, direct/personal/sensitive information, unrelated history, motives, grades, rank, named comparisons, emotional/psychological profiling, download tokens, storage IDs, and signing secrets. Fail QA if it spills beyond one readable page or uses tiny text.
