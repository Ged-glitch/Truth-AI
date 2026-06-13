"""TC-05 missing provenance predicate."""

from __future__ import annotations

from truthkernel.predicates.context import PredicateContext
from truthkernel.predicates.finding import finding
from truthkernel.schemas import Finding, RemedyType, RulePack, Severity, TruthClass


def evaluate(context: PredicateContext, rulepack: RulePack) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for claim in context.claims:
        if claim.claim_type not in rulepack.gate_relevant_claim_types:
            continue
        if not claim.provenance.model_id or not claim.provenance.content_hash:
            findings.append(
                finding(
                    TruthClass.TC_05,
                    Severity.MAJOR,
                    "claim provenance is missing model id or content hash",
                    RemedyType.RESTATE_WITH_SOURCE,
                    claim_ids=(claim.id,),
                )
            )
    for evidence in context.evidence:
        if (
            not evidence.snapshot_hash
            or not evidence.provenance.source_uri
            or not evidence.provenance.content_hash
        ):
            findings.append(
                finding(
                    TruthClass.TC_05,
                    Severity.MAJOR,
                    "evidence provenance is missing source URI, snapshot hash or content hash",
                    RemedyType.RESTATE_WITH_SOURCE,
                    evidence_ids=(evidence.id,),
                )
            )
    return tuple(findings)
