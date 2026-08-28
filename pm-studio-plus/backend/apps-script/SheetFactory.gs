/**
 * Workbook topology:
 *   Dashboard
 *   StudentIndex (hidden/restricted operational index)
 *   exactly one HMAC/hash-derived tab per allowlisted pseudonymous student key
 *
 * The caller already holds the ScriptLock before any function here mutates.
 */

var DASHBOARD_HEADERS_ = Object.freeze([
  "student_key",
  "current_stage",
  "last_active_date",
  "latest_summary",
  "critique_depth",
  "ai_reliance_index",
  "substantive_iteration_count",
  "gate_attempt_count",
  "misconception_flags",
  "gate_result",
  "report_status",
  "updated_at_server"
]);

var STUDENT_INDEX_HEADERS_ = Object.freeze([
  "student_key",
  "student_key_hash",
  "tab_id",
  "tab_name",
  "created_at_server",
  "status"
]);

var STUDENT_TAB_HEADERS_ = Object.freeze([
  "row_key",
  "row_type",
  "operation",
  "phase",
  "record_id",
  "server_timestamp",
  "course",
  "term",
  "student_key",
  "session_id",
  "attempt_number",
  "stage",
  "advisor",
  "protocol_role",
  "event_id",
  "event_type",
  "artifact_version_id",
  "critique_depth",
  "accepted_verbatim_count",
  "challenged_or_modified_count",
  "rejected_count",
  "ai_reliance_index",
  "substantive_iteration_count",
  "gate_attempt_count",
  "misconception_flags_json",
  "reason_codes_json",
  "one_line_note",
  "digest_working_on",
  "digest_ai_use",
  "digest_decided_or_revised",
  "digest_stuck_or_next",
  "gate_outcome",
  "dimension_scores_json",
  "report_id",
  "generation_number",
  "verification_hash",
  "schema_version",
  "request_id",
  "request_hash",
  "status",
  "receipt_json",
  "file_url",
  "pdf_byte_length",
  "first_received_at_server",
  "updated_at_server",
  "response_json"
]);

function getWorkbook_() {
  var id = PropertiesService.getScriptProperties().getProperty("WORKBOOK_ID");
  if (!id) {
    throw new ApiError_("SERVER_MISCONFIGURED", "WORKBOOK_ID is not configured.", 500);
  }
  try {
    return SpreadsheetApp.openById(id);
  } catch (error) {
    throw new ApiError_("SERVER_MISCONFIGURED", "Workbook cannot be opened.", 500);
  }
}

function ensureFixedSheets_() {
  var dashboard = ensureSheetWithHeaders_("Dashboard", DASHBOARD_HEADERS_);
  var index = ensureSheetWithHeaders_("StudentIndex", STUDENT_INDEX_HEADERS_);
  try {
    if (!index.isSheetHidden()) index.hideSheet();
  } catch (error) {
    // Some test doubles and restricted tenants do not expose hideSheet.
  }
  protectStudentIndex_(index);
  return { dashboard: dashboard, index: index };
}

function protectStudentIndex_(sheet) {
  // Keep lightweight test doubles usable; the production Sheets API always
  // exposes sheet protection.
  if (
    typeof sheet.getProtections !== "function" ||
    typeof sheet.protect !== "function"
  ) return;
  var protections = sheet.getProtections(SpreadsheetApp.ProtectionType.SHEET);
  if (protections.length > 1) {
    throw new ApiError_(
      "SHEET_PROTECTION_MISMATCH",
      "StudentIndex has conflicting sheet protections.",
      500
    );
  }
  var protection = protections.length ? protections[0] : sheet.protect();
  protection.setDescription("Restricted V550 StudentIndex");
  protection.setWarningOnly(false);
  if (
    typeof protection.canDomainEdit === "function" &&
    protection.canDomainEdit()
  ) {
    protection.setDomainEdit(false);
  }
  if (!protections.length && typeof protection.addEditor === "function") {
    var effectiveUser = Session.getEffectiveUser();
    protection.addEditor(effectiveUser);
    if (typeof protection.getEditors === "function") {
      var effectiveEmail = effectiveUser.getEmail();
      var extras = protection.getEditors().filter(function (editor) {
        return editor.getEmail() !== effectiveEmail;
      });
      if (extras.length && typeof protection.removeEditors === "function") {
        protection.removeEditors(extras);
      }
    }
  }
}

function ensureSheetWithHeaders_(name, headers) {
  var workbook = getWorkbook_();
  var sheet = workbook.getSheetByName(name);
  if (!sheet) sheet = workbook.insertSheet(name);
  verifyOrInitializeHeaders_(sheet, headers, name);
  return sheet;
}

