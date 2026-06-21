from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from pathlib import Path

from adapters.extract import ExtractedPackBundle, ExtractionRequest
from adapters.verified_chat import (
    ChatReference,
    ModelResponse,
    ModelSelection,
    ModelSettings,
    ProviderKind,
    ReferenceKind,
    VerifiedChatRequest,
    VerifiedChatRunRequest,
    VerifiedChatService,
    VerifiedChatServiceConfig,
    build_verified_chat_run,
    create_verified_chat_http_server,
)
from adapters.verified_chat.supabase import (
    SupabaseVerifiedChatStore,
    SupabaseVerifiedChatStoreConfig,
    VerifiedChatArchiveRecord,
)
from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.schemas import (
    Claim,
    ClaimType,
    Decision,
    Entity,
    Evidence,
    EvidenceKind,
    Pack,
    Provenance,
    RulePack,
    TruthClass,
)

_RULEPACK_PATH = (
    Path(__file__).resolve().parents[1] / "rulepacks" / "strict-default" / "rulepack.json"
)


def test_verified_chat_service_runs_model_adapter_and_persists_outputs(tmp_path: Path) -> None:
    service = VerifiedChatService(
        VerifiedChatServiceConfig(store_root=tmp_path, rulepack_path=_RULEPACK_PATH)
    )

    response = service.run(
        VerifiedChatRunRequest(
            prompt_text="Explain why frozen replay artefacts matter.",
            provider=ProviderKind.LOCAL,
            model_id="truth-ai-local-adapter",
            credential_ref="local-secret",
            credential_value="do-not-persist",
        )
    )

    assert response.decision is Decision.ACCEPT
    assert "frozen" in response.cleaned_output
    assert response.artefacts["run"].endswith(f"{response.request_hash}.json")
    assert Path(response.artefacts["request"]).exists()
    assert Path(response.artefacts["response"]).exists()
    assert Path(response.artefacts["extracted_pack"]).exists()
    assert Path(response.artefacts["cleaned_output"]).exists()
    assert service.latest().run_hash == response.run_hash

    request_payload = Path(response.artefacts["request"]).read_text(encoding="utf-8")
    run_payload = Path(response.artefacts["run"]).read_text(encoding="utf-8")
    assert "do-not-persist" not in request_payload
    assert "do-not-persist" not in run_payload
    assert "local-secret" in request_payload


