# Apps Script tenant-certification plan

The offline suite statically verifies the public surface and security-critical implementation markers. Before deployment, run these stateful cases in a disposable instructor-owned IU workbook and restricted Drive folder with synthetic keys.

1. A declined or malformed consent request creates no tab and no row.
2. A valid `startSession` appends `consent_recorded` before `session_started` in one locked transaction and derives attempt 1 server-side.
3. Unknown, inactive, malformed, and mismatched keys create no tab.
4. Two concurrent first sessions for one key resolve to one tab ID.
5. A repeated event ID with identical content returns the original acknowledgement; different content conflicts without a second write.
6. Formula-prefixed strings are stored inert; transcripts, drafts, identifiers, sensitive prose, secrets, and actual grades are rejected.
7. Multiple sessions on one course day yield one materialized summary row while raw events remain append-only.
8. A client-supplied stage attempt, report generation, PDF bytes, hash, prose, storage ID, signature, or issuance status is rejected.
9. Gates 1–5, a closed Gate 6, and Gate 6 without a complete internal 6B audit cannot issue a report.
10. A forged `gate_result` or out-of-order event sequence cannot manufacture reportable state.
11. First issuance renders once on the backend, stores restricted bytes, rereads them, hashes them, signs a versioned registry row, and returns only the narrow receipt/capability.
12. Exact re-download, including refreshed capability, streams byte-identical stored bytes without rerendering or generation change.
13. Same-attempt regeneration stores a new watermarked object, increments generation, links the prior issuance, and preserves both objects.
14. A report request alone cannot create a new stage attempt. Qualifying new work requires an artifact/version, `revision_submitted`, affected/downstream gate activity, and Gate 6 `OPEN` after 6B.
15. Capabilities cannot retrieve another report, another student’s object, Drive paths, workbook rows, or report history.
16. The instructor-authenticated verifier returns only one of the four frozen statuses and never exposes registry history.
17. Rotating to a new signing-key version leaves earlier receipts verifiable.
18. `StudentIndex`, report storage, workbook sharing, and the registry are restricted to named instructor/TA accounts.

Record tenant, deployment ID, synthetic key IDs, timestamps, expected/actual outcome, and cleanup confirmation. Never use real student data in certification.
