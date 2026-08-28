/**
 * V550 Stage-1 write-only Action.
 *
 * doPost exposes exactly four Action operations: startSession, logEvent,
 * closeSession, and issueReport. ReportDelivery.gs also provides one narrow
 * capability-only doGet download handler; it is not an Action or workbook API.
 * Public camelCase fields are mapped explicitly to snake_case workbook rows.
 */

var MAX_REQUEST_BYTES_ = 16384;
var LOCK_WAIT_MILLISECONDS_ = 10000;

function doPost(e) {
  var lock = null;
  var locked = false;
  var now = new Date();
  try {
    var payload = parseJsonBody_(e);
    var operation = resolveOperation_(e, payload);
    var auth = authorizeRequest_(payload, operation);
    assertNoProhibitedTelemetryFields_(payload, "request", 0);
    var validated = validateOperationRequest_(operation, payload);
    var phase = operation === "issueReport" ? validated.phase : "";
    var bodyHash = requestHash_(payload);

    lock = LockService.getScriptLock();
    locked = lock.tryLock(LOCK_WAIT_MILLISECONDS_);
    if (!locked) {
      throw new ApiError_(
        "SERVICE_BUSY",
        "Writer is busy; retry with the same requestId.",
        503
      );
    }

    var studentSheet = operation === "startSession"
      ? getOrCreateStudentTab_(auth, now)
      : getExistingStudentTab_(auth);
    var prior = findRequestReceipt_(
      studentSheet,
      operation,
      phase,
      validated.requestId
    );
    if (prior) return jsonOutput_(replayRequest_(prior, bodyHash));

    var result;
    if (operation === "startSession") {
      result = handleStartSession_(studentSheet, auth, validated, now, bodyHash);
    } else if (operation === "logEvent") {
      result = handleLogEvent_(studentSheet, auth, validated, now);
    } else if (operation === "closeSession") {
      result = handleCloseSession_(studentSheet, auth, validated, now, bodyHash);
    } else {
      result = handleIssueReport_(studentSheet, auth, validated, now, bodyHash);
    }

    var response;
    if (operation === "issueReport") {
      // The report Action contract permits exactly these four receipt fields.
      response = result.data;
    } else if (operation === "startSession") {
      response = {
        ok: true,
        operation: operation,
        serverTimestamp: now.toISOString(),
        sessionId: result.sessionId
      };
    } else {
      response = {
        ok: true,
        operation: operation,
        serverTimestamp: now.toISOString(),
        acknowledged: true,
        duplicate: Boolean(result.data && result.data.duplicate)
      };
    }
    recordRequestReceipt_(
      studentSheet,
      auth,
      operation,
      phase,
      validated.requestId,
      bodyHash,
      {
        sessionId: result.sessionId,
        schemaVersion: validated.schemaVersion
      },
      response,
      now
    );
    return jsonOutput_(response);
  } catch (error) {
    logControlledFailure_(error, now);
    return jsonOutput_(errorResponse_(error, now));
  } finally {
    if (lock && locked) lock.releaseLock();
  }
}

function parseJsonBody_(e) {
  if (!e || !e.postData || typeof e.postData.contents !== "string") {
    throw new ApiError_("INVALID_REQUEST", "JSON request body is required.", 400);
  }
  var contents = e.postData.contents;
  var byteLength = contents.length;
  try {
    byteLength = Utilities.newBlob(contents).getBytes().length;
  } catch (error) {
    byteLength = contents.length * 2;
  }
  if (!contents.length || byteLength > MAX_REQUEST_BYTES_) {
    throw new ApiError_(
      "INVALID_REQUEST_SIZE",
      "Request body must not exceed 16,384 bytes.",
      contents.length ? 413 : 400
    );
  }
  if (
    e.postData.type &&
    String(e.postData.type).toLowerCase().indexOf("application/json") === -1
  ) {
    throw new ApiError_(
      "UNSUPPORTED_MEDIA_TYPE",
      "Content-Type must be application/json.",
      415
    );
  }
  try {
    var parsed = JSON.parse(contents);
    assertPlainObject_(parsed, "request body");
    return parsed;
  } catch (error) {
    if (error && error.name === "ApiError") throw error;
    throw new ApiError_("INVALID_JSON", "Request body is not valid JSON.", 400);
  }
}

