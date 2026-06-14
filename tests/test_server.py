from __future__ import annotations

import json
import subprocess
import threading
from http.client import HTTPConnection
from pathlib import Path
from typing import Any

from truthkernel.canonical import canonical_text
from truthkernel.schemas import Decision, DecisionBundle
from truthkernel.server import ServerConfig, _is_authorized, create_http_server

ROOT = Path(__file__).resolve().parents[1]
RULEPACK = ROOT / "rulepacks" / "strict-default" / "rulepack.json"
MINIMAL_PACK = ROOT / "fixtures" / "golden" / "m1" / "minimal-supported.pack.json"


def test_http_sidecar_verify_query_and_snapshot(tmp_path: Path) -> None:
    server = create_http_server(
        ServerConfig(
            ledger_path=tmp_path / "ledger",
            rulepack_path=RULEPACK,
            host="127.0.0.1",
            port=0,
        )
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        verify = post_json(port, "/verify_pack", {"pack": load_json(MINIMAL_PACK)})
        assert verify["decision"] == Decision.ACCEPT
        assert verify["ledger_head_hash"] is not None
        assert DecisionBundle.model_validate(verify["decision_bundle"]).decision is Decision.ACCEPT

        query = post_json(port, "/query_facts", {"term": "ledger", "top_k": 5})
        assert query["facts"]
        assert query["facts"][0]["claim"]["id"] == "claim-alpha"

        snapshot = post_json(port, "/get_snapshot", {})
        assert snapshot["snapshot"]["head_hash"] == verify["ledger_head_hash"]

        repair = post_json(
            port,
            "/get_repair_contract",
            {
                "decision_bundle_id": verify["decision_bundle"]["id"],
                "findings": verify["findings"],
                "rulepack": load_json(RULEPACK),
            },
        )
        assert repair["repair_contract"]["decision_bundle_id"] == verify["decision_bundle"]["id"]
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_http_auth_rejects_non_loopback_without_token() -> None:
    assert not _is_authorized("8.8.8.8", None, None)
    assert _is_authorized("8.8.8.8", "Bearer secret", "secret")


def test_mcp_session_scripted_tools(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger"
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "truth",
            "serve",
            "mcp",
            str(ledger_path),
            str(RULEPACK),
        ],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    try:
        send_mcp(proc, {"id": 1, "method": "initialize", "params": {}})
        initialize = read_mcp(proc)
        assert initialize["result"]["serverInfo"]["name"] == "truth-ai"

        send_mcp(proc, {"id": 2, "method": "tools/list", "params": {}})
        tool_list = read_mcp(proc)
        assert {tool["name"] for tool in tool_list["result"]["tools"]} == {
            "verify_pack",
            "get_repair_contract",
            "query_facts",
            "get_snapshot",
        }

        send_mcp(
            proc,
            {
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "verify_pack",
                    "arguments": {"pack": load_json(MINIMAL_PACK), "persist": True},
                },
            },
        )
        verify = read_mcp(proc)
        verify_payload = json.loads(verify["result"]["content"][0]["text"])
        assert verify_payload["decision"] == Decision.ACCEPT

        send_mcp(
            proc,
            {
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "query_facts",
                    "arguments": {"term": "ledger", "top_k": 5},
                },
            },
        )
        query = read_mcp(proc)
        query_payload = json.loads(query["result"]["content"][0]["text"])
        assert query_payload["facts"][0]["claim"]["id"] == "claim-alpha"

        send_mcp(
            proc,
            {
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "get_snapshot",
                    "arguments": {},
                },
            },
        )
        snapshot = read_mcp(proc)
        snapshot_payload = json.loads(snapshot["result"]["content"][0]["text"])
        assert snapshot_payload["snapshot"]["facts"]
    finally:
        if proc.stdin is not None:
            proc.stdin.close()
        proc.terminate()
        proc.wait(timeout=10)


def post_json(port: int, path: str, payload: object) -> Any:
    connection = HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        body = canonical_text(payload).encode("utf-8")
        connection.request("POST", path, body=body, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        data = response.read().decode("utf-8")
        assert response.status == 200, data
        return json.loads(data)
    finally:
        connection.close()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def send_mcp(proc: subprocess.Popen[str], payload: object) -> None:
    assert proc.stdin is not None
    proc.stdin.write(canonical_text(payload) + "\n")
    proc.stdin.flush()


def read_mcp(proc: subprocess.Popen[str]) -> Any:
    assert proc.stdout is not None
    line = proc.stdout.readline()
    assert line
    return json.loads(line)
