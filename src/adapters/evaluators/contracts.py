"""Contracts for advisory context evaluators outside the deterministic kernel."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from pydantic import field_validator

from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.schemas.models import StrictBaseModel


class EvaluatorAccess(StrEnum):
    """How an evaluator or benchmark can be used by the product."""

    OPEN_SOURCE = "open-source"
    BENCHMARK = "benchmark"
    OPTIONAL_DEPENDENCY = "optional-dependency"


class EvaluationMetric(StrictBaseModel):
    """A metric exposed by an advisory evaluator."""

    id: str
    label: str
    signal: str
    deterministic: bool
    output_scale: str

    @property
    def metric_hash(self) -> str:
        return sha256_of(self)


class EvaluationEngine(StrictBaseModel):
    """An advisory evaluator that can score context or benchmark verifier quality."""

    id: str
    name: str
    package_name: str
    access: EvaluatorAccess
    source_url: str
    role: str
    licence_note: str
    metrics: tuple[EvaluationMetric, ...]

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, source_url: str) -> str:
        if not source_url.startswith(("https://", "http://")):
            raise ValueError("source_url must be an HTTP(S) URL")
        return source_url

    @property
    def engine_hash(self) -> str:
        return sha256_of(self)


class BenchmarkDataset(StrictBaseModel):
    """Dataset used to benchmark evaluator and retrieval behaviour."""

    id: str
    name: str
    source_url: str
    domain: str
    use_case: str
    licence_note: str

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, source_url: str) -> str:
        if not source_url.startswith(("https://", "http://")):
            raise ValueError("source_url must be an HTTP(S) URL")
        return source_url

    @property
    def dataset_hash(self) -> str:
        return sha256_of(self)


class EvaluatorRunRecord(StrictBaseModel):
    """Frozen advisory evaluator output for a verified-chat run."""

    evaluator_id: str
    metric_id: str
    request_hash: str
    evidence_hashes: tuple[str, ...]
    score: Decimal
    reason: str

    @property
    def run_hash(self) -> str:
        return sha256_of(self)


class EvaluatorLibrary(StrictBaseModel):
    """Canonical catalogue of advisory evaluators and benchmark datasets."""

    version: str
    engines: tuple[EvaluationEngine, ...]
    benchmarks: tuple[BenchmarkDataset, ...]

    @property
    def library_hash(self) -> str:
        return sha256_of(self)


def load_evaluator_library(path: Path) -> EvaluatorLibrary:
    """Load a canonical evaluator catalogue."""
    return EvaluatorLibrary.model_validate_json(path.read_text(encoding="utf-8"))


def save_evaluator_library(library: EvaluatorLibrary, path: Path) -> None:
    """Write a canonical evaluator catalogue."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_text(library) + "\n", encoding="utf-8")
