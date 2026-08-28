/**
 * Private Drive persistence and short-lived exact-byte report delivery.
 *
 * doGet is intentionally not a GPT Action. It accepts only an opaque capability
 * query value, never a student key, report ID, Drive ID, or workbook selector.
 * The response reconstructs the exact registered PDF bytes in the browser; the
 * renderer is never invoked on download or capability refresh.
 */

function storeIssuedPdf_(pdfBlob, reportId, attemptNumber, generation, config) {
  if (!pdfBlob || typeof pdfBlob.getBytes !== "function") {
    throw new ApiError_(
      "REPORT_RENDER_FAILED",
      "The report renderer did not return PDF bytes.",
      500
    );
  }
  var sourceBytes = pdfBlob.getBytes();
  if (!sourceBytes.length) {
    throw new ApiError_("REPORT_RENDER_FAILED", "The rendered PDF is empty.", 500);
  }
  var sourceHash = sha256Bytes_(sourceBytes);
  var filename = reportFilename_(reportId, attemptNumber, generation);
  var file = null;
  try {
    var folder = DriveApp.getFolderById(config.folderId);
    var immutableBlob = Utilities.newBlob(
      sourceBytes,
      "application/pdf",
      filename
    );
    file = folder.createFile(immutableBlob);
    file.setDescription(
      "V550 immutable issued report; report=" + reportId +
      "; attempt=" + attemptNumber + "; generation=" + generation
    );
    enforcePrivateReportFile_(file);
    assertFileInFolder_(file, config.folderId);

    // Hash the stored object, not the transient renderer blob.
    var storedFile = DriveApp.getFileById(file.getId());
    var storedBlob = storedFile.getBlob();
    var storedBytes = storedBlob.getBytes();
    var storedHash = sha256Bytes_(storedBytes);
    if (
      storedBytes.length !== sourceBytes.length ||
      !constantTimeEquals_(storedHash, sourceHash)
    ) {
      throw new ApiError_(
        "REPORT_STORAGE_MISMATCH",
        "Stored report bytes differ from the rendered issuance.",
        500
      );
    }
    return {
      objectId: storedFile.getId(),
      byteLength: storedBytes.length,
      sha256: storedHash
    };
  } catch (error) {
    if (file) quarantineOrphanedReport_(file.getId());
    if (error && error.name === "ApiError") throw error;
    throw new ApiError_(
      "REPORT_STORAGE_FAILED",
      "The issued report could not be stored in the restricted folder.",
      500
    );
  }
}

function reportFilename_(reportId, attemptNumber, generation) {
  return "V550_" + reportId + "_A" + attemptNumber + "_G" + generation + ".pdf";
}

function enforcePrivateReportFile_(file) {
  file.setSharing(DriveApp.Access.PRIVATE, DriveApp.Permission.VIEW);
  if (file.getSharingAccess() !== DriveApp.Access.PRIVATE) {
    throw new ApiError_(
      "REPORT_STORAGE_NOT_PRIVATE",
      "The report object is not restricted to named access.",
      500
    );
  }
}

function assertFileInFolder_(file, folderId) {
  var parents = file.getParents();
  var found = false;
  while (parents.hasNext()) {
    if (parents.next().getId() === folderId) found = true;
  }
  if (!found) {
    throw new ApiError_(
      "REPORT_STORAGE_MISMATCH",
      "The report object is outside the configured restricted folder.",
      500
    );
  }
}

function quarantineOrphanedReport_(objectId) {
  try {
    DriveApp.getFileById(objectId).setTrashed(true);
  } catch (ignored) {
    try {
      console.warn(JSON.stringify({
        event: "report_orphan_quarantine_failed",
        objectIdHash: hashKey_(objectId)
      }));
    } catch (ignoredLog) {}
  }
}

function assertStoredPdfMatchesRegistry_(registry, config) {
  var verified = parseAndVerifyRegistry_(registry);
  var payload = verified.payload;
  var folderId = config && config.folderId
    ? config.folderId
    : PropertiesService.getScriptProperties().getProperty("REPORT_DRIVE_FOLDER_ID");
  var file;
  try {
    file = DriveApp.getFileById(payload.storageObjectId);
  } catch (error) {
    throw new ApiError_(
      "REPORT_OBJECT_MISSING",
      "The registered report object is unavailable.",
      500
    );
  }
  assertFileInFolder_(file, folderId);
  if (file.getSharingAccess() !== DriveApp.Access.PRIVATE) {
    throw new ApiError_(
      "REPORT_STORAGE_NOT_PRIVATE",
      "The registered report object is not private.",
      500
    );
  }
  if (file.getMimeType() !== "application/pdf") {
    throw new ApiError_(
      "REPORT_OBJECT_INVALID",
      "The registered report object is not a PDF.",
      500
    );
  }
  var expectedName = reportFilename_(
    payload.reportId,
    payload.attemptNumber,
    payload.generationNumber
  );
  if (file.getName() !== expectedName) {
    throw new ApiError_(
      "REPORT_OBJECT_INVALID",
      "The registered report object name is invalid.",
      500
    );
  }
  var bytes = file.getBlob().getBytes();
  var hash = sha256Bytes_(bytes);
  if (
    bytes.length !== Number(payload.pdfByteLength) ||
    !constantTimeEquals_(hash, payload.pdfSha256)
  ) {
    throw new ApiError_(
      "REPORT_OBJECT_MODIFIED",
      "The registered report object no longer matches its signed registry.",
      500
    );
  }
  return { bytes: bytes, filename: expectedName };
}

