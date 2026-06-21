const DEFAULT_BACKEND_URL = process.env.VERIFIED_CHAT_BACKEND_URL;
const LOCAL_BACKEND_URL = "http://127.0.0.1:8010";

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");

  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }

  const parts = normalizePathParts(req.query.path);
  const suffix = parts.join("/");
  if (suffix !== "run" && suffix !== "latest") {
    res.status(404).json({ error: `unknown endpoint: ${suffix}` });
    return;
  }

  const upstreamUrl = buildUpstreamUrl(resolveBackendUrl(req), suffix);
  const init = {
    method: req.method,
    headers: {
      "Content-Type": "application/json",
    },
  };
  const authorization = req.headers?.authorization || req.headers?.Authorization;
  if (authorization) {
    init.headers.Authorization = authorization;
  }
  if (req.method !== "GET") {
    init.body = JSON.stringify(req.body ?? {});
  }

  const upstream = await fetch(upstreamUrl, init);
  const text = await upstream.text();
  res.status(upstream.status);
  res.setHeader("Content-Type", upstream.headers.get("content-type") || "application/json");
  res.send(text);
};

function resolveBackendUrl(req) {
  if (DEFAULT_BACKEND_URL) {
    return DEFAULT_BACKEND_URL;
  }
  if (process.env.VERCEL) {
    return resolveProductionBackendUrl(req);
  }
  return LOCAL_BACKEND_URL;
}

function normalizePathParts(path) {
  if (Array.isArray(path)) {
    return path;
  }
  if (typeof path === "string" && path.length > 0) {
    return [path];
  }
  return [];
}

function resolveProductionBackendUrl(req) {
  const host = req.headers?.host || "www.truthai.tech";
  const forwardedProto = req.headers?.["x-forwarded-proto"] || "https";
  return `${forwardedProto}://${host}/api/verified-chat-backend`;
}

function buildUpstreamUrl(baseUrl, suffix) {
  if (baseUrl === LOCAL_BACKEND_URL) {
    return `${baseUrl.replace(/\/$/, "")}/verified-chat/${suffix}`;
  }

  if (baseUrl.endsWith("/api/verified-chat-backend")) {
    const upstream = new URL(baseUrl);
    upstream.searchParams.set("path", suffix);
    return upstream.toString();
  }

  const upstream = new URL(baseUrl);
  upstream.searchParams.set("path", suffix);
  return upstream.toString();
}
