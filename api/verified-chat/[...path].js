const DEFAULT_BACKEND_URL = process.env.VERIFIED_CHAT_BACKEND_URL;
const LOCAL_BACKEND_URL = "http://127.0.0.1:8010";
const RESOLVED_BACKEND_URL = DEFAULT_BACKEND_URL || (process.env.VERCEL ? null : LOCAL_BACKEND_URL);

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");

  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }

  if (!RESOLVED_BACKEND_URL) {
    res.status(503).json({
      error: "VERIFIED_CHAT_BACKEND_URL is not configured for the website API",
    });
    return;
  }

  const parts = Array.isArray(req.query.path) ? req.query.path : [];
  const suffix = parts.join("/");
  if (suffix !== "run" && suffix !== "latest") {
    res.status(404).json({ error: `unknown endpoint: ${suffix}` });
    return;
  }

  const upstreamUrl = buildUpstreamUrl(RESOLVED_BACKEND_URL, suffix);
  const init = {
    method: req.method,
    headers: {
      "Content-Type": "application/json",
    },
  };
  if (req.method !== "GET") {
    init.body = JSON.stringify(req.body ?? {});
  }

  const upstream = await fetch(upstreamUrl, init);
  const text = await upstream.text();
  res.status(upstream.status);
  res.setHeader("Content-Type", upstream.headers.get("content-type") || "application/json");
  res.send(text);
};

function buildUpstreamUrl(baseUrl, suffix) {
  if (baseUrl === LOCAL_BACKEND_URL) {
    return `${baseUrl.replace(/\/$/, "")}/verified-chat/${suffix}`;
  }

  const upstream = new URL(baseUrl);
  upstream.searchParams.set("path", suffix);
  return upstream.toString();
}
