/**
 * Server-authoritative report issuance and append-only registry.
 *
 * The single public issueReport operation accepts only the common wire fields,
 * sessionId, and an optional regenerate boolean. With regenerate omitted/false,
 * the server creates Generation 1 when none exists or refreshes a capability for
 * the latest exact stored object. With regenerate true, it creates a new object
 * and generation for the same server-derived stage attempt.
 *
 * Report prose, PDF bytes, hashes, storage IDs, attempts, generations, statuses,
 * key versions, and template versions are never accepted from the client.
 */

function validateIssueReportRequest_(payload) {
  assertOnlyKeys_(
    payload,
    {
      operation: true,
      classToken: true,
      studentKey: true,
      requestId: true,
      schemaVersion: true,
      sessionId: true,
      regenerate: true
    },
    "issueReport request"
  );
  var result = commonWireValues_(payload);
  result.sessionId = validateOpaqueId_(payload.sessionId, "sessionId");
  if (
    payload.regenerate !== undefined &&
    typeof payload.regenerate !== "boolean"
  ) {
    throw new ApiError_(
      "INVALID_FIELD",
      "regenerate must be a boolean when supplied.",
      400
    );
  }
  result.regenerate = payload.regenerate === true;
  // Internal-only idempotency partition; this is not a public request field.
  result.phase = result.regenerate ? "regenerate" : "issue";
  return result;
}

function handleIssueReport_(sheet, auth, request, now, bodyHash) {
  requireConsentedSession_(sheet, request.sessionId);
  enforceRateLimit_(auth, now);

  // Recover a committed issuance when a prior request failed only while writing
  // its acknowledgement row. This prevents a retry from creating Generation N+1.
  var recovered = recoverCommittedReportRequest_(
    sheet,
    auth,
    request,
    now,
    bodyHash
  );
  if (recovered) return recovered;

  var config = reportConfiguration_();
  requireCurrentReportSchema_(request, config);
  var state = requireReportableStageState_(sheet, request.sessionId);
  var current = latestIssuedReportForAttempt_(
    sheet,
    auth,
    state.attemptNumber
  );

  if (request.regenerate) {
    if (!current) {
      throw new ApiError_(
        "REPORT_NOT_FOUND",
        "There is no current issuance to regenerate.",
        409
      );
    }
    return issueNewReport_(
      sheet,
      auth,
      request,
      state,
      current,
      config,
      now,
      bodyHash
    );
  }

  if (current) {
    return refreshCurrentReportDownload_(auth, request, current, config, now);
  }
  return issueNewReport_(
    sheet,
    auth,
    request,
    state,
    null,
    config,
    now,
    bodyHash
  );
}

function requireConsentedSession_(sheet, sessionId) {
  var rows = findStudentRecords_(sheet, { session_id: sessionId });
  var consents = rows.filter(function (row) {
    return row.event_type === "consent_recorded";
  });
  var starts = rows.filter(function (row) {
    return row.event_type === "session_started";
  });
  if (
    consents.length !== 1 ||
    starts.length !== 1 ||
    consents[0]._rowNumber >= starts[0]._rowNumber
  ) {
    throw new ApiError_(
      "CONSENT_REQUIRED",
      "A valid consented session is required.",
      409
    );
  }
  return starts[0];
}

