from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from m4_examples import bundle_cases

from truthkernel.canonical import canonical_text
from truthkernel.contract import build_repair_contract
from truthkernel.gate import build_decision_bundle
from truthkernel.schemas import RemedyType


def test_repair_contract_round_trips_through_canonical_json() -> None:
    case = bundle_cases()["critical"]
    contract = build_repair_contract(
        decision_bundle_id="decision-bundle-critical",
        findings=case.findings,
        rulepack=case.rulepack,
    )

    assert contract.items[0].remedy_type == RemedyType.QUALIFY
    assert contract == contract.model_validate_json(canonical_text(contract))


def test_decision_bundle_round_trips_through_canonical_json() -> None:
    case = bundle_cases()["critical"]
    contract = build_repair_contract(
        decision_bundle_id="decision-bundle-critical",
        findings=case.findings,
        rulepack=case.rulepack,
    )
    bundle = build_decision_bundle(
        pack=case.pack,
        claim_graph_hash=case.graph_hash,
        evidence_snapshot_hashes=tuple(evidence.snapshot_hash for evidence in case.pack.evidence),
        ledger_root=None,
        rulepack=case.rulepack,
        findings=case.findings,
        decision=case.decision,
        compiler_id=case.compiler_id,
        repair_contract_id=contract.id,
    )

    assert bundle.repair_contract_id == contract.id
    assert bundle == bundle.model_validate_json(canonical_text(bundle))