function verifyOrInitializeHeaders_(sheet, headers, label) {
  var width = Math.max(sheet.getLastColumn(), headers.length);
  var existing = sheet.getRange(1, 1, 1, width).getDisplayValues()[0];
  var isEmpty = existing.every(function (value) { return value === ""; });
  if (isEmpty) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.setFrozenRows(1);
    return;
  }
  var exact =
    headers.every(function (header, index) { return existing[index] === header; }) &&
    existing.slice(headers.length).every(function (value) { return value === ""; });
  if (!exact) {
    throw new ApiError_(
      "SHEET_SCHEMA_MISMATCH",
      label + " does not match the locked schema.",
      500
    );
  }
}

function getOrCreateStudentTab_(auth, now) {
  var fixed = ensureFixedSheets_();
  var matches = findRowsByColumn_(
    fixed.index,
    STUDENT_INDEX_HEADERS_,
    "student_key",
    auth.studentKey
  );
  if (matches.length > 1) {
    throw new ApiError_(
      "DUPLICATE_STUDENT_TAB",
      "Duplicate student-tab mappings require instructor review.",
      500
    );
  }
  if (matches.length === 1) {
    return resolveIndexedStudentTab_(matches[0], auth);
  }

  var name = "S_" + auth.studentKeyHash.substring(0, 20);
  var workbook = getWorkbook_();
  if (workbook.getSheetByName(name)) {
    throw new ApiError_(
      "ORPHAN_STUDENT_TAB",
      "An unindexed historical student tab requires instructor review.",
      500
    );
  }
  var sheet = workbook.insertSheet(name);
  verifyOrInitializeHeaders_(sheet, STUDENT_TAB_HEADERS_, name);
  appendRowByHeaders_(fixed.index, STUDENT_INDEX_HEADERS_, {
    student_key: auth.studentKey,
    student_key_hash: auth.studentKeyHash,
    tab_id: sheet.getSheetId(),
    tab_name: name,
    created_at_server: now.toISOString(),
    status: "ACTIVE"
  });
  return sheet;
}

function getExistingStudentTab_(auth) {
  var fixed = ensureFixedSheets_();
  var matches = findRowsByColumn_(
    fixed.index,
    STUDENT_INDEX_HEADERS_,
    "student_key",
    auth.studentKey
  );
  if (matches.length > 1) {
    throw new ApiError_(
      "DUPLICATE_STUDENT_TAB",
      "Duplicate student-tab mappings require instructor review.",
      500
    );
  }
  if (!matches.length) {
    throw new ApiError_("SESSION_NOT_FOUND", "No session exists for this student key.", 404);
  }
  return resolveIndexedStudentTab_(matches[0], auth);
}

function resolveIndexedStudentTab_(indexRecord, auth) {
  if (
    indexRecord.student_key_hash !== auth.studentKeyHash ||
    indexRecord.status !== "ACTIVE"
  ) {
    throw new ApiError_("STUDENT_TAB_MISMATCH", "Student-tab mapping is invalid.", 500);
  }
  var targetId = Number(indexRecord.tab_id);
  var sheets = getWorkbook_().getSheets().filter(function (sheet) {
    return sheet.getSheetId() === targetId;
  });
  if (sheets.length !== 1 || sheets[0].getName() !== indexRecord.tab_name) {
    throw new ApiError_("STUDENT_TAB_MISMATCH", "Student-tab mapping is invalid.", 500);
  }
  verifyOrInitializeHeaders_(
    sheets[0],
    STUDENT_TAB_HEADERS_,
    indexRecord.tab_name
  );
  return sheets[0];
}

function appendStudentRecord_(sheet, record) {
  return appendRowByHeaders_(sheet, STUDENT_TAB_HEADERS_, record);
}

/**
 * Append a small ordered batch with one Sheets write. startSession uses this so
 * consent_recorded is durably ordered before session_started without exposing a
 * half-created session between separate append calls.
 */
function appendStudentRecords_(sheet, records) {
  if (!Array.isArray(records) || !records.length) {
    throw new ApiError_("SERVER_MISCONFIGURED", "Record batch is empty.", 500);
  }
  var values = records.map(function (record) {
    return STUDENT_TAB_HEADERS_.map(function (header) {
      return safeCellValue_(record[header]);
    });
  });
  var firstRow = sheet.getLastRow() + 1;
  sheet
    .getRange(firstRow, 1, values.length, STUDENT_TAB_HEADERS_.length)
    .setValues(values);
  return firstRow;
}

function readAllStudentRecords_(sheet) {
  if (sheet.getLastRow() < 2) return [];
  var rows = sheet
    .getRange(2, 1, sheet.getLastRow() - 1, STUDENT_TAB_HEADERS_.length)
    .getDisplayValues();
  return rows.map(function (values, offset) {
    var record = { _rowNumber: offset + 2 };
    STUDENT_TAB_HEADERS_.forEach(function (header, index) {
      record[header] = values[index];
    });
    return record;
  });
}