function resolveOperation_(e, payload) {
  var path = String((e && e.pathInfo) || "").replace(/^\/+|\/+$/g, "");
  if (path.indexOf("/") !== -1) {
    throw new ApiError_("OPERATION_NOT_ALLOWED", "Nested paths are not allowed.", 404);
  }
  var bodyOperation = requireString_(
    payload.operation,
    "operation",
    8,
    16,
    /^[A-Za-z]+$/
  );
  if (path && bodyOperation && path !== bodyOperation) {
    throw new ApiError_(
      "OPERATION_MISMATCH",
      "Path and body operations do not match.",
      400
    );
  }
  var operation = path || bodyOperation;
  if (!PUBLIC_OPERATIONS_[operation]) {
    throw new ApiError_("OPERATION_NOT_ALLOWED", "Operation is not allowed.", 404);
  }
  return operation;
}

function validateOperationRequest_(operation, payload) {
  if (operation === "startSession") return validateStartSessionRequest_(payload);
  if (operation === "logEvent") return validateLogEventRequest_(payload);
  if (operation === "closeSession") return validateCloseSessionRequest_(payload);
  return validateIssueReportRequest_(payload);
}

function commonWireValues_(payload) {
  return {
    requestId: validateOpaqueId_(payload.requestId, "requestId"),
    schemaVersion: validateSchemaVersion_(payload.schemaVersion)
  };
}

function validateStartSessionRequest_(payload) {
  assertOnlyKeys_(
    payload,
    {
      operation: true,
      classToken: true,
      studentKey: true,
      requestId: true,
      schemaVersion: true,
      consent: true
    },
    "startSession request"
  );
  assertOnlyKeys_(
    payload.consent,
    {
      asserted: true,
      version: true,
      clientObservedAt: true
    },
    "startSession request consent"
  );
  var result = commonWireValues_(payload);
  if (payload.consent.asserted !== true) {
    throw new ApiError_("CONSENT_REQUIRED", "Visible consent is required.", 400);
  }
  result.consentVersion = validateConsentVersion_(payload.consent.version);
  result.clientObservedConsentAt = validateClientObservedTimestamp_(
    payload.consent.clientObservedAt
  );
  return result;
}

