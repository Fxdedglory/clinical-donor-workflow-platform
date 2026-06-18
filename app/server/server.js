const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const port = process.env.PORT || 8080;
const clinicalRoot = path.join(__dirname, "Clinical");

const dataLake = {
  account: process.env.CLINICAL_DATA_LAKE_ACCOUNT || process.env.DATA_LAKE_ACCOUNT_NAME || "",
  container: process.env.CLINICAL_DATA_LAKE_CONTAINER || process.env.DATA_LAKE_CONTAINER || "raw",
  prefix: (process.env.CLINICAL_DATA_LAKE_PREFIX || "apps/clinical/events").replace(/^\/+|\/+$/g, ""),
  module: process.env.CLINICAL_APP_MODULE || "Clinical",
  authMode: process.env.CLINICAL_AUTH_MODE || "demo"
};

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".ico": "image/x-icon"
};

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type,X-User-Id,X-Correlation-Id"
};

function apiPath(pathname) {
  return pathname.startsWith("/Clinical/api/clinical/") ? pathname.slice("/Clinical".length) : pathname;
}

function isClinicalApi(pathname) {
  const normalized = apiPath(pathname);

  return (
    normalized === "/api/clinical/health" ||
    normalized === "/api/clinical/events" ||
    normalized === "/api/clinical/events/recent"
  );
}

function jsonResponse(res, status, payload) {
  const body = JSON.stringify(payload, null, 2);

  res.writeHead(status, {
    ...corsHeaders,
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-cache",
    "Content-Length": Buffer.byteLength(body)
  });

  res.end(body);
}

function sendFile(res, filePath) {
  const ext = path.extname(filePath).toLowerCase();

  res.writeHead(200, {
    "Content-Type": mimeTypes[ext] || "application/octet-stream",
    "Cache-Control": ext === ".html" ? "no-cache" : "public, max-age=31536000, immutable"
  });

  fs.createReadStream(filePath).pipe(res);
}

function safePath(base, relativePath) {
  const resolved = path.resolve(base, relativePath);

  if (!resolved.startsWith(path.resolve(base))) {
    return null;
  }

  return resolved;
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    const maxBytes = 1024 * 1024;

    req.on("data", (chunk) => {
      body += chunk.toString("utf8");

      if (Buffer.byteLength(body) > maxBytes) {
        reject(new Error("Request body too large."));
        req.destroy();
      }
    });

    req.on("end", () => {
      if (!body.trim()) {
        resolve({});
        return;
      }

      try {
        resolve(JSON.parse(body));
      } catch {
        reject(new Error("Invalid JSON request body."));
      }
    });

    req.on("error", reject);
  });
}

function requestRaw(method, urlString, headers = {}, body = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlString);
    const lib = url.protocol === "https:" ? https : http;
    const payload = body === null || body === undefined ? null : Buffer.from(String(body), "utf8");

    const options = {
      method,
      hostname: url.hostname,
      port: url.port || (url.protocol === "https:" ? 443 : 80),
      path: `${url.pathname}${url.search}`,
      headers: { ...headers }
    };

    if (payload) {
      options.headers["Content-Length"] = payload.length;
    }

    const request = lib.request(options, (response) => {
      const chunks = [];

      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => {
        resolve({
          statusCode: response.statusCode,
          headers: response.headers,
          body: Buffer.concat(chunks).toString("utf8")
        });
      });
    });

    request.on("error", reject);

    if (payload) {
      request.write(payload);
    }

    request.end();
  });
}

async function getManagedIdentityToken() {
  const endpoint = process.env.IDENTITY_ENDPOINT || process.env.MSI_ENDPOINT;
  const identityHeader = process.env.IDENTITY_HEADER || process.env.MSI_SECRET;

  if (!endpoint || !identityHeader) {
    throw new Error("Managed identity endpoint is not available in this App Service environment.");
  }

  const url = new URL(endpoint);
  const headers = {};

  if (process.env.IDENTITY_ENDPOINT) {
    url.searchParams.set("api-version", "2019-08-01");
    url.searchParams.set("resource", "https://storage.azure.com/");
    headers["X-IDENTITY-HEADER"] = identityHeader;
  } else {
    url.searchParams.set("api-version", "2017-09-01");
    url.searchParams.set("resource", "https://storage.azure.com/");
    headers["Secret"] = identityHeader;
  }

  const response = await requestRaw("GET", url.toString(), headers);

  if (response.statusCode < 200 || response.statusCode >= 300) {
    throw new Error(`Managed identity token request failed: ${response.statusCode} ${response.body}`);
  }

  const tokenPayload = JSON.parse(response.body);

  if (!tokenPayload.access_token) {
    throw new Error("Managed identity token response did not include access_token.");
  }

  return tokenPayload.access_token;
}

