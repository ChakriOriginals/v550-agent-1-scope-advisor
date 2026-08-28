/**
 * Fail-closed security and wire validation.
 *
 * Required Script Properties (the only deployment secrets/configuration read):
 *   CLASS_DEPLOYMENT_TOKEN
 *   ACTIVE_STUDENT_KEYS_JSON
 *   WORKBOOK_ID
 *   REPORT_DRIVE_FOLDER_ID
 *   REPORT_HMAC_KEYS_JSON
 *   REPORT_HMAC_ACTIVE_KEY_VERSION
 *   REPORT_TEMPLATE_VERSION
 *   REPORT_SCHEMA_VERSION
 *   INSTRUCTOR_VERIFIER_TOKEN
 *
 * REPORT_HMAC_SECRET remains a development-only compatibility fallback. New
 * deployments use the versioned key map so historical report signatures remain
 * verifiable after rotation.
 *
 * ACTIVE_STUDENT_KEYS_JSON is an object keyed by the issued pseudonymous key:
 * {"V550-...":{"active":true,"course":"V550","term":"Fall 2026"}}
 * Boolean `true` entries remain supported for synthetic tenant tests.
 */

var PUBLIC_OPERATIONS_ = Object.freeze({
  startSession: true,
  logEvent: true,
  closeSession: true,
  issueReport: true
});

var EVENT_TYPES_ = Object.freeze({
  session_started: true,
  consent_recorded: true,
  role_framing_submitted: true,
  requirements_submitted: true,
  expectations_submitted: true,
  moscow_submitted: true,
  goals_objectives_submitted: true,
  smart_check_completed: true,
  deliverables_submitted: true,
  project_statement_submitted: true,
  scope_boundaries_submitted: true,
  scope_action_plan_submitted: true,
  wbs_submitted: true,
  assumption_audit_completed: true,
  draft_submitted: true,
  critique_given: true,
  critique_answered: true,
  revision_submitted: true,
  justification_submitted: true,
  scope_creep_flagged: true,
  misconception_flagged: true,
  gate_attempt: true,
  gate_result: true,
  report_issued: true,
  report_regenerated: true,
  session_closed: true,
  daily_summary_written: true
});

var STAGES_ = Object.freeze({
  stage_1_scope: true
});

var PROTOCOL_ROLES_ = Object.freeze({
  main_scope_advisor: true,
  auto_grader: true,
  insights: true,
  summarizer: true,
  wbs_decomposer_action_plan: true,
  assumption_auditor: true,
  scope_review_board: true
});

var EVENT_ROLES_ = Object.freeze({
  role_framing_submitted: Object.freeze({ main_scope_advisor: true }),
  requirements_submitted: Object.freeze({ main_scope_advisor: true }),
  expectations_submitted: Object.freeze({ main_scope_advisor: true }),
  moscow_submitted: Object.freeze({ main_scope_advisor: true }),
  goals_objectives_submitted: Object.freeze({ main_scope_advisor: true }),
  smart_check_completed: Object.freeze({ auto_grader: true }),
  deliverables_submitted: Object.freeze({
    main_scope_advisor: true,
    wbs_decomposer_action_plan: true
  }),
  project_statement_submitted: Object.freeze({ main_scope_advisor: true }),
  scope_boundaries_submitted: Object.freeze({
    main_scope_advisor: true,
    assumption_auditor: true
  }),
  scope_action_plan_submitted: Object.freeze({
    wbs_decomposer_action_plan: true
  }),
  wbs_submitted: Object.freeze({ wbs_decomposer_action_plan: true }),
  assumption_audit_completed: Object.freeze({ assumption_auditor: true }),
  revision_submitted: Object.freeze({
    main_scope_advisor: true,
    wbs_decomposer_action_plan: true,
    assumption_auditor: true
  }),
  misconception_flagged: Object.freeze({
    insights: true,
    auto_grader: true,
    scope_review_board: true
  }),
  gate_attempt: Object.freeze({ scope_review_board: true }),
  gate_result: Object.freeze({ scope_review_board: true }),
  scope_creep_flagged: Object.freeze({ assumption_auditor: true }),
  daily_summary_written: Object.freeze({ summarizer: true })
});

var MISCONCEPTION_FLAGS_ = Object.freeze({
  requirements_expectations_conflated: true,
  goal_objective_conflated: true,
  solution_chosen_before_requirements: true,
  activity_mislabeled_as_deliverable: true,
  success_criterion_not_measurable: true,
  missing_exclusion: true,
  assumption_presented_as_fact: true,
  ownerless_action: true,
  vague_wbs_work_package: true,
  wbs_overlap_or_gap: true,
  scope_creep_unacknowledged: true,
  stage2_scheduling_pulled_into_stage1: true
});

