from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "app" / "sign-in" / "sign-in.js"


def test_load_config_falls_back_to_current_origin_when_public_config_is_unavailable() -> None:
    payload = invoke_load_config()

    assert payload["config"]["ready"] is False
    assert payload["config"]["siteOrigin"] == "http://127.0.0.1:4174"
    assert payload["config_banner"] == (
        "Authentication settings are unavailable in this environment. Add the "
        "environment variables to enable login."
    )


def invoke_load_config() -> dict[str, object]:
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
  "back-to-app": {{ href: "" }},
  status: {{ textContent: "", dataset: {{}} }},
  "config-banner": {{ textContent: "" }},
  "session-user": {{ textContent: "" }},
  "session-token": {{ textContent: "" }},
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
global.window = {{
  location: {{
    origin: "http://127.0.0.1:4174",
  }},
}};
global.fetch = async () => {{
  throw new Error("network unavailable");
}};
global.console = {{
  error() {{}},
}};
eval(source);
(async () => {{
  state.config = await loadConfig();
  state.config_banner = elements["config-banner"].textContent;
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
