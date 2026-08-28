/**
 * Deterministic, server-side, single-page report model and PDF renderer.
 * Final prose is selected only from server-held structured metrics. No client
 * prose, transcript text, draft text, or evaluator quotation enters the model.
 */

function buildServerReportRenderView_(
  auth,
  state,
  reportId,
  generation,
  previousReportId,
  watermark,
  now,
  config
) {
  var metrics = state.metrics;
  return {
    title: "V550 AI Usage & Learning Report",
    course: auth.course,
    stage: "Stage 1 — Scope",
    studentKey: auth.studentKey,
    projectTitle: metrics.sanitizedProjectTitle,
    sessionId: state.sessionId,
    attemptNumber: state.attemptNumber,
    reportId: reportId,
    issuedAt: now.toISOString(),
    generationNumber: generation,
    previousReportId: previousReportId,
    schemaVersion: config.schemaVersion,
    templateVersion: config.templateVersion,
    watermark: watermark,
    metrics: metrics,
    critiqueInterpretation: critiqueInterpretation_(metrics.critiqueDepth),
    whatEvidenceShows: evidenceParagraph_(metrics),
    relianceAnalysis: relianceParagraph_(metrics),
    nextBehavior: nextBehavior_(metrics),
    transparency:
      "Logged: pseudonymous identifiers, server timestamps, structured AI-use " +
      "counts, gate outcomes, controlled reason codes, sanitized summaries, " +
      "dimension scores, and report receipt metadata. Not logged: transcripts, " +
      "full drafts, evidence quotations, direct identifiers, sensitive details, " +
      "hidden reasoning, secrets, or an actual grade."
  };
}

/**
 * Build the authoritative internal model in the exact unchanged
 * report.schema.json shape. This happens only after the server has stored and
 * reread the one rendered PDF, so the receipt contains truthful byte metadata.
 * The renderer consumes the separate render view above and never prints the
 * private byte hash, storage locator, signature, or download capability.
 */
function buildServerReportModel_(
  auth,
  state,
  reportId,
  generation,
  previousReportId,
  watermark,
  now,
  config,
  stored,
  renderView
) {
  var metrics = state.metrics;
  var loggedCategories = [
    "pseudonymous_student_key",
    "session_and_attempt_ids",
    "structured_event_codes",
    "artifact_and_version_ids",
    "critique_depth",
    "ai_disposition_counts",
    "ai_reliance_index",
    "substantive_iteration_count",
    "gate_counts_and_outcome",
    "misconception_flags",
    "sanitized_digest_and_report_metadata"
  ];
  if (metrics.dimensionScores !== null && metrics.dimensionScores !== undefined) {
    loggedCategories.push("dimension_scores");
  }
  var model = {
    report_title: "V550 AI Usage & Learning Report",
    course: auth.course,
    stage: "stage_1_scope",
    student_key: auth.studentKey,
    sanitized_project_title: metrics.sanitizedProjectTitle,
    session_id: state.sessionId,
    attempt_number: state.attemptNumber,
    receipt: {
      schema_version: config.schemaVersion,
      report_id: reportId,
      session_id: state.sessionId,
      attempt_number: state.attemptNumber,
      issuance_type: generation === 1 ? "original" : "regenerated",
      generation_number: generation,
      previous_issuance_report_id: previousReportId,
      issued_at: now.toISOString(),
      frozen_metrics_snapshot_hash: state.frozenMetricsSnapshotHash,
      pdf_sha256: stored.sha256,
      pdf_byte_length: stored.byteLength,
      verification_method: "server_held_sha256",
      verification_value: stored.sha256,
      watermark: watermark
    },
    critique_depth: {
      level: metrics.critiqueDepth,
      interpretation: critiqueDepthLabel_(metrics.critiqueDepth)
    },
    ai_reliance: {
      accepted_verbatim_count: metrics.acceptedVerbatim,
      challenged_or_modified_count: metrics.challengedOrModified,
      rejected_count: metrics.rejected,
      status: metrics.aiRelianceIndex === null
        ? "not_applicable"
        : "calculated",
      index: metrics.aiRelianceIndex
    },
    substantive_iteration_count: metrics.substantiveIterations,
    gate_attempt_count: metrics.gateAttempts,
    gate_outcome: "PASS",
    misconception_flags: metrics.misconceptionFlags.slice(),
    what_the_evidence_shows: renderView.whatEvidenceShows,
    where_ai_reliance_is_helping_or_hurting: renderView.relianceAnalysis,
    next_step_behavior: renderView.nextBehavior,
    transparency: {
      note: "This report summarizes minimized, server-held structured activity and does not infer motive or determine the Canvas grade.",
      logged_categories: loggedCategories,
      not_logged_categories: [
        "raw_transcript",
        "full_drafts",
        "evaluator_evidence_quotes",
        "names_or_contact_details",
        "sensitive_personal_information",
        "unrelated_chat_history",
        "hidden_model_reasoning",
        "secrets_or_credentials",
        "real_canvas_grade",
        "class_rank"
      ]
    },
    verification_instructions: "The instructor verifier hashes the submitted PDF bytes and compares them with the signed private report registry.",
    layout: {
      page_size: "US_LETTER",
      page_count: 1,
      minimum_font_points: 9,
      flattened: true,
      read_only_presentation: true
    },
    privacy_assertions: {
      contains_raw_transcript: false,
      contains_full_draft: false,
      contains_personal_information: false,
      contains_unrelated_history: false,
      contains_inferred_motive: false,
      contains_real_grade: false,
      contains_class_rank: false,
      contains_psychological_profile: false
    }
  };
  validateServerReportModel_(model);
  return model;
}

