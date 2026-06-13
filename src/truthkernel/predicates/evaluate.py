"""Predicate evaluator."""

from __future__ import annotations

from truthkernel.predicates import tc01, tc02, tc03, tc04, tc05, tc07, tc08
from truthkernel.predicates.context import PredicateContext
from truthkernel.predicates.precedence import resolve_precedence
from truthkernel.schemas import Finding, RulePack

_PREDICATES = (
    tc01.evaluate,
    tc02.evaluate,
    tc03.evaluate,
    tc04.evaluate,
    tc05.evaluate,
    tc07.evaluate,
    tc08.evaluate,
)


def evaluate_predicates(graph: dict[str, object], rulepack: RulePack) -> tuple[Finding, ...]:
    """Evaluate all M3 predicates and apply fixed precedence."""
    context = PredicateContext.from_graph(graph)
    findings: list[Finding] = []
    for predicate in _PREDICATES:
        findings.extend(predicate(context, rulepack))
    return resolve_precedence(tuple(findings))