function requireReportableStageState_(sheet, sessionId) {
  var rows = readAllStudentRecords_(sheet);
  var attempt = deriveCurrentStageAttempt_(sheet);
  var gateResults = rows.filter(function (row) {
    return Number(row.attempt_number) === attempt &&
      row.event_type === "gate_result" &&
      isGate6ResultRow_(row);
  });
  if (!gateResults.length) {
    throw new ApiError_(
      "GATE_6_OPEN_REQUIRED",
      "A Gate 6 result is required before report issuance.",
      409
    );
  }
  var latestGate = gateResults.reduce(function (latest, row) {
    return !latest || row._rowNumber > latest._rowNumber ? row : latest;
  }, null);
  if (!isOpenGateOutcome_(latestGate.gate_outcome)) {
    throw new ApiError_(
      "GATE_6_OPEN_REQUIRED",
      "Gate 6 must be OPEN before report issuance.",
      409
    );
  }

  var evidenceRows = stageAttemptEvidenceRows_(
    rows,
    attempt,
    latestGate._rowNumber
  );
  var sequence = requireOrderedGateReevaluation_(
    evidenceRows,
    attempt,
    latestGate
  );

  var metrics = collectServerReportMetrics_(evidenceRows, latestGate);
  var frozenSnapshotHash = hashKey_(canonicalJson_({
    attemptNumber: attempt,
    gateEventId: latestGate.event_id,
    gateRequestHash: latestGate.request_hash,
    affectedGate: sequence.affectedGate,
    orderedGateAttemptEventIds: sequence.gateAttempts.map(function (row) {
      return row.event_id;
    }),
    orderedGateResultEventIds: sequence.gateResults.map(function (row) {
      return row.event_id;
    }),
    auditEventId: sequence.audit.event_id,
    gate6RevisionEventId: sequence.gate6Revision.event_id,
    metrics: metrics
  }));
  return {
    sessionId: sessionId,
    attemptNumber: attempt,
    latestGate: latestGate,
    latestAudit: sequence.audit,
    affectedGate: sequence.affectedGate,
    metrics: metrics,
    frozenMetricsSnapshotHash: frozenSnapshotHash
  };
}

function isGate6ResultRow_(row) {
  var identity = canonicalGateIdentityFromCodes_(reasonCodesFromRow_(row));
  return row.event_type === "gate_result" &&
    identity &&
    identity.gateNumber === 6 &&
    { RESULT: true, OPEN: true, CLOSED: true }[identity.qualifier];
}

function isOpenGateOutcome_(value) {
  return value === "OPEN" || value === "PASS";
}

function gateNumberFromLedgerRow_(row) {
  var identity = canonicalGateIdentityFromCodes_(reasonCodesFromRow_(row));
  return identity ? identity.gateNumber : 0;
}

/**
 * Reportability is derived from append-only server rows. Attempt 1 must show
 * Gates 1 through 6 in order. A later attempt starts at its earliest affected
 * gate and must re-evaluate that gate plus every downstream gate. The latest
 * result for each required gate must be OPEN and must follow a matching attempt.
 * Gate 6 additionally requires the Gate 6B audit -> versioned revision ->
 * attempt -> OPEN ordering. No client-supplied attempt value participates.
 */
