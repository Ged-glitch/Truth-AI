"""HTTP service for verified-chat model generation and kernel replay."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import typer
from pydantic import Field

from adapters.verified_chat.contracts import (
    ChatReference,
    ModelSelection,
    ModelSettings,
    ProviderKind,
    VerifiedChatRequest,
)
from adapters.verified_chat.extraction import extract_model_response_pack
from adapters.verified_chat.llm import LLMAdapterError, adapter_for_provider
from adapters.verified_chat.runner import (
    VerifiedChatArtifactPaths,
    VerifiedChatPipelineResult,
    build_and_persist_verified_chat_run,
)
from adapters.verified_chat.supabase import (
    SupabaseVerifiedChatStore,
    SupabaseVerifiedChatStoreConfig,
    SupabaseVerifiedChatStoreError,
    VerifiedChatArchiveRecord,
)
from truthkernel.canonical import canonical_text
from truthkernel.schemas import Decision, DecisionBundle, RulePack
from truthkernel.schemas.models import StrictBaseModel

_DEFAULT_STORE_ROOT = Path("adapters") / "verified-chat"
_DEFAULT_RULEPACK_PATH = Path("rulepacks") / "strict-default" / "rulepack.json"
_STORE_ROOT_OPTION = typer.Option(_DEFAULT_STORE_ROOT, "--store-root")
_RULEPACK_OPTION = typer.Option(_DEFAULT_RULEPACK_PATH, "--rulepack")
_HOST_OPTION = typer.Option("127.0.0.1", "--host")
_PORT_OPTION = typer.Option(8010, "--port", min=0)
_GEMINI_KEY_OPTION = typer.Option(None, "--gemini-api-key")


class VerifiedChatServiceConfig(StrictBaseModel):
    """Runtime configuration for the adapter-side verified-chat service."""

    store_root: Path = _DEFAULT_STORE_ROOT
    rulepack_path: Path = _DEFAULT_RULEPACK_PATH
    host: str = "127.0.0.1"
    port: int = 8010
    credential_values: dict[str, str] = Field(default_factory=dict)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_table_name: str = "verified_chat_runs"


class VerifiedChatRunRequest(StrictBaseModel):
    """User-facing input payload for a verified-chat run."""

    prompt_text: str
    provider: ProviderKind = ProviderKind.LOCAL
    model_id: str = "truth-ai-local-adapter"
    credential_ref: str | None = None
    credential_value: str | None = None
    endpoint_url: str | None = None
    settings: ModelSettings = Field(default_factory=ModelSettings)
    references: tuple[ChatReference, ...] = ()
    uploaded_file_hashes: tuple[str, ...] = ()


class VerifiedChatRunResponse(StrictBaseModel):
    """Response returned to the app after generation and verification."""

    request_hash: str
    response_hash: str
    run_hash: str
    decision: Decision
    cleaned_output: str
    decision_bundle: DecisionBundle
    artefacts: dict[str, str]


class VerifiedChatLatestResponse(StrictBaseModel):
    """Latest successful adapter run recorded under the store root."""

    request_hash: str
    run_hash: str
    decision: Decision
    cleaned_output: str


class VerifiedChatService:
    """Adapter-side orchestration that keeps live model calls outside the kernel."""

    def __init__(self, config: VerifiedChatServiceConfig):
        self.config = config
        self._rulepack = RulePack.model_validate_json(
            config.rulepack_path.read_text(encoding="utf-8")
        )
        self._supabase_store = SupabaseVerifiedChatStore(
            SupabaseVerifiedChatStoreConfig(
                supabase_url=config.supabase_url,
                supabase_anon_key=config.supabase_anon_key,
                table_name=config.supabase_table_name,
            )
        )

    def run(
        self,
        payload: VerifiedChatRunRequest,
        *,
        authorization_token: str | None = None,
    ) -> VerifiedChatRunResponse:
        request = VerifiedChatRequest(
            prompt_text=payload.prompt_text,
            rulepack_id=self._rulepack.id,
            selection=ModelSelection(
                provider=payload.provider,
                model_id=payload.model_id,
                credential_ref=payload.credential_ref,
                endpoint_url=payload.endpoint_url,
                settings=payload.settings,
            ),
            references=payload.references,
            uploaded_file_hashes=payload.uploaded_file_hashes,
        )
        adapter = adapter_for_provider(payload.provider)
        model_response = adapter.generate(
            request,
            credential_value=self._credential_value(payload),
        )
        extracted_pack_bundle = extract_model_response_pack(
            request=request,
            model_response=model_response,
        )
        pipeline = build_and_persist_verified_chat_run(
            root=self.config.store_root,
            request=request,
            model_response=model_response,
            extracted_pack_bundle=extracted_pack_bundle,
            cleaned_output=model_response.raw_text,
            rulepack=self._rulepack,
        )
        response = _response_from_pipeline(pipeline)
        self._write_latest(response)
        if authorization_token:
            self._supabase_store.save(pipeline.run, authorization_token)
        return response

    def latest(self, *, authorization_token: str | None = None) -> VerifiedChatLatestResponse:
        if authorization_token:
            record = self._supabase_store.latest_record(authorization_token)
            if record is not None:
                return _response_from_archive_record(record)
        latest_path = self._latest_path()
        if not latest_path.exists():
            raise ValueError("no verified-chat run has been recorded")
        return VerifiedChatLatestResponse.model_validate_json(
            latest_path.read_text(encoding="utf-8")
        )

    def _credential_value(self, payload: VerifiedChatRunRequest) -> str | None:
        if payload.credential_value:
            return payload.credential_value
        if payload.credential_ref and payload.credential_ref in self.config.credential_values:
            return self.config.credential_values[payload.credential_ref]
        provider_key = payload.provider.value
        if provider_key in self.config.credential_values:
            return self.config.credential_values[provider_key]
        return self.config.credential_values.get("default")

    def _write_latest(self, response: VerifiedChatRunResponse) -> None:
        self.config.store_root.mkdir(parents=True, exist_ok=True)
        latest = VerifiedChatLatestResponse(
            request_hash=response.request_hash,
            run_hash=response.run_hash,
            decision=response.decision,
            cleaned_output=response.cleaned_output,
        )
        self._latest_path().write_text(canonical_text(latest) + "\n", encoding="utf-8")

    def _latest_path(self) -> Path:
        return self.config.store_root / "latest.json"


def create_verified_chat_http_server(config: VerifiedChatServiceConfig) -> ThreadingHTTPServer:
    """Create the adapter HTTP server for app-facing verified chat."""
    service = VerifiedChatService(config)

    class _Handler(BaseHTTPRequestHandler):
        server_version = "TruthAIVerifiedChatHTTP/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send_json({}, HTTPStatus.NO_CONTENT)

        def do_GET(self) -> None:  # noqa: N802
            try:
                if self.path.rstrip("/") == "/verified-chat/latest":
                    self._send_json(service.latest(authorization_token=self._authorization_token()))
                    return
                raise ValueError(f"unknown path: {self.path}")
            except SupabaseVerifiedChatStoreError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
            except Exception as exc:  # pragma: no cover - surfaced by clients
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            try:
                if self.path.rstrip("/") != "/verified-chat/run":
                    raise ValueError(f"unknown path: {self.path}")
                response = service.run(
                    VerifiedChatRunRequest.model_validate(payload),
                    authorization_token=self._authorization_token(),
                )
            except SupabaseVerifiedChatStoreError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
                return
            except (LLMAdapterError, ValueError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(response)

        def log_message(self, *_: object) -> None:
            return

        def _authorization_token(self) -> str | None:
            value = self.headers.get("Authorization") or self.headers.get("authorization")
            return value if value else None

        def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = canonical_text(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((config.host, config.port), _Handler)


def run_verified_chat_http_service(config: VerifiedChatServiceConfig) -> None:
    """Run the adapter HTTP service until interrupted."""
    server = create_verified_chat_http_server(config)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main() -> None:
    """Run the adapter service CLI."""
    typer.run(_serve)


def _serve(
    store_root: Path = _STORE_ROOT_OPTION,
    rulepack_path: Path = _RULEPACK_OPTION,
    host: str = _HOST_OPTION,
    port: int = _PORT_OPTION,
    gemini_api_key: str | None = _GEMINI_KEY_OPTION,
) -> None:
    credential_values = {"gemini": gemini_api_key} if gemini_api_key else {}
    run_verified_chat_http_service(
        VerifiedChatServiceConfig(
            store_root=store_root,
            rulepack_path=rulepack_path,
            host=host,
            port=port,
            credential_values=credential_values,
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
        )
    )


def _response_from_pipeline(pipeline: VerifiedChatPipelineResult) -> VerifiedChatRunResponse:
    return VerifiedChatRunResponse(
        request_hash=pipeline.run.request_hash,
        response_hash=pipeline.run.model_response.response_hash,
        run_hash=pipeline.run.run_hash,
        decision=pipeline.run.replay_inputs.decision_bundle.decision,
        cleaned_output=pipeline.run.cleaned_output,
        decision_bundle=pipeline.run.replay_inputs.decision_bundle,
        artefacts=_artefact_paths(pipeline.paths),
    )


def _artefact_paths(paths: VerifiedChatArtifactPaths) -> dict[str, str]:
    return {
        "cleaned_output": str(paths.cleaned_output_path),
        "extracted_pack": str(paths.extracted_pack_path),
        "request": str(paths.request_path),
        "response": str(paths.response_path),
        "run": str(paths.run_path),
    }


def _response_from_archive_record(record: VerifiedChatArchiveRecord) -> VerifiedChatLatestResponse:
    return VerifiedChatLatestResponse(
        request_hash=record.request_hash,
        run_hash=record.run_hash,
        decision=record.decision,
        cleaned_output=record.cleaned_output,
    )