function validateLogEventRequest_(payload) {
  assertOnlyKeys_(
    payload,
    {
      operation: true,
      classToken: true,
      studentKey: true,
      requestId: true,
      schemaVersion: true,
      sessionId: true,
      eventId: true,
      eventType: true,
      stage: true,
      role: true,
      artifactVersionId: true,
      metrics: true,
      reasonCodes: true,
      oneLineNote: true,
      misconceptionFlags: true,
      digest: true,
      gateOutcome: true,
      dimensionScores: true
    },
    "logEvent request"
  );
  var result = commonWireValues_(payload);
  result.sessionId = validateOpaqueId_(payload.sessionId, "sessionId");
  result.eventId = validateOpaqueId_(payload.eventId, "eventId");
  result.eventType = validateEventType_(payload.eventType);
  result.stage = validateStage_(payload.stage);
  result.role = validateProtocolRole_(payload.role);
  validateEventRole_(result.eventType, result.role);
  result.artifactVersionId = payload.artifactVersionId === undefined
    ? ""
    : validateOpaqueId_(payload.artifactVersionId, "artifactVersionId");
  result.metrics = validateMetrics_(payload.metrics);
  result.reasonCodes = validateStringEnumArray_(
    payload.reasonCodes,
    "reasonCodes",
    null,
    20,
    /^[A-Za-z0-9_:-]+$/
  );
  result.oneLineNote = validateOneLineNote_(payload.oneLineNote);
  result.misconceptionFlags = validateStringEnumArray_(
    payload.misconceptionFlags,
    "misconceptionFlags",
    MISCONCEPTION_FLAGS_,
    12
  );
  result.digest = validateDigest_(payload.digest);
  result.gateOutcome = validateGateOutcome_(payload.gateOutcome);
  result.dimensionScores = validateDimensionScores_(payload.dimensionScores);

  if (result.eventType === "daily_summary_written" && !result.digest) {
    throw new ApiError_(
      "INVALID_FIELD",
      "daily_summary_written requires digest.",
      400
    );
  }
  if (result.eventType === "gate_result" && !result.gateOutcome) {
    throw new ApiError_(
      "INVALID_FIELD",
      "gate_result requires gateOutcome. Advisory dimension scores are optional.",
      400
    );
  }
  if (
    result.eventType === "gate_result" &&
    result.gateOutcome === "INCOMPLETE"
  ) {
    throw new ApiError_(
      "NO_ATTEMPT_NOT_LOGGABLE",
      "Diagnostic INCOMPLETE is not a recorded gate result.",
      400
    );
  }
  result.gateNumber = validateGateEventIdentity_(
    result.eventType,
    result.reasonCodes,
    result.gateOutcome
  );
  if ({
    consent_recorded: true,
    session_started: true,
    session_closed: true,
    report_issued: true,
    report_regenerated: true
  }[result.eventType]) {
    throw new ApiError_(
      "SERVER_OWNED_EVENT",
      "This event type is emitted only by the server.",
      400
    );
  }
  if (
    result.eventType === "revision_submitted" &&
    !result.artifactVersionId
  ) {
    throw new ApiError_(
      "INVALID_FIELD",
      "revision_submitted requires artifactVersionId.",
      400
    );
  }
  return result;
}

function validateCloseSessionRequest_(payload) {
  assertOnlyKeys_(
    payload,
    {
      operation: true,
      classToken: true,
      studentKey: true,
      requestId: true,
      schemaVersion: true,
      sessionId: true,
      stage: true,
      role: true,
      metrics: true,
      reasonCodes: true,
      oneLineNote: true,
      misconceptionFlags: true,
      digest: true,
      gateOutcome: true
    },
    "closeSession request"
  );
  var result = commonWireValues_(payload);
  result.sessionId = validateOpaqueId_(payload.sessionId, "sessionId");
  result.stage = validateStage_(payload.stage);
  result.role = validateProtocolRole_(payload.role);
  if (result.role !== "summarizer") {
    throw new ApiError_(
      "ROLE_EVENT_MISMATCH",
      "Only the summarizer protocol may close a session.",
      400
    );
  }
  result.metrics = validateMetrics_(payload.metrics);
  result.reasonCodes = validateStringEnumArray_(
    payload.reasonCodes,
    "reasonCodes",
    null,
    20,
    /^[A-Za-z0-9_:-]+$/
  );
  result.oneLineNote = validateOneLineNote_(payload.oneLineNote);
  result.misconceptionFlags = validateStringEnumArray_(
    payload.misconceptionFlags,
    "misconceptionFlags",
    MISCONCEPTION_FLAGS_,
    12
  );
  result.digest = validateDigest_(payload.digest);
  result.gateOutcome = validateGateOutcome_(payload.gateOutcome);
  if (!result.digest) {
    throw new ApiError_(
      "INVALID_FIELD",
      "closeSession requires the sanitized three- or four-line digest.",
      400
    );
  }
  return result;
}

