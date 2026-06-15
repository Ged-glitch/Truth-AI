"""Adapter-side orchestration for verified-chat runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from adapters.extract import ExtractedPackBundle
from adapters.verified_chat.contracts import (
    FrozenReplayInputs,
    ModelResponse,
    VerifiedChatRequest,
    VerifiedChatRun,
)
from adapters.verified_chat.storage import (
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
from truthkernel.canonical import sha256_of
from truthkernel.gate import build_decision_bundle, decide
from truthkernel.graph import build_graph
from truthkernel.predicates.evaluate import evaluate_predicates
from truthkernel.schemas import Decision, DecisionBundle, Finding, RulePack


@dataclass(frozen=True, slots=True)
class VerifiedChatArtifactPaths:
    """Canonical storage paths for a verified-chat run."""

    request_path: Path
    response_path: Path
    extracted_pack_path: Path
    cleaned_output_path: Path
    run_path: Path


@dataclass(frozen=True, slots=True)
class VerifiedChatPipelineResult:
    """Materialised artefacts produced by the verified-chat runner."""

    run: VerifiedChatRun
    paths: VerifiedChatArtifactPaths


def build_verified_chat_run(
    *,
    request: VerifiedChatRequest,
    model_response: ModelResponse,
    extracted_pack_bundle: ExtractedPackBundle,
    cleaned_output: str,
    rulepack: RulePack,
    compiler_id: str = "verified-chat-adapter",
) -> VerifiedChatRun:
    """Compile frozen verified-chat artefacts into a deterministic run bundle."""
    _validate_run_inputs(
        request=request,
        model_response=model_response,
        extracted_pack_bundle=extracted_pack_bundle,
    )

    graph_result = build_graph(extracted_pack_bundle.pack)
    if graph_result.graph is None:
        raise ValueError("extracted pack failed pre-graph validation")

    findings = evaluate_predicates(graph_result.graph, rulepack)
    graph_hash = str(graph_result.graph["graph_hash"])
    gate = decide(findings, rulepack, graph_hash=graph_hash)
    decision_bundle = _build_decision_bundle(
        extracted_pack_bundle=extracted_pack_bundle,
        findings=findings,
        graph_hash=graph_hash,
        rulepack=rulepack,
        decision=gate.decision,
        compiler_id=compiler_id,
    )
    return VerifiedChatRun(
        request=request,
        model_response=model_response,
        extracted_pack_bundle=extracted_pack_bundle,
        replay_inputs=FrozenReplayInputs(
            pack=extracted_pack_bundle.pack,
            rulepack=rulepack,
            decision_bundle=decision_bundle,
        ),
        cleaned_output=cleaned_output,
    )


def persist_verified_chat_run(root: Path, run: VerifiedChatRun) -> VerifiedChatArtifactPaths:
    """Persist all frozen verified-chat artefacts under a hash-keyed root."""
    request_path = verified_chat_request_path(root, run.request)
    response_path = verified_chat_response_path(root, run.request)
    extracted_pack_path = verified_chat_extracted_pack_path(root, run.request)
    cleaned_output_path = verified_chat_cleaned_output_path(root, run.request)

    save_verified_chat_request(run.request, request_path)
    save_verified_chat_response(run.model_response, response_path)
    save_verified_chat_extracted_pack(run.extracted_pack_bundle, extracted_pack_path)
    save_verified_chat_cleaned_output(run.cleaned_output, cleaned_output_path)
    run_path = save_verified_chat_run_at_root(root, run)

    return VerifiedChatArtifactPaths(
        request_path=request_path,
        response_path=response_path,
        extracted_pack_path=extracted_pack_path,
        cleaned_output_path=cleaned_output_path,
        run_path=run_path,
    )


def build_and_persist_verified_chat_run(
    *,
    root: Path,
    request: VerifiedChatRequest,
    model_response: ModelResponse,
    extracted_pack_bundle: ExtractedPackBundle,
    cleaned_output: str,
    rulepack: RulePack,
    compiler_id: str = "verified-chat-adapter",
) -> VerifiedChatPipelineResult:
    """Compile and persist a verified-chat run in one adapter-side step."""
    run = build_verified_chat_run(
        request=request,
        model_response=model_response,
        extracted_pack_bundle=extracted_pack_bundle,
        cleaned_output=cleaned_output,
        rulepack=rulepack,
        compiler_id=compiler_id,
    )
    paths = persist_verified_chat_run(root, run)
    return VerifiedChatPipelineResult(run=run, paths=paths)


def load_verified_chat_run_bundle(root: Path, request: VerifiedChatRequest) -> VerifiedChatRun:
    """Load a fully persisted verified-chat run from hash-keyed artefacts."""
    return load_verified_chat_run_at_root(root, request)


def _build_decision_bundle(
    *,
    extracted_pack_bundle: ExtractedPackBundle,
    findings: tuple[Finding, ...],
    graph_hash: str,
    rulepack: RulePack,
    decision: Decision,
    compiler_id: str,
) -> DecisionBundle:
    return build_decision_bundle(
        pack=extracted_pack_bundle.pack,
        claim_graph_hash=graph_hash,
        evidence_snapshot_hashes=tuple(
            evidence.snapshot_hash for evidence in extracted_pack_bundle.pack.evidence
        ),
        ledger_root=None,
        rulepack=rulepack,
        findings=findings,
        decision=decision,
        compiler_id=compiler_id,
    )


def _validate_run_inputs(
    *,
    request: VerifiedChatRequest,
    model_response: ModelResponse,
    extracted_pack_bundle: ExtractedPackBundle,
) -> None:
    if model_response.request_hash != request.request_hash:
        raise ValueError("model response does not match the verified-chat request")
    if extracted_pack_bundle.request.prompt_text != request.prompt_text:
        raise ValueError("extracted pack request does not match the verified-chat request")
    if extracted_pack_bundle.request.model_id != request.selection.model_id:
        raise ValueError("extracted pack model does not match the verified-chat request")
    if extracted_pack_bundle.request.settings_hash != sha256_of(request.selection.settings):
        raise ValueError("extracted pack settings do not match the verified-chat request")
    if extracted_pack_bundle.raw_model_output != model_response.raw_text:
        raise ValueError("extracted pack does not match the raw model response")
