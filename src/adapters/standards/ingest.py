"""Build frozen evidence packs from authorised standards text."""

from __future__ import annotations

from adapters.standards.contracts import (
    StandardAccess,
    StandardEvidenceBundle,
    StandardIngestRequest,
    StandardSource,
    StandardTextSegment,
)
from truthkernel.canonical import sha256_of
from truthkernel.schemas import Entity, Evidence, EvidenceKind, Pack, Provenance

_PACK_VERSION = "0.1"


def build_standard_evidence_bundle(request: StandardIngestRequest) -> StandardEvidenceBundle:
    """Convert authorised standard text into a deterministic evidence bundle."""
    _validate_ingest_request(request)
    source_entity = _source_entity(request.source)
    evidence = tuple(
        _segment_evidence(request.source, segment, request.uploaded_file_hash)
        for segment in sorted(request.segments, key=lambda item: item.clause_id)
    )
    pack_body = {
        "entities": (source_entity,),
        "evidence": evidence,
        "source_hash": request.source.source_hash,
        "version": _PACK_VERSION,
    }
    pack = Pack(
        id=sha256_of(pack_body),
        version=_PACK_VERSION,
        entities=(source_entity,),
        evidence=evidence,
    )
    return StandardEvidenceBundle(request=request, pack=pack)


def _validate_ingest_request(request: StandardIngestRequest) -> None:
    if not request.segments:
        raise ValueError("standards ingestion requires at least one text segment")
    if (
        request.source.access in {StandardAccess.PAID, StandardAccess.INSTITUTIONAL}
        and request.uploaded_file_hash is None
    ):
        raise ValueError("licensed standards require an authorised uploaded_file_hash")
    seen: set[str] = set()
    for segment in request.segments:
        if segment.clause_id in seen:
            raise ValueError(f"duplicate standard clause id: {segment.clause_id}")
        seen.add(segment.clause_id)


def _source_entity(source: StandardSource) -> Entity:
    return Entity(
        id=sha256_of(
            {
                "source_hash": source.source_hash,
                "type": "standard-source",
            }
        ),
        kind="standard-source",
        label=source.title,
        canonical_name=source.id,
        attributes={
            "access": source.access.value,
            "domain": source.domain,
            "publisher": source.publisher,
            "version": source.version,
        },
    )


def _segment_evidence(
    source: StandardSource,
    segment: StandardTextSegment,
    uploaded_file_hash: str | None,
) -> Evidence:
    content_hash = sha256_of(
        {
            "segment": segment,
            "source_hash": source.source_hash,
            "uploaded_file_hash": uploaded_file_hash,
        }
    )
    snapshot_hash = sha256_of(
        {
            "content_hash": content_hash,
            "source_url": source.source_url,
            "source_version": source.version,
        }
    )
    return Evidence(
        id=sha256_of(
            {
                "clause_id": segment.clause_id,
                "content_hash": content_hash,
                "source_hash": source.source_hash,
                "type": "standard-document-segment",
            }
        ),
        kind=EvidenceKind.DOCUMENT_SEGMENT,
        text=segment.text,
        snapshot_hash=snapshot_hash,
        provenance=Provenance(
            provider=source.publisher,
            source_uri=f"{source.source_url}#{segment.clause_id}",
            content_hash=content_hash,
            request_hash=source.source_hash,
        ),
    )