function validateGateOutcome_(value) {
  if (value === undefined || value === null || value === "") return "";
  requireString_(
    value,
    "gateOutcome",
    4,
    10,
    /^(PASS|REVISE|INCOMPLETE)$/
  );
  var allowed = {
    PASS: true,
    REVISE: true,
    INCOMPLETE: true
  };
  if (!allowed[value]) {
    throw new ApiError_("INVALID_FIELD", "gateOutcome is invalid.", 400);
  }
  if (value === "PASS") return "OPEN";
  if (value === "REVISE") return "CLOSED";
  return "INCOMPLETE";
}

/**
 * Gate identity travels only in the unchanged reasonCodes array. Accept a
 * deliberately small vocabulary so an arbitrary client string cannot forge an
 * affected gate, a Gate 6 result, or a Gate 6B audit.
 */
function parseCanonicalGateIdentityCode_(code) {
  var match = /^GATE_([1-6])(?:_(ATTEMPT_RECORDED|RESULT|OPEN|CLOSED))?$/.exec(
    String(code || "")
  );
  if (!match) return null;
  return {
    gateNumber: Number(match[1]),
    qualifier: match[2] || "GATE"
  };
}

function canonicalGateIdentityFromCodes_(reasonCodes) {
  var identities = (reasonCodes || []).map(function (code) {
    return parseCanonicalGateIdentityCode_(code);
  }).filter(function (identity) {
    return identity !== null;
  });
  return identities.length === 1 ? identities[0] : null;
}

function validateGateEventIdentity_(eventType, reasonCodes, gateOutcome) {
  var expected = {
    revision_submitted: { GATE: true },
    assumption_audit_completed: { GATE: true },
    gate_attempt: { ATTEMPT_RECORDED: true },
    gate_result: { RESULT: true, OPEN: true, CLOSED: true }
  }[eventType];
  if (!expected) return 0;

  var gateLikeCodes = (reasonCodes || []).filter(function (code) {
    return /^GATE_/i.test(String(code || ""));
  });
  var identity = canonicalGateIdentityFromCodes_(reasonCodes);
  if (!identity || gateLikeCodes.length !== 1 || !expected[identity.qualifier]) {
    throw new ApiError_(
      "GATE_IDENTITY_REQUIRED",
      eventType + " requires exactly one canonical gate identity reason code.",
      400
    );
  }
  if (
    eventType === "assumption_audit_completed" &&
    identity.gateNumber !== 6
  ) {
    throw new ApiError_(
      "GATE_IDENTITY_INVALID",
      "The final assumption audit is internal to Gate 6.",
      400
    );
  }
  if (
    eventType === "gate_result" &&
    ((identity.qualifier === "OPEN" && gateOutcome !== "OPEN") ||
      (identity.qualifier === "CLOSED" && gateOutcome !== "CLOSED"))
  ) {
    throw new ApiError_(
      "GATE_RESULT_CONTRADICTION",
      "The gate identity reason code contradicts gateOutcome.",
      400
    );
  }
  return identity.gateNumber;
}

