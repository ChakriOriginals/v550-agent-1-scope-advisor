/**
 * Instructor-only materialized views.
 *
 * Raw source events remain append-only. The sole student-row mutation is the
 * stable daily_summary projection. Dashboard rows are also materialized views,
 * never public Action data.
 */

function upsertDailySummary_(sheet, auth, event, now) {
  var courseDate = Utilities.formatDate(
    now,
    Session.getScriptTimeZone(),
    "yyyy-MM-dd"
  );
  var stableKey = hashKey_(
    [auth.studentKey, courseDate, event.stage].join("|")
  );
  var rows = findStudentRecords_(sheet, {
    row_key: stableKey,
    row_type: "daily_summary"
  });
  if (rows.length > 1) {
    throw new ApiError_(
      "DUPLICATE_DAILY_SUMMARY",
      "Duplicate daily summaries require instructor review.",
      500
    );
  }

  var values = {
    session_id: event.sessionId,
    attempt_number: event.attempt,
    protocol_role: event.role,
    event_id: event.eventId,
    reason_codes_json: canonicalJson_(event.reasonCodes),
    one_line_note: event.oneLineNote,
    digest_working_on: event.digest.workingOn,
    digest_ai_use: event.digest.aiUse,
    digest_decided_or_revised: event.digest.decidedOrRevised,
    digest_stuck_or_next: event.digest.stuckOrNext || "",
    updated_at_server: now.toISOString()
  };
  if (rows.length === 1) {
    updateStudentRecord_(sheet, rows[0]._rowNumber, values);
    return { mode: "updated", courseDate: courseDate };
  }

  values.row_key = stableKey;
  values.row_type = "daily_summary";
  values.operation = "logEvent";
  values.record_id = deterministicId_("sum", stableKey);
  values.server_timestamp = now.toISOString();
  values.course = auth.course;
  values.term = auth.term;
  values.student_key = auth.studentKey;
  values.stage = event.stage;
  values.advisor = "scope_advisor";
  values.event_type = "daily_summary_written";
  values.schema_version = event.schemaVersion;
  values.status = "MATERIALIZED";
  values.first_received_at_server = now.toISOString();
  appendStudentRecord_(sheet, values);
  return { mode: "created", courseDate: courseDate };
}

function upsertDashboard_(auth, event, reportStatus, now) {
  var sheet = ensureFixedSheets_().dashboard;
  var rows = findRowsByColumn_(
    sheet,
    DASHBOARD_HEADERS_,
    "student_key",
    auth.studentKey
  );
  if (rows.length > 1) {
    throw new ApiError_("DASHBOARD_CORRUPT", "Duplicate dashboard rows found.", 500);
  }
  var metrics = event && event.metrics ? event.metrics : {};
  var digest = event && event.digest ? event.digest : null;
  var latestSummary = digest
    ? [
        digest.workingOn,
        digest.aiUse,
        digest.decidedOrRevised,
        digest.stuckOrNext
      ].filter(Boolean).join(" | ")
    : "";
  var values = {
    student_key: auth.studentKey,
    current_stage: event ? event.stage : "",
    last_active_date: Utilities.formatDate(now, Session.getScriptTimeZone(), "yyyy-MM-dd"),
    latest_summary: latestSummary,
    critique_depth: metrics.critiqueDepth,
    ai_reliance_index: metrics.aiRelianceIndex,
    substantive_iteration_count: metrics.substantiveIterations,
    gate_attempt_count: metrics.gateAttempts,
    misconception_flags: event ? canonicalJson_(event.misconceptionFlags || []) : "",
    gate_result: event ? event.gateOutcome || "" : "",
    report_status: reportStatus || "",
    updated_at_server: now.toISOString()
  };
  if (!rows.length) {
    appendRowByHeaders_(sheet, DASHBOARD_HEADERS_, values);
    return;
  }
  Object.keys(values).forEach(function (column) {
    if (
      values[column] !== "" &&
      values[column] !== null &&
      values[column] !== undefined
    ) {
      var index = DASHBOARD_HEADERS_.indexOf(column);
      sheet.getRange(rows[0]._rowNumber, index + 1).setValue(safeCellValue_(values[column]));
    }
  });
}