function createDownloadCapability_(registry, authorizedSessionId, now, config) {
  var verified = parseAndVerifyRegistry_(registry);
  var nonce = Utilities.getUuid().replace(/-/g, "") +
    Utilities.getUuid().replace(/-/g, "");
  var proofPayload = {
    type: "report-download-capability",
    nonce: nonce
  };
  var proof = signVersionedPayload_(proofPayload, config.keyVersion);
  var opaqueToken = "cap." + nonce + "." + proof;
  var propertyKey = reportCapabilityPropertyKey_(opaqueToken);
  var issuedAt = now.toISOString();
  var expiresAt = new Date(
    now.getTime() + config.capabilityTtlSeconds * 1000
  ).toISOString();
  var payload = {
    version: "1",
    tokenHash: hashKey_(opaqueToken),
    reportId: verified.payload.reportId,
    registryRef: reportRegistryPropertyKey_(verified.payload.reportId),
    studentKeyHash: verified.payload.studentKeyHash,
    authorizedSessionId: authorizedSessionId,
    issuedAt: issuedAt,
    expiresAt: expiresAt,
    keyVersion: config.keyVersion
  };
  var envelope = {
    payload: payload,
    signature: signVersionedPayload_(payload, config.keyVersion)
  };
  var properties = PropertiesService.getScriptProperties();
  if (properties.getProperty(propertyKey)) {
    throw new ApiError_(
      "CAPABILITY_COLLISION",
      "A download capability collision occurred.",
      500
    );
  }
  properties.setProperty(propertyKey, canonicalJson_(envelope));
  try {
    return {
      url: reportCapabilityUrl_(opaqueToken),
      propertyKey: propertyKey
    };
  } catch (error) {
    deletePrivateProperty_(propertyKey);
    throw error;
  }
}

function reportCapabilityPropertyKey_(token) {
  return "REPORT_CAPABILITY_" + hashKey_(token).substring(0, 40);
}

function reportCapabilityUrl_(opaqueToken) {
  var baseUrl = ScriptApp.getService().getUrl();
  if (!baseUrl || !/^https:\/\//.test(baseUrl)) {
    throw new ApiError_(
      "SERVER_MISCONFIGURED",
      "The report download web app is not deployed.",
      500
    );
  }
  return baseUrl.replace(/\/$/, "") +
    "?capability=" + encodeURIComponent(opaqueToken);
}

function validateDownloadCapability_(opaqueToken, now) {
  var token = requireString_(
    opaqueToken,
    "capability",
    80,
    512,
    /^cap\.[A-Fa-f0-9]{64}\.[A-Za-z0-9_-]{20,256}$/
  );
  var pieces = token.split(".");
  var nonce = pieces[1];
  var proof = pieces[2];
  var propertyKey = reportCapabilityPropertyKey_(token);
  var encoded = PropertiesService.getScriptProperties().getProperty(propertyKey);
  if (!encoded) {
    throw new ApiError_(
      "REPORT_CAPABILITY_INVALID",
      "The report download capability is invalid.",
      403
    );
  }
  var envelope;
  try {
    envelope = JSON.parse(encoded);
  } catch (error) {
    throw new ApiError_(
      "REPORT_CAPABILITY_INVALID",
      "The report download capability is invalid.",
      403
    );
  }
  assertOnlyKeys_(
    envelope,
    { payload: true, signature: true },
    "download capability"
  );
  assertPlainObject_(envelope.payload, "download capability payload");
  assertOnlyKeys_(
    envelope.payload,
    {
      version: true,
      tokenHash: true,
      reportId: true,
      registryRef: true,
      studentKeyHash: true,
      authorizedSessionId: true,
      issuedAt: true,
      expiresAt: true,
      keyVersion: true
    },
    "download capability payload"
  );
  var payload = envelope.payload;
  requireString_(payload.version, "capability version", 1, 8, /^[0-9]+$/);
  validateSha256_(payload.tokenHash, "capability token hash");
  validateOpaqueId_(payload.reportId, "capability reportId");
  requireString_(
    payload.registryRef,
    "capability registry reference",
    20,
    80,
    /^REPORT_REGISTRY_[A-Fa-f0-9]{40}$/
  );
  validateSha256_(payload.studentKeyHash, "capability student key hash");
  validateOpaqueId_(payload.authorizedSessionId, "capability sessionId");
  requireValidServerTimestamp_(payload.issuedAt, "capability issuedAt");
  requireValidServerTimestamp_(payload.expiresAt, "capability expiresAt");
  var keyVersion = requireString_(
    payload.keyVersion,
    "capability key version",
    1,
    32,
    /^[A-Za-z0-9._-]+$/
  );
  if (!verifyVersionedSignature_(payload, envelope.signature, keyVersion)) {
    throw new ApiError_(
      "REPORT_CAPABILITY_INVALID",
      "The report download capability is invalid.",
      403
    );
  }
  if (!verifyVersionedSignature_({
    type: "report-download-capability",
    nonce: nonce
  }, proof, keyVersion)) {
    throw new ApiError_(
      "REPORT_CAPABILITY_INVALID",
      "The report download capability is invalid.",
      403
    );
  }
  if (
    !constantTimeEquals_(payload.tokenHash, hashKey_(token)) ||
    !constantTimeEquals_(
      payload.registryRef,
      reportRegistryPropertyKey_(payload.reportId)
    )
  ) {
    throw new ApiError_(
      "REPORT_CAPABILITY_INVALID",
      "The report download capability is invalid.",
      403
    );
  }
  var expiry = new Date(payload.expiresAt).getTime();
  if (!isFinite(expiry) || now.getTime() > expiry) {
    throw new ApiError_(
      "REPORT_CAPABILITY_EXPIRED",
      "The report download capability has expired.",
      410
    );
  }
  return payload;
}

