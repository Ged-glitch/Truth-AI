from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "app" / "sign-in" / "sign-in.js"


def test_signup_body_uses_production_confirmation_redirect() -> None:
    payload = invoke_build_signup_body()

    assert payload["body"]["options"]["emailRedirectTo"] == (
        "https://www.truthai.tech/app/sign-in?confirmed=1"
    )


def invoke_build_signup_body() -> dict[str, object]:
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
global.window = {{
  location: {{
    origin: "https://www.truthai.tech",
  }},
}};
global.localStorage = {{
  getItem() {{
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
eval(source);
state.body = buildSignUpBody("user@example.com", "secret123");
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
