"""Deterministic acceptance gate and decision-bundle assembly."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from truthkernel import __version__
from truthkernel.canonical import sha256_of
from truthkernel.schemas import (
    Decision,
    DecisionBundle,
    Finding,
    Pack,
    RulePack,
    Severity,
    TruthClass,
)

_TRUTH_CLASS_ORDER = tuple(TruthClass)
_TRUTH_CLASS_INDEX = {truth_class: index for index, truth_class in enumerate(_TRUTH_CLASS_ORDER)}


@dataclass(frozen=True, slots=True)
class GateResult:
    """Outcome of a deterministic gate evaluation."""

    decision: Decision
    finding_counts: dict[TruthClass, int]
    critical_count: int
    total_findings: int
    ordering_key: tuple[int, str]


def count_findings(findings: Iterable[Finding]) -> dict[TruthClass, int]:
    """Count findings by Truth Class in committed taxonomy order."""
    counts = {truth_class: 0 for truth_class in _TRUTH_CLASS_ORDER}
    for finding in findings:
        counts[finding.truth_class] += 1
    return counts


def decide(
    findings: Iterable[Finding],
    rulepack: RulePack,
    *,
    graph_hash: str | None = None,
    previous_counts: dict[TruthClass, int] | None = None,
    previous_graph_hash: str | None = None,
) -> GateResult:
    """Apply the lexicographic acceptance gate."""
    ordered_findings = tuple(sorted(findings, key=_finding_sort_key))
    finding_counts = count_findings(ordered_findings)
    critical_count = sum(1 for finding in ordered_findings if finding.severity is Severity.CRITICAL)
    total_findings = len(ordered_findings)
    ordering_key = (total_findings, graph_hash or "")

    if critical_count:
        return GateResult(
            decision=Decision.REJECT,
            finding_counts=finding_counts,
            critical_count=critical_count,
            total_findings=total_findings,
            ordering_key=ordering_key,
        )

    non_critical_counts = count_findings(
        finding for finding in ordered_findings if finding.severity is not Severity.CRITICAL
    )
    if previous_counts is None:
        decision = (
            Decision.ACCEPT if _within_ceilings(non_critical_counts, rulepack) else Decision.REJECT
        )
    else:
        decision = _compare_with_previous(
            non_critical_counts,
            previous_counts,
            graph_hash=graph_hash,
            previous_graph_hash=previous_graph_hash,
        )

    return GateResult(
        decision=decision,
        finding_counts=finding_counts,
        critical_count=critical_count,
        total_findings=total_findings,
        ordering_key=ordering_key,
    )


def build_decision_bundle(
    *,
    pack: Pack,
    claim_graph_hash: str,
    evidence_snapshot_hashes: tuple[str, ...],
    ledger_root: str | None,
    rulepack: RulePack,
    findings: tuple[Finding, ...],
    decision: Decision,
    compiler_id: str,
    verifier_ids: tuple[str, ...] = (),
    verifier_weights: dict[str, Decimal] | None = None,
    repair_contract_id: str | None = None,
    kernel_version: str = __version__,
) -> DecisionBundle:
    """Assemble a deterministic decision bundle."""
    ordered_findings = tuple(sorted(findings, key=_finding_sort_key))
    finding_counts = count_findings(ordered_findings)
    verifier_weights_value = (
        verifier_weights if verifier_weights is not None else rulepack.verifier_weights
    )
    bundle_body: dict[str, object] = {
        "pack_hash": sha256_of(pack),
        "claim_graph_hash": claim_graph_hash,
        "evidence_snapshot_hashes": tuple(sorted(evidence_snapshot_hashes)),
        "ledger_root": ledger_root,
        "policy_hash": rulepack.policy_hash,
        "taxonomy_hash": rulepack.taxonomy_hash,
        "kernel_version": kernel_version,
        "compiler_id": compiler_id,
        "verifier_ids": tuple(sorted(verifier_ids)),
        "verifier_weights": verifier_weights_value,
        "findings": ordered_findings,
        "finding_counts": finding_counts,
        "decision": decision,
        "repair_contract_id": repair_contract_id,
    }
    bundle_id = sha256_of(bundle_body)
    return DecisionBundle(
        id=bundle_id,
        pack_hash=sha256_of(pack),
        claim_graph_hash=claim_graph_hash,
        evidence_snapshot_hashes=tuple(sorted(evidence_snapshot_hashes)),
        ledger_root=ledger_root,
        policy_hash=rulepack.policy_hash,
        taxonomy_hash=rulepack.taxonomy_hash,
        kernel_version=kernel_version,
        compiler_id=compiler_id,
        verifier_ids=tuple(sorted(verifier_ids)),
        verifier_weights=verifier_weights_value,
        findings=ordered_findings,
        finding_counts=finding_counts,
        decision=decision,
        repair_contract_id=repair_contract_id,
    )


def _compare_with_previous(
    current_counts: dict[TruthClass, int],
    previous_counts: dict[TruthClass, int],
    *,
    graph_hash: str | None,
    previous_graph_hash: str | None,
) -> Decision:
    current_vector = _counts_vector(current_counts)
    previous_vector = _counts_vector(previous_counts)
    if current_vector == previous_vector:
        if graph_hash is None or previous_graph_hash is None:
            return Decision.ACCEPT
        return Decision.ACCEPT if graph_hash <= previous_graph_hash else Decision.REJECT
    if all(
        current <= previous
        for current, previous in zip(current_vector, previous_vector, strict=True)
    ):
        return Decision.ACCEPT
    return Decision.REJECT


def _within_ceilings(counts: dict[TruthClass, int], rulepack: RulePack) -> bool:
    for truth_class in _TRUTH_CLASS_ORDER:
        if counts[truth_class] > rulepack.gate_ceilings.get(truth_class, 0):
            return False
    return True


def _counts_vector(counts: dict[TruthClass, int]) -> tuple[int, ...]:
    return tuple(counts[truth_class] for truth_class in _TRUTH_CLASS_ORDER)


def _finding_sort_key(finding: Finding) -> tuple[int, str, tuple[str, ...], tuple[str, ...], str]:
    return (
        _TRUTH_CLASS_INDEX[finding.truth_class],
        finding.truth_class.value,
        finding.claim_ids,
        finding.evidence_ids,
        finding.id,
    )
