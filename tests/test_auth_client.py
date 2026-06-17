from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "app" / "auth-client.js"


def test_auth_client_replaces_sign_in_with_session_controls() -> None:
    payload = invoke_auth_client(
        session={"access_token": "token-123", "user": {"email": "user@example.com"}},
    )

    assert payload["has_badge"] is True
    assert payload["button_text"] == "Sign out"
    assert payload["label_text"] == "user@example.com"
    assert payload["button_has_click"] is True


def invoke_auth_client(*, session: dict[str, object] | None) -> dict[str, object]:
    script = f"""
const fs = require("fs");
const source = fs.readFileSync({json.dumps(SCRIPT.as_posix())}, "utf8");
const state = {{
  replaced_to: null,
}};
const controls = {{
  innerHTML: "",
  children: [],
  appendChild(node) {{
    this.children.push(node);
  }},
  querySelector(selector) {{
    return null;
  }},
}};
global.document = {{
  readyState: "complete",
  querySelector(selector) {{
    if (selector === "[data-auth-controls]") return controls;
    return null;
  }},
  addEventListener() {{}},
  createElement(tag) {{
    return {{
      tagName: tag,
      style: {{}},
      textContent: "",
      children: [],
      innerHTML: "",
      appendChild(node) {{
        this.children.push(node);
      }},
      addEventListener(type, handler) {{
        this._handlers = this._handlers || {{}};
        this._handlers[type] = handler;
      }},
    }};
  }},
}};
global.location = {{
  pathname: "/app/overview",
  search: "?studio=1",
  hash: "#app",
  assign(url) {{
    state.replaced_to = url;
  }},
}};
global.localStorage = {{
  getItem(key) {{
    if (key !== "truthai.supabase.session") {{
      return null;
    }}
    return {json.dumps(json.dumps(session) if session is not None else None)};
  }},
  removeItem() {{}},
}};
global.console = {{
  error() {{}},
}};
eval(source);
state.has_badge = controls.children.length >= 2;
state.badge_text = controls.children[0]?.children?.[1]?.textContent || "";
state.button_text = controls.children[1]?.textContent || "";
state.label_text = controls.children[0]?.children?.[1]?.textContent || "";
state.button_has_click = Boolean(controls.children[1]?._handlers?.click);
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