function critiqueDepthLabel_(depth) {
  return [
    "No critique",
    "Surface critique",
    "Substantive critique",
    "Deep critique"
  ][depth];
}

function validateReportText_(value, label, maximum) {
  var text = requireString_(value, label, 1, maximum);
  if (/^[=+@-]/.test(text) || /[\r\n]/.test(text)) {
    throw new ApiError_(
      "REPORT_MODEL_INVALID",
      label + " contains an unsafe formula prefix or newline.",
      500
    );
  }
  rejectLikelyPii_(text, label);
  return text;
}

function validateReportStringSet_(values, label, allowed, minimum, maximum) {
  if (!Array.isArray(values) || values.length < minimum || values.length > maximum) {
    throw new ApiError_("REPORT_MODEL_INVALID", label + " has an invalid count.", 500);
  }
  var seen = {};
  values.forEach(function (value) {
    if (!allowed[value] || seen[value]) {
      throw new ApiError_("REPORT_MODEL_INVALID", label + " contains an invalid or duplicate value.", 500);
    }
    seen[value] = true;
  });
}

function validateServerReportModel_(model) {
  assertPlainObject_(model, "authoritative report model");
  assertOnlyKeys_(model, {
    report_title: true,
    course: true,
    stage: true,
    student_key: true,
    sanitized_project_title: true,
    session_id: true,
    attempt_number: true,
    receipt: true,
    critique_depth: true,
    ai_reliance: true,
    substantive_iteration_count: true,
    gate_attempt_count: true,
    gate_outcome: true,
    misconception_flags: true,
    what_the_evidence_shows: true,
    where_ai_reliance_is_helping_or_hurting: true,
    next_step_behavior: true,
    transparency: true,
    verification_instructions: true,
    layout: true,
    privacy_assertions: true
  }, "authoritative report model");
  if (model.report_title !== "V550 AI Usage & Learning Report") {
    throw new ApiError_("REPORT_MODEL_INVALID", "Report title is invalid.", 500);
  }
  if (!{ V450: true, V550: true }[model.course] || model.stage !== "stage_1_scope") {
    throw new ApiError_("REPORT_MODEL_INVALID", "Course or stage is invalid.", 500);
  }
  requireString_(model.student_key, "student_key", 12, 64, /^[A-Za-z0-9_-]+$/);
  validateReportText_(model.sanitized_project_title, "sanitized_project_title", 120);
  validateOpaqueId_(model.session_id, "report session_id");
  requireInteger_(model.attempt_number, "report attempt_number", 1, 999);

  var receipt = model.receipt;
  assertPlainObject_(receipt, "report receipt");
  assertOnlyKeys_(receipt, {
    schema_version: true,
    report_id: true,
    session_id: true,
    attempt_number: true,
    issuance_type: true,
    generation_number: true,
    previous_issuance_report_id: true,
    issued_at: true,
    frozen_metrics_snapshot_hash: true,
    pdf_sha256: true,
    pdf_byte_length: true,
    verification_method: true,
    verification_value: true,
    watermark: true
  }, "report receipt");
  validateSchemaVersion_(receipt.schema_version);
  validateOpaqueId_(receipt.report_id, "report_id");
  validateOpaqueId_(receipt.session_id, "receipt session_id");
  requireInteger_(receipt.attempt_number, "receipt attempt_number", 1, 999);
  requireInteger_(receipt.generation_number, "generation_number", 1, 999);
  requireValidServerTimestamp_(receipt.issued_at, "receipt issued_at");
  validateSha256_(receipt.frozen_metrics_snapshot_hash, "metrics snapshot hash");
  validateSha256_(receipt.pdf_sha256, "report PDF hash");
  requireInteger_(receipt.pdf_byte_length, "report PDF byte length", 1, 10485760);
  if (receipt.verification_method !== "server_held_sha256") {
    throw new ApiError_("REPORT_MODEL_INVALID", "Verification method is invalid.", 500);
  }
  requireString_(receipt.verification_value, "verification_value", 43, 256, /^[A-Za-z0-9_+/=-]+$/);
  if (
    receipt.session_id !== model.session_id ||
    receipt.attempt_number !== model.attempt_number ||
    receipt.verification_value !== receipt.pdf_sha256
  ) {
    throw new ApiError_("REPORT_MODEL_INVALID", "Receipt metadata is internally inconsistent.", 500);
  }
  if (receipt.generation_number === 1) {
    if (receipt.issuance_type !== "original" || receipt.previous_issuance_report_id !== null || receipt.watermark !== null) {
      throw new ApiError_("REPORT_MODEL_INVALID", "Original issuance metadata is invalid.", 500);
    }
  } else {
    validateOpaqueId_(receipt.previous_issuance_report_id, "previous issuance report ID");
    var expectedWatermark = "REGENERATED COPY — GENERATION " + receipt.generation_number + " — PREVIOUS ISSUANCE EXISTS";
    if (receipt.issuance_type !== "regenerated" || receipt.watermark !== expectedWatermark) {
      throw new ApiError_("REPORT_MODEL_INVALID", "Regenerated issuance metadata is invalid.", 500);
    }
  }

  assertOnlyKeys_(model.critique_depth, { level: true, interpretation: true }, "critique_depth");
  requireInteger_(model.critique_depth.level, "critique depth", 0, 3);
  if (model.critique_depth.interpretation !== critiqueDepthLabel_(model.critique_depth.level)) {
    throw new ApiError_("REPORT_MODEL_INVALID", "Critique interpretation is invalid.", 500);
  }
  assertOnlyKeys_(model.ai_reliance, {
    accepted_verbatim_count: true,
    challenged_or_modified_count: true,
    rejected_count: true,
    status: true,
    index: true
  }, "ai_reliance");
  ["accepted_verbatim_count", "challenged_or_modified_count", "rejected_count"].forEach(function (field) {
    requireInteger_(model.ai_reliance[field], field, 0, 100000);
  });
  var denominator = model.ai_reliance.accepted_verbatim_count +
    model.ai_reliance.challenged_or_modified_count + model.ai_reliance.rejected_count;
  if (denominator === 0) {
    if (model.ai_reliance.status !== "not_applicable" || model.ai_reliance.index !== null) {
      throw new ApiError_("REPORT_MODEL_INVALID", "Zero AI dispositions require a not-applicable reliance index.", 500);
    }
  } else if (
    model.ai_reliance.status !== "calculated" ||
    typeof model.ai_reliance.index !== "number" ||
    model.ai_reliance.index < 0 ||
    model.ai_reliance.index > 100 ||
    Math.abs(
      model.ai_reliance.index -
      Math.round(
        model.ai_reliance.accepted_verbatim_count / denominator * 10000
      ) / 100
    ) > 0.001
  ) {
    throw new ApiError_("REPORT_MODEL_INVALID", "Calculated AI reliance is invalid.", 500);
  }
  requireInteger_(model.substantive_iteration_count, "substantive_iteration_count", 0, 100000);
  requireInteger_(model.gate_attempt_count, "gate_attempt_count", 1, 999);
  if (model.gate_outcome !== "PASS") {
    throw new ApiError_("REPORT_MODEL_INVALID", "An issued report requires PASS.", 500);
  }
  validateReportStringSet_(model.misconception_flags, "misconception_flags", MISCONCEPTION_FLAGS_, 0, 12);
  validateReportText_(model.what_the_evidence_shows, "what_the_evidence_shows", 800);
  validateReportText_(model.where_ai_reliance_is_helping_or_hurting, "where_ai_reliance_is_helping_or_hurting", 800);
  validateReportText_(model.next_step_behavior, "next_step_behavior", 300);

  var transparency = model.transparency;
  assertOnlyKeys_(transparency, {
    note: true,
    logged_categories: true,
    not_logged_categories: true
  }, "transparency");
  validateReportText_(transparency.note, "transparency note", 800);
  var loggedAllowed = {
    pseudonymous_student_key: true,
    session_and_attempt_ids: true,
    structured_event_codes: true,
    artifact_and_version_ids: true,
    critique_depth: true,
    ai_disposition_counts: true,
    ai_reliance_index: true,
    substantive_iteration_count: true,
    gate_counts_and_outcome: true,
    misconception_flags: true,
    dimension_scores: true,
    sanitized_digest_and_report_metadata: true
  };
  var notLoggedAllowed = {
    raw_transcript: true,
    full_drafts: true,
    evaluator_evidence_quotes: true,
    names_or_contact_details: true,
    sensitive_personal_information: true,
    unrelated_chat_history: true,
    hidden_model_reasoning: true,
    secrets_or_credentials: true,
    real_canvas_grade: true,
    class_rank: true
  };
  validateReportStringSet_(transparency.logged_categories, "logged_categories", loggedAllowed, 1, 12);
  validateReportStringSet_(transparency.not_logged_categories, "not_logged_categories", notLoggedAllowed, 7, 10);
  if (transparency.not_logged_categories.indexOf("raw_transcript") < 0) {
    throw new ApiError_("REPORT_MODEL_INVALID", "Transparency must identify raw transcripts as not logged.", 500);
  }
  validateReportText_(model.verification_instructions, "verification_instructions", 800);

  assertOnlyKeys_(model.layout, {
    page_size: true,
    page_count: true,
    minimum_font_points: true,
    flattened: true,
    read_only_presentation: true
  }, "layout");
  if (
    model.layout.page_size !== "US_LETTER" ||
    model.layout.page_count !== 1 ||
    typeof model.layout.minimum_font_points !== "number" ||
    model.layout.minimum_font_points < 9 ||
    model.layout.minimum_font_points > 14 ||
    model.layout.flattened !== true ||
    model.layout.read_only_presentation !== true
  ) {
    throw new ApiError_("REPORT_MODEL_INVALID", "Report layout is invalid.", 500);
  }
  var privacy = model.privacy_assertions;
  var privacyFields = {
    contains_raw_transcript: true,
    contains_full_draft: true,
    contains_personal_information: true,
    contains_unrelated_history: true,
    contains_inferred_motive: true,
    contains_real_grade: true,
    contains_class_rank: true,
    contains_psychological_profile: true
  };
  assertOnlyKeys_(privacy, privacyFields, "privacy_assertions");
  Object.keys(privacyFields).forEach(function (field) {
    if (privacy[field] !== false) {
      throw new ApiError_("REPORT_MODEL_INVALID", "Privacy assertion " + field + " must be false.", 500);
    }
  });
  return model;
}

