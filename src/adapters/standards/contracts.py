"""Contracts for standards-library sources outside the deterministic kernel."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import field_validator

from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.schemas import Pack
from truthkernel.schemas.models import StrictBaseModel


class StandardAccess(StrEnum):
    """How a standard can be loaded or referenced."""

    PUBLIC = "public"
    PAID = "paid"
    USER_UPLOAD = "user-upload"
    INSTITUTIONAL = "institutional"


class StandardClause(StrictBaseModel):
    """Small sample clause metadata for demo packs and test fixtures."""

    clause_id: str
    title: str
    summary: str
    source_locator: str

    @property
    def clause_hash(self) -> str:
        return sha256_of(self)


class StandardSource(StrictBaseModel):
    """A standards source that can later be converted into evidence packs."""

    id: str
    title: str
    publisher: str
    domain: str
    version: str | None = None
    access: StandardAccess
    source_url: str
    licence_note: str
    retrieval_policy: str
    clauses: tuple[StandardClause, ...] = ()

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, source_url: str) -> str:
        if not source_url.startswith(("https://", "http://")):
            raise ValueError("source_url must be an HTTP(S) URL")
        return source_url

    @property
    def source_hash(self) -> str:
        return sha256_of(self)


class StandardImportRequest(StrictBaseModel):
    """User request to register a standards source by official URL or upload."""

    title: str
    publisher: str
    source_url: str | None = None
    access: StandardAccess
    licence_note: str
    uploaded_file_hash: str | None = None

    @field_validator("source_url")
    @classmethod
    def validate_optional_source_url(cls, source_url: str | None) -> str | None:
        if source_url is None:
            return None
        if not source_url.startswith(("https://", "http://")):
            raise ValueError("source_url must be an HTTP(S) URL")
        return source_url

    @property
    def request_hash(self) -> str:
        return sha256_of(self)


class StandardTextSegment(StrictBaseModel):
    """Authorised standard text segment ready to freeze as evidence."""

    clause_id: str
    title: str
    text: str
    source_locator: str

    @property
    def segment_hash(self) -> str:
        return sha256_of(self)


class StandardIngestRequest(StrictBaseModel):
    """Request to convert authorised standard text into a kernel evidence pack."""

    source: StandardSource
    segments: tuple[StandardTextSegment, ...]
    uploaded_file_hash: str | None = None

    @property
    def request_hash(self) -> str:
        return sha256_of(self)


class StandardEvidenceBundle(StrictBaseModel):
    """Frozen evidence pack produced from an authorised standards source."""

    request: StandardIngestRequest
    pack: Pack

    @property
    def bundle_hash(self) -> str:
        return sha256_of(self)


class StandardLibrary(StrictBaseModel):
    """A canonical library manifest of known standards sources."""

    version: str
    sources: tuple[StandardSource, ...]

    @property
    def library_hash(self) -> str:
        return sha256_of(self)


def load_standard_library(path: Path) -> StandardLibrary:
    """Load a canonical standards-library manifest."""
    return StandardLibrary.model_validate_json(path.read_text(encoding="utf-8"))


def save_standard_library(library: StandardLibrary, path: Path) -> None:
    """Write a canonical standards-library manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(library) + "\n", encoding="utf-8")