var DIMENSION_KEYS_ = Object.freeze([
  "projectStatement",
  "objectivesAndSuccessCriteria",
  "scopeOfWork",
  "deliverables",
  "scopeActionPlan",
  "constraintsAndUncertainties",
  "exclusions",
  "doYouDeliver"
]);

var PER_KEY_REQUESTS_PER_MINUTE_ = 30;

function ApiError_(code, message, status, details) {
  this.name = "ApiError";
  this.code = code;
  this.message = message;
  this.status = status || 400;
  this.details = details || null;
  this.stack = new Error(message).stack;
}
ApiError_.prototype = Object.create(Error.prototype);
ApiError_.prototype.constructor = ApiError_;

function assertPlainObject_(value, label) {
  if (!value || Object.prototype.toString.call(value) !== "[object Object]") {
    throw new ApiError_("INVALID_REQUEST", label + " must be an object.", 400);
  }
}

function assertOnlyKeys_(object, allowed, label) {
  assertPlainObject_(object, label);
  Object.keys(object).forEach(function (key) {
    if (!allowed[key]) {
      throw new ApiError_(
        "UNEXPECTED_FIELD",
        label + " contains an unsupported field: " + key,
        400
      );
    }
  });
}

function requireString_(value, label, minimum, maximum, pattern) {
  if (typeof value !== "string") {
    throw new ApiError_("INVALID_FIELD", label + " must be a string.", 400);
  }
  if (value.length < minimum || value.length > maximum) {
    throw new ApiError_(
      "INVALID_FIELD",
      label + " must contain " + minimum + " to " + maximum + " characters.",
      400
    );
  }
  if (pattern && !pattern.test(value)) {
    throw new ApiError_("INVALID_FIELD", label + " has an invalid format.", 400);
  }
  return value;
}

function requireInteger_(value, label, minimum, maximum) {
  if (
    typeof value !== "number" ||
    !isFinite(value) ||
    Math.floor(value) !== value ||
    value < minimum ||
    value > maximum
  ) {
    throw new ApiError_(
      "INVALID_FIELD",
      label + " must be an integer from " + minimum + " to " + maximum + ".",
      400
    );
  }
  return value;
}

function requireNumberOrNull_(value, label, minimum, maximum) {
  if (value === null) return null;
  if (
    typeof value !== "number" ||
    !isFinite(value) ||
    value < minimum ||
    value > maximum
  ) {
    throw new ApiError_(
      "INVALID_FIELD",
      label + " must be null or a number from " + minimum + " to " + maximum + ".",
      400
    );
  }
  return value;
}

function validateOpaqueId_(value, label) {
  return requireString_(
    value,
    label,
    8,
    128,
    /^[A-Za-z0-9][A-Za-z0-9._:-]*$/
  );
}

function validateStudentKey_(value) {
  return requireString_(
    value,
    "studentKey",
    12,
    64,
    /^[A-Za-z0-9][A-Za-z0-9_-]*$/
  );
}

function validateSchemaVersion_(value) {
  return requireString_(
    value,
    "schemaVersion",
    5,
    32,
    /^[0-9]+\.[0-9]+\.[0-9]+$/
  );
}

function validateConsentVersion_(value) {
  return requireString_(
    value,
    "consent.version",
    3,
    32,
    /^[A-Za-z0-9][A-Za-z0-9._-]*$/
  );
}

function validateClientObservedTimestamp_(value) {
  var text = requireString_(
    value,
    "consent.clientObservedAt",
    20,
    40,
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/
  );
  var parsed = new Date(text);
  if (!isFinite(parsed.getTime())) {
    throw new ApiError_(
      "INVALID_FIELD",
      "consent.clientObservedAt must be a valid RFC 3339 timestamp.",
      400
    );
  }
  return text;
}

function validateStage_(value) {
  requireString_(value, "stage", 2, 64, /^[a-z0-9_]+$/);
  if (!STAGES_[value]) {
    throw new ApiError_("INVALID_STAGE", "stage is not allowlisted.", 400);
  }
  return value;
}

function validateProtocolRole_(value) {
  requireString_(value, "role", 2, 64, /^[a-z0-9_]+$/);
  if (!PROTOCOL_ROLES_[value]) {
    throw new ApiError_("INVALID_ROLE", "role is not allowlisted.", 400);
  }
  return value;
}

