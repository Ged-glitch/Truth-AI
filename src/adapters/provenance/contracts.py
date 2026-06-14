"""Contracts for frozen provenance artefacts."""

from __future__ import annotations

from pathlib import Path

from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.schemas.models import StrictBaseModel


class ProvenanceFetchRequest(StrictBaseModel):
    """A deterministic, file-backed provenance fetch request."""

    source_uri: str
    retriever_id: str
    settings_hash: str
    raw_text: str

    @property
    def request_hash(self) -> str:
        return sha256_of(self)


class FetchedArtifact(StrictBaseModel):
    """Fetched provenance content written to a committed artefact file."""

    request: ProvenanceFetchRequest
    content_hash: str

    @property
    def artifact_hash(self) -> str:
        return sha256_of(self)


def fetched_artifact_path(root: Path, request: ProvenanceFetchRequest) -> Path:
    """Return the canonical file path for a fetched provenance artefact."""
    return root / f"{request.request_hash}.json"


def save_fetched_artifact(artifact: FetchedArtifact, path: Path) -> None:
    """Write a canonical provenance artefact to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(artifact) + "\n", encoding="utf-8")
