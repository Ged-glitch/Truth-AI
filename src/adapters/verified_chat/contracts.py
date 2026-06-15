"""Contracts for the verified-chat adapter boundary.

Live provider calls, credential handling and request shaping stay outside the
deterministic kernel. The kernel only receives the frozen replay inputs.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field

from adapters.extract import ExtractedPackBundle
from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.schemas import DecisionBundle, Pack, RulePack
from truthkernel.schemas.models import StrictBaseModel


class ProviderKind(StrEnum):
    """Model providers supported by the verified-chat adapter."""

    GEMINI = "gemini"
    USER_OWNED = "user-owned"
    LOCAL = "local"


class ReferenceKind(StrEnum):
    """Source kinds that can be frozen into a verified-chat request."""

    UPLOAD = "upload"
    RETRIEVAL = "retrieval"
    LEDGER = "ledger"
    RULEPACK = "rulepack"


class ModelSettings(StrictBaseModel):
    """Provider settings recorded for replay, not for secret material."""

    temperature: Decimal = Decimal("0")
    top_p: Decimal | None = None
    max_output_tokens: int | None = None


class ChatReference(StrictBaseModel):
    """A frozen reference included in the generation context."""

    kind: ReferenceKind
    source_uri: str
    content_hash: str
    label: str | None = None


class ModelSelection(StrictBaseModel):
    """Model selection metadata held outside the kernel."""

    provider: ProviderKind
    model_id: str
    credential_ref: str | None = None
    endpoint_url: str | None = None
    settings: ModelSettings = Field(default_factory=ModelSettings)


class VerifiedChatRequest(StrictBaseModel):
    """Canonical generation input for a verified chat session."""

    prompt_text: str
    rulepack_id: str
    selection: ModelSelection
    references: tuple[ChatReference, ...] = ()
    uploaded_file_hashes: tuple[str, ...] = ()

    @property
    def request_hash(self) -> str:
        return sha256_of(self)


class ModelResponse(StrictBaseModel):
    """Raw provider output persisted outside the kernel."""

    request_hash: str
    raw_text: str
    response_hash: str
    content_type: Literal["text/plain", "application/json"] = "text/plain"


class FrozenReplayInputs(StrictBaseModel):
    """The only verified-chat artefacts that the kernel needs for replay."""

    pack: Pack
    rulepack: RulePack
    decision_bundle: DecisionBundle

    @property
    def replay_hash(self) -> str:
        return sha256_of(self)


class VerifiedChatRun(StrictBaseModel):
    """End-to-end verified-chat artefacts with a frozen replay boundary."""

    request: VerifiedChatRequest
    model_response: ModelResponse
    extracted_pack_bundle: ExtractedPackBundle
    replay_inputs: FrozenReplayInputs
    cleaned_output: str

    @property
    def request_hash(self) -> str:
        return sha256_of(self.request)

    @property
    def run_hash(self) -> str:
        return sha256_of(self)

    @property
    def extracted_pack_hash(self) -> str:
        return sha256_of(self.extracted_pack_bundle)


def verified_chat_run_path(root: Path, request: VerifiedChatRequest) -> Path:
    """Return the canonical file path for a verified-chat run bundle."""
    return root / f"{request.request_hash}.json"


def save_verified_chat_run(run: VerifiedChatRun, path: Path) -> None:
    """Write a canonical verified-chat bundle for deterministic replay."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(run) + "\n", encoding="utf-8")