function validateEventType_(value) {
  requireString_(value, "eventType", 2, 64, /^[a-z0-9_]+$/);
  if (!EVENT_TYPES_[value]) {
    throw new ApiError_("INVALID_EVENT_TYPE", "eventType is not allowlisted.", 400);
  }
  return value;
}

function validateEventRole_(eventType, role) {
  var allowed = EVENT_ROLES_[eventType];
  if (allowed && !allowed[role]) {
    throw new ApiError_(
      "ROLE_EVENT_MISMATCH",
      "The selected protocol role cannot emit this event type.",
      400
    );
  }
  return role;
}

function authorizeRequest_(payload, operation) {
  if (!PUBLIC_OPERATIONS_[operation]) {
    throw new ApiError_("OPERATION_NOT_ALLOWED", "Operation is not allowed.", 404);
  }
  assertPlainObject_(payload, "request body");
  var suppliedToken = requireString_(
    payload.classToken,
    "classToken",
    16,
    512
  );
  var studentKey = validateStudentKey_(payload.studentKey);
  var properties = PropertiesService.getScriptProperties();
  var expectedToken = properties.getProperty("CLASS_DEPLOYMENT_TOKEN");
  if (!expectedToken || expectedToken.length < 16) {
    throw new ApiError_(
      "SERVER_MISCONFIGURED",
      "CLASS_DEPLOYMENT_TOKEN is not configured.",
      500
    );
  }
  if (!constantTimeEquals_(suppliedToken, expectedToken)) {
    throw new ApiError_("UNAUTHORIZED", "Invalid class deployment token.", 401);
  }

  var rawAllowlist = properties.getProperty("ACTIVE_STUDENT_KEYS_JSON");
  var allowlist;
  try {
    allowlist = JSON.parse(rawAllowlist || "");
  } catch (error) {
    throw new ApiError_(
      "SERVER_MISCONFIGURED",
      "ACTIVE_STUDENT_KEYS_JSON is invalid.",
      500
    );
  }
  assertPlainObject_(allowlist, "ACTIVE_STUDENT_KEYS_JSON");

  var matchedKey = null;
  Object.keys(allowlist).some(function (candidate) {
    if (constantTimeEquals_(candidate, studentKey)) {
      matchedKey = candidate;
      return true;
    }
    return false;
  });
  if (!matchedKey) {
    throw new ApiError_("STUDENT_KEY_NOT_ALLOWED", "Student key is not active.", 403);
  }
  var entry = allowlist[matchedKey];
  var active = entry === true || (
    entry &&
    Object.prototype.toString.call(entry) === "[object Object]" &&
    entry.active === true
  );
  if (!active) {
    throw new ApiError_("STUDENT_KEY_NOT_ALLOWED", "Student key is not active.", 403);
  }

  var course = entry && typeof entry === "object" && entry.course
    ? requireString_(entry.course, "allowlist course", 2, 20, /^[A-Za-z0-9_-]+$/)
    : "V550";
  var term = entry && typeof entry === "object" && entry.term
    ? requireString_(entry.term, "allowlist term", 2, 60, /^[A-Za-z0-9 ._-]+$/)
    : "SET_BEFORE_DEPLOYMENT";

  return {
    studentKey: matchedKey,
    studentKeyHash: hashKey_(matchedKey),
    course: course,
    term: term
  };
}

