"""Deterministic repair contract assembly."""

from __future__ import annotations

from truthkernel.canonical import sha256_of
from truthkernel.gate import _finding_sort_key
from truthkernel.schemas import (
    EvidenceKind,
    Finding,
    RemedyType,
    RepairContract,
    RepairItem,
    RulePack,
)

_REMEDY_EVIDENCE_KINDS = {
    RemedyType.SUPPLY_EVIDENCE: None,
    RemedyType.RESTATE_WITH_SOURCE: None,
    RemedyType.RETRACT: (),
    RemedyType.QUALIFY: None,
    RemedyType.RESOLVE_CONTRADICTION: (EvidenceKind.LEDGER_FACT,),
}


def build_repair_contract(
    *,
    decision_bundle_id: str,
    findings: tuple[Finding, ...],
    rulepack: RulePack,
) -> RepairContract:
    """Build a stable repair contract from a set of findings."""
    ordered_findings = tuple(sorted(findings, key=_finding_sort_key))
    items = tuple(_repair_item(finding, rulepack) for finding in ordered_findings)
    body: dict[str, object] = {
        "decision_bundle_id": decision_bundle_id,
        "items": items,
    }
    return RepairContract(
        id=sha256_of(body),
        decision_bundle_id=decision_bundle_id,
        items=items,
    )


def _repair_item(finding: Finding, rulepack: RulePack) -> RepairItem:
    admissible_raw = _REMEDY_EVIDENCE_KINDS.get(finding.remedy_type)
    admissible: tuple[EvidenceKind, ...]
    if admissible_raw is None:
        admissible = tuple(rulepack.qualified_source_kinds)
    else:
        admissible = tuple(admissible_raw)
    return RepairItem(
        finding_id=finding.id,
        claim_ids=tuple(sorted(finding.claim_ids)),
        remedy_type=finding.remedy_type,
        admissible_evidence_kinds=admissible,
        conflicting_ledger_entry_ids=tuple(sorted(finding.conflicting_ledger_entry_ids)),
    )