function critiqueInterpretation_(depth) {
  return [
    "No demonstrated critique in the recorded pattern.",
    "Surface critique: mostly wording or format response without a material test.",
    "Substantive critique: a material issue was revised with a relevant reason.",
    "Deep critique: assumptions, evidence, trade-offs, or boundaries were tested."
  ][depth] || "No demonstrated critique in the recorded pattern.";
}

function evidenceParagraph_(metrics) {
  if (metrics.critiqueDepth === 0 && metrics.substantiveIterations === 0) {
    return "The structured record shows no substantive critique or material iteration. " +
      "Gate 6 opened because the explicit hard checks passed; the thin learning " +
      "pattern remains a non-blocking signal for instructor review.";
  }
  if (metrics.critiqueDepth >= 3) {
    return "The structured record shows deep critique and " +
      metrics.substantiveIterations +
      " substantive iteration(s). The student tested assumptions or boundaries " +
      "and completed the Gate 6 audit before the final OPEN result.";
  }
  if (metrics.critiqueDepth === 2) {
    return "The structured record shows substantive critique and " +
      metrics.substantiveIterations +
      " material iteration(s). Revisions were connected to a project reason or " +
      "course concept before the final Gate 6 OPEN result.";
  }
  return "The structured record shows surface-level critique and " +
    metrics.substantiveIterations +
    " material iteration(s). The gate result is OPEN, while the evidence suggests " +
    "the student can make future critique more decision-focused.";
}

