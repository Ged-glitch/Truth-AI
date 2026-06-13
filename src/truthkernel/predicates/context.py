"""Helpers for reading deterministic graph dumps in predicates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from truthkernel.schemas import Claim, Evidence, LinkRelation


@dataclass(frozen=True, slots=True)
class PredicateContext:
    claims: tuple[Claim, ...]
    evidence: tuple[Evidence, ...]
    edges: tuple[dict[str, Any], ...]

    @classmethod
    def from_graph(cls, graph: dict[str, Any]) -> PredicateContext:
        claims: list[Claim] = []
        evidence: list[Evidence] = []
        for node in graph["nodes"]:
            if node["kind"] == "claim":
                claims.append(node["attributes"])
            if node["kind"] == "evidence":
                evidence.append(node["attributes"])
        return cls(
            claims=tuple(sorted(claims, key=lambda claim: claim.id)),
            evidence=tuple(sorted(evidence, key=lambda item: item.id)),
            edges=tuple(sorted(graph["edges"], key=lambda edge: edge["content_hash"])),
        )

    def evidence_by_id(self) -> dict[str, Evidence]:
        return {item.id: item for item in self.evidence}

    def outgoing(self, claim_id: str, relations: set[LinkRelation]) -> tuple[dict[str, Any], ...]:
        return tuple(
            edge
            for edge in self.edges
            if edge["source_id"] == claim_id and LinkRelation(edge["relation"]) in relations
        )
