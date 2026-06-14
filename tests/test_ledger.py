from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from truthkernel.canonical import sha256_of
from truthkernel.ledger import LedgerStore
from truthkernel.schemas import (
    Claim,
    ClaimType,
    Decision,
    DecisionBundle,
    Entity,
    Evidence,
    EvidenceKind,
    Pack,
    Provenance,
    RemedyType,
    TruthClass,
)


def test_ledger_replay_and_context(tmp_path: Path) -> None:
    ledger = LedgerStore(tmp_path / "ledger")
    claim = sample_claim("claim-1", "2.5 mm cable", Decimal("2.5"))
    pack = bundle_pack("bundle-1", claim)
    bundle = accepted_bundle("bundle-1", pack=pack)

    entries = ledger.append_decision_bundle(
        bundle,
        pack,
        asserted_at="2026-06-14T09:00:00Z",
    )

    assert entries[-1].entry_hash == ledger.head_hash
    assert ledger.replay_head() == ledger.head_hash
    snapshot = ledger.snapshot()
    assert tuple(fact.claim.id for fact in snapshot.facts) == (claim.id,)
    assert tuple(fact.claim.id for fact in ledger.assemble_context()) == (claim.id,)


def test_supersession_closes_previous_interval(tmp_path: Path) -> None:
    ledger = LedgerStore(tmp_path / "ledger")
    first = sample_claim("claim-1", "2.5 mm cable", Decimal("2.5"))
    second = sample_claim("claim-2", "1.5 mm cable", Decimal("1.5"))
    first_pack = bundle_pack("bundle-1", first)
    second_pack = bundle_pack("bundle-2", second)
    first_bundle = accepted_bundle("bundle-1", pack=first_pack)
    second_bundle = accepted_bundle("bundle-2", pack=second_pack)

    first_entries = ledger.append_decision_bundle(
        first_bundle,
        first_pack,
        asserted_at="2026-06-14T09:00:00Z",
    )
    second_entries = ledger.append_decision_bundle(
        second_bundle,
        second_pack,
        asserted_at="2026-06-14T09:05:00Z",
    )

    assert len(first_entries) == 1
    assert len(second_entries) == 1
    assert ledger.snapshot().facts[0].claim.id == second.id
    superseded_fact = ledger._fact_for_entry_hash(first_entries[0].entry_hash)
    assert superseded_fact is not None
    assert superseded_fact.entry.valid_to == "2026-06-14T09:05:00Z"


def test_explicit_invalidation_closes_entry(tmp_path: Path) -> None:
    ledger = LedgerStore(tmp_path / "ledger")
    claim = sample_claim("claim-1", "2.5 mm cable", Decimal("2.5"))
    pack = bundle_pack("bundle-1", claim)
    bundle = accepted_bundle("bundle-1", pack=pack)
    entries = ledger.append_decision_bundle(
        bundle,
        pack,
        asserted_at="2026-06-14T09:00:00Z",
    )

    invalidation = ledger.invalidate_entry(
        entries[0].entry_hash,
        asserted_at="2026-06-14T09:10:00Z",
        reason="correction",
    )

    assert invalidation.previous_entry_hash == entries[0].entry_hash
    fact = ledger._fact_for_entry_hash(entries[0].entry_hash)
    assert fact is not None
    assert fact.entry.valid_to == "2026-06-14T09:10:00Z"
    assert ledger.snapshot().facts == ()


def test_contradictions_target_exact_ledger_fact(tmp_path: Path) -> None:
    ledger = LedgerStore(tmp_path / "ledger")
    accepted = sample_claim("claim-1", "2.5 mm cable", Decimal("2.5"))
    conflicting = sample_claim("claim-2", "1.5 mm cable", Decimal("1.5"))
    pack = bundle_pack("bundle-1", accepted)
    bundle = accepted_bundle("bundle-1", pack=pack)
    entries = ledger.append_decision_bundle(
        bundle,
        pack,
        asserted_at="2026-06-14T09:00:00Z",
    )

    findings = ledger.contradictions(conflicting)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.truth_class == TruthClass.TC_07
    assert finding.conflicting_ledger_entry_ids == (entries[0].entry_hash,)
    assert finding.remedy_type == RemedyType.RESOLVE_CONTRADICTION


def sample_claim(claim_id: str, label: str, value: Decimal) -> Claim:
    return Claim(
        id=claim_id,
        text=f"The circuit uses {label}.",
        subject="circuit",
        relation="uses",
        object="cable",
        modifiers={"value": value, "unit": "mm"},
        claim_type=ClaimType.FACTUAL,
        gate_relevant=True,
        critical=True,
        provenance=Provenance(model_id="unit-test"),
    )


def accepted_bundle(bundle_id: str, *, pack: Pack) -> DecisionBundle:
    return DecisionBundle(
        id=bundle_id,
        pack_hash=sha256_of(pack),
        claim_graph_hash=f"graph-{bundle_id}",
        evidence_snapshot_hashes=tuple(),
        ledger_root=None,
        policy_hash=f"policy-{bundle_id}",
        taxonomy_hash=f"taxonomy-{bundle_id}",
        kernel_version="0.1.0",
        compiler_id="test",
        verifier_ids=(),
        verifier_weights={},
        findings=(),
        finding_counts={TruthClass.TC_01: 0},
        decision=Decision.ACCEPT,
        repair_contract_id=None,
    )


def bundle_pack(bundle_id: str, claim: Claim) -> Pack:
    evidence = Evidence(
        id=f"evidence-{bundle_id}",
        kind=EvidenceKind.TOOL_OUTPUT,
        text="Frozen evidence snapshot.",
        snapshot_hash=f"snapshot-{bundle_id}",
        provenance=Provenance(model_id="unit-test"),
    )
    entity = Entity(id=f"entity-{bundle_id}", kind="session", label="Ledger test")
    return Pack(
        id=f"pack-{bundle_id}",
        version="0.1",
        claims=(claim,),
        evidence=(evidence,),
        entities=(entity,),
    )
