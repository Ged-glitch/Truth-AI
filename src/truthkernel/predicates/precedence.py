"""Fixed predicate precedence rules."""

from __future__ import annotations

from truthkernel.schemas import Finding, TruthClass

_PRECEDENCE = {
    TruthClass.TC_03: 0,
    TruthClass.TC_07: 1,
    TruthClass.TC_08: 2,
    TruthClass.TC_01: 3,
    TruthClass.TC_02: 4,
    TruthClass.TC_05: 5,
    TruthClass.TC_04: 6,
}


def resolve_precedence(findings: tuple[Finding, ...]) -> tuple[Finding, ...]:
    """Keep the highest-precedence finding for each claim/evidence location."""
    selected: dict[tuple[tuple[str, ...], tuple[str, ...]], Finding] = {}
    for item in sorted(findings, key=_sort_key):
        location = (item.claim_ids, item.evidence_ids)
        current = selected.get(location)
        if current is None or _PRECEDENCE[item.truth_class] < _PRECEDENCE[current.truth_class]:
            selected[location] = item
    return tuple(sorted(selected.values(), key=_sort_key))


def _sort_key(finding: Finding) -> tuple[int, str, tuple[str, ...], tuple[str, ...], str]:
    return (
        _PRECEDENCE[finding.truth_class],
        finding.truth_class.value,
        finding.claim_ids,
        finding.evidence_ids,
        finding.id,
    )