function requireOrderedGateReevaluation_(evidenceRows, attempt, latestGate) {
  var rows = evidenceRows.slice().sort(function (left, right) {
    return left._rowNumber - right._rowNumber;
  });
  var revisions = rows.filter(function (row) {
    return row.event_type === "revision_submitted" &&
      Boolean(row.artifact_version_id) &&
      gateNumberFromLedgerRow_(row) >= 1;
  });
  if (attempt > 1 && !revisions.length) {
    throw new ApiError_(
      "NEW_ATTEMPT_REVISION_REQUIRED",
      "A later stage attempt requires a versioned revision bound to an affected gate.",
      409
    );
  }

  var affectedGate = attempt > 1
    ? revisions.reduce(function (minimum, row) {
      return Math.min(minimum, gateNumberFromLedgerRow_(row));
    }, 6)
    : 1;
  var gateAttempts = [];
  var gateResults = [];
  var cursor = 0;

  for (var gate = affectedGate; gate <= 6; gate += 1) {
    var revisionBarrier = revisions.reduce(function (maximum, row) {
      return gateNumberFromLedgerRow_(row) <= gate
        ? Math.max(maximum, row._rowNumber)
        : maximum;
    }, 0);
    var barrier = Math.max(cursor, revisionBarrier);
    var resultsForGate = rows.filter(function (row) {
      return row.event_type === "gate_result" &&
        gateNumberFromLedgerRow_(row) === gate &&
        row._rowNumber > barrier;
    });
    if (!resultsForGate.length) {
      throw new ApiError_(
        "DOWNSTREAM_REEVALUATION_REQUIRED",
        "Gate " + gate + " must be re-evaluated after the latest affected revision.",
        409
      );
    }
    var result = resultsForGate[resultsForGate.length - 1];
    if (!isOpenGateOutcome_(result.gate_outcome)) {
      throw new ApiError_(
        "DOWNSTREAM_GATE_OPEN_REQUIRED",
        "The latest required Gate " + gate + " result is not OPEN.",
        409
      );
    }
    var attemptsForGate = rows.filter(function (row) {
      return row.event_type === "gate_attempt" &&
        gateNumberFromLedgerRow_(row) === gate &&
        row._rowNumber > barrier &&
        row._rowNumber < result._rowNumber;
    });
    if (!attemptsForGate.length) {
      throw new ApiError_(
        "GATE_ATTEMPT_REQUIRED",
        "Gate " + gate + " OPEN must follow a recorded gate attempt.",
        409
      );
    }
    gateAttempts.push(attemptsForGate[attemptsForGate.length - 1]);
    gateResults.push(result);
    cursor = result._rowNumber;
  }

  var finalResult = gateResults[gateResults.length - 1];
  if (finalResult._rowNumber !== latestGate._rowNumber) {
    throw new ApiError_(
      "GATE_SEQUENCE_INVALID",
      "The ordered re-evaluation does not end at the latest Gate 6 result.",
      409
    );
  }

  var audits = rows.filter(function (row) {
    return row.event_type === "assumption_audit_completed" &&
      gateNumberFromLedgerRow_(row) === 6 &&
      row._rowNumber < latestGate._rowNumber;
  });
  if (!audits.length) {
    throw new ApiError_(
      "GATE_6B_REQUIRED",
      "The Gate 6B audit must precede Gate 6 OPEN.",
      409
    );
  }
  var audit = audits[audits.length - 1];
  var gate6Revisions = revisions.filter(function (row) {
    return gateNumberFromLedgerRow_(row) === 6 &&
      row._rowNumber > audit._rowNumber &&
      row._rowNumber < latestGate._rowNumber;
  });
  if (!gate6Revisions.length) {
    throw new ApiError_(
      "GATE_6B_REQUIRED",
      "A versioned Gate 6 revision must follow the Gate 6B audit and precede Gate 6 OPEN.",
      409
    );
  }
  var gate6Revision = gate6Revisions[gate6Revisions.length - 1];
  var gate6Attempt = gateAttempts[gateAttempts.length - 1];
  if (gate6Attempt._rowNumber <= gate6Revision._rowNumber) {
    throw new ApiError_(
      "GATE_6B_ORDER_INVALID",
      "Gate 6 must be attempted again after its Gate 6B revision.",
      409
    );
  }
  return {
    affectedGate: affectedGate,
    gateAttempts: gateAttempts,
    gateResults: gateResults,
    audit: audit,
    gate6Revision: gate6Revision
  };
}

function collectServerReportMetrics_(evidenceRows, latestGate) {
  var attemptRows = evidenceRows.filter(function (row) {
    return row._rowNumber <= latestGate._rowNumber;
  });
  var latestValue = function (column, fallback) {
    for (var index = attemptRows.length - 1; index >= 0; index -= 1) {
      if (attemptRows[index][column] !== "") return attemptRows[index][column];
    }
    return fallback;
  };
  var flags = {};
  attemptRows.forEach(function (row) {
    try {
      var parsed = JSON.parse(row.misconception_flags_json || "[]");
      if (Array.isArray(parsed)) {
        parsed.forEach(function (flag) {
          if (MISCONCEPTION_FLAGS_[flag]) flags[flag] = true;
        });
      }
    } catch (ignored) {}
  });
  var accepted = Number(latestValue("accepted_verbatim_count", 0)) || 0;
  var challenged = Number(latestValue("challenged_or_modified_count", 0)) || 0;
  var rejected = Number(latestValue("rejected_count", 0)) || 0;
  var denominator = accepted + challenged + rejected;
  var digestWorkingOn = String(latestValue("digest_working_on", ""));
  var title = digestWorkingOn.replace(/^Working on:\s*/i, "").trim();
  if (!title) title = "Stage 1 Scope Project";
  if (title.length > 120) title = title.substring(0, 120);

  var dimensionScores = null;
  try {
    if (latestGate.dimension_scores_json) {
      dimensionScores = JSON.parse(latestGate.dimension_scores_json);
    }
  } catch (ignoredScores) {}

  return {
    sanitizedProjectTitle: title,
    critiqueDepth: Math.max(
      0,
      Math.min(3, Number(latestValue("critique_depth", 0)) || 0)
    ),
    acceptedVerbatim: accepted,
    challengedOrModified: challenged,
    rejected: rejected,
    aiRelianceIndex: denominator
      ? Math.round(accepted / denominator * 10000) / 100
      : null,
    substantiveIterations: Math.max(
      0,
      Number(latestValue("substantive_iteration_count", 0)) || 0
    ),
    gateAttempts: Math.max(
      1,
      Number(latestValue("gate_attempt_count", 1)) || 1
    ),
    gateOutcome: "OPEN",
    misconceptionFlags: Object.keys(flags).sort(),
    dimensionScores: dimensionScores
  };
}