function storageHeaders(token, contentType = "application/json; charset=utf-8") {
  return {
    Authorization: `Bearer ${token}`,
    "x-ms-version": "2023-11-03",
    "x-ms-date": new Date().toUTCString(),
    "Content-Type": contentType
  };
}

async function ensureContainer(token) {
  const url = `https://${dataLake.account}.blob.core.windows.net/${encodeURIComponent(dataLake.container)}?restype=container`;
  const response = await requestRaw("PUT", url, storageHeaders(token), "");

  if ([201, 202, 409].includes(response.statusCode)) {
    return;
  }

  throw new Error(`Container create/check failed: ${response.statusCode} ${response.body}`);
}

async function writeEventBlob(blobName, envelope, token) {
  const encodedBlobName = blobName.split("/").map(encodeURIComponent).join("/");
  const url = `https://${dataLake.account}.blob.core.windows.net/${encodeURIComponent(dataLake.container)}/${encodedBlobName}`;
  const body = JSON.stringify(envelope, null, 2);

  const response = await requestRaw("PUT", url, {
    ...storageHeaders(token),
    "x-ms-blob-type": "BlockBlob"
  }, body);

  if (response.statusCode !== 201) {
    throw new Error(`Blob write failed: ${response.statusCode} ${response.body}`);
  }
}

function decodeXml(value) {
  return String(value || "")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&amp;", "&")
    .replaceAll("&quot;", '"')
    .replaceAll("&apos;", "'");
}

function safeEventResponse(event, blobName) {
  return {
    blob_name: blobName,
    event_id: event.event_id,
    event_type: event.event_type,
    source_app: event.source_app,
    module: event.module,
    occurred_at: event.occurred_at,
    received_at: event.received_at,
    actor_user_id: event.actor_user_id,
    correlation_id: event.correlation_id,
    aggregate_type: event.aggregate_type,
    aggregate_id: event.aggregate_id,
    payload_version: event.payload_version,
    sensitivity_classification: event.sensitivity_classification,
    metadata: event.metadata || {}
  };
}

async function listRecentEvents(token, limit) {
  const boundedLimit = Math.max(1, Math.min(Number(limit) || 20, 100));
  const prefix = `${dataLake.prefix}/`;
  const listUrl = `https://${dataLake.account}.blob.core.windows.net/${encodeURIComponent(dataLake.container)}?restype=container&comp=list&prefix=${encodeURIComponent(prefix)}`;

  const listResponse = await requestRaw("GET", listUrl, storageHeaders(token));

  if (listResponse.statusCode === 404) {
    return [];
  }

  if (listResponse.statusCode < 200 || listResponse.statusCode >= 300) {
    throw new Error(`Blob list failed: ${listResponse.statusCode} ${listResponse.body}`);
  }

  const names = [...listResponse.body.matchAll(/<Name>([^<]+)<\/Name>/g)]
    .map((match) => decodeXml(match[1]))
    .filter((name) => name.startsWith(prefix))
    .filter((name) => name.toLowerCase().endsWith(".json"))
    .sort()
    .reverse()
    .slice(0, boundedLimit);

  const events = [];

  for (const blobName of names) {
    const encodedBlobName = blobName.split("/").map(encodeURIComponent).join("/");
    const blobUrl = `https://${dataLake.account}.blob.core.windows.net/${encodeURIComponent(dataLake.container)}/${encodedBlobName}`;
    const blobResponse = await requestRaw("GET", blobUrl, storageHeaders(token));

    if (blobResponse.statusCode >= 200 && blobResponse.statusCode < 300) {
      try {
        events.push(safeEventResponse(JSON.parse(blobResponse.body), blobName));
      } catch {
        events.push({
          blob_name: blobName,
          event_type: "clinical.event.unreadable",
          sensitivity_classification: "unknown"
        });
      }
    }
  }

  return events;
}

function createEnvelope(input, req) {
  const now = new Date();
  const eventId = input.event_id || input.eventId || crypto.randomUUID();
  const eventType = input.event_type || input.eventType || "clinical.ui.event";
  const correlationId = req.headers["x-correlation-id"] || input.correlation_id || input.correlationId || crypto.randomUUID();
  const actor = req.headers["x-user-id"] || input.actor_user_id || input.actorUserId || "demo";

  return {
    event_id: eventId,
    event_type: eventType,
    source_app: "Clinical",
    module: dataLake.module,
    occurred_at: input.occurred_at || input.occurredAt || now.toISOString(),
    received_at: now.toISOString(),
    actor_user_id: actor,
    correlation_id: correlationId,
    aggregate_type: input.aggregate_type || input.aggregateType || "clinical_demo",
    aggregate_id: input.aggregate_id || input.aggregateId || eventId,
    payload_version: input.payload_version || input.payloadVersion || "1.0",
    sensitivity_classification: input.sensitivity_classification || input.sensitivityClassification || "public_internal",
    payload: input.payload || input,
    metadata: {
      auth_mode: dataLake.authMode,
      request_url: req.url,
      user_agent: req.headers["user-agent"] || null
    }
  };
}