function updateStudentRecord_(sheet, rowNumber, changes) {
  Object.keys(changes).forEach(function (column) {
    var index = STUDENT_TAB_HEADERS_.indexOf(column);
    if (index < 0) {
      throw new ApiError_("SERVER_MISCONFIGURED", "Unknown student column.", 500);
    }
    sheet.getRange(rowNumber, index + 1).setValue(safeCellValue_(changes[column]));
  });
}

function findStudentRecords_(sheet, criteria) {
  var candidateColumn = Object.keys(criteria)[0];
  var candidates = findRowsByColumn_(
    sheet,
    STUDENT_TAB_HEADERS_,
    candidateColumn,
    criteria[candidateColumn]
  );
  return candidates.filter(function (record) {
    return Object.keys(criteria).every(function (key) {
      return String(record[key]) === String(criteria[key]);
    });
  });
}

function appendRowByHeaders_(sheet, headers, record) {
  var values = headers.map(function (header) {
    return safeCellValue_(record[header]);
  });
  var rowNumber = sheet.getLastRow() + 1;
  sheet.getRange(rowNumber, 1, 1, values.length).setValues([values]);
  return rowNumber;
}

function findRowsByColumn_(sheet, headers, column, exactValue) {
  var index = headers.indexOf(column);
  if (index < 0) {
    throw new ApiError_("SERVER_MISCONFIGURED", "Unknown sheet column.", 500);
  }
  if (sheet.getLastRow() < 2) return [];
  var finder = sheet
    .getRange(2, index + 1, sheet.getLastRow() - 1, 1)
    .createTextFinder(String(exactValue))
    .matchEntireCell(true)
    .useRegularExpression(false);
  var matches = typeof finder.findAll === "function"
    ? finder.findAll()
    : (function () {
        var one = finder.findNext();
        return one ? [one] : [];
      })();
  return matches.map(function (range) {
    return readRowByHeaders_(sheet, headers, range.getRow());
  });
}

function readRowByHeaders_(sheet, headers, rowNumber) {
  var values = sheet
    .getRange(rowNumber, 1, 1, headers.length)
    .getDisplayValues()[0];
  var record = { _rowNumber: rowNumber };
  headers.forEach(function (header, index) { record[header] = values[index]; });
  return record;
}

function findRequestReceipt_(sheet, operation, phase, requestId) {
  var rows = findStudentRecords_(sheet, {
    request_id: requestId,
    row_type: "request_receipt"
  });
  var matching = rows.filter(function (row) {
    // requestId is unique per public operation. `phase` is internal-only and
    // cannot be used to bypass an idempotency conflict by toggling regenerate.
    return row.operation === operation;
  });
  if (matching.length > 1) {
    throw new ApiError_("REQUEST_LEDGER_CORRUPT", "Duplicate request receipts found.", 500);
  }
  return matching[0] || null;
}

function replayRequest_(record, expectedHash) {
  if (!constantTimeEquals_(record.request_hash, expectedHash)) {
    throw new ApiError_(
      "IDEMPOTENCY_CONFLICT",
      "requestId was already used with different data.",
      409
    );
  }
  try {
    var stored = JSON.parse(record.response_json);
    if (stored && stored.private_response_ref) {
      var encoded = PropertiesService
        .getScriptProperties()
        .getProperty(stored.private_response_ref);
      if (!encoded) {
        throw new Error("private response missing");
      }
      return JSON.parse(encoded);
    }
    return stored;
  } catch (error) {
    throw new ApiError_("REQUEST_LEDGER_CORRUPT", "Stored response is invalid.", 500);
  }
}

function recordRequestReceipt_(sheet, auth, operation, phase, requestId, bodyHash, result, response, now) {
  var storedResponse = response;
  if (operation === "issueReport") {
    // Download capabilities never enter the workbook or telemetry rows.
    var responseRef = "REPORT_RESPONSE_" + hashKey_(
      [auth.studentKeyHash, phase || "", requestId].join("|")
    ).substring(0, 40);
    PropertiesService
      .getScriptProperties()
      .setProperty(responseRef, JSON.stringify(response));
    storedResponse = { private_response_ref: responseRef };
  }
  appendStudentRecord_(sheet, {
    row_key: hashKey_(
      [auth.studentKey, "request_receipt", operation, phase || "", requestId].join("|")
    ),
    row_type: "request_receipt",
    operation: operation,
    phase: phase || "",
    record_id: deterministicId_("req", [auth.studentKey, operation, phase || "", requestId].join("|")),
    server_timestamp: now.toISOString(),
    course: auth.course,
    term: auth.term,
    student_key: auth.studentKey,
    session_id: result.sessionId || "",
    request_id: requestId,
    request_hash: bodyHash,
    status: "ACKNOWLEDGED",
    response_json: canonicalJson_(storedResponse),
    schema_version: result.schemaVersion || "1.0.0"
  });
}
