from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "app" / "sign-in" / "sign-in.js"


def test_restore_session_redirects_signed_in_users_back_to_app() -> None:
    payload = invoke_restore_session()

    assert payload["assigned"] == "/app/overview?studio=1#app"
    assert payload["status_text"] == "Session restored from local storage."


def invoke_restore_session() -> dict[str, object]:
    script = f"""
const fs = require("fs");
const source = fs.readFileSync({json.dumps(SCRIPT.as_posix())}, "utf8").replace("boot();", "");
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
  store: {{}},
  getItem(key) {{
    if (key === "truthai.supabase.session") {{
      return JSON.stringify({{
        access_token: "access-123",
        refresh_token: "refresh-123",
        expires_at: 1234567890,
        user: {{ email: "user@example.com" }},
      }});
    }}
    return null;
  }},
  setItem() {{}},
  removeItem() {{}},
}};
global.document = {{
  getElementById(id) {{
    return elements[id] || null;
  }},
}};
global.window = {{
  location: {{
    origin: "https://www.truthai.tech",
    search: "?return=%2Fapp%2Foverview%3Fstudio%3D1%23app",
    assign(url) {{
      state.assigned = url;
    }},
  }},
}};
global.fetch = async (url) => {{
  state.fetch_url = url;
  return {{
    ok: true,
    json: async () => ({{
      ready: true,
      supabaseUrl: "https://example.supabase.co",
      supabaseAnonKey: "anon",
      siteOrigin: "https://www.truthai.tech",
    }}),
  }};
}};
global.console = {{
  error() {{}},
}};
(async () => {{
  eval(source);
  await boot();
  state.status_text = elements.status.textContent;
  state.session_user = elements["session-user"].textContent;
  process.stdout.write(JSON.stringify(state));
}})();
"""
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)
