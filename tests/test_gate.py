from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from m4_examples import bundle_cases, strict_default_rulepack

from truthkernel.gate import count_findings, decide
from truthkernel.schemas import Decision, TruthClass


def test_gate_accepts_when_within_policy_ceilings() -> None:
    case = bundle_cases()["accept"]
    result = decide(case.findings, case.rulepack, graph_hash=case.graph_hash)

    assert result.decision == Decision.ACCEPT
    assert result.critical_count == 0
    assert result.total_findings == 0
    assert result.finding_counts == {truth_class: 0 for truth_class in TruthClass}


def test_gate_rejects_on_critical_findings() -> None:
    case = bundle_cases()["critical"]
    result = decide(case.findings, case.rulepack, graph_hash=case.graph_hash)

    assert result.decision == Decision.REJECT
    assert result.critical_count == 1


def test_gate_rejects_on_ceiling_breach() -> None:
    case = bundle_cases()["ceiling"]
    result = decide(case.findings, case.rulepack, graph_hash=case.graph_hash)

    assert result.decision == Decision.REJECT


def test_gate_uses_fixed_graph_hash_tie_breaker_when_vectors_match() -> None:
    rulepack = strict_default_rulepack()
    zero_counts = {truth_class: 0 for truth_class in TruthClass}
    current = decide(
        (),
        rulepack,
        graph_hash="aaaa",
        previous_counts=zero_counts,
        previous_graph_hash="zzzz",
    )
    later = decide(
        (),
        rulepack,
        graph_hash="zzzz",
        previous_counts=zero_counts,
        previous_graph_hash="aaaa",
    )

    assert current.decision == Decision.ACCEPT
    assert later.decision == Decision.REJECT


def test_count_findings_is_taxonomy_ordered() -> None:
    case = bundle_cases()["ceiling"]
    counts = count_findings(case.findings)

    assert tuple(counts) == tuple(TruthClass)
