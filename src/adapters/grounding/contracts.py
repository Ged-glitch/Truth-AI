"""Contracts for committed grounding-verifier verdict artefacts."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field

from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.schemas.models import StrictBaseModel


class GroundingVerdictRequest(StrictBaseModel):
    """Hash-keyed request metadata for a frozen grounding verdict."""

    claim_hash: str
    evidence_hash: str
    model_id: str
    settings_hash: str
    source_uri: str

    @property
    def storage_key(self) -> str:
        return sha256_of(self)


class GroundingVerdict(StrictBaseModel):
    """Static grounding verdict persisted outside the kernel."""

    request: GroundingVerdictRequest
    verdict: Literal["entails", "contradicts", "insufficient", "abstain"]
    confidence: Decimal | None = None
    response_hash: str

    @property
    def verdict_hash(self) -> str:
        return sha256_of(self)


class CalibrationReport(StrictBaseModel):
    """Frozen calibration output for advisory threshold setting."""

    adapter_id: str
    benchmark_names: tuple[str, ...]
    balanced_accuracy: Decimal
    abstention_rate: Decimal
    frozen_thresholds: dict[str, Decimal] = Field(default_factory=dict)

    @property
    def report_hash(self) -> str:
        return sha256_of(self)


def grounding_verdict_path(root: Path, request: GroundingVerdictRequest) -> Path:
    """Return the committed file path for a grounding verdict."""
    return root / f"{request.storage_key}.json"


def save_grounding_verdict(verdict: GroundingVerdict, path: Path) -> None:
    """Write a canonical grounding verdict bundle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(verdict) + "\n", encoding="utf-8")


def save_calibration_report(report: CalibrationReport, path: Path) -> None:
    """Write a canonical calibration report for frozen thresholds."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(report) + "\n", encoding="utf-8")
