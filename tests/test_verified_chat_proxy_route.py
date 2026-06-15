from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / "api" / "verified-chat" / "[...path].js"


def test_verified_chat_proxy_requires_backend_url() -> None:
    payload = invoke_route(
        env_backend=None,
        method="GET",
        suffix="latest",
        vercel_env="1",
    )

    assert payload["status"] == 503
    assert payload["json"]["error"] == (
        "VERIFIED_CHAT_BACKEND_URL is not configured for the website API"
    )


def test_verified_chat_proxy_forwards_run_request() -> None:
    payload = invoke_route(
        env_backend="https://backend.example.test/",
        method="POST",
        suffix="run",
        body={"prompt_text": "Verify this prompt."},
        upstream_status=202,
        upstream_text='{"decision":"accept"}',
        upstream_content_type="application/json",
    )

    assert payload["status"] == 202
    assert payload["send"] == '{"decision":"accept"}'
    assert payload["upstream_url"] == "https://backend.example.test/verified-chat/run"
    assert payload["upstream_init"]["method"] == "POST"
    assert payload["upstream_init"]["headers"]["Content-Type"] == "application/json"
    assert payload["upstream_init"]["body"] == '{"prompt_text":"Verify this prompt."}'


def test_verified_chat_proxy_falls_back_to_local_backend_in_dev() -> None:
    payload = invoke_route(env_backend=None, method="GET", suffix="latest")

    assert payload["status"] == 200
    assert payload["upstream_url"] == "http://127.0.0.1:8010/verified-chat/latest"


def test_verified_chat_proxy_rejects_unknown_suffix() -> None:
    payload = invoke_route(
        env_backend="https://backend.example.test",
        method="GET",
        suffix="unexpected",
    )

    assert payload["status"] == 404
    assert payload["json"]["error"] == "unknown endpoint: unexpected"


def invoke_route(
    *,
    env_backend: str | None,
    method: str,
    suffix: str,
    body: object | None = None,
    upstream_status: int = 200,
    upstream_text: str = '{"ok":true}',
    upstream_content_type: str = "application/json",
    vercel_env: str | None = None,
) -> dict[str, object]:
    script = f"""
if ({json.dumps(env_backend)} === null) {{
  delete process.env.VERIFIED_CHAT_BACKEND_URL;
}} else {{
  process.env.VERIFIED_CHAT_BACKEND_URL = {json.dumps(env_backend)};
}}
if ({json.dumps(vercel_env)} === null) {{
  delete process.env.VERCEL;
}} else {{
  process.env.VERCEL = {json.dumps(vercel_env)};
}}
const handler = require({json.dumps(ROUTE.as_posix())});
const state = {{
  status: null,
  json: null,
  send: null,
  headers: null,
  upstream_url: null,
  upstream_init: null,
}};
global.fetch = async (url, init) => {{
  state.upstream_url = url;
  state.upstream_init = init;
  return {{
    status: {upstream_status},
    headers: {{
      get: (name) =>
        name === "content-type" ? {json.dumps(upstream_content_type)} : null,
    }},
    text: async () => {json.dumps(upstream_text)},
  }};
}};
const res = {{
  setHeader(name, value) {{
    state.headers = state.headers || {{}};
    state.headers[name] = value;
  }},
  status(code) {{
    state.status = code;
    return this;
  }},
  json(payload) {{
    state.json = payload;
  }},
  send(text) {{
    state.send = text;
  }},
  end() {{
    state.ended = true;
  }},
}};
const req = {{
  method: {json.dumps(method)},
  query: {{ path: {json.dumps([part for part in suffix.split("/") if part])} }},
  body: {json.dumps(body)},
}};
(async () => {{
  await handler(req, res);
  process.stdout.write(JSON.stringify(state));
}})().catch((error) => {{
  process.stderr.write(error.stack || String(error));
  process.exit(1);
}});
"""
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)