function validateMetrics_(value) {
  if (value === undefined) return null;
  assertOnlyKeys_(
    value,
    {
      critiqueDepth: true,
      acceptedVerbatim: true,
      challengedOrModified: true,
      rejected: true,
      aiRelianceStatus: true,
      aiRelianceIndex: true,
      substantiveIterations: true,
      gateAttempts: true
    },
    "metrics"
  );
  var result = {};
  if (value.critiqueDepth !== undefined) {
    result.critiqueDepth = requireInteger_(value.critiqueDepth, "metrics.critiqueDepth", 0, 3);
  }
  ["acceptedVerbatim", "challengedOrModified", "rejected", "substantiveIterations"].forEach(
    function (key) {
      if (value[key] !== undefined) {
        result[key] = requireInteger_(value[key], "metrics." + key, 0, 100000);
      }
    }
  );
  if (value.gateAttempts !== undefined) {
    result.gateAttempts = requireInteger_(value.gateAttempts, "metrics.gateAttempts", 0, 999);
  }
  if (value.aiRelianceStatus !== undefined) {
    if (value.aiRelianceStatus !== "calculated" && value.aiRelianceStatus !== "not_applicable") {
      throw new ApiError_("INVALID_FIELD", "metrics.aiRelianceStatus is invalid.", 400);
    }
    result.aiRelianceStatus = value.aiRelianceStatus;
  }
  if (value.aiRelianceIndex !== undefined) {
    result.aiRelianceIndex = requireNumberOrNull_(
      value.aiRelianceIndex,
      "metrics.aiRelianceIndex",
      0,
      100
    );
  }
  var relianceFields = [
    "acceptedVerbatim",
    "challengedOrModified",
    "rejected",
    "aiRelianceStatus",
    "aiRelianceIndex"
  ];
  var hasReliance = relianceFields.some(function (key) {
    return Object.prototype.hasOwnProperty.call(value, key);
  });
  if (hasReliance) {
    var missing = relianceFields.filter(function (key) {
      return !Object.prototype.hasOwnProperty.call(value, key);
    });
    if (missing.length) {
      throw new ApiError_(
        "INVALID_FIELD",
        "Reliance metrics require all disposition counts, status, and index.",
        400
      );
    }
    var denominator =
      result.acceptedVerbatim +
      result.challengedOrModified +
      result.rejected;
    if (denominator === 0) {
      if (
        result.aiRelianceStatus !== "not_applicable" ||
        result.aiRelianceIndex !== null
      ) {
        throw new ApiError_(
          "INVALID_FIELD",
          "Zero disposition count requires not_applicable and a null index.",
          400
        );
      }
    } else {
      var expected = Math.round(
        result.acceptedVerbatim / denominator * 10000
      ) / 100;
      if (
        result.aiRelianceStatus !== "calculated" ||
        result.aiRelianceIndex === null ||
        Math.abs(result.aiRelianceIndex - expected) > 0.01
      ) {
        throw new ApiError_(
          "INVALID_FIELD",
          "AI-reliance index does not match the disposition counts.",
          400
        );
      }
    }
  }
  return result;
}

function validateStringEnumArray_(value, label, allowed, maximumItems, pattern) {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > maximumItems) {
    throw new ApiError_("INVALID_FIELD", label + " must be a bounded array.", 400);
  }
  var seen = {};
  return value.map(function (item) {
    requireString_(item, label + " item", 1, 80, pattern || /^[A-Za-z0-9_:-]+$/);
    if (allowed && !allowed[item]) {
      throw new ApiError_("INVALID_FIELD", label + " contains an unsupported value.", 400);
    }
    if (seen[item]) {
      throw new ApiError_("INVALID_FIELD", label + " must contain unique values.", 400);
    }
    seen[item] = true;
    return item;
  });
}

function validateDimensionScores_(value) {
  if (value === undefined) return null;
  var allowed = {};
  DIMENSION_KEYS_.forEach(function (key) { allowed[key] = true; });
  assertOnlyKeys_(value, allowed, "dimensionScores");
  var result = {};
  DIMENSION_KEYS_.forEach(function (key) {
    if (value[key] === undefined) {
      throw new ApiError_(
        "INVALID_FIELD",
        "dimensionScores must contain all eight advisory dimensions.",
        400
      );
    }
    result[key] = requireInteger_(value[key], "dimensionScores." + key, 1, 5);
  });
  return result;
}

function validateDigest_(value) {
  if (value === undefined) return null;
  assertOnlyKeys_(
    value,
    {
      workingOn: true,
      aiUse: true,
      decidedOrRevised: true,
      stuckOrNext: true
    },
    "digest"
  );
  var digest = {
    workingOn: validateSanitizedLine_(value.workingOn, "digest.workingOn", "Working on: "),
    aiUse: validateSanitizedLine_(value.aiUse, "digest.aiUse", "AI use: "),
    decidedOrRevised: validateSanitizedLine_(
      value.decidedOrRevised,
      "digest.decidedOrRevised",
      "Decided/revised: "
    ),
    stuckOrNext: null
  };
  if (value.stuckOrNext !== undefined && value.stuckOrNext !== null) {
    digest.stuckOrNext = validateSanitizedLine_(
      value.stuckOrNext,
      "digest.stuckOrNext",
      "Stuck/next: "
    );
  }
  return digest;
}

function validateSanitizedLine_(value, label, prefix) {
  var text = requireString_(value, label, prefix.length + 1, 240);
  if (text.indexOf(prefix) !== 0 || /[\r\n]/.test(text)) {
    throw new ApiError_("INVALID_FIELD", label + " has an invalid summary format.", 400);
  }
  rejectLikelyPii_(text, label);
  return neutralizeFormula_(text);
}

