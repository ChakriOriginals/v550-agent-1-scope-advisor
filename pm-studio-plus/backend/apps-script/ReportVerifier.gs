/**
 * Instructor-only report verifier.
 *
 * This administrative function is intentionally absent from the GPT Action
 * allowlist/OpenAPI schema. It reads only the private report registry, the exact
 * registered object, and the submitted PDF bytes. It never returns student data
 * or workbook history.
 */

function verifySubmittedReport(reportId, submittedPdf, instructorToken) {
  authorizeInstructorVerifier_(instructorToken);

  var normalizedReportId;
  try {
    normalizedReportId = validateOpaqueId_(reportId, "reportId");
  } catch (invalidId) {
    return { status: "UNKNOWN REPORT ID" };
  }

  var registry;
  try {
    registry = getReportRegistryById_(normalizedReportId);
  } catch (invalidRegistry) {
    return failedVerificationResult_(normalizedReportId, null);
  }
  if (!registry) {
    return { status: "UNKNOWN REPORT ID", reportId: normalizedReportId };
  }

  try {
    // A valid submission must match both the signed registry and the current
    // exact stored object; a caller-supplied hash is never accepted.
    var stored = assertStoredPdfMatchesRegistry_(registry);
    var submittedBytes = submittedPdfBytes_(submittedPdf);
    var submittedHash = sha256Bytes_(submittedBytes);
    if (
      submittedBytes.length !== Number(registry.payload.pdfByteLength) ||
      submittedBytes.length !== stored.bytes.length ||
      !constantTimeEquals_(submittedHash, registry.payload.pdfSha256)
    ) {
      return failedVerificationResult_(normalizedReportId, registry);
    }
    var generation = Number(registry.payload.generationNumber);
    return {
      status: generation === 1
        ? "VALID ORIGINAL"
        : "VALID REGENERATED COPY — GENERATION " + generation,
      reportId: normalizedReportId,
      generation: generation,
      issuedAt: registry.payload.issuedAt
    };
  } catch (error) {
    return failedVerificationResult_(normalizedReportId, registry);
  }
}

function authorizeInstructorVerifier_(suppliedToken) {
  var token = requireString_(
    suppliedToken,
    "instructor verifier token",
    32,
    512
  );
  var expected = PropertiesService
    .getScriptProperties()
    .getProperty("INSTRUCTOR_VERIFIER_TOKEN");
  if (!expected || expected.length < 32) {
    throw new ApiError_(
      "SERVER_MISCONFIGURED",
      "INSTRUCTOR_VERIFIER_TOKEN is not configured.",
      500
    );
  }
  if (!constantTimeEquals_(token, expected)) {
    throw new ApiError_(
      "INSTRUCTOR_UNAUTHORIZED",
      "Instructor verification authorization failed.",
      401
    );
  }
}

function submittedPdfBytes_(submittedPdf) {
  var bytes;
  if (submittedPdf && typeof submittedPdf.getBytes === "function") {
    bytes = submittedPdf.getBytes();
  } else if (Array.isArray(submittedPdf)) {
    bytes = submittedPdf.slice();
  } else {
    throw new ApiError_(
      "INVALID_SUBMITTED_REPORT",
      "A submitted PDF blob or byte array is required.",
      400
    );
  }
  if (!bytes.length || bytes.length > 50000000) {
    throw new ApiError_(
      "INVALID_SUBMITTED_REPORT",
      "Submitted PDF bytes are empty or too large.",
      400
    );
  }
  bytes.forEach(function (value) {
    if (
      typeof value !== "number" ||
      !isFinite(value) ||
      Math.floor(value) !== value ||
      value < -128 ||
      value > 255
    ) {
      throw new ApiError_(
        "INVALID_SUBMITTED_REPORT",
        "Submitted PDF bytes are invalid.",
        400
      );
    }
  });
  return bytes.map(function (value) {
    return value > 127 ? value - 256 : value;
  });
}

function failedVerificationResult_(reportId, registry) {
  var result = {
    status: "VERIFICATION FAILED — FILE MAY HAVE BEEN MODIFIED",
    reportId: reportId
  };
  // These values are already printed on the submitted report and are returned
  // only when they came from a successfully parsed, signed private registry.
  if (registry && registry.payload) {
    result.generation = Number(registry.payload.generationNumber);
    result.issuedAt = registry.payload.issuedAt;
  }
  return result;
}