function handleStartSession_(sheet, auth, request, now, bodyHash) {
  var sessionId = deterministicId_(
    "ses",
    [auth.studentKey, request.requestId].join("|")
  );
  var consentEventId = deterministicId_("evt", sessionId + "|consent_recorded");
  var sessionEventId = deterministicId_("evt", sessionId + "|session_started");
  var existingStarts = findStudentRecords_(sheet, {
    event_id: sessionEventId,
    row_type: "event"
  });
  var existingConsents = findStudentRecords_(sheet, {
    event_id: consentEventId,
    row_type: "event"
  });
  if (existingStarts.length || existingConsents.length) {
    if (existingStarts.length !== 1 || existingConsents.length !== 1) {
      throw new ApiError_(
        "SESSION_LEDGER_CORRUPT",
        "Consent and session-start records are incomplete.",
        500
      );
    }
    if (
      !constantTimeEquals_(existingStarts[0].request_hash, bodyHash) ||
      !constantTimeEquals_(existingConsents[0].request_hash, bodyHash)
    ) {
      throw new ApiError_(
        "IDEMPOTENCY_CONFLICT",
        "Session start conflicts with an existing session.",
        409
      );
    }
    return {
      resourceId: sessionId,
      sessionId: sessionId,
      data: {
        acknowledged: true,
        sessionId: sessionId,
        stageAttempt: Number(existingStarts[0].attempt_number),
        duplicate: true
      }
    };
  }
  enforceRateLimit_(auth, now);
  var stageAttempt = deriveCurrentStageAttempt_(sheet);
  var common = {
    operation: "startSession",
    server_timestamp: now.toISOString(),
    course: auth.course,
    term: auth.term,
    student_key: auth.studentKey,
    session_id: sessionId,
    attempt_number: stageAttempt,
    stage: "stage_1_scope",
    advisor: "scope_advisor",
    protocol_role: "main_scope_advisor",
    schema_version: request.schemaVersion,
    request_id: request.requestId,
    request_hash: bodyHash,
    status: "APPENDED",
    first_received_at_server: now.toISOString(),
    updated_at_server: now.toISOString()
  };
  var consentRow = Object.assign({}, common, {
    row_key: hashKey_([auth.studentKey, consentEventId].join("|")),
    row_type: "event",
    record_id: consentEventId,
    event_id: consentEventId,
    event_type: "consent_recorded",
    reason_codes_json: canonicalJson_(["CONSENT_RECORDED"]),
    one_line_note:
      "consent_version=" + request.consentVersion +
      "; client_observed=" + request.clientObservedConsentAt
  });
  var sessionRow = Object.assign({}, common, {
    row_key: hashKey_([auth.studentKey, sessionEventId].join("|")),
    row_type: "event",
    record_id: sessionEventId,
    event_id: sessionEventId,
    event_type: "session_started",
    reason_codes_json: canonicalJson_(["IDENTITY_FIELDS_LOCKED"])
  });

  // One Sheets mutation preserves the required consent-before-session order.
  appendStudentRecords_(sheet, [consentRow, sessionRow]);
  upsertDashboard_(auth, {
    stage: "stage_1_scope",
    metrics: null,
    misconceptionFlags: []
  }, "", now);
  return {
    resourceId: sessionId,
    sessionId: sessionId,
    data: {
      acknowledged: true,
      sessionId: sessionId,
      stageAttempt: stageAttempt,
      duplicate: false
    }
  };
}

function handleLogEvent_(sheet, auth, event, now) {
  requireOpenSession_(sheet, event.sessionId);
  event.attempt = deriveStageAttemptForEvent_(sheet, event);
  if (
    event.eventType === "gate_result" &&
    isGate6ResultEvent_(event) &&
    event.gateOutcome === "OPEN"
  ) {
    assertGate6AuditComplete_(sheet, event.attempt);
  }
  var semanticEvent = {};
  Object.keys(event).forEach(function (key) {
    if (key !== "requestId") semanticEvent[key] = event[key];
  });
  var eventHash = hashKey_(canonicalJson_(semanticEvent));
  var existing = findStudentRecords_(sheet, {
    event_id: event.eventId,
    row_type: "event"
  });
  if (existing.length > 1) {
    throw new ApiError_("DUPLICATE_EVENT", "Duplicate historical events require review.", 500);
  }
  if (existing.length === 1) {
    if (!constantTimeEquals_(existing[0].request_hash, eventHash)) {
      throw new ApiError_(
        "IDEMPOTENCY_CONFLICT",
        "eventId was already used with different event data.",
        409
      );
    }
    var repaired = event.eventType === "daily_summary_written"
      ? upsertDailySummary_(sheet, auth, event, now)
      : null;
    return {
      resourceId: event.eventId,
      sessionId: event.sessionId,
      data: {
        acknowledged: true,
        eventId: event.eventId,
        duplicate: true,
        dailySummary: repaired
      }
    };
  }

  enforceRateLimit_(auth, now);
  appendStudentRecord_(sheet, eventToStudentRow_(auth, event, now, eventHash));
  var dailySummary = event.eventType === "daily_summary_written"
    ? upsertDailySummary_(sheet, auth, event, now)
    : null;
  upsertDashboard_(auth, event, "", now);
  return {
    resourceId: event.eventId,
    sessionId: event.sessionId,
    data: {
      acknowledged: true,
      eventId: event.eventId,
      duplicate: false,
      dailySummary: dailySummary
    }
  };
}

