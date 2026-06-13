"""TC-03 unqualified critical claim predicate."""

from __future__ import annotations

from truthkernel.predicates.context import PredicateContext
from truthkernel.predicates.finding import finding
from truthkernel.schemas import Finding, LinkRelation, RemedyType, RulePack, Severity, TruthClass

_SUPPORT_RELATIONS = {LinkRelation.SUPPORTS, LinkRelation.CITES, LinkRelation.DERIVES}


def evaluate(context: PredicateContext, rulepack: RulePack) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    evidence_by_id = context.evidence_by_id()
    for claim in context.claims:
        if not claim.critical:
            continue
        qualified = False
        for edge in context.outgoing(claim.id, _SUPPORT_RELATIONS):
            evidence = evidence_by_id.get(str(edge["target_id"]))
            if evidence and evidence.kind in rulepack.qualified_source_kinds:
                qualified = True
        if not qualified:
            findings.append(
                finding(
                    TruthClass.TC_03,
                    Severity.CRITICAL,
                    "critical claim lacks a qualified source",
                    RemedyType.QUALIFY,
                    claim_ids=(claim.id,),
                )
            )
    return tuple(findings)