function validateOneLineNote_(value) {
  if (value === undefined || value === null || value === "") return "";
  var text = requireString_(value, "oneLineNote", 1, 240);
  if (/[\r\n]/.test(text)) {
    throw new ApiError_("INVALID_FIELD", "oneLineNote must be one line.", 400);
  }
  rejectLikelyPii_(text, "oneLineNote");
  return neutralizeFormula_(text);
}

function rejectLikelyPii_(text, label) {
  var directIdentifierPatterns = [
    /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/,
    /(?:\+?1[-. ]?)?\(?[0-9]{3}\)?[-. ][0-9]{3}[-. ][0-9]{4}/,
    /\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b/,
    /(?:https?:\/\/|www\.)/i,
    /\b[0-9]{1,6}\s+[A-Za-z0-9.' -]{2,40}\s+(?:street|st|road|rd|avenue|ave|boulevard|blvd|lane|ln|drive|dr|court|ct|way|parkway|pkwy)\b/i
  ];
  if (directIdentifierPatterns.some(function (pattern) { return pattern.test(text); })) {
    throw new ApiError_(
      "PII_PROHIBITED",
      label + " appears to contain personal or contact information.",
      400
    );
  }
  var sensitiveValuePattern = /\b(?:medical|health condition|accommodation details|financial account|immigration|disciplinary|authentication credential|password|social security|overwhelmed|frustrated|tearful|ready to cry|crying|emotional distress)\b/i;
  if (sensitiveValuePattern.test(text)) {
    throw new ApiError_(
      "SENSITIVE_CONTENT",
      label + " appears to contain prohibited sensitive information.",
      400
    );
  }
}

function assertNoProhibitedTelemetryFields_(value, path, depth) {
  path = path || "request";
  depth = depth || 0;
  if (depth > 6) {
    throw new ApiError_("PAYLOAD_TOO_DEEP", "Request nesting is too deep.", 400);
  }
  if (value === null || value === undefined) return;
  if (Array.isArray(value)) {
    value.forEach(function (item, index) {
      assertNoProhibitedTelemetryFields_(item, path + "[" + index + "]", depth + 1);
    });
    return;
  }
  if (Object.prototype.toString.call(value) !== "[object Object]") return;

  var prohibited = {
    name: true,
    firstname: true,
    lastname: true,
    fullname: true,
    email: true,
    phone: true,
    address: true,
    transcript: true,
    transcripttext: true,
    chat: true,
    draft: true,
    fulldraft: true,
    upload: true,
    evidenceexcerpt: true,
    evidenceexcerpts: true,
    rationale: true,
    hiddenreasoning: true,
    chainofthought: true,
    actualgrade: true,
    canvasgrade: true,
    finalgrade: true,
    password: true,
    secret: true,
    accesstoken: true
  };
  Object.keys(value).forEach(function (key) {
    if (key === "__proto__" || key === "prototype" || key === "constructor") {
      throw new ApiError_("UNSAFE_FIELD", "Unsafe object field.", 400);
    }
    var normalized = key.toLowerCase().replace(/[\s_-]/g, "");
    if (prohibited[normalized]) {
      throw new ApiError_(
        "PROHIBITED_TELEMETRY_FIELD",
        "Private content, PII, secrets, and actual grades are not accepted.",
        400
      );
    }
    assertNoProhibitedTelemetryFields_(value[key], path + "." + key, depth + 1);
  });
}

function neutralizeFormula_(value) {
  var text = String(value).replace(/\u0000/g, "");
  return /^[=+\-@]/.test(text) ? "'" + text : text;
}

function safeCellValue_(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number" || typeof value === "boolean") return value;
  return neutralizeFormula_(String(value));
}

function canonicalJson_(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) {
    return "[" + value.map(canonicalJson_).join(",") + "]";
  }
  if (Object.prototype.toString.call(value) === "[object Object]") {
    return (
      "{" +
      Object.keys(value)
        .sort()
        .map(function (key) {
          return JSON.stringify(key) + ":" + canonicalJson_(value[key]);
        })
        .join(",") +
      "}"
    );
  }
  return JSON.stringify(value);
}

function requestHash_(payload) {
  var copy = {};
  Object.keys(payload).forEach(function (key) {
    if (key !== "classToken" && key !== "operation") copy[key] = payload[key];
  });
  return hashKey_(canonicalJson_(copy));
}