def test_verified_chat_http_server_accepts_prompt_and_returns_latest(tmp_path: Path) -> None:
    server = create_verified_chat_http_server(
        VerifiedChatServiceConfig(
            store_root=tmp_path,
            rulepack_path=_RULEPACK_PATH,
            host="127.0.0.1",
            port=0,
        )
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        payload = json.dumps(
            {
                "prompt_text": "Summarise deterministic verification.",
                "provider": "local",
                "model_id": "truth-ai-local-adapter",
            }
        )
        connection = HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(
            "POST",
            "/verified-chat/run",
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["decision"] == "accept"
        assert body["cleaned_output"].startswith("Truth AI received the prompt")

        connection.request("GET", "/verified-chat/latest")
        latest_response = connection.getresponse()
        latest_body = json.loads(latest_response.read().decode("utf-8"))
        assert latest_response.status == 200
        assert latest_body["run_hash"] == body["run_hash"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_verified_chat_supabase_store_mirrors_runs_and_reads_latest() -> None:
    run = sample_verified_chat_run()
    calls: list[dict[str, object]] = []

    def request_json(
        url: str,
        method: str,
        headers: dict[str, str],
        body: object | None,
    ) -> object:
        calls.append(
            {
                "url": url,
                "method": method,
                "headers": headers,
                "body": body,
            }
        )
        if method == "GET":
            return [
                {
                    "request_hash": run.request_hash,
                    "run_hash": run.run_hash,
                    "decision": run.replay_inputs.decision_bundle.decision.value,
                    "cleaned_output": run.cleaned_output,
                    "run_json": canonical_text(run),
                }
            ]
        return {}

    store = SupabaseVerifiedChatStore(
        SupabaseVerifiedChatStoreConfig(
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon-key",
        ),
        request_json=request_json,
    )

    store.save(run, authorization_token="Bearer session-token")
    record = store.latest_record("Bearer session-token")

    assert isinstance(record, VerifiedChatArchiveRecord)
    assert record.request_hash == run.request_hash
    assert record.run_hash == run.run_hash
    assert record.decision is run.replay_inputs.decision_bundle.decision
    assert record.cleaned_output == run.cleaned_output
    assert calls[0]["method"] == "POST"
    assert calls[0]["headers"]["Authorization"] == "Bearer session-token"
    assert calls[0]["body"][0]["run_json"] == canonical_text(run)
    assert calls[1]["method"] == "GET"
    assert (
        "select=request_hash%2Crun_hash%2Cdecision%2Ccleaned_output%2Crun_json" in calls[1]["url"]
    )


def sample_verified_chat_run():
    claim = Claim(
        id="claim-verified-chat",
        text="The system uses a frozen replay bundle.",
        subject="system",
        relation="uses",
        object="frozen replay bundle",
        claim_type=ClaimType.FACTUAL,
        gate_relevant=True,
        provenance=Provenance(model_id="unit-test"),
    )
    evidence = Evidence(
        id="evidence-verified-chat",
        kind=EvidenceKind.TOOL_OUTPUT,
        text="Replay input was frozen before kernel evaluation.",
        snapshot_hash="snapshot-verified-chat",
        provenance=Provenance(model_id="unit-test"),
    )
    entity = Entity(
        id="entity-verified-chat",
        kind="session",
        label="Verified chat session",
    )
    pack = Pack(
        id="pack-verified-chat",
        version="0.1",
        claims=(claim,),
        evidence=(evidence,),
        entities=(entity,),
    )
    rulepack = RulePack(
        id="rulepack-verified-chat",
        name="verified-chat",
        version="0.1",
        policy_hash="policy-verified-chat",
        taxonomy_hash="taxonomy-verified-chat",
        gate_relevant_claim_types=(ClaimType.FACTUAL,),
        critical_truth_classes=(TruthClass.TC_01,),
        qualified_source_kinds=(EvidenceKind.TOOL_OUTPUT,),
        gate_ceilings={TruthClass.TC_01: 0},
        verifier_weights={},
        retrieval_permissions={},
    )
    request = VerifiedChatRequest(
        prompt_text="Verify this technical claim against the supplied sources.",
        rulepack_id=rulepack.id,
        selection=ModelSelection(
            provider=ProviderKind.GEMINI,
            model_id="gemini-2.0-flash",
            credential_ref="vault://gemini/user-key",
            endpoint_url=None,
            settings=ModelSettings(max_output_tokens=1024),
        ),
        references=(
            ChatReference(
                kind=ReferenceKind.UPLOAD,
                source_uri="file://technical-spec.pdf",
                content_hash="upload-technical-spec",
                label="Technical spec",
            ),
            ChatReference(
                kind=ReferenceKind.RULEPACK,
                source_uri="rulepack://verified-chat",
                content_hash=rulepack.policy_hash,
                label="Strict policy pack",
            ),
        ),
        uploaded_file_hashes=("upload-technical-spec",),
    )
    model_response = ModelResponse(
        request_hash=sha256_of(request),
        raw_text="The system uses a frozen replay bundle.",
        response_hash="response-verified-chat",
        content_type="text/plain",
    )
    extracted_pack_bundle = ExtractedPackBundle(
        request=ExtractionRequest(
            prompt_text=request.prompt_text,
            model_id=request.selection.model_id,
            settings_hash=sha256_of(request.selection.settings),
            source_uri="file://technical-spec.pdf",
        ),
        raw_model_output=model_response.raw_text,
        pack=pack,
    )
    return build_verified_chat_run(
        request=request,
        model_response=model_response,
        extracted_pack_bundle=extracted_pack_bundle,
        cleaned_output="The system uses a frozen replay bundle.",
        rulepack=rulepack,
    )