function issueNewReport_(
  sheet,
  auth,
  request,
  state,
  current,
  config,
  now,
  bodyHash
) {
  var generation = current
    ? Number(current.registry.payload.generationNumber) + 1
    : 1;
  var previousReportId = current
    ? current.registry.payload.reportId
    : null;
  var reportId = "rpt_" + Utilities.getUuid().replace(/-/g, "");
  var watermark = generation === 1
    ? null
    : "REGENERATED COPY — GENERATION " + generation +
      " — PREVIOUS ISSUANCE EXISTS";
  var renderView = buildServerReportRenderView_(
    auth,
    state,
    reportId,
    generation,
    previousReportId,
    watermark,
    now,
    config
  );

  // Render exactly once. Only these resulting bytes may become this issuance.
  var renderedPdf = renderReportPdf_(renderView);
  var stored = null;
  var model = null;
  var registryRef = null;
  var capability = null;
  var committed = false;
  try {
    stored = storeIssuedPdf_(
      renderedPdf,
      reportId,
      state.attemptNumber,
      generation,
      config
    );
    model = buildServerReportModel_(
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
    );
    var payload = {
      registryVersion: "2",
      reportId: reportId,
      sessionId: request.sessionId,
      attemptNumber: state.attemptNumber,
      generationNumber: generation,
      issuanceType: generation === 1 ? "original" : "regenerated",
      issuedAt: now.toISOString(),
      studentKeyHash: auth.studentKeyHash,
      storageObjectId: stored.objectId,
      pdfByteLength: stored.byteLength,
      pdfSha256: stored.sha256,
      frozenMetricsSnapshotHash: state.frozenMetricsSnapshotHash,
      reportModelSha256: hashKey_(canonicalJson_(model)),
      previousReportId: previousReportId,
      watermark: watermark,
      keyVersion: config.keyVersion,
      templateVersion: config.templateVersion,
      schemaVersion: config.schemaVersion
    };
    var registry = {
      payload: payload,
      signature: signVersionedPayload_(payload, config.keyVersion)
    };
    registryRef = persistReportRegistry_(registry);
    capability = createDownloadCapability_(
      registry,
      request.sessionId,
      now,
      config
    );

    // The workbook stores only a non-secret registry reference. The storage ID
    // and signed private registry remain in Script Properties.
    appendStudentRecord_(sheet, {
      row_key: hashKey_([auth.studentKey, "report_issuance", reportId].join("|")),
      row_type: "report_issuance",
      operation: "issueReport",
      phase: request.phase,
      record_id: reportId,
      server_timestamp: now.toISOString(),
      course: auth.course,
      term: auth.term,
      student_key: auth.studentKey,
      session_id: request.sessionId,
      attempt_number: state.attemptNumber,
      stage: "stage_1_scope",
      advisor: "scope_advisor",
      protocol_role: "scope_review_board",
      event_id: deterministicId_("evt", reportId + "|issued"),
      event_type: generation === 1 ? "report_issued" : "report_regenerated",
      reason_codes_json: canonicalJson_([
        generation === 1 ? "REPORT_ORIGINAL" : "REPORT_REGENERATED"
      ]),
      gate_outcome: "PASS",
      report_id: reportId,
      generation_number: generation,
      verification_hash: stored.sha256,
      schema_version: config.schemaVersion,
      request_id: request.requestId,
      request_hash: bodyHash,
      status: "ISSUED",
      receipt_json: canonicalJson_({ private_registry_ref: registryRef }),
      pdf_byte_length: stored.byteLength,
      first_received_at_server: now.toISOString(),
      updated_at_server: now.toISOString()
    });
    committed = true;

    // Dashboard is a repairable materialized view; it cannot revoke an already
    // committed immutable issuance.
    try {
      upsertDashboard_(
        auth,
        null,
        "GENERATION_" + generation + "_ISSUED",
        now
      );
    } catch (dashboardError) {
      console.warn(JSON.stringify({
        event: "report_dashboard_update_failed",
        reportIdHash: hashKey_(reportId),
        serverTimestamp: now.toISOString()
      }));
    }
    return {
      resourceId: reportId,
      sessionId: request.sessionId,
      data: reportActionData_(registry, capability)
    };
  } catch (error) {
    if (!committed) {
      if (capability && capability.propertyKey) {
        deletePrivateProperty_(capability.propertyKey);
      }
      if (registryRef) deletePrivateProperty_(registryRef);
      if (stored && stored.objectId) quarantineOrphanedReport_(stored.objectId);
    }
    throw error;
  }
}

