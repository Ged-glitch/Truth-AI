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


def test_verified_chat_defaults_to_local_adapter_on_localhost_preview() -> None:
    payload = invoke_client(
        "/app/assistant",
        host="127.0.0.1:4174",
        hostname="127.0.0.1",
    )

    assert payload["mounted"] is True
    assert payload["panel_text"] == "Adapter ready at http://127.0.0.1:8010"


def test_verified_chat_output_mounts_on_truth_output_route() -> None:
    payload = invoke_output_client("/app/truth-output")

    assert payload["mounted"] is True
    assert payload["panel_text"] == "Loading latest verified output..."


def test_verified_chat_submit_uses_session_authorization_and_scoped_storage() -> None:
    payload = invoke_submit_client("/app/assistant")

    assert payload["mounted"] is True
    assert payload["upstream_init"]["headers"]["Authorization"] == "Bearer token-123"
    assert payload["storage_key"] == "truthAiVerifiedChatLatest:user_example.com"
    assert payload["secret_key"] == "truthAiVerifiedChatSecret:user_example.com"
    assert payload["secret_writes"][0]["value"] == "legacy-local-key"
    assert payload["settings_value"] == (
        '{"provider":"local","modelId":"truth-ai-local-adapter",'
        '"endpointUrl":"/api/verified-chat","remember":true,"rememberKey":true}'
    )


def invoke_client(
    pathname: str,
    *,
    host: str | None = None,
    hostname: str | None = None,
    port: str | None = None,
) -> dict[str, object]:
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
    host: {json.dumps(host)},
    hostname: {json.dumps(hostname)},
    port: {json.dumps(port)},
    localStorage: null,
  }},
  localStorage: {{
    getItem() {{
      return null;
    }},
    setItem() {{}},
    removeItem() {{}},
  }},
  sessionStorage: {{
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
        encoding="utf-8",
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
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def invoke_submit_client(pathname: str) -> dict[str, object]:
    script = f"""
const fs = require("fs");
const source = fs.readFileSync({json.dumps(CLIENT.as_posix())}, "utf8");
const state = {{}};
const panel = {{
  innerHTML: "",
  textContent: "",
  setAttribute() {{}},
}};
const submit = {{
  disabled: false,
  style: {{}},
  closest(selector) {{
    if (selector === "[data-verified-chat-form]") return shell;
    return null;
  }},
}};
const input = {{ value: "Verify the prompt." }};
const provider = {{ value: "local" }};
const model = {{ value: "truth-ai-local-adapter" }};
const key = {{ value: "session-token-123" }};
const endpoint = {{ value: "" }};
const remember = {{ checked: true }};
const rememberKey = {{ checked: true }};
const shell = {{
  attrs: {{}},
  innerHTML: "",
  setAttribute(name, value) {{
    this.attrs[name] = value;
    state.mounted = true;
  }},
  parentElement: {{
    appendChild(node) {{
      state.panel = node;
      state.panel_text = node.textContent;
    }},
  }},
  querySelector(selector) {{
    if (selector === "[data-verified-chat-input]") return input;
    if (selector === "[data-verified-chat-submit]") return submit;
    if (selector === "[data-verified-chat-provider]") return provider;
    if (selector === "[data-verified-chat-model]") return model;
    if (selector === "[data-verified-chat-key]") return key;
    if (selector === "[data-verified-chat-endpoint]") return endpoint;
    if (selector === "[data-verified-chat-remember]") return remember;
    if (selector === "[data-verified-chat-remember-key]") return rememberKey;
    return null;
  }},
}};
const placeholder = {{
  textContent: "Ask anything",
  parentElement: shell,
}};
global.window = {{
  location: {{
    pathname: {json.dumps(pathname)},
  }},
  localStorage: {{
    getItem(key) {{
      if (key === "truthai.supabase.session") {{
        return JSON.stringify({{
          access_token: "token-123",
          user: {{ email: "user@example.com" }},
        }});
      }}
      if (key === "truthAiVerifiedChatSettings:user_example.com") {{
        return JSON.stringify({{
          provider: "local",
          modelId: "truth-ai-local-adapter",
          endpointUrl: "",
          remember: true,
          rememberKey: true,
          apiKey: "legacy-local-key",
        }});
      }}
      return null;
    }},
    setItem(key, value) {{
      if (key.startsWith("truthAiVerifiedChatSettings:")) {{
        state.settings_key = key;
        state.settings_value = value;
      }}
      if (key.startsWith("truthAiVerifiedChatLatest:")) {{
        state.storage_key = key;
      }}
      state.storage_value = value;
    }},
    removeItem() {{}},
  }},
    sessionStorage: {{
      getItem(key) {{
        if (key === "truthAiVerifiedChatSecret:user_example.com") {{
          return "session-token-123";
        }}
        return null;
      }},
      setItem(key, value) {{
        if (key.startsWith("truthAiVerifiedChatSecret:")) {{
          state.secret_key = key;
          state.secret_value = value;
          state.secret_writes = state.secret_writes || [];
          state.secret_writes.push({{ key, value }});
        }}
      }},
    removeItem(key) {{
      if (key.startsWith("truthAiVerifiedChatSecret:")) {{
        state.secret_removed = key;
      }}
    }},
  }},
}};
global.location = global.window.location;
global.document = {{
  querySelectorAll(selector) {{
    if (selector === "span") return [placeholder];
    if (selector === "[data-verified-chat-form]" && state.mounted) return [shell];
    if (selector === "[data-verified-chat-status]" && state.panel) return [state.panel];
    return [];
  }},
  querySelector(selector) {{
    if (selector === "[data-verified-chat-form]" && state.mounted) return shell;
    if (selector === "[data-verified-chat-status]" && state.panel) return state.panel;
    return null;
  }},
  addEventListener(type, handler) {{
    state.handlers = state.handlers || {{}};
    state.handlers[type] = state.handlers[type] || [];
    state.handlers[type].push(handler);
  }},
  createElement() {{
    return {{
      setAttribute() {{}},
      style: {{}},
      textContent: "",
      innerHTML: "",
      appendChild() {{}},
    }};
  }},
}};
global.setInterval = (fn) => {{
  state.interval = fn;
  return 1;
}};
global.clearInterval = () => {{}};
global.fetch = async (url, init) => {{
  state.upstream_url = url;
  state.upstream_init = init;
  return {{
    ok: true,
    json: async () => ({{
      cleaned_output: "Verified response",
      decision: "accept",
      run_hash: "run-1234567890abcdef",
    }}),
  }};
}};
global.console = {{
  error() {{}},
}};
eval(source);
state.interval();
(async () => {{
  if (state.handlers.click[1]) {{
    state.handlers.click[1]({{
      target: {{
        closest(selector) {{
          if (selector === "[data-verified-chat-save]") return {{
            closest(innerSelector) {{
              if (innerSelector === "[data-verified-chat-form]") return shell;
              return null;
            }},
          }};
          return null;
        }},
      }},
    }});
  }}
  const maybePromise = state.handlers.click[0]({{
    target: {{
      closest(selector) {{
        if (selector === "[data-verified-chat-submit]") return submit;
        return null;
      }},
    }},
  }});
  if (maybePromise && typeof maybePromise.then === "function") {{
    await maybePromise;
  }}
  await Promise.resolve();
  process.stdout.write(JSON.stringify(state));
}})();
"""
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)
