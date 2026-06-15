from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from adapters.evaluators import (
    EvaluatorAccess,
    EvaluatorRunRecord,
    load_evaluator_library,
)
from truthkernel.canonical import sha256_of

_LIBRARY_PATH = (
    Path(__file__).resolve().parents[1]
    / "standards"
    / "evaluators"
    / "sample-evaluator-library.json"
)


def test_sample_evaluator_library_loads_with_stable_hashes() -> None:
    library = load_evaluator_library(_LIBRARY_PATH)

    assert library.version == "0.1"
    assert library.library_hash == sha256_of(library)
    assert {engine.id for engine in library.engines} == {
        "deepeval",
        "open-rag-eval",
        "ragas",
    }
    assert {dataset.id for dataset in library.benchmarks} == {
        "ragtruth",
        "vectara-ragbench",
    }

    for engine in library.engines:
        assert engine.engine_hash == sha256_of(engine)
        assert engine.metrics
        for metric in engine.metrics:
            assert metric.metric_hash == sha256_of(metric)

    for dataset in library.benchmarks:
        assert dataset.dataset_hash == sha256_of(dataset)


def test_runtime_evaluators_are_advisory_and_not_kernel_authorities() -> None:
    library = load_evaluator_library(_LIBRARY_PATH)

    for engine in library.engines:
        assert engine.access in {EvaluatorAccess.OPEN_SOURCE, EvaluatorAccess.OPTIONAL_DEPENDENCY}
        assert "Advisory" in engine.role
        assert all(not metric.deterministic for metric in engine.metrics)


def test_evaluator_run_record_hashes_frozen_advisory_output() -> None:
    record = EvaluatorRunRecord(
        evaluator_id="ragas",
        metric_id="ragas-faithfulness",
        request_hash="request-hash",
        evidence_hashes=("evidence-a", "evidence-b"),
        score=Decimal("0.87"),
        reason="Answer claims are mostly supported by retrieved standard clauses.",
    )

    assert record.run_hash == sha256_of(record)
