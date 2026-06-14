"""HTTP sidecar and MCP-style server surfaces for Truth-AI."""

from __future__ import annotations

import ipaddress
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from truthkernel.canonical import canonical_text
from truthkernel.contract import build_repair_contract
from truthkernel.gate import build_decision_bundle, decide
from truthkernel.graph import build_graph
from truthkernel.ledger import LedgerFact, LedgerSnapshot, LedgerStore
from truthkernel.predicates.evaluate import evaluate_predicates
from truthkernel.schemas import (
    Decision,
    DecisionBundle,
    Finding,
    Pack,
    RepairContract,
    RulePack,
)
from truthkernel.schemas.models import StrictBaseModel

_DEFAULT_ASSERTED_AT = "1970-01-01T00:00:00Z"


class VerifyPackRequest(StrictBaseModel):
    pack: Pack
    rulepack: RulePack | None = None
    asserted_at: str = _DEFAULT_ASSERTED_AT
    persist: bool = True


class VerifyPackResponse(StrictBaseModel):
    decision: Decision
    graph_hash: str
    findings: tuple[Finding, ...]
    decision_bundle: DecisionBundle
    repair_contract: RepairContract | None = None
    ledger_head_hash: str | None = None


class RepairContractRequest(StrictBaseModel):
    decision_bundle_id: str
    findings: tuple[Finding, ...]
    rulepack: RulePack


class RepairContractResponse(StrictBaseModel):
    repair_contract: RepairContract


class QueryFactsRequest(StrictBaseModel):
    term: str
    top_k: int = 5
    head_hash: str | None = None


class QueryFactsResponse(StrictBaseModel):
    facts: tuple[LedgerFact, ...]


class SnapshotRequest(StrictBaseModel):
    head_hash: str | None = None


class SnapshotResponse(StrictBaseModel):
    snapshot: LedgerSnapshot


class ServerConfig(StrictBaseModel):
    ledger_path: Path
    rulepack_path: Path
    host: str = "127.0.0.1"
    port: int = 8000
    bearer_token: str | None = None


class TruthService:
    """Deterministic verification service backed by the explicit ledger path."""

    def __init__(self, config: ServerConfig):
        self.config = config
        self._default_rulepack = self._load_rulepack(config.rulepack_path)

    def verify_pack(self, request: VerifyPackRequest) -> VerifyPackResponse:
        rulepack = request.rulepack or self._default_rulepack
        graph_result = build_graph(request.pack)
        if graph_result.graph is None:
            raise ValueError("pack failed pre-graph validation")

        findings = evaluate_predicates(graph_result.graph, rulepack)
        graph_hash = str(graph_result.graph["graph_hash"])
        gate = decide(findings, rulepack, graph_hash=graph_hash)
        with LedgerStore(self.config.ledger_path) as ledger:
            ledger_root = ledger.head_hash
            bundle = build_decision_bundle(
                pack=request.pack,
                claim_graph_hash=graph_hash,
                evidence_snapshot_hashes=tuple(
                    evidence.snapshot_hash for evidence in request.pack.evidence
                ),
                ledger_root=ledger_root,
                rulepack=rulepack,
                findings=findings,
                decision=gate.decision,
                compiler_id="truth-server",
            )
            repair_contract = (
                None
                if gate.decision is Decision.ACCEPT
                else build_repair_contract(
                    decision_bundle_id=bundle.id,
                    findings=findings,
                    rulepack=rulepack,
                )
            )
            if request.persist and gate.decision is Decision.ACCEPT:
                ledger.append_decision_bundle(
                    bundle,
                    request.pack,
                    asserted_at=request.asserted_at,
                )
            ledger_head_hash = ledger.head_hash

        return VerifyPackResponse(
            decision=gate.decision,
            graph_hash=graph_hash,
            findings=findings,
            decision_bundle=bundle,
            repair_contract=repair_contract,
            ledger_head_hash=ledger_head_hash,
        )

    def get_repair_contract(self, request: RepairContractRequest) -> RepairContractResponse:
        return RepairContractResponse(
            repair_contract=build_repair_contract(
                decision_bundle_id=request.decision_bundle_id,
                findings=request.findings,
                rulepack=request.rulepack,
            )
        )

    def query_facts(self, request: QueryFactsRequest) -> QueryFactsResponse:
        with LedgerStore(self.config.ledger_path) as ledger:
            if request.head_hash is None:
                facts = ledger.query_facts(request.term, top_k=request.top_k)
            else:
                facts = _query_snapshot_facts(ledger.snapshot(request.head_hash), request)
        return QueryFactsResponse(facts=facts)

    def get_snapshot(self, request: SnapshotRequest) -> SnapshotResponse:
        with LedgerStore(self.config.ledger_path) as ledger:
            return SnapshotResponse(snapshot=ledger.snapshot(request.head_hash))

    @staticmethod
    def _load_rulepack(path: Path) -> RulePack:
        return RulePack.model_validate_json(path.read_text(encoding="utf-8"))


