"""TC-02 stale evidence predicate."""

from __future__ import annotations

from truthkernel.comparators import intervals_overlap
from truthkernel.predicates.context import PredicateContext
from truthkernel.predicates.finding import finding
from truthkernel.schemas import Finding, LinkRelation, RemedyType, RulePack, Severity, TruthClass

_SUPPORT_RELATIONS = {LinkRelation.SUPPORTS, LinkRelation.CITES, LinkRelation.DERIVES}


def evaluate(context: PredicateContext, rulepack: RulePack) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    evidence_by_id = context.evidence_by_id()
    claims_by_id = {claim.id: claim for claim in context.claims}
    for claim in context.claims:
        if claim.claim_type not in rulepack.gate_relevant_claim_types:
            continue
        for edge in context.outgoing(claim.id, _SUPPORT_RELATIONS):
            evidence = evidence_by_id.get(str(edge["target_id"]))
            if evidence is None:
                continue
            if not intervals_overlap(
                claim.valid_from,
                claim.valid_to,
                evidence.valid_from,
                evidence.valid_to,
            ):
                findings.append(
                    finding(
                        TruthClass.TC_02,
                        Severity.MAJOR,
                        "supporting evidence is outside the claim validity interval",
                        RemedyType.RESTATE_WITH_SOURCE,
                        claim_ids=(claims_by_id[str(edge["source_id"])].id,),
                        evidence_ids=(evidence.id,),
                    )
                )
    return tuple(findings)
