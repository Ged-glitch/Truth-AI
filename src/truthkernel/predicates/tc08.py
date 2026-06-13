"""TC-08 self-contradiction predicate."""

from __future__ import annotations

from itertools import combinations

from truthkernel.comparators import claims_conflict
from truthkernel.predicates.context import PredicateContext
from truthkernel.predicates.finding import finding
from truthkernel.schemas import Finding, RemedyType, RulePack, Severity, TruthClass


def evaluate(context: PredicateContext, rulepack: RulePack) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    claims = tuple(
        claim for claim in context.claims if claim.claim_type in rulepack.gate_relevant_claim_types
    )
    for left, right in combinations(claims, 2):
        if claims_conflict(left, right):
            findings.append(
                finding(
                    TruthClass.TC_08,
                    Severity.MAJOR,
                    "claims in the same output conflict on canonical SROM",
                    RemedyType.RESOLVE_CONTRADICTION,
                    claim_ids=(left.id, right.id),
                )
            )
    return tuple(findings)
