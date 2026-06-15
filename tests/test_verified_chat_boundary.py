from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

from adapters.extract import ExtractedPackBundle, ExtractionRequest
from adapters.verified_chat import (
    ChatReference,
    FrozenReplayInputs,
    ModelResponse,
    ModelSelection,
    ModelSettings,
    ProviderKind,
    ReferenceKind,
    VerifiedChatRequest,
    VerifiedChatRun,
    load_verified_chat_cleaned_output,
    load_verified_chat_extracted_pack,
    load_verified_chat_request,
    load_verified_chat_response,
    load_verified_chat_run_at_root,
    save_verified_chat_cleaned_output,
    save_verified_chat_extracted_pack,
    save_verified_chat_request,
    save_verified_chat_response,
    save_verified_chat_run_at_root,
    verified_chat_cleaned_output_path,
    verified_chat_extracted_pack_path,
    verified_chat_request_path,
    verified_chat_response_path,
)
from adapters.verified_chat.replay import kernel_replay_inputs, load_verified_chat_run
from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.schemas import (
    Claim,
    ClaimType,
    Decision,
    DecisionBundle,
    Entity,
    Evidence,
    EvidenceKind,
    Finding,
    Pack,
    Provenance,
    RemedyType,
    RulePack,
    Severity,
    TruthClass,
)


def test_verified_chat_run_round_trips_through_canonical_json(tmp_path: Path) -> None:
    run = sample_verified_chat_run()
    path = save_verified_chat_run_at_root(tmp_path, run)

    assert path.name == f"{run.request.request_hash}.json"

    loaded = load_verified_chat_run(path)
    loaded_from_root = load_verified_chat_run_at_root(tmp_path, run.request)

    assert loaded == run
    assert loaded_from_root == run
    assert canonical_text(loaded) == canonical_text(run)
    assert kernel_replay_inputs(loaded) == run.replay_inputs
    assert run.request.request_hash == sha256_of(run.request)
    assert run.extracted_pack_hash == sha256_of(run.extracted_pack_bundle)


def test_verified_chat_storage_helpers_round_trip(tmp_path: Path) -> None:
    run = sample_verified_chat_run()

    request_path = verified_chat_request_path(tmp_path, run.request)
    response_path = verified_chat_response_path(tmp_path, run.request)
    extracted_pack_path = verified_chat_extracted_pack_path(tmp_path, run.request)
    cleaned_output_path = verified_chat_cleaned_output_path(tmp_path, run.request)

    save_verified_chat_request(run.request, request_path)
    save_verified_chat_response(run.model_response, response_path)
    save_verified_chat_extracted_pack(run.extracted_pack_bundle, extracted_pack_path)
    save_verified_chat_cleaned_output(run.cleaned_output, cleaned_output_path)

    assert load_verified_chat_request(request_path) == run.request
    assert load_verified_chat_response(response_path) == run.model_response
    assert load_verified_chat_extracted_pack(extracted_pack_path) == run.extracted_pack_bundle
    assert load_verified_chat_cleaned_output(cleaned_output_path) == run.cleaned_output


def test_kernel_replay_inputs_exclude_live_provider_credentials() -> None:
    run = sample_verified_chat_run()
    payload = canonical_text(kernel_replay_inputs(run))

    assert "credential_ref" not in payload
    assert "gemini" not in payload
    assert run.replay_inputs.replay_hash == sha256_of(run.replay_inputs)


def test_truthkernel_package_does_not_import_adapters() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "truthkernel"

    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(not alias.name.startswith("adapters") for alias in node.names), path
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                assert not node.module.startswith("adapters"), path


def sample_verified_chat_run() -> VerifiedChatRun:
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
    decision_bundle = DecisionBundle(
        id="decision-bundle-verified-chat",
        pack_hash=sha256_of(pack),
        claim_graph_hash="graph-verified-chat",
        evidence_snapshot_hashes=(evidence.snapshot_hash,),
        ledger_root=None,
        policy_hash=rulepack.policy_hash,
        taxonomy_hash=rulepack.taxonomy_hash,
        kernel_version="0.1.0",
        compiler_id="verified-chat-adapter",
        verifier_ids=(),
        verifier_weights={},
        findings=(
            Finding(
                id="finding-verified-chat",
                truth_class=TruthClass.TC_01,
                severity=Severity.MAJOR,
                claim_ids=(claim.id,),
                evidence_ids=(evidence.id,),
                message="Claim is grounded in a frozen replay bundle.",
                remedy_type=RemedyType.SUPPLY_EVIDENCE,
                conflicting_ledger_entry_ids=(),
            ),
        ),
        finding_counts={TruthClass.TC_01: 1},
        decision=Decision.REVIEW,
        repair_contract_id=None,
    )
    request = VerifiedChatRequest(
        prompt_text="Verify this technical claim against the supplied sources.",
        rulepack_id=rulepack.id,
        selection=ModelSelection(
            provider=ProviderKind.GEMINI,
            model_id="gemini-2.0-flash",
            credential_ref="vault://gemini/user-key",
            endpoint_url=None,
            settings=ModelSettings(
                temperature=Decimal("0"),
                top_p=Decimal("1"),
                max_output_tokens=1024,
            ),
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
    return VerifiedChatRun(
        request=request,
        model_response=model_response,
        extracted_pack_bundle=extracted_pack_bundle,
        replay_inputs=FrozenReplayInputs(
            pack=pack,
            rulepack=rulepack,
            decision_bundle=decision_bundle,
        ),
        cleaned_output="The system uses a frozen replay bundle.",
    )
