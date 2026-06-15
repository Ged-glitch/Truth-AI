"""Python backend for the verified-chat adapter service.

This lives outside the deterministic kernel and serves the same adapter
behaviour through a Vercel Python function.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from adapters.verified_chat.llm import LLMAdapterError
from adapters.verified_chat.service import (
    VerifiedChatRunRequest,
    VerifiedChatService,
    VerifiedChatServiceConfig,
)
from truthkernel.canonical import canonical_text

_DEFAULT_RULEPACK_PATH = (
    Path(__file__).resolve().parents[1] / "rulepacks" / "strict-default" / "rulepack.json"
)
_DEFAULT_STORE_ROOT = Path("/tmp") / "truth-ai-verified-chat"


def app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
    """WSGI entrypoint for the verified-chat backend function."""
    method = str(environ.get("REQUEST_METHOD", "GET")).upper()
    query = parse_qs(str(environ.get("QUERY_STRING", "")))
    action = _resolve_action(query, str(environ.get("PATH_INFO", "")))

    if method == "OPTIONS":
        return _json_response(start_response, HTTPStatus.NO_CONTENT, {})

    service = _service()
    if method == "GET" and action == "latest":
        try:
            payload = service.latest()
        except ValueError as exc:
            return _json_response(start_response, HTTPStatus.NOT_FOUND, {"error": str(exc)})
        return _json_response(start_response, HTTPStatus.OK, payload)

    if method == "POST" and action == "run":
        try:
            length = int(str(environ.get("CONTENT_LENGTH", "0")))
        except ValueError:
            length = 0
        body = environ.get("wsgi.input")
        raw = body.read(length).decode("utf-8") if length and body is not None else "{}"
        try:
            payload = json.loads(raw) if raw else {}
            response = service.run(VerifiedChatRunRequest.model_validate(payload))
        except (LLMAdapterError, ValueError) as exc:
            return _json_response(start_response, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        return _json_response(start_response, HTTPStatus.OK, response)

    return _json_response(
        start_response,
        HTTPStatus.NOT_FOUND,
        {"error": f"unknown endpoint: {action}"},
    )


def _service() -> VerifiedChatService:
    return VerifiedChatService(
        VerifiedChatServiceConfig(
            store_root=_DEFAULT_STORE_ROOT,
            rulepack_path=_DEFAULT_RULEPACK_PATH,
        )
    )


def _resolve_action(query: dict[str, list[str]], path_info: str) -> str:
    if "path" in query and query["path"]:
        return query["path"][0]
    cleaned = path_info.strip("/")
    return cleaned or "latest"


def _json_response(
    start_response: Any,
    status: HTTPStatus,
    payload: object,
) -> list[bytes]:
    body = canonical_text(payload).encode("utf-8")
    start_response(
        f"{status.value} {status.phrase}",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
        ],
    )
    return [body]