def _query_snapshot_facts(
    snapshot: LedgerSnapshot,
    request: QueryFactsRequest,
) -> tuple[LedgerFact, ...]:
    term = request.term.casefold()
    matched = tuple(
        fact
        for fact in snapshot.facts
        if term in fact.claim.text.casefold()
        or term in fact.claim.subject.casefold()
        or term in fact.claim.object.casefold()
        or term in fact.claim.id.casefold()
    )
    ordered = sorted(
        matched,
        key=lambda fact: (fact.entry.valid_from, fact.entry.entry_hash),
        reverse=True,
    )
    return tuple(ordered[: request.top_k])


def create_http_server(config: ServerConfig) -> ThreadingHTTPServer:
    service = TruthService(config)

    class _Handler(BaseHTTPRequestHandler):
        server_version = "TruthAIHTTP/0.1"

        def do_POST(self) -> None:  # noqa: N802
            if not _is_authorized(
                client_ip=self.client_address[0],
                authorization=self.headers.get("Authorization"),
                bearer_token=config.bearer_token,
            ):
                self._send_json({"error": "forbidden"}, HTTPStatus.FORBIDDEN)
                return

            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            try:
                response = self._dispatch(payload)
            except Exception as exc:  # pragma: no cover - surfaced in tests
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(response)

        def log_message(self, *_: object) -> None:
            return

        def _dispatch(self, payload: dict[str, Any]) -> object:
            path = self.path.rstrip("/")
            if path == "/verify_pack":
                return service.verify_pack(VerifyPackRequest.model_validate(payload))
            if path == "/get_repair_contract":
                return service.get_repair_contract(RepairContractRequest.model_validate(payload))
            if path == "/query_facts":
                return service.query_facts(QueryFactsRequest.model_validate(payload))
            if path == "/get_snapshot":
                return service.get_snapshot(SnapshotRequest.model_validate(payload))
            raise ValueError(f"unknown path: {self.path}")

        def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = canonical_text(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((config.host, config.port), _Handler)


def run_http_sidecar(config: ServerConfig) -> None:
    server = create_http_server(config)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def run_mcp_session(config: ServerConfig) -> None:
    service = TruthService(config)
    tools = _tools_payload()
    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        response = _dispatch_mcp(service, tools, request)
        print(canonical_text(response), flush=True)


def _dispatch_mcp(
    service: TruthService,
    tools: tuple[dict[str, object], ...],
    request: dict[str, Any],
) -> dict[str, object]:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "truth-ai", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
    if method == "tools/call":
        result = _call_tool(service, params)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": [{"type": "text", "text": canonical_text(result)}]},
        }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"unknown method: {method}"},
    }


def _call_tool(service: TruthService, params: dict[str, Any]) -> object:
    name = params.get("name")
    arguments = params.get("arguments", {})
    if name == "verify_pack":
        return service.verify_pack(VerifyPackRequest.model_validate(arguments))
    if name == "get_repair_contract":
        return service.get_repair_contract(RepairContractRequest.model_validate(arguments))
    if name == "query_facts":
        return service.query_facts(QueryFactsRequest.model_validate(arguments))
    if name == "get_snapshot":
        return service.get_snapshot(SnapshotRequest.model_validate(arguments))
    raise ValueError(f"unknown tool: {name}")


def _tools_payload() -> tuple[dict[str, object], ...]:
    return (
        {
            "name": "verify_pack",
            "description": "Verify a pack against the deterministic kernel and ledger.",
            "inputSchema": VerifyPackRequest.model_json_schema(),
        },
        {
            "name": "get_repair_contract",
            "description": "Build a repair contract from a bundle id and findings.",
            "inputSchema": RepairContractRequest.model_json_schema(),
        },
        {
            "name": "query_facts",
            "description": "Query accepted facts from the continuity ledger.",
            "inputSchema": QueryFactsRequest.model_json_schema(),
        },
        {
            "name": "get_snapshot",
            "description": "Return a pinned continuity snapshot.",
            "inputSchema": SnapshotRequest.model_json_schema(),
        },
    )


def _is_authorized(client_ip: str, authorization: str | None, bearer_token: str | None) -> bool:
    if _is_loopback(client_ip):
        return True
    if bearer_token is None:
        return False
    return authorization == f"Bearer {bearer_token}"


def _is_loopback(client_ip: str) -> bool:
    return ipaddress.ip_address(client_ip).is_loopback
