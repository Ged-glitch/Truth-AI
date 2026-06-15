from __future__ import annotations

from pathlib import Path

from adapters.standards import (
    StandardAccess,
    StandardImportRequest,
    load_standard_library,
)
from truthkernel.canonical import sha256_of

_LIBRARY_PATH = (
    Path(__file__).resolve().parents[1] / "standards" / "library" / "sample-standard-library.json"
)


def test_sample_standard_library_loads_with_stable_hashes() -> None:
    library = load_standard_library(_LIBRARY_PATH)

    assert library.version == "0.1"
    assert library.library_hash == sha256_of(library)
    assert len(library.sources) >= 8

    source_ids = {source.id for source in library.sources}
    assert "nasa-technical-standards" in source_ids
    assert "nist-csrc-publications" in source_ids
    assert "bsi-knowledge" in source_ids

    for source in library.sources:
        assert source.source_hash == sha256_of(source)
        assert source.retrieval_policy
        assert source.licence_note
        for clause in source.clauses:
            assert clause.clause_hash == sha256_of(clause)


def test_paid_standards_are_marked_for_link_or_authorised_upload() -> None:
    library = load_standard_library(_LIBRARY_PATH)
    paid_sources = tuple(
        source
        for source in library.sources
        if source.access in {StandardAccess.PAID, StandardAccess.INSTITUTIONAL}
    )

    assert paid_sources
    for source in paid_sources:
        policy = source.retrieval_policy.casefold()
        assert "link" in policy or "upload" in policy or "authorised" in policy
        assert "scrape" not in policy or "do not scrape" in policy


def test_standard_import_request_hashes_user_source_metadata() -> None:
    request = StandardImportRequest(
        title="BS 7671 Requirements for Electrical Installations",
        publisher="BSI",
        source_url="https://knowledge.bsigroup.com/",
        access=StandardAccess.PAID,
        licence_note="User must provide a licensed copy before text extraction.",
        uploaded_file_hash=None,
    )

    assert request.request_hash == sha256_of(request)