function relianceParagraph_(metrics) {
  if (metrics.aiRelianceIndex === null) {
    return "AI reliance is N/A because no accepted, modified/challenged, or rejected " +
      "suggestion dispositions were recorded. This is a missing signal, not proof " +
      "of either independence or misuse.";
  }
  if (metrics.aiRelianceIndex >= 70) {
    return "The AI-reliance index is " + metrics.aiRelianceIndex +
      "%. Verbatim acceptance dominates the recorded dispositions, so the next " +
      "revision should test one consequential suggestion before accepting it.";
  }
  if (metrics.aiRelianceIndex <= 30) {
    return "The AI-reliance index is " + metrics.aiRelianceIndex +
      "%. Most recorded dispositions challenged, modified, or rejected guidance; " +
      "the useful next step is to keep those decisions evidence-linked.";
  }
  return "The AI-reliance index is " + metrics.aiRelianceIndex +
    "%. The record contains a mix of verbatim acceptance and student challenge; " +
    "future revisions should make the reason for each consequential choice explicit.";
}

function nextBehavior_(metrics) {
  if (metrics.misconceptionFlags.length) {
    return "In the next PM task, revisit the first flagged misconception (" +
      metrics.misconceptionFlags[0] +
      ") and write one evidence-based check before accepting AI guidance.";
  }
  if (metrics.critiqueDepth < 2) {
    return "In the next PM task, challenge one consequential AI suggestion by naming " +
      "the assumption, testing it against evidence, and recording your decision.";
  }
  return "In the next PM task, preserve this critique pattern and make one trade-off " +
    "explicit before finalizing the scope boundary.";
}

function renderReportPdf_(model) {
  var lines = [];
  addReportLine_(lines, model.title, "F2", 14, 16);
  addReportLine_(lines, "Course / stage: " + model.course + " / " + model.stage, "F1", 9, 11);
  addReportLine_(lines, "Pseudonymous key: " + model.studentKey, "F1", 9, 11);
  addReportLine_(lines, "Project: " + model.projectTitle, "F1", 9, 11);
  addReportLine_(lines, "Session / stage attempt: " + model.sessionId + " / " + model.attemptNumber, "F1", 9, 11);
  var generationLabel = model.generationNumber === 1
    ? "Generation 1 — ORIGINAL"
    : "Generation " + model.generationNumber + " — REGENERATED";
  addReportLine_(lines, "Report: " + model.reportId + " | " + generationLabel, "F1", 9, 11);
  addReportLine_(lines, "Issued: " + model.issuedAt + " | Schema/template: " + model.schemaVersion + " / " + model.templateVersion, "F1", 9, 13);

  addReportLine_(lines, "Learning signals", "F2", 11, 14);
  addWrappedReportLines_(lines, "Critique depth " + model.metrics.critiqueDepth + "/3 — " + model.critiqueInterpretation, "F1", 9, 11, 96);
  addReportLine_(lines, "AI reliance: " + (model.metrics.aiRelianceIndex === null ? "N/A" : model.metrics.aiRelianceIndex + "%") +
    " | accepted " + model.metrics.acceptedVerbatim +
    " | challenged/modified " + model.metrics.challengedOrModified +
    " | rejected " + model.metrics.rejected, "F1", 9, 11);
  addReportLine_(lines, "Substantive iterations: " + model.metrics.substantiveIterations +
    " | Gate attempts: " + model.metrics.gateAttempts +
    " | Gate 6: " + model.metrics.gateOutcome, "F1", 9, 11);
  addWrappedReportLines_(lines, "Misconception flags: " +
    (model.metrics.misconceptionFlags.length
      ? model.metrics.misconceptionFlags.join(", ")
      : "None recorded"), "F1", 9, 11, 108);

  addReportLine_(lines, "What the evidence shows", "F2", 11, 14);
  addWrappedReportLines_(lines, model.whatEvidenceShows, "F1", 9, 11, 100);
  addReportLine_(lines, "Where AI reliance is helping or hurting", "F2", 11, 14);
  addWrappedReportLines_(lines, model.relianceAnalysis, "F1", 9, 11, 100);
  addReportLine_(lines, "Next behavior", "F2", 11, 14);
  addWrappedReportLines_(lines, model.nextBehavior, "F1", 9, 11, 100);

  addReportLine_(lines, "Transparency", "F2", 11, 14);
  addWrappedReportLines_(lines, model.transparency, "F1", 9, 11, 110);
  addReportLine_(lines, "Verification", "F2", 11, 14);
  addWrappedReportLines_(
    lines,
    "Receipt: " + model.reportId +
      ". The instructor verifier hashes the submitted bytes and compares them " +
      "with the signed private registry. The download capability is not printed " +
      "in this report.",
    "F1",
    9,
    11,
    110
  );

  return buildSinglePagePdf_(
    lines,
    model.watermark,
    "V550_Report_" + model.reportId + ".pdf"
  );
}