async function handleHealth(req, res) {
  jsonResponse(res, 200, {
    status: "ok",
    app: "Meridian Clinical",
    module: dataLake.module,
    data_lake: {
      account_configured: Boolean(dataLake.account),
      account: dataLake.account,
      container: dataLake.container,
      prefix: dataLake.prefix
    },
    managed_identity_available: Boolean(process.env.IDENTITY_ENDPOINT || process.env.MSI_ENDPOINT),
    timestamp: new Date().toISOString()
  });
}

async function handleEventPost(req, res) {
  if (!dataLake.account) {
    jsonResponse(res, 503, { ok: false, error: "CLINICAL_DATA_LAKE_ACCOUNT is not configured." });
    return;
  }

  const input = await readJsonBody(req);
  const envelope = createEnvelope(input, req);

  const datePath = envelope.received_at.slice(0, 10).replaceAll("-", "/");
  const safeTimestamp = envelope.received_at.replaceAll(":", "-").replaceAll(".", "-");
  const blobName = `${dataLake.prefix}/${datePath}/${safeTimestamp}-${envelope.event_id}.json`;

  const token = await getManagedIdentityToken();
  await ensureContainer(token);
  await writeEventBlob(blobName, envelope, token);

  jsonResponse(res, 201, {
    ok: true,
    event_id: envelope.event_id,
    event_type: envelope.event_type,
    blob_name: blobName,
    container: dataLake.container,
    account: dataLake.account
  });
}

async function handleRecentEvents(req, res) {
  if (!dataLake.account) {
    jsonResponse(res, 503, { ok: false, error: "CLINICAL_DATA_LAKE_ACCOUNT is not configured." });
    return;
  }

  const requestUrl = new URL(req.url, "http://localhost");
  const token = await getManagedIdentityToken();
  const events = await listRecentEvents(token, requestUrl.searchParams.get("limit") || 20);

  jsonResponse(res, 200, {
    ok: true,
    account: dataLake.account,
    container: dataLake.container,
    prefix: dataLake.prefix,
    count: events.length,
    events
  });
}

async function handleRequest(req, res) {
  const requestUrl = new URL(req.url, "http://localhost");
  const pathname = decodeURIComponent(requestUrl.pathname);
  const normalizedApiPath = apiPath(pathname);

  if (req.method === "OPTIONS" && isClinicalApi(pathname)) {
    res.writeHead(204, corsHeaders);
    res.end();
    return;
  }

  if (normalizedApiPath === "/api/clinical/health") {
    await handleHealth(req, res);
    return;
  }

  if (normalizedApiPath === "/api/clinical/events/recent") {
    if (req.method !== "GET") {
      jsonResponse(res, 405, { ok: false, error: "Method not allowed." });
      return;
    }

    await handleRecentEvents(req, res);
    return;
  }

  if (normalizedApiPath === "/api/clinical/events") {
    if (req.method !== "POST") {
      jsonResponse(res, 405, { ok: false, error: "Method not allowed." });
      return;
    }

    await handleEventPost(req, res);
    return;
  }

  if (pathname === "/" || pathname === "/Clinical") {
    res.writeHead(302, { Location: "/Clinical/" });
    res.end();
    return;
  }

  if (!pathname.startsWith("/Clinical/")) {
    res.writeHead(302, { Location: "/Clinical/" });
    res.end();
    return;
  }

  let relativePath = pathname.slice("/Clinical/".length);

  if (!relativePath || relativePath.endsWith("/")) {
    relativePath = path.join(relativePath, "index.html");
  }

  const filePath = safePath(clinicalRoot, relativePath);

  if (!filePath) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }

  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    sendFile(res, filePath);
    return;
  }

  sendFile(res, path.join(clinicalRoot, "index.html"));
}

http.createServer((req, res) => {
  handleRequest(req, res).catch((error) => {
    jsonResponse(res, 500, {
      ok: false,
      error: error.message || "Unexpected server error."
    });
  });
}).listen(port, () => {
  console.log(`Meridian Clinical listening on ${port}`);
});