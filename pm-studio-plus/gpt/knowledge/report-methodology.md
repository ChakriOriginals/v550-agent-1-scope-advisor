# Report Methodology

The final artifact is one readable US Letter page titled `V550 AI Usage & Learning Report`. The instructor-controlled backend is its sole authoritative issuer. ChatGPT must not render authoritative PDF bytes, compose client-supplied final report prose, choose a hash, upload a PDF, or create an issuance record.

Resolve issuance labels, regeneration watermarks, and verifier results from the machine contract in `generated/frozen-six-gates.md`. Use the versioned template and deterministic server rules; do not maintain those controlled strings here.

## Eligibility and content

Issue a final report only when server-held state says Gate 6 is `OPEN` after its internal Gate 6B audit, or when the same authorized student explicitly requests another report after that condition is already true. A report request alone never creates or advances a stage attempt.

Build the report model only from the current student's frozen, server-held structured metrics, controlled reason codes, and sanitized summaries. Include the course/stage, pseudonymous key, sanitized title, session and server-derived attempt, report metadata, critique depth, AI-reliance components, substantive iteration and gate counts, misconception flags, two short evidence-based analysis paragraphs, one concrete next behavior, accurate logging transparency, and non-secret verification instructions.

Exclude transcripts, full drafts, evidence excerpts, personal or sensitive information, unrelated history, inferred motives, actual grades, rankings, named student comparisons, psychological profiling, credentials, signing material, storage pointers, download capabilities, and the private byte hash or signature.

## One backend transaction

The public operation is only `issueReport`. Under one server lock, the backend must:

1. authorize the key/session and verify current report eligibility from append-only server state;
2. derive attempt, generation, report ID, issuance time, and status server-side;
3. freeze the sanitized metrics snapshot, derive a render-only view, and render the final one-page PDF once from the versioned server template;
4. store those exact bytes as a new immutable object without overwriting any prior issuance;
5. reread the stored object, compute its byte length and SHA-256 digest, then build and deterministically validate the authoritative snake-case model against the unchanged report-schema field/enum/privacy rules using those truthful receipt values;
6. hash that validated model, create and sign the append-only private registry metadata, and commit the issuance record;
7. return only the current receipt plus an opaque expiring capability bound to that stored object.

The render-only view is not the authoritative report model. The authoritative internal model uses the unchanged `report.schema.json` shape; private receipt fields are validated and model-hashed after storage but are not printed on the page.

All issuance phases are backend-internal; the client makes one `issueReport` request and supplies none of the authoritative metadata or bytes. A failure at any required step must not return a successful issuance receipt. Any uncommitted stored object is an operator-cleanup concern, not an issued report.

## Download, regeneration, and verification

- A normal download, repeat download, or refreshed capability streams the same stored object bytes and does not increment generation.
- An explicit same-attempt regeneration creates a new server-rendered object, preserves the prior issuance, increments generation, and uses the canonical regeneration watermark.
- A new stage attempt is server-derived only after qualifying revision and gate activity; affected and downstream gates must be reevaluated through Gate 6 and Gate 6B before that attempt is reportable.
- The instructor-only verifier hashes the submitted PDF bytes and compares them with the valid signed registry record. A student- or client-supplied hash is never authoritative.
- Verification proves whether submitted bytes match a registered issuance. It does not prove who created the underlying student work or why a report was regenerated.

The download capability is a narrow delivery exception, not a workbook or report-registry read endpoint. The renderer, storage, registry, and verifier remain instructor-controlled and unavailable for cross-student browsing.
