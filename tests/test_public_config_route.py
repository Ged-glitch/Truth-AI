from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / "api" / "public-config.js"


def test_public_config_route_returns_supabase_env_values() -> None:
    payload = invoke_route(
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-key",
    )

    assert payload["status"] == 200
    assert payload["json"] == {
        "ready": True,
        "supabaseUrl": "https://example.supabase.co",
        "supabaseAnonKey": "anon-key",
    }


def test_public_config_route_marks_missing_env_as_not_ready() -> None:
    payload = invoke_route(supabase_url="", supabase_anon_key="")

    assert payload["status"] == 200
    assert payload["json"]["ready"] is False


def invoke_route(*, supabase_url: str, supabase_anon_key: str) -> dict[str, object]:
    script = f"""
process.env.SUPABASE_URL = {json.dumps(supabase_url)};
process.env.SUPABASE_ANON_KEY = {json.dumps(supabase_anon_key)};
const handler = require({json.dumps(ROUTE.as_posix())});
const state = {{
  status: null,
  headers: null,
  json: null,
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
  end() {{
    state.ended = true;
  }},
}};
const req = {{ method: "GET" }};
handler(req, res);
process.stdout.write(JSON.stringify(state));
"""
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)
