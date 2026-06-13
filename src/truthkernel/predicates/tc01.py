"""TC-01 unsupported claim predicate."""

from __future__ import annotations

from truthkernel.predicates.context import PredicateContext
from truthkernel.predicates.finding import finding
from truthkernel.schemas import Finding, LinkRelation, RemedyType, RulePack, Severity, TruthClass

_SUPPORT_RELATIONS = {LinkRelation.SUPPORTS, LinkRelation.CITES, LinkRelation.DERIVES}


def evaluate(context: PredicateContext, rulepack: RulePack) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for claim in context.claims:
        if claim.claim_type not in rulepack.gate_relevant_claim_types:
            continue
        support_edges = context.outgoing(claim.id, _SUPPORT_RELATIONS)
        if not support_edges:
            findings.append(
                finding(
                    TruthClass.TC_01,
                    Severity.MAJOR,
                    "gate-relevant claim has no resolvable evidence",
                    RemedyType.SUPPLY_EVIDENCE,
                    claim_ids=(claim.id,),
                )
            )
    return tuple(findings)
