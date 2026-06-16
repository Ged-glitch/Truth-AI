from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE_LOADER = ROOT / "app" / "route-loader.js"


def test_route_loader_redirects_unauthed_app_routes_to_sign_in() -> None:
    payload = invoke_route_loader(
        pathname="/app/overview",
        search="?studio=123",
        hash="#app",
        session=None,
    )

    assert (
        payload["replaced_to"]
        == "http://localhost/app/sign-in?return=%2Fapp%2Foverview%3Fstudio%3D123%23app"
    )
    assert payload["fetched_source"] is None


def test_route_loader_allows_authed_app_routes() -> None:
    payload = invoke_route_loader(
        pathname="/app/overview",
        search="",
        hash="",
        session={"access_token": "token-123"},
    )

    assert payload["replaced_to"] is None
    assert payload["fetched_source"] == "/frontend/Truth-AI-App.dc.html"


def invoke_route_loader(
    *,
    pathname: str,
    search: str,
    hash: str,
    session: dict[str, str] | None,
) -> dict[str, object]:
    script = f"""
const fs = require("fs");
const source = fs.readFileSync({json.dumps(ROUTE_LOADER.as_posix())}, "utf8");
const state = {{
  fetched_source: null,
  replaced_to: null,
}};
global.location = {{
  origin: "http://localhost",
  pathname: {json.dumps(pathname)},
  search: {json.dumps(search)},
  hash: {json.dumps(hash)},
  replace(url) {{
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
}};
global.document = {{
  body: {{
    innerHTML: "",
  }},
  open() {{
    state.opened = true;
  }},
  write(html) {{
    state.written = html;
  }},
  close() {{
    state.closed = true;
  }},
}};
global.fetch = async (url) => {{
  state.fetched_source = url;
  return {{
    ok: true,
    text: async () => "<script src=\\\"./support.js\\\"></script>",
  }};
}};
global.console = {{
  error() {{}},
}};
eval(source);
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
