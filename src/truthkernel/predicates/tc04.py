"""TC-04 orphan claim predicate."""

from __future__ import annotations

from truthkernel.predicates.context import PredicateContext
from truthkernel.predicates.finding import finding
from truthkernel.schemas import Finding, LinkRelation, RemedyType, RulePack, Severity, TruthClass

_ANCHOR_RELATIONS = {LinkRelation.ANCHORS, LinkRelation.ABOUT}


def evaluate(context: PredicateContext, rulepack: RulePack) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for claim in context.claims:
        if claim.claim_type not in rulepack.gate_relevant_claim_types:
            continue
        if not context.outgoing(claim.id, _ANCHOR_RELATIONS):
            findings.append(
                finding(
                    TruthClass.TC_04,
                    Severity.MINOR,
                    "claim is not anchored to the task or context graph",
                    RemedyType.QUALIFY,
                    claim_ids=(claim.id,),
                )
            )
    return tuple(findings)