function addReportLine_(lines, text, font, size, leading) {
  lines.push({ text: String(text), font: font, size: size, leading: leading });
}

function addWrappedReportLines_(lines, text, font, size, leading, width) {
  wrapReportText_(String(text), width).forEach(function (line) {
    addReportLine_(lines, line, font, size, leading);
  });
}

function wrapReportText_(text, maximumCharacters) {
  var words = text.replace(/\s+/g, " ").trim().split(" ");
  var lines = [];
  var current = "";
  words.forEach(function (word) {
    if (!current) {
      current = word;
    } else if ((current + " " + word).length <= maximumCharacters) {
      current += " " + word;
    } else {
      lines.push(current);
      current = word;
    }
  });
  if (current) lines.push(current);
  return lines.length ? lines : [""];
}

function buildSinglePagePdf_(lines, watermark, filename) {
  var y = 756;
  var commands = ["q\n"];
  if (watermark) {
    commands.push(
      "0.88 g BT /F2 15 Tf 0.7071 0.7071 -0.7071 0.7071 95 260 Tm (" +
      pdfEscapeWinAnsi_(watermark) +
      ") Tj ET 0 g\n"
    );
  }
  lines.forEach(function (line) {
    if (y < 38) {
      throw new ApiError_(
        "REPORT_LAYOUT_FAILED",
        "The report did not fit on one readable page.",
        500
      );
    }
    commands.push(
      "BT /" + line.font + " " + line.size + " Tf 42 " + y +
      " Td (" + pdfEscapeWinAnsi_(line.text) + ") Tj ET\n"
    );
    y -= line.leading;
  });
  commands.push("Q\n");
  var stream = commands.join("");
  var objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] " +
      "/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    "<< /Length " + stream.length + " >>\nstream\n" + stream + "endstream"
  ];
  var pdf = "%PDF-1.4\n%V550\n";
  var offsets = [0];
  objects.forEach(function (object, index) {
    offsets.push(pdf.length);
    pdf += (index + 1) + " 0 obj\n" + object + "\nendobj\n";
  });
  var xref = pdf.length;
  pdf += "xref\n0 " + (objects.length + 1) + "\n";
  pdf += "0000000000 65535 f \n";
  offsets.slice(1).forEach(function (offset) {
    pdf += ("0000000000" + offset).slice(-10) + " 00000 n \n";
  });
  pdf += "trailer\n<< /Size " + (objects.length + 1) + " /Root 1 0 R >>\n";
  pdf += "startxref\n" + xref + "\n%%EOF\n";
  return Utilities.newBlob(pdf, "application/pdf", filename);
}

function pdfEscapeWinAnsi_(value) {
  var replacements = {
    "—": "\\227",
    "–": "\\226",
    "“": "\\223",
    "”": "\\224",
    "‘": "\\221",
    "’": "\\222",
    "•": "\\225"
  };
  return String(value).split("").map(function (character) {
    if (replacements[character]) return replacements[character];
    var code = character.charCodeAt(0);
    if (character === "\\" || character === "(" || character === ")") {
      return "\\" + character;
    }
    if (code < 32 || code > 126) return "?";
    return character;
  }).join("");
}