function eventToStudentRow_(auth, event, now, eventHash) {
  var metrics = event.metrics || {};
  return {
    row_key: hashKey_([auth.studentKey, event.eventId].join("|")),
    row_type: "event",
    operation: "logEvent",
    record_id: event.eventId,
    server_timestamp: now.toISOString(),
    course: auth.course,
    term: auth.term,
    student_key: auth.studentKey,
    session_id: event.sessionId,
    attempt_number: event.attempt,
    stage: event.stage,
    advisor: "scope_advisor",
    protocol_role: event.role,
    event_id: event.eventId,
    event_type: event.eventType,
    artifact_version_id: event.artifactVersionId,
    critique_depth: metrics.critiqueDepth,
    accepted_verbatim_count: metrics.acceptedVerbatim,
    challenged_or_modified_count: metrics.challengedOrModified,
    rejected_count: metrics.rejected,
    ai_reliance_index: metrics.aiRelianceIndex,
    substantive_iteration_count: metrics.substantiveIterations,
    gate_attempt_count: metrics.gateAttempts,
    misconception_flags_json: canonicalJson_(event.misconceptionFlags),
    reason_codes_json: canonicalJson_(event.reasonCodes),
    one_line_note: event.oneLineNote,
    digest_working_on: event.digest ? event.digest.workingOn : "",
    digest_ai_use: event.digest ? event.digest.aiUse : "",
    digest_decided_or_revised: event.digest ? event.digest.decidedOrRevised : "",
    digest_stuck_or_next: event.digest ? event.digest.stuckOrNext : "",
    // The frozen telemetry schema retains its legacy storage enum. Public gate
    // status remains canonical OPEN/CLOSED and is mapped only at this boundary.
    gate_outcome: gateOutcomeForStorage_(event.gateOutcome),
    dimension_scores_json: event.dimensionScores
      ? canonicalJson_(event.dimensionScores)
      : "",
    schema_version: event.schemaVersion,
    request_id: event.requestId,
    request_hash: eventHash,
    status: "APPENDED",
    first_received_at_server: now.toISOString(),
    updated_at_server: now.toISOString()
  };
}

function gateOutcomeForStorage_(value) {
  if (value === "OPEN") return "PASS";
  if (value === "CLOSED") return "REVISE";
  return value || "";
}

function handleCloseSession_(sheet, auth, request, now, bodyHash) {
  var eventId = deterministicId_(
    "evt",
    [auth.studentKey, request.sessionId, "session_closed", request.requestId].join("|")
  );
  var existing = findStudentRecords_(sheet, {
    event_id: eventId,
    row_type: "event"
  });
  if (existing.length) {
    if (!constantTimeEquals_(existing[0].request_hash, bodyHash)) {
      throw new ApiError_("IDEMPOTENCY_CONFLICT", "Close request conflicts.", 409);
    }
    return {
      resourceId: request.sessionId,
      sessionId: request.sessionId,
      data: {
        acknowledged: true,
        sessionId: request.sessionId,
        status: "CLOSED",
        duplicate: true
      }
    };
  }
  requireOpenSession_(sheet, request.sessionId);
  request.attempt = deriveStageAttemptForEvent_(sheet, {
    eventType: "session_closed",
    reasonCodes: []
  });
  enforceRateLimit_(auth, now);
  var event = {
    requestId: request.requestId,
    schemaVersion: request.schemaVersion,
    sessionId: request.sessionId,
    eventId: eventId,
    eventType: "session_closed",
    stage: request.stage,
    attempt: request.attempt,
    role: request.role,
    artifactVersionId: "",
    metrics: request.metrics,
    reasonCodes: request.reasonCodes,
    oneLineNote: request.oneLineNote,
    misconceptionFlags: request.misconceptionFlags,
    digest: request.digest,
    gateOutcome: request.gateOutcome,
    dimensionScores: null
  };
  appendStudentRecord_(sheet, eventToStudentRow_(auth, event, now, bodyHash));
  upsertDailySummary_(sheet, auth, event, now);
  upsertDashboard_(auth, event, "", now);
  return {
    resourceId: request.sessionId,
    sessionId: request.sessionId,
    data: {
      acknowledged: true,
      sessionId: request.sessionId,
      status: "CLOSED",
      duplicate: false
    }
  };
}

