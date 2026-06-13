import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from m1_examples import minimal_supported_pack

from truthkernel.canonical import canonical_text
from truthkernel.graph import GraphFindingClass, build_graph, graph_hash
from truthkernel.schemas import Claim, ClaimType, Link, LinkRelation, Pack, Provenance


def test_graph_hash_is_independent_of_pack_element_order() -> None:
    pack = minimal_supported_pack()
    shuffled = Pack(
        id=pack.id,
        version=pack.version,
        claims=tuple(reversed(pack.claims)),
        evidence=tuple(reversed(pack.evidence)),
        entities=tuple(reversed(pack.entities)),
        links=tuple(reversed(pack.links)),
    )

    assert graph_hash(shuffled) == graph_hash(pack)
    assert canonical_text(build_graph(shuffled).graph) == canonical_text(build_graph(pack).graph)


def test_malformed_pack_yields_only_gc00_findings_and_no_graph() -> None:
    claim = Claim(
        id="claim-missing-link-target",
        text="A claim exists.",
        subject="claim",
        relation="exists",
        object="true",
        claim_type=ClaimType.FACTUAL,
        gate_relevant=True,
        provenance=Provenance(model_id="test"),
    )
    link = Link(
        id="bad-link",
        source_id=claim.id,
        relation=LinkRelation.SUPPORTS,
        target_id="missing-evidence",
    )
    result = build_graph(Pack(id="bad-pack", version="0.1", claims=(claim,), links=(link,)))

    assert result.graph is None
    assert result.findings
    assert {finding.finding_class for finding in result.findings} == {GraphFindingClass.GC_00}


def test_duplicate_node_ids_yield_gc00() -> None:
    claim = Claim(
        id="duplicate-id",
        text="A claim exists.",
        subject="claim",
        relation="exists",
        object="true",
        claim_type=ClaimType.FACTUAL,
        gate_relevant=True,
        provenance=Provenance(model_id="test"),
    )
    duplicate = claim.model_copy(update={"text": "Another claim exists."})
    result = build_graph(Pack(id="duplicate-pack", version="0.1", claims=(claim, duplicate)))

    assert result.graph is None
    assert tuple(finding.finding_class for finding in result.findings) == (GraphFindingClass.GC_00,)
