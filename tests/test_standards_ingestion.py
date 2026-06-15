from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.standards import (
    StandardIngestRequest,
    StandardTextSegment,
    build_standard_evidence_bundle,
    load_standard_library,
)
from truthkernel.canonical import sha256_of
from truthkernel.graph import build_graph
from truthkernel.schemas import EvidenceKind

_ROOT = Path(__file__).resolve().parents[1]
_LIBRARY_PATH = _ROOT / "standards" / "library" / "sample-standard-library.json"
_SAMPLE_PATH = _ROOT / "standards" / "ingest" / "nasa-orbital-debris-sample.json"


def test_public_standard_text_ingests_as_document_segment_pack() -> None:
    library = load_standard_library(_LIBRARY_PATH)
    sample = json.loads(_SAMPLE_PATH.read_text(encoding="utf-8"))
    source = next(item for item in library.sources if item.id == sample["source_id"])
    request = StandardIngestRequest(
        source=source,
        segments=tuple(StandardTextSegment.model_validate(item) for item in sample["segments"]),
    )

    bundle = build_standard_evidence_bundle(request)

    assert bundle.bundle_hash == sha256_of(bundle)
    assert bundle.request.request_hash == sha256_of(bundle.request)
    assert len(bundle.pack.evidence) == 2
    assert all(item.kind is EvidenceKind.DOCUMENT_SEGMENT for item in bundle.pack.evidence)
    assert all(item.provenance.source_uri is not None for item in bundle.pack.evidence)
    assert all(item.provenance.content_hash is not None for item in bundle.pack.evidence)

    graph = build_graph(bundle.pack)
    assert graph.graph is not None
    assert graph.findings == ()


def test_standards_ingestion_rejects_paid_source_without_upload_hash() -> None:
    library = load_standard_library(_LIBRARY_PATH)
    source = next(item for item in library.sources if item.id == "bsi-knowledge")
    request = StandardIngestRequest(
        source=source,
        segments=(
            StandardTextSegment(
                clause_id="BS-licensed-sample",
                title="Licensed clause",
                text="Licensed standard text provided by a user upload.",
                source_locator="sample",
            ),
        ),
    )

    with pytest.raises(ValueError, match="licensed standards require"):
        build_standard_evidence_bundle(request)


def test_standards_ingestion_allows_paid_source_with_upload_hash() -> None:
    library = load_standard_library(_LIBRARY_PATH)
    source = next(item for item in library.sources if item.id == "bsi-knowledge")
    request = StandardIngestRequest(
        source=source,
        uploaded_file_hash="licensed-upload-hash",
        segments=(
            StandardTextSegment(
                clause_id="BS-licensed-sample",
                title="Licensed clause",
                text="Licensed standard text provided by a user upload.",
                source_locator="sample",
            ),
        ),
    )

    bundle = build_standard_evidence_bundle(request)

    assert len(bundle.pack.evidence) == 1
    assert bundle.pack.evidence[0].kind is EvidenceKind.DOCUMENT_SEGMENT
