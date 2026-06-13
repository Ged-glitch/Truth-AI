"""TC-07 ledger contradiction predicate."""

from __future__ import annotations

from truthkernel.predicates.context import PredicateContext
from truthkernel.predicates.finding import finding
from truthkernel.schemas import (
    EvidenceKind,
    Finding,
    LinkRelation,
    RemedyType,
    RulePack,
    Severity,
    TruthClass,
)


def evaluate(context: PredicateContext, rulepack: RulePack) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    evidence_by_id = context.evidence_by_id()
    for claim in context.claims:
        for edge in context.outgoing(claim.id, {LinkRelation.CONTRADICTS}):
            evidence = evidence_by_id.get(str(edge["target_id"]))
            if evidence and evidence.kind == EvidenceKind.LEDGER_FACT:
                severity = Severity.CRITICAL if claim.critical else Severity.MAJOR
                findings.append(
                    finding(
                        TruthClass.TC_07,
                        severity,
                        "claim contradicts a ledger fact",
                        RemedyType.RESOLVE_CONTRADICTION,
                        claim_ids=(claim.id,),
                        evidence_ids=(evidence.id,),
                    )
                )
    return tuple(findings)
