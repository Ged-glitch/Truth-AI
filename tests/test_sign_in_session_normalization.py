from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "app" / "sign-in" / "sign-in.js"


def test_save_session_uses_nested_supabase_session_payload() -> None:
    payload = invoke_save_session(
        {
            "session": {
                "access_token": "access-123",
                "refresh_token": "refresh-123",
                "expires_at": 1234567890,
                "user": {"email": "user@example.com"},
            }
        }
    )

    assert payload["stored"]["access_token"] == "access-123"
    assert payload["stored"]["refresh_token"] == "refresh-123"
    assert payload["stored"]["expires_at"] == 1234567890
    assert payload["stored"]["user"]["email"] == "user@example.com"


def invoke_save_session(payload: dict[str, object]) -> dict[str, object]:
    script = f"""
const fs = require("fs");
const source = fs.readFileSync({json.dumps(SCRIPT.as_posix())}, "utf8");
const state = {{}};
const elements = {{
  "auth-form": {{ addEventListener() {{}} }},
  email: {{ value: "" }},
  password: {{ value: "" }},
  "signup-button": {{ addEventListener() {{}} }},
  "signout-button": {{ addEventListener() {{}} }},
  status: {{ textContent: "", dataset: {{}} }},
  "config-banner": {{ textContent: "" }},
  "session-user": {{ textContent: "" }},
  "session-token": {{ textContent: "" }},
}};
global.localStorage = {{
  setItem(key, value) {{
    state.key = key;
    state.value = value;
  }},
  getItem() {{
    return null;
  }},
  removeItem() {{}},
}};
global.document = {{
  getElementById() {{
    return null;
  }},
}};
global.window = {{
  location: {{
    search: "",
    assign(url) {{
      state.assigned = url;
    }},
  }},
}};
global.fetch = async () => ({{
  ok: true,
  json: async () => ({{
    ready: true,
    supabaseUrl: "https://example.supabase.co",
    supabaseAnonKey: "anon",
  }}),
}});
global.console = {{
  error() {{}},
}};
global.document.getElementById = (id) => elements[id] || null;
eval(source);
saveSession({json.dumps(payload)});
state.stored = JSON.parse(state.value);
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
