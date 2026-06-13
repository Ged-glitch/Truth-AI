"""Hand-authored M1 example packs used for golden canonical fixtures."""

from __future__ import annotations

from decimal import Decimal

from truthkernel.canonical import sha256_of
from truthkernel.schemas import (
    Claim,
    ClaimType,
    Entity,
    Evidence,
    EvidenceKind,
    Link,
    LinkRelation,
    Pack,
    Provenance,
)


def minimal_supported_pack() -> Pack:
    entity = Entity(id="entity-alpha", kind="system", label="Truth-AI")
    claim = Claim(
        id="claim-alpha",
        text="Truth-AI stores accepted claims in an append-only ledger.",
        subject="Truth-AI",
        relation="stores",
        object="accepted claims in an append-only ledger",
        claim_type=ClaimType.FACTUAL,
        gate_relevant=True,
        provenance=Provenance(model_id="fixture-generator", content_hash="content-alpha"),
    )
    evidence = Evidence(
        id="evidence-alpha",
        kind=EvidenceKind.DOCUMENT_SEGMENT,
        text="Accepted claims are appended to an append-only, bitemporal ledger.",
        snapshot_hash="snapshot-alpha",
        provenance=Provenance(source_uri="spec://truth-ai/ledger", content_hash="content-alpha"),
    )
    link = Link(
        id="link-alpha",
        source_id=claim.id,
        relation=LinkRelation.SUPPORTS,
        target_id=evidence.id,
    )
    about = Link(
        id="link-alpha-about",
        source_id=claim.id,
        relation=LinkRelation.ABOUT,
        target_id=entity.id,
    )
    return Pack(
        id="pack-alpha",
        version="0.1",
        claims=(claim,),
        evidence=(evidence,),
        entities=(entity,),
        links=(about, link),
    )


def calculation_pack() -> Pack:
    claim = Claim(
        id="claim-beta",
        text="Two plus two equals four.",
        subject="two plus two",
        relation="equals",
        object="four",
        modifiers={"computed_value": Decimal("4")},
        claim_type=ClaimType.CALCULATION,
        gate_relevant=True,
        provenance=Provenance(model_id="fixture-generator", content_hash="content-beta"),
    )
    evidence = Evidence(
        id="evidence-beta",
        kind=EvidenceKind.TOOL_OUTPUT,
        text='{"expression":"2+2","result":"4"}',
        snapshot_hash="snapshot-beta",
        provenance=Provenance(source_uri="tool://calculator", content_hash="content-beta"),
    )
    link = Link(
        id="link-beta",
        source_id=claim.id,
        relation=LinkRelation.DERIVES,
        target_id=evidence.id,
    )
    return Pack(
        id="pack-beta",
        version="0.1",
        claims=(claim,),
        evidence=(evidence,),
        links=(link,),
    )


def citation_pack() -> Pack:
    claim = Claim(
        id="claim-gamma",
        text="The report cites a frozen evidence snapshot.",
        subject="the report",
        relation="cites",
        object="a frozen evidence snapshot",
        claim_type=ClaimType.CITATION,
        gate_relevant=True,
        provenance=Provenance(model_id="fixture-generator", content_hash="content-gamma"),
    )
    evidence = Evidence(
        id="evidence-gamma",
        kind=EvidenceKind.RETRIEVAL_SNIPPET,
        text="Evidence snapshots are frozen, hashed and stored.",
        snapshot_hash="snapshot-gamma",
        provenance=Provenance(source_uri="spec://truth-ai/evidence", content_hash="content-gamma"),
    )
    link = Link(
        id="link-gamma",
        source_id=claim.id,
        relation=LinkRelation.CITES,
        target_id=evidence.id,
        attributes={"rank": Decimal("1")},
    )
    return Pack(
        id="pack-gamma",
        version="0.1",
        claims=(claim,),
        evidence=(evidence,),
        links=(link,),
    )


def example_packs() -> dict[str, Pack]:
    return {
        "calculation": calculation_pack(),
        "citation": citation_pack(),
        "minimal-supported": minimal_supported_pack(),
    }


def example_pack_hashes() -> dict[str, str]:
    return {name: sha256_of(pack) for name, pack in example_packs().items()}
