"""Hand-authored M4 examples used for golden decision-bundle fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from m1_examples import minimal_supported_pack

from truthkernel.gate import build_decision_bundle, decide
from truthkernel.graph import build_graph
from truthkernel.predicates.finding import finding
from truthkernel.schemas import (
    Decision,
    DecisionBundle,
    Finding,
    Pack,
    RemedyType,
    RulePack,
    Severity,
    TruthClass,
)

ROOT = Path(__file__).resolve().parents[1]
RULEPACK_PATH = ROOT / "rulepacks" / "strict-default" / "rulepack.json"


@dataclass(frozen=True, slots=True)
class BundleCase:
    name: str
    pack: Pack
    rulepack: RulePack
    findings: tuple[Finding, ...]
    graph_hash: str
    decision: Decision
    compiler_id: str = "truthkernel-gate"


def strict_default_rulepack() -> RulePack:
    return RulePack.model_validate_json(RULEPACK_PATH.read_text(encoding="utf-8"))


def sample_pack() -> Pack:
    return minimal_supported_pack()


def sample_findings() -> dict[str, tuple[Finding, ...]]:
    claim_id = sample_pack().claims[0].id
    return {
        "accept": (),
        "critical": (
            finding(
                TruthClass.TC_03,
                Severity.CRITICAL,
                "critical claim lacks a qualified source",
                RemedyType.QUALIFY,
                claim_ids=(claim_id,),
            ),
        ),
        "ceiling": (
            finding(
                TruthClass.TC_01,
                Severity.MAJOR,
                "gate-relevant claim has no resolvable evidence",
                RemedyType.SUPPLY_EVIDENCE,
                claim_ids=(claim_id,),
            ),
        ),
    }


def bundle_cases() -> dict[str, BundleCase]:
    pack = sample_pack()
    rulepack = strict_default_rulepack()
    graph = build_graph(pack)
    if graph.graph is None:
        raise RuntimeError("sample pack is malformed")
    graph_hash = str(graph.graph["graph_hash"])
    findings = sample_findings()
    return {
        name: BundleCase(
            name=name,
            pack=pack,
            rulepack=rulepack,
            findings=case_findings,
            graph_hash=graph_hash,
            decision=decide(case_findings, rulepack, graph_hash=graph_hash).decision,
        )
        for name, case_findings in findings.items()
    }


def build_bundle_case(case: BundleCase) -> DecisionBundle:
    return build_decision_bundle(
        pack=case.pack,
        claim_graph_hash=case.graph_hash,
        evidence_snapshot_hashes=tuple(evidence.snapshot_hash for evidence in case.pack.evidence),
        ledger_root=None,
        rulepack=case.rulepack,
        findings=case.findings,
        decision=case.decision,
        compiler_id=case.compiler_id,
    )