function requireOpenSession_(sheet, sessionId) {
  var rows = findStudentRecords_(sheet, { session_id: sessionId });
  var consents = rows.filter(function (row) {
    return row.event_type === "consent_recorded";
  });
  var starts = rows.filter(function (row) { return row.event_type === "session_started"; });
  if (consents.length !== 1 || starts.length !== 1) {
    throw new ApiError_("SESSION_NOT_FOUND", "Session was not found.", 404);
  }
  if (consents[0]._rowNumber >= starts[0]._rowNumber) {
    throw new ApiError_(
      "CONSENT_ORDER_INVALID",
      "Consent was not persisted before the session start.",
      500
    );
  }
  var closed = rows.some(function (row) { return row.event_type === "session_closed"; });
  if (closed) {
    throw new ApiError_("SESSION_CLOSED", "Session is already closed.", 409);
  }
  return starts[0];
}

function deriveCurrentStageAttempt_(sheet) {
  var maximum = readAllStudentRecords_(sheet).reduce(function (current, row) {
    var value = Number(row.attempt_number || 0);
    return isFinite(value) && value > current ? value : current;
  }, 0);
  return maximum || 1;
}

/**
 * A report request never creates a new stage attempt. After an issuance, a new
 * attempt begins only when a versioned revision has been recorded and the
 * student subsequently submits gate activity. The client cannot set this value.
 */
function deriveStageAttemptForEvent_(sheet, event) {
  var rows = readAllStudentRecords_(sheet);
  var current = deriveCurrentStageAttempt_(sheet);
  var eventType = typeof event === "string" ? event : event.eventType;
  var incomingGate = typeof event === "string"
    ? 0
    : Number(event.gateNumber || (
      canonicalGateIdentityFromCodes_(event.reasonCodes) || {}
    ).gateNumber || 0);
  var issuances = rows.filter(function (row) {
    return row.row_type === "report_issuance" &&
      Number(row.attempt_number) === current &&
      row.status === "ISSUED";
  });
  if (!issuances.length) return current;

  // A same-attempt regeneration must not erase a qualifying revision recorded
  // after the original issuance, so the boundary is the first issuance.
  var firstIssuanceRow = issuances.reduce(function (minimum, row) {
    return Math.min(minimum, row._rowNumber);
  }, Infinity);
  var qualifyingRevision = rows.some(function (row) {
    var identity = canonicalGateIdentityFromCodes_(reasonCodesFromRow_(row));
    return row._rowNumber > firstIssuanceRow &&
      row.event_type === "revision_submitted" &&
      Boolean(row.artifact_version_id) &&
      identity &&
      identity.gateNumber === incomingGate;
  });
  if (
    qualifyingRevision &&
    incomingGate >= 1 &&
    (eventType === "gate_attempt" || eventType === "gate_result")
  ) {
    return current + 1;
  }
  return current;
}

/**
 * Evidence entered after the latest prior issuance but before the gate event
 * that activates a new attempt is part of that new attempt's immutable cycle.
 * Rows remain append-only; this helper derives that boundary without rewriting
 * their historical attempt_number cells.
 */
