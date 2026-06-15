"""Adapter-side extraction from model text to frozen kernel packs."""

from __future__ import annotations

from adapters.extract import ExtractedPackBundle, ExtractionRequest
from adapters.verified_chat.contracts import ModelResponse, VerifiedChatRequest
from truthkernel.canonical import sha256_of
from truthkernel.schemas import (
    Claim,
    ClaimType,
    Entity,
    Evidence,
    EvidenceKind,
    Link,
    LinkRelation,
    Pack,
    Provenance,
)

_PACK_VERSION = "0.1"


def extract_model_response_pack(
    *,
    request: VerifiedChatRequest,
    model_response: ModelResponse,
) -> ExtractedPackBundle:
    """Freeze a raw model response as a minimal pack for kernel verification."""
    source_uri = _source_uri(request, model_response)
    session_id = sha256_of(
        {
            "request_hash": request.request_hash,
            "type": "verified-chat-session",
        }
    )
    claim_id = sha256_of(
        {
            "request_hash": request.request_hash,
            "response_hash": model_response.response_hash,
            "type": "verified-chat-claim",
        }
    )
    evidence_id = sha256_of(
        {
            "request_hash": request.request_hash,
            "response_hash": model_response.response_hash,
            "type": "verified-chat-evidence",
        }
    )
    snapshot_hash = sha256_of(
        {
            "raw_text": model_response.raw_text,
            "request_hash": request.request_hash,
            "response_hash": model_response.response_hash,
            "type": "verified-chat-model-output-snapshot",
        }
    )
    provenance = Provenance(
        model_id=request.selection.model_id,
        provider=request.selection.provider.value,
        source_uri=source_uri,
        content_hash=model_response.response_hash,
        request_hash=request.request_hash,
    )
    entity = Entity(
        id=session_id,
        kind="verified-chat-session",
        label="Verified chat session",
        canonical_name=request.request_hash,
    )
    claim = Claim(
        id=claim_id,
        text=model_response.raw_text,
        subject="assistant response",
        relation="states",
        object=model_response.raw_text,
        claim_type=ClaimType.FACTUAL,
        gate_relevant=True,
        critical=False,
        provenance=provenance,
    )
    evidence = Evidence(
        id=evidence_id,
        kind=EvidenceKind.TOOL_OUTPUT,
        text=model_response.raw_text,
        snapshot_hash=snapshot_hash,
        provenance=provenance,
    )
    support_link = Link(
        id=sha256_of(
            {
                "relation": LinkRelation.SUPPORTS.value,
                "source_id": claim_id,
                "target_id": evidence_id,
            }
        ),
        source_id=claim_id,
        relation=LinkRelation.SUPPORTS,
        target_id=evidence_id,
    )
    anchor_link = Link(
        id=sha256_of(
            {
                "relation": LinkRelation.ABOUT.value,
                "source_id": claim_id,
                "target_id": session_id,
            }
        ),
        source_id=claim_id,
        relation=LinkRelation.ABOUT,
        target_id=session_id,
    )
    pack_without_id = {
        "version": _PACK_VERSION,
        "claims": (claim,),
        "evidence": (evidence,),
        "entities": (entity,),
        "links": (support_link, anchor_link),
    }
    pack = Pack(
        id=sha256_of(pack_without_id),
        version=_PACK_VERSION,
        claims=(claim,),
        evidence=(evidence,),
        entities=(entity,),
        links=(support_link, anchor_link),
    )
    return ExtractedPackBundle(
        request=ExtractionRequest(
            prompt_text=request.prompt_text,
            model_id=request.selection.model_id,
            settings_hash=sha256_of(request.selection.settings),
            source_uri=source_uri,
        ),
        raw_model_output=model_response.raw_text,
        pack=pack,
    )


def _source_uri(request: VerifiedChatRequest, model_response: ModelResponse) -> str:
    if request.references:
        return request.references[0].source_uri
    return f"verified-chat://model-response/{model_response.response_hash}"