function doGet(e) {
  var now = new Date();
  try {
    var parameters = e && e.parameter ? e.parameter : {};
    var keys = Object.keys(parameters);
    if (keys.length !== 1 || keys[0] !== "capability") {
      throw new ApiError_(
        "REPORT_CAPABILITY_INVALID",
        "A single report capability is required.",
        403
      );
    }
    var capability = validateDownloadCapability_(parameters.capability, now);
    var registry = getReportRegistryById_(capability.reportId);
    if (
      !registry ||
      !constantTimeEquals_(
        capability.registryRef,
        reportRegistryPropertyKey_(registry.payload.reportId)
      ) ||
      !constantTimeEquals_(
        capability.studentKeyHash,
        registry.payload.studentKeyHash
      )
    ) {
      throw new ApiError_(
        "REPORT_CAPABILITY_INVALID",
        "The report download capability is invalid.",
        403
      );
    }
    var stored = assertStoredPdfMatchesRegistry_(registry);
    return exactPdfDownloadHtml_(stored.bytes, stored.filename);
  } catch (error) {
    try {
      console.warn(JSON.stringify({
        event: "report_download_failed",
        code: error && error.name === "ApiError"
          ? error.code
          : "INTERNAL_ERROR",
        serverTimestamp: now.toISOString()
      }));
    } catch (ignored) {}
    return reportDownloadErrorHtml_(error);
  }
}

function exactPdfDownloadHtml_(bytes, filename) {
  var encoded = Utilities.base64Encode(bytes);
  var safeEncoded = JSON.stringify(encoded);
  var safeFilename = JSON.stringify(filename);
  var html = "<!doctype html><html><head><meta charset=\"utf-8\">" +
    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">" +
    "<title>V550 report download</title></head><body>" +
    "<p id=\"status\">Preparing the exact issued report…</p>" +
    "<button id=\"download\" type=\"button\">Download report</button>" +
    "<noscript>JavaScript is required to reconstruct the issued PDF bytes.</noscript>" +
    "<script>(function(){var encoded=" + safeEncoded + ";" +
    "var raw=atob(encoded),bytes=new Uint8Array(raw.length);" +
    "for(var i=0;i<raw.length;i++){bytes[i]=raw.charCodeAt(i);}" +
    "var url=URL.createObjectURL(new Blob([bytes],{type:'application/pdf'}));" +
    "var button=document.getElementById('download');" +
    "function download(){var a=document.createElement('a');a.href=url;" +
    "a.download=" + safeFilename + ";document.body.appendChild(a);a.click();a.remove();" +
    "document.getElementById('status').textContent='Download ready.';}" +
    "button.addEventListener('click',download);download();" +
    "setTimeout(function(){URL.revokeObjectURL(url);},60000);}());</script>" +
    "</body></html>";
  return HtmlService.createHtmlOutput(html).setTitle("V550 report download");
}

function reportDownloadErrorHtml_(error) {
  var expired = error && error.name === "ApiError" &&
    error.code === "REPORT_CAPABILITY_EXPIRED";
  var message = expired
    ? "This report link has expired. Request the current report again for a new link."
    : "This report link is invalid or unavailable.";
  return HtmlService.createHtmlOutput(
    "<!doctype html><html><head><meta charset=\"utf-8\"><title>" +
    "V550 report download</title></head><body><p>" + message +
    "</p></body></html>"
  ).setTitle("V550 report download");
}
