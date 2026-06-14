"""Contracts for frozen extraction artefacts written before verification."""

from __future__ import annotations

from pathlib import Path

from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.schemas import Pack
from truthkernel.schemas.models import StrictBaseModel


class ExtractionRequest(StrictBaseModel):
    """Metadata for a structured extraction run outside the kernel."""

    prompt_text: str
    model_id: str
    settings_hash: str
    source_uri: str | None = None

    @property
    def request_hash(self) -> str:
        return sha256_of(self)


class ExtractedPackBundle(StrictBaseModel):
    """Frozen extraction output consumed by the deterministic kernel."""

    request: ExtractionRequest
    raw_model_output: str
    pack: Pack

    @property
    def bundle_hash(self) -> str:
        return sha256_of(self)


def extracted_pack_path(root: Path, request: ExtractionRequest) -> Path:
    """Return the canonical file path for a frozen extraction artefact."""
    return root / f"{request.request_hash}.json"


def save_extracted_pack_bundle(bundle: ExtractedPackBundle, path: Path) -> None:
    """Write a canonical extraction bundle to disk before verification."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(bundle) + "\n", encoding="utf-8")