function latestIssuedReportForAttempt_(sheet, auth, attemptNumber) {
  var rows = findStudentRecords_(sheet, {
    attempt_number: attemptNumber,
    row_type: "report_issuance"
  }).filter(function (row) {
    return row.status === "ISSUED";
  });
  if (!rows.length) return null;

  var generations = {};
  rows.forEach(function (row) {
    var generation = Number(row.generation_number);
    if (!isFinite(generation) || Math.floor(generation) !== generation || generation < 1) {
      throw new ApiError_(
        "REPORT_REGISTRY_CORRUPT",
        "A report generation record is invalid.",
        500
      );
    }
    if (generations[generation]) {
      throw new ApiError_(
        "REPORT_REGISTRY_CORRUPT",
        "Duplicate report generations were found.",
        500
      );
    }
    generations[generation] = true;
  });
  var latest = rows.reduce(function (selected, row) {
    return !selected ||
      Number(row.generation_number) > Number(selected.generation_number)
      ? row
      : selected;
  }, null);
  var registry = getVerifiedReportRegistry_(sheet, latest.report_id);
  if (
    Number(registry.payload.attemptNumber) !== Number(attemptNumber) ||
    registry.payload.studentKeyHash !== auth.studentKeyHash ||
    Number(registry.payload.generationNumber) !== Number(latest.generation_number)
  ) {
    throw new ApiError_(
      "REPORT_REGISTRY_INVALID",
      "The report registry does not match the issuance ledger.",
      500
    );
  }
  return { row: latest, registry: registry };
}

function refreshCurrentReportDownload_(auth, request, current, config, now) {
  var registry = current.registry;
  if (registry.payload.studentKeyHash !== auth.studentKeyHash) {
    throw new ApiError_(
      "REPORT_CAPABILITY_MISMATCH",
      "The report is bound to a different student key.",
      403
    );
  }
  assertStoredPdfMatchesRegistry_(registry, config);
  var capability = createDownloadCapability_(
    registry,
    request.sessionId,
    now,
    config
  );
  return {
    resourceId: registry.payload.reportId,
    sessionId: request.sessionId,
    data: reportActionData_(registry, capability)
  };
}

function recoverCommittedReportRequest_(sheet, auth, request, now, bodyHash) {
  var rows = findStudentRecords_(sheet, {
    request_id: request.requestId,
    row_type: "report_issuance"
  });
  if (!rows.length) return null;
  if (rows.length !== 1) {
    throw new ApiError_(
      "REQUEST_LEDGER_CORRUPT",
      "Duplicate report issuances exist for the request.",
      500
    );
  }
  var row = rows[0];
  if (
    row.phase !== request.phase ||
    !constantTimeEquals_(row.request_hash, bodyHash)
  ) {
    throw new ApiError_(
      "IDEMPOTENCY_CONFLICT",
      "requestId was already used with different report data.",
      409
    );
  }
  var registry = getVerifiedReportRegistry_(sheet, row.report_id);
  if (registry.payload.studentKeyHash !== auth.studentKeyHash) {
    throw new ApiError_(
      "REPORT_REGISTRY_INVALID",
      "The committed report registry is invalid.",
      500
    );
  }
  var config = reportConfiguration_();
  assertStoredPdfMatchesRegistry_(registry, config);
  var capability = createDownloadCapability_(
    registry,
    request.sessionId,
    now,
    config
  );
  return {
    resourceId: registry.payload.reportId,
    sessionId: request.sessionId,
    data: reportActionData_(registry, capability)
  };
}

function reportActionData_(registry, capability) {
  return {
    reportId: registry.payload.reportId,
    generationNumber: Number(registry.payload.generationNumber),
    issuedAtServer: registry.payload.issuedAt,
    verificationToken: capability.url
  };
}

