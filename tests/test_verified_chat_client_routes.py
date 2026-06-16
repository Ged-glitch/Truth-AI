from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "app" / "verified-chat-client.js"


def test_verified_chat_composer_mounts_on_assistant_route() -> None:
    payload = invoke_client("/app/assistant")

    assert payload["mounted"] is True
    assert payload["panel_text"] == "Adapter ready at /api/verified-chat"


def test_verified_chat_output_mounts_on_truth_output_route() -> None:
    payload = invoke_output_client("/app/truth-output")

    assert payload["mounted"] is True
    assert payload["panel_text"] == "Loading latest verified output..."


def invoke_client(pathname: str) -> dict[str, object]:
    script = f"""
const fs = require("fs");
const source = fs.readFileSync({json.dumps(CLIENT.as_posix())}, "utf8");
const state = {{}};
const mountedKey = "data-verified-chat-form";
const statusKey = "data-verified-chat-status";
function hasMountedShell() {{
  return state.shell_attrs && state.shell_attrs[mountedKey] !== undefined;
}}
function hasStatusPanel() {{
  return Boolean(state.panel);
}}
const panel = {{
  setAttribute(name, value) {{
    state.panel_attrs = state.panel_attrs || {{}};
    state.panel_attrs[name] = value;
  }},
  style: {{}},
  textContent: "",
  innerHTML: "",
}};
const shell = {{
  setAttribute(name, value) {{
    state.shell_attrs = state.shell_attrs || {{}};
    state.shell_attrs[name] = value;
  }},
  parentElement: {{
    appendChild(node) {{
      state.mounted = true;
      state.panel_text = node.textContent;
      state.panel = node;
    }},
  }},
  querySelector() {{
    return {{
      value: "Ask anything",
    }};
  }},
  innerHTML: "",
}};
const placeholder = {{
  textContent: "Ask anything",
  parentElement: shell,
}};
global.window = {{
  location: {{
    pathname: {json.dumps(pathname)},
    localStorage: null,
  }},
  localStorage: {{
    getItem() {{
      return null;
    }},
    setItem() {{}},
    removeItem() {{}},
  }},
}};
global.document = {{
  querySelectorAll(selector) {{
    if (selector === "span") return [placeholder];
    if (selector === "[" + mountedKey + "]" && hasMountedShell()) {{
      return [shell];
    }}
    if (selector === "[" + statusKey + "]" && hasStatusPanel()) {{
      return [state.panel];
    }}
    return [];
  }},
  querySelector(selector) {{
    if (selector === "[" + mountedKey + "]" && hasMountedShell()) {{
      return shell;
    }}
    if (selector === "[" + statusKey + "]" && hasStatusPanel()) {{
      return state.panel;
    }}
    return null;
  }},
  addEventListener() {{}},
  createElement() {{
    return panel;
  }},
}};
global.localStorage = window.localStorage;
global.setInterval = (fn) => {{
  state.interval = fn;
  return 1;
}};
global.clearInterval = () => {{}};
global.console = {{
  error() {{}},
}};
eval(source);
state.interval();
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


def invoke_output_client(pathname: str) -> dict[str, object]:
    script = f"""
const fs = require("fs");
const source = fs.readFileSync({json.dumps(CLIENT.as_posix())}, "utf8");
const state = {{}};
const frame = {{
  prepend(node) {{
    state.mounted = true;
    state.panel_text = node.textContent;
    state.panel = node;
  }},
}};
const screen = {{
  querySelector(selector) {{
    if (selector === ".ta-frame") return frame;
    return null;
  }},
}};
global.window = {{
  location: {{
    pathname: {json.dumps(pathname)},
  }},
  localStorage: {{
    getItem() {{
      return null;
    }},
    setItem() {{}},
    removeItem() {{}},
  }},
}};
global.document = {{
  querySelectorAll(selector) {{
    if (selector === "[data-verified-output-screen]") return [screen];
    return [];
  }},
  querySelector(selector) {{
    if (selector === "[data-verified-output-screen]") return screen;
    if (selector === "[data-live-output-panel]" && state.panel) return state.panel;
    return null;
  }},
  addEventListener() {{}},
  createElement() {{
    return {{
      setAttribute() {{}},
      style: {{}},
      textContent: "",
      innerHTML: "",
    }};
  }},
}};
global.localStorage = window.localStorage;
global.setInterval = (fn) => {{
  state.interval = fn;
  return 1;
}};
global.clearInterval = () => {{}};
global.console = {{
  error() {{}},
}};
eval(source);
state.interval();
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