function hashKey_(value) {
  var bytes = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    String(value),
    Utilities.Charset.UTF_8
  );
  return bytes.map(function (item) {
    var unsigned = item < 0 ? item + 256 : item;
    return ("0" + unsigned.toString(16)).slice(-2);
  }).join("");
}

function deterministicId_(prefix, value) {
  return prefix + "_" + hashKey_(value).substring(0, 24);
}

function constantTimeEquals_(left, right) {
  left = String(left);
  right = String(right);
  var mismatch = left.length ^ right.length;
  var length = Math.max(left.length, right.length);
  for (var index = 0; index < length; index += 1) {
    mismatch |=
      (index < left.length ? left.charCodeAt(index) : 0) ^
      (index < right.length ? right.charCodeAt(index) : 0);
  }
  return mismatch === 0;
}

function enforceRateLimit_(auth, now) {
  var properties = PropertiesService.getScriptProperties();
  var key = "RATE_" + auth.studentKeyHash.substring(0, 24);
  var bucket = Utilities.formatDate(now, "Etc/UTC", "yyyyMMddHHmm");
  var state;
  try {
    state = JSON.parse(properties.getProperty(key) || "{}");
  } catch (error) {
    state = {};
  }
  if (state.bucket !== bucket) state = { bucket: bucket, count: 0 };
  if (Number(state.count || 0) >= PER_KEY_REQUESTS_PER_MINUTE_) {
    throw new ApiError_(
      "RATE_LIMITED",
      "Per-key request limit exceeded.",
      429,
      { retryAfterSeconds: 60 }
    );
  }
  state.count = Number(state.count || 0) + 1;
  properties.setProperty(key, JSON.stringify(state));
}

function activeReportKeyVersion_() {
  var properties = PropertiesService.getScriptProperties();
  var version = properties.getProperty("REPORT_HMAC_ACTIVE_KEY_VERSION");
  if (version) {
    return requireString_(
      version,
      "REPORT_HMAC_ACTIVE_KEY_VERSION",
      1,
      32,
      /^[A-Za-z0-9._-]+$/
    );
  }
  if (properties.getProperty("REPORT_HMAC_SECRET")) return "legacy-v1";
  throw new ApiError_(
    "SERVER_MISCONFIGURED",
    "REPORT_HMAC_ACTIVE_KEY_VERSION is not configured.",
    500
  );
}

function reportSigningKey_(version) {
  var properties = PropertiesService.getScriptProperties();
  if (version === "legacy-v1") {
    var legacy = properties.getProperty("REPORT_HMAC_SECRET");
    if (!legacy || legacy.length < 32) {
      throw new ApiError_(
        "SERVER_MISCONFIGURED",
        "REPORT_HMAC_SECRET must contain at least 32 characters.",
        500
      );
    }
    return legacy;
  }

  var parsed;
  try {
    parsed = JSON.parse(properties.getProperty("REPORT_HMAC_KEYS_JSON") || "");
  } catch (error) {
    throw new ApiError_(
      "SERVER_MISCONFIGURED",
      "REPORT_HMAC_KEYS_JSON is invalid JSON.",
      500
    );
  }
  assertPlainObject_(parsed, "REPORT_HMAC_KEYS_JSON");
  var secret = parsed[version];
  if (typeof secret !== "string" || secret.length < 32) {
    throw new ApiError_(
      "SERVER_MISCONFIGURED",
      "The requested report signing key version is unavailable.",
      500
    );
  }
  return secret;
}

function signVersionedPayload_(payload, keyVersion) {
  var bytes = Utilities.computeHmacSha256Signature(
    canonicalJson_(payload),
    reportSigningKey_(keyVersion),
    Utilities.Charset.UTF_8
  );
  return Utilities.base64EncodeWebSafe(bytes).replace(/=+$/g, "");
}

function verifyVersionedSignature_(payload, signature, keyVersion) {
  requireString_(signature, "signature", 20, 256, /^[A-Za-z0-9_-]+$/);
  return constantTimeEquals_(
    signature,
    signVersionedPayload_(payload, keyVersion)
  );
}

function validateSha256_(value, label) {
  return requireString_(
    value,
    label || "sha256",
    64,
    64,
    /^[A-Fa-f0-9]{64}$/
  ).toLowerCase();
}

function sha256Bytes_(bytes) {
  var digest = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    bytes
  );
  return digest.map(function (item) {
    var unsigned = item < 0 ? item + 256 : item;
    return ("0" + unsigned.toString(16)).slice(-2);
  }).join("");
}