function getVerifiedReportRegistry_(sheet, reportId) {
  var rows = findStudentRecords_(sheet, {
    report_id: reportId,
    row_type: "report_issuance"
  });
  if (rows.length !== 1 || rows[0].status !== "ISSUED") {
    throw new ApiError_("REPORT_NOT_FOUND", "Issued report was not found.", 404);
  }
  var expectedRef = reportRegistryPropertyKey_(reportId);
  var storedRef;
  try {
    var reference = JSON.parse(rows[0].receipt_json || "{}");
    assertOnlyKeys_(
      reference,
      { private_registry_ref: true },
      "report registry reference"
    );
    storedRef = reference.private_registry_ref;
  } catch (error) {
    if (error && error.name === "ApiError") throw error;
    throw new ApiError_(
      "REPORT_REGISTRY_CORRUPT",
      "Stored report registry reference is invalid.",
      500
    );
  }
  if (!constantTimeEquals_(storedRef, expectedRef)) {
    throw new ApiError_(
      "REPORT_REGISTRY_INVALID",
      "Stored report registry reference is invalid.",
      500
    );
  }
  var registry = getReportRegistryById_(reportId);
  if (!registry) {
    throw new ApiError_(
      "REPORT_REGISTRY_CORRUPT",
      "The private report registry record is missing.",
      500
    );
  }
  if (
    rows[0].verification_hash !== registry.payload.pdfSha256 ||
    Number(rows[0].pdf_byte_length) !== Number(registry.payload.pdfByteLength) ||
    Number(rows[0].generation_number) !== Number(registry.payload.generationNumber)
  ) {
    throw new ApiError_(
      "REPORT_REGISTRY_INVALID",
      "The issuance ledger does not match the signed registry.",
      500
    );
  }
  return registry;
}

function reportRegistryPropertyKey_(reportId) {
  return "REPORT_REGISTRY_" + hashKey_(reportId).substring(0, 40);
}

function persistReportRegistry_(registry) {
  var verified = parseAndVerifyRegistry_(registry);
  var key = reportRegistryPropertyKey_(verified.payload.reportId);
  var properties = PropertiesService.getScriptProperties();
  if (properties.getProperty(key)) {
    throw new ApiError_(
      "REPORT_ID_COLLISION",
      "The generated report ID already exists.",
      500
    );
  }
  properties.setProperty(key, canonicalJson_(verified));
  return key;
}

function getReportRegistryById_(reportId) {
  var key = reportRegistryPropertyKey_(reportId);
  var encoded = PropertiesService.getScriptProperties().getProperty(key);
  if (!encoded) return null;
  var registry = parseAndVerifyRegistry_(encoded);
  if (!constantTimeEquals_(registry.payload.reportId, reportId)) {
    throw new ApiError_(
      "REPORT_REGISTRY_INVALID",
      "The report registry locator is invalid.",
      500
    );
  }
  return registry;
}

function deletePrivateProperty_(propertyKey) {
  try {
    PropertiesService.getScriptProperties().deleteProperty(propertyKey);
  } catch (ignored) {}
}

