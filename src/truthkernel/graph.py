"""Deterministic typed graph builder for validated packs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from truthkernel.canonical import sha256_of
from truthkernel.schemas import Pack


class GraphNodeKind(StrEnum):
    CLAIM = "claim"
    EVIDENCE = "evidence"
    ENTITY = "entity"


class GraphFindingClass(StrEnum):
    GC_00 = "GC-00"


@dataclass(frozen=True, slots=True)
class GraphFinding:
    finding_class: GraphFindingClass
    location: str
    message: str

    @property
    def sort_key(self) -> tuple[str, str, str]:
        return (self.finding_class.value, self.location, self.message)


@dataclass(frozen=True, slots=True)
class GraphBuildResult:
    graph: dict[str, Any] | None
    findings: tuple[GraphFinding, ...]


def build_graph(pack: Pack) -> GraphBuildResult:
    """Build a deterministic graph dump, or return only GC-00 findings."""
    findings = _validate_pre_graph(pack)
    if findings:
        return GraphBuildResult(graph=None, findings=findings)

    nodes = (
        [_node(GraphNodeKind.CLAIM, claim.id, claim) for claim in pack.claims]
        + [_node(GraphNodeKind.EVIDENCE, evidence.id, evidence) for evidence in pack.evidence]
        + [_node(GraphNodeKind.ENTITY, entity.id, entity) for entity in pack.entities]
    )
    edges = [_edge(link) for link in pack.links]

    sorted_nodes = tuple(sorted(nodes, key=lambda item: item["content_hash"]))
    sorted_edges = tuple(sorted(edges, key=lambda item: item["content_hash"]))

    graph = {
        "pack_id": pack.id,
        "version": pack.version,
        "nodes": sorted_nodes,
        "edges": sorted_edges,
    }
    graph["graph_hash"] = sha256_of(graph)
    return GraphBuildResult(graph=graph, findings=())


def graph_hash(pack: Pack) -> str:
    """Return the deterministic graph hash for a valid pack."""
    result = build_graph(pack)
    if result.graph is None:
        raise ValueError("cannot hash malformed pack graph")
    return str(result.graph["graph_hash"])


def _validate_pre_graph(pack: Pack) -> tuple[GraphFinding, ...]:
    findings: list[GraphFinding] = []
    node_ids = [claim.id for claim in pack.claims]
    node_ids += [evidence.id for evidence in pack.evidence]
    node_ids += [entity.id for entity in pack.entities]

    seen: set[str] = set()
    duplicates: set[str] = set()
    for node_id in sorted(node_ids):
        if node_id in seen:
            duplicates.add(node_id)
        seen.add(node_id)

    for duplicate in sorted(duplicates):
        findings.append(
            GraphFinding(
                finding_class=GraphFindingClass.GC_00,
                location=f"node:{duplicate}",
                message="duplicate node id",
            )
        )

    valid_node_ids = set(node_ids)
    link_ids: set[str] = set()
    duplicate_link_ids: set[str] = set()
    for link in sorted(pack.links, key=lambda item: item.id):
        if link.id in link_ids:
            duplicate_link_ids.add(link.id)
        link_ids.add(link.id)
        if link.source_id not in valid_node_ids:
            findings.append(
                GraphFinding(
                    finding_class=GraphFindingClass.GC_00,
                    location=f"link:{link.id}:source_id",
                    message=f"missing node {link.source_id}",
                )
            )
        if link.target_id not in valid_node_ids:
            findings.append(
                GraphFinding(
                    finding_class=GraphFindingClass.GC_00,
                    location=f"link:{link.id}:target_id",
                    message=f"missing node {link.target_id}",
                )
            )

    for duplicate in sorted(duplicate_link_ids):
        findings.append(
            GraphFinding(
                finding_class=GraphFindingClass.GC_00,
                location=f"link:{duplicate}",
                message="duplicate link id",
            )
        )

    return tuple(sorted(findings, key=lambda finding: finding.sort_key))


def _node(kind: GraphNodeKind, node_id: str, payload: Any) -> dict[str, Any]:
    node = {
        "id": node_id,
        "kind": kind.value,
        "attributes": payload,
    }
    return {
        "id": node_id,
        "kind": kind.value,
        "content_hash": sha256_of(node),
        "attributes": payload,
    }


def _edge(link: Any) -> dict[str, Any]:
    edge = {
        "id": link.id,
        "source_id": link.source_id,
        "relation": link.relation,
        "target_id": link.target_id,
        "attributes": link.attributes,
    }
    return {
        **edge,
        "content_hash": sha256_of(edge),
    }
