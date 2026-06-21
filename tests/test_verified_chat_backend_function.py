from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "api" / "verified-chat-backend.py"


def test_verified_chat_backend_run_and_latest_round_trip(tmp_path: Path) -> None:
    module = load_backend_module()

    run_payload = invoke_wsgi_app(
        module,
        method="POST",
        path_info="/api/verified-chat-backend",
        query_string="path=run",
        body={"prompt_text": "Summarise deterministic verification."},
        store_root=tmp_path,
    )

    assert run_payload["status"] == 200
    assert run_payload["json"]["decision"] == "accept"
    assert run_payload["json"]["cleaned_output"].startswith("Truth AI received the prompt")

    latest_payload = invoke_wsgi_app(
        module,
        method="GET",
        path_info="/api/verified-chat-backend",
        query_string="path=latest",
        store_root=tmp_path,
    )

    assert latest_payload["status"] == 200
    assert latest_payload["json"]["run_hash"] == run_payload["json"]["run_hash"]
    assert latest_payload["json"]["response_hash"] == run_payload["json"]["response_hash"]
    assert latest_payload["json"]["replay_hash"] == run_payload["json"]["replay_hash"]
    assert (
        latest_payload["json"]["decision_bundle_id"] == run_payload["json"]["decision_bundle"]["id"]
    )
    assert latest_payload["json"]["decision"] == "accept"


def test_verified_chat_backend_returns_not_found_for_missing_latest(tmp_path: Path) -> None:
    module = load_backend_module()

    payload = invoke_wsgi_app(
        module,
        method="GET",
        path_info="/api/verified-chat-backend",
        query_string="path=latest",
        store_root=tmp_path,
    )

    assert payload["status"] == 404
    assert payload["json"]["error"] == "no verified-chat run has been recorded"


def test_verified_chat_backend_rejects_unknown_action(tmp_path: Path) -> None:
    module = load_backend_module()

    payload = invoke_wsgi_app(
        module,
        method="GET",
        path_info="/api/verified-chat-backend",
        query_string="path=unexpected",
        store_root=tmp_path,
    )

    assert payload["status"] == 404
    assert payload["json"]["error"] == "unknown endpoint: unexpected"


def test_verified_chat_backend_forwards_authorization_token(tmp_path: Path) -> None:
    module = load_backend_module()
    captured: dict[str, str | None] = {}

    class FakeService:
        def run(
            self, payload: object, *, authorization_token: str | None = None
        ) -> dict[str, object]:
            captured["run_token"] = authorization_token
            return {
                "request_hash": "request-hash",
                "response_hash": "response-hash",
                "run_hash": "run-hash",
                "decision": "accept",
                "cleaned_output": "Verified response",
                "decision_bundle": {},
                "artefacts": {},
            }

        def latest(self, *, authorization_token: str | None = None) -> dict[str, object]:
            captured["latest_token"] = authorization_token
            return {
                "request_hash": "request-hash",
                "run_hash": "run-hash",
                "decision": "accept",
                "cleaned_output": "Verified response",
            }

    module._service = lambda: FakeService()

    run_payload = invoke_wsgi_app(
        module,
        method="POST",
        path_info="/api/verified-chat-backend",
        query_string="path=run",
        body={"prompt_text": "Summarise deterministic verification."},
        store_root=tmp_path,
        headers={"Authorization": "Bearer session-token-123"},
    )

    latest_payload = invoke_wsgi_app(
        module,
        method="GET",
        path_info="/api/verified-chat-backend",
        query_string="path=latest",
        store_root=tmp_path,
        headers={"Authorization": "Bearer session-token-123"},
    )

    assert run_payload["status"] == 200
    assert latest_payload["status"] == 200
    assert captured["run_token"] == "Bearer session-token-123"
    assert captured["latest_token"] == "Bearer session-token-123"


def load_backend_module() -> Any:
    spec = importlib.util.spec_from_file_location("verified_chat_backend", BACKEND_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load verified chat backend module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invoke_wsgi_app(
    module: Any,
    *,
    method: str,
    path_info: str,
    query_string: str,
    body: object | None = None,
    store_root: Path,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path_info,
        "QUERY_STRING": query_string,
        "CONTENT_LENGTH": "0",
        "wsgi.input": io.BytesIO(),
    }
    if headers:
        for key, value in headers.items():
            env[f"HTTP_{key.upper().replace('-', '_')}"] = value
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        env["CONTENT_LENGTH"] = str(len(raw))
        env["wsgi.input"] = io.BytesIO(raw)

    state: dict[str, Any] = {"status": None, "headers": None, "body": None}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        state["status"] = int(status.split()[0])
        state["headers"] = dict(headers)

    module._DEFAULT_STORE_ROOT = store_root
    result = module.app(env, start_response)
    state["body"] = b"".join(result).decode("utf-8")
    state["json"] = json.loads(state["body"]) if state["body"] else None
    return state