function parseAndVerifyRegistry_(encoded) {
  var registry;
  try {
    registry = typeof encoded === "string" ? JSON.parse(encoded) : encoded;
  } catch (error) {
    throw new ApiError_(
      "REPORT_REGISTRY_CORRUPT",
      "Stored report registry JSON is invalid.",
      500
    );
  }
  assertOnlyKeys_(registry, { payload: true, signature: true }, "report registry");
  assertPlainObject_(registry.payload, "report registry payload");
  assertOnlyKeys_(
    registry.payload,
    {
      registryVersion: true,
      reportId: true,
      sessionId: true,
      attemptNumber: true,
      generationNumber: true,
      issuanceType: true,
      issuedAt: true,
      studentKeyHash: true,
      storageObjectId: true,
      pdfByteLength: true,
      pdfSha256: true,
      frozenMetricsSnapshotHash: true,
      reportModelSha256: true,
      previousReportId: true,
      watermark: true,
      keyVersion: true,
      templateVersion: true,
      schemaVersion: true
    },
    "report registry payload"
  );
  var payload = registry.payload;
  requireString_(payload.registryVersion, "registryVersion", 1, 8, /^[0-9]+$/);
  validateOpaqueId_(payload.reportId, "reportId");
  validateOpaqueId_(payload.sessionId, "registry sessionId");
  requireInteger_(payload.attemptNumber, "attemptNumber", 1, 1000000);
  requireInteger_(payload.generationNumber, "generationNumber", 1, 1000000);
  requireString_(
    payload.issuanceType,
    "issuanceType",
    8,
    11,
    /^(original|regenerated)$/
  );
  requireValidServerTimestamp_(payload.issuedAt, "issuedAt");
  validateSha256_(payload.studentKeyHash, "student key hash");
  requireString_(
    payload.storageObjectId,
    "storage object ID",
    10,
    200,
    /^[A-Za-z0-9_-]+$/
  );
  requireInteger_(payload.pdfByteLength, "PDF byte length", 1, 50000000);
  validateSha256_(payload.pdfSha256, "registered PDF hash");
  validateSha256_(payload.frozenMetricsSnapshotHash, "metrics snapshot hash");
  validateSha256_(payload.reportModelSha256, "report model hash");
  var keyVersion = requireString_(
    payload.keyVersion,
    "report key version",
    1,
    32,
    /^[A-Za-z0-9._-]+$/
  );
  requireString_(
    payload.templateVersion,
    "templateVersion",
    1,
    32,
    /^[A-Za-z0-9._-]+$/
  );
  validateSchemaVersion_(payload.schemaVersion);

  if (payload.generationNumber === 1) {
    if (
      payload.issuanceType !== "original" ||
      payload.previousReportId !== null ||
      payload.watermark !== null
    ) {
      throw new ApiError_(
        "REPORT_REGISTRY_INVALID",
        "Original report metadata is inconsistent.",
        500
      );
    }
  } else {
    validateOpaqueId_(payload.previousReportId, "previousReportId");
    var expectedWatermark = "REGENERATED COPY — GENERATION " +
      payload.generationNumber + " — PREVIOUS ISSUANCE EXISTS";
    if (
      payload.issuanceType !== "regenerated" ||
      payload.watermark !== expectedWatermark
    ) {
      throw new ApiError_(
        "REPORT_REGISTRY_INVALID",
        "Regenerated report metadata is inconsistent.",
        500
      );
    }
  }
  if (!verifyVersionedSignature_(payload, registry.signature, keyVersion)) {
    throw new ApiError_(
      "REPORT_REGISTRY_INVALID",
      "Report registry signature is invalid.",
      500
    );
  }
  return registry;
}

function requireValidServerTimestamp_(value, label) {
  var text = requireString_(
    value,
    label,
    20,
    40,
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/
  );
  if (!isFinite(new Date(text).getTime())) {
    throw new ApiError_("INVALID_FIELD", label + " is invalid.", 400);
  }
  return text;
}

function requireCurrentReportSchema_(request, config) {
  if (request.schemaVersion !== config.schemaVersion) {
    throw new ApiError_(
      "SCHEMA_VERSION_MISMATCH",
      "The client schema version does not match the deployed report schema.",
      409
    );
  }
}

function reportConfiguration_() {
  var properties = PropertiesService.getScriptProperties();
  var folderId = requireString_(
    properties.getProperty("REPORT_DRIVE_FOLDER_ID"),
    "REPORT_DRIVE_FOLDER_ID",
    10,
    200,
    /^[A-Za-z0-9_-]+$/
  );
  var templateVersion = requireString_(
    properties.getProperty("REPORT_TEMPLATE_VERSION"),
    "REPORT_TEMPLATE_VERSION",
    1,
    32,
    /^[A-Za-z0-9._-]+$/
  );
  var schemaVersion = validateSchemaVersion_(
    properties.getProperty("REPORT_SCHEMA_VERSION")
  );
  var ttl = Number(properties.getProperty("REPORT_CAPABILITY_TTL_SECONDS") || 900);
  if (!isFinite(ttl) || Math.floor(ttl) !== ttl || ttl < 60 || ttl > 3600) {
    throw new ApiError_(
      "SERVER_MISCONFIGURED",
      "REPORT_CAPABILITY_TTL_SECONDS must be an integer from 60 to 3600.",
      500
    );
  }
  return {
    folderId: folderId,
    templateVersion: templateVersion,
    schemaVersion: schemaVersion,
    keyVersion: activeReportKeyVersion_(),
    capabilityTtlSeconds: ttl
  };
}