function stageAttemptEvidenceRows_(rows, attempt, upperRowNumber) {
  var upper = upperRowNumber === undefined ? Infinity : upperRowNumber;
  if (attempt <= 1) {
    return rows.filter(function (row) {
      return Number(row.attempt_number) === attempt && row._rowNumber <= upper;
    });
  }
  var currentRows = rows.filter(function (row) {
    return Number(row.attempt_number) === attempt;
  });
  var firstCurrentRow = currentRows.reduce(function (minimum, row) {
    return Math.min(minimum, row._rowNumber);
  }, Infinity);
  var priorIssuanceBoundary = rows.reduce(function (minimum, row) {
    if (
      row.row_type === "report_issuance" &&
      row.status === "ISSUED" &&
      Number(row.attempt_number) === attempt - 1 &&
      row._rowNumber < firstCurrentRow
    ) {
      return Math.min(minimum, row._rowNumber);
    }
    return minimum;
  }, Infinity);
  return rows.filter(function (row) {
    if (row._rowNumber > upper) return false;
    if (Number(row.attempt_number) === attempt) return true;
    return isFinite(priorIssuanceBoundary) &&
      row._rowNumber > priorIssuanceBoundary &&
      row._rowNumber < firstCurrentRow;
  });
}

function reasonCodesFromRow_(row) {
  try {
    var parsed = JSON.parse(row.reason_codes_json || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    return [];
  }
}

function isGate6ResultEvent_(event) {
  var identity = canonicalGateIdentityFromCodes_(event.reasonCodes);
  return Boolean(
    identity &&
    identity.gateNumber === 6 &&
    { RESULT: true, OPEN: true, CLOSED: true }[identity.qualifier]
  );
}

function assertGate6AuditComplete_(sheet, attempt) {
  var evidenceRows = stageAttemptEvidenceRows_(
    readAllStudentRecords_(sheet),
    attempt
  );
  var audits = evidenceRows.filter(function (row) {
    var identity = canonicalGateIdentityFromCodes_(reasonCodesFromRow_(row));
    return row.event_type === "assumption_audit_completed" &&
      identity && identity.gateNumber === 6;
  });
  var latestAudit = audits.reduce(function (latest, row) {
    return !latest || row._rowNumber > latest._rowNumber ? row : latest;
  }, null);
  var revisions = evidenceRows.filter(function (row) {
    var identity = canonicalGateIdentityFromCodes_(reasonCodesFromRow_(row));
    return row.event_type === "revision_submitted" &&
      Boolean(row.artifact_version_id) &&
      identity && identity.gateNumber === 6 &&
      latestAudit && row._rowNumber > latestAudit._rowNumber;
  });
  if (!audits.length || !revisions.length) {
    throw new ApiError_(
      "GATE_6B_REQUIRED",
      "Gate 6 cannot open until the Gate 6B audit and versioned revision are complete.",
      409
    );
  }
}

function logControlledFailure_(error, now) {
  var code = error && error.name === "ApiError" ? error.code : "INTERNAL_ERROR";
  try {
    console.warn(JSON.stringify({
      event: "action_failure",
      code: code,
      serverTimestamp: now.toISOString()
    }));
  } catch (ignored) {}
}

function errorResponse_(error, now) {
  var known = error && error.name === "ApiError";
  var response = {
    ok: false,
    serverTimestamp: now.toISOString(),
    error: {
      code: known ? error.code : "INTERNAL_ERROR",
      message: known ? error.message : "Unexpected server error.",
      status: known ? error.status : 500
    }
  };
  if (known && error.details && error.details.retryAfterSeconds) {
    response.error.retryAfterSeconds = error.details.retryAfterSeconds;
  }
  return response;
}

function jsonOutput_(value) {
  return ContentService
    .createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}
