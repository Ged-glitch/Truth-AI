from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from adapters.extract import (
    ExtractedPackBundle,
    ExtractionRequest,
    save_extracted_pack_bundle,
)
from adapters.grounding import (
    CalibrationReport,
    GroundingVerdict,
    GroundingVerdictRequest,
    save_calibration_report,
    save_grounding_verdict,
)
from adapters.provenance import (
    FetchedArtifact,
    ProvenanceFetchRequest,
    save_fetched_artifact,
)
from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.gate import decide
from truthkernel.graph import build_graph
from truthkernel.predicates.evaluate import evaluate_predicates
from truthkernel.schemas import (
    Claim,
    ClaimType,
    Decision,
    DeterminismTier,
    Entity,
    Evidence,
    EvidenceKind,
    Link,
    LinkRelation,
    Pack,
    Provenance,
    RulePack,
    TruthClass,
    VerifierResult,
)


def test_frozen_adapter_contracts_round_trip(tmp_path: Path) -> None:
    grounding_request = GroundingVerdictRequest(
        claim_hash="claim-hash-alpha",
        evidence_hash="evidence-hash-alpha",
        model_id="mini-check",
        settings_hash="settings-hash-alpha",
        source_uri="file://verdicts/alpha",
    )
    verdict = GroundingVerdict(
        request=grounding_request,
        verdict="entails",
        confidence=Decimal("0.93"),
        response_hash="response-hash-alpha",
    )
    verdict_path = tmp_path / "verdict.json"
    save_grounding_verdict(verdict, verdict_path)
    loaded_verdict = GroundingVerdict.model_validate_json(verdict_path.read_text(encoding="utf-8"))
    assert loaded_verdict == verdict
    assert loaded_verdict.verdict_hash == sha256_of(verdict)

    extraction_request = ExtractionRequest(
        prompt_text="Extract a verified pack from this technical summary.",
        model_id="outlines-mini",
        settings_hash="settings-hash-beta",
        source_uri="file://prompt.txt",
    )
    extracted_bundle = ExtractedPackBundle(
        request=extraction_request,
        raw_model_output='{"claims": []}',
        pack=Pack(id="pack-alpha", version="0.1"),
    )
    extracted_path = tmp_path / "extracted.json"
    save_extracted_pack_bundle(extracted_bundle, extracted_path)
    loaded_bundle = ExtractedPackBundle.model_validate_json(
        extracted_path.read_text(encoding="utf-8")
    )
    assert loaded_bundle == extracted_bundle
    assert canonical_text(loaded_bundle) == canonical_text(extracted_bundle)

    fetch_request = ProvenanceFetchRequest(
        source_uri="https://example.test/source",
        retriever_id="provenance-fetcher",
        settings_hash="settings-hash-gamma",
        raw_text="Accepted claims are appended to an append-only ledger.",
    )
    fetched_artifact = FetchedArtifact(
        request=fetch_request,
        content_hash="content-hash-gamma",
    )
    fetched_path = tmp_path / "fetched.json"
    save_fetched_artifact(fetched_artifact, fetched_path)
    loaded_fetched = FetchedArtifact.model_validate_json(fetched_path.read_text(encoding="utf-8"))
    assert loaded_fetched == fetched_artifact

    calibration_report = CalibrationReport(
        adapter_id="grounding-mini-check",
        benchmark_names=("llm-aggrefact", "ragtruth"),
        balanced_accuracy=Decimal("0.91"),
        abstention_rate=Decimal("0.07"),
        frozen_thresholds={"accept": Decimal("0.80"), "review": Decimal("0.55")},
    )
    calibration_path = tmp_path / "calibration.json"
    save_calibration_report(calibration_report, calibration_path)
    loaded_calibration = CalibrationReport.model_validate_json(
        calibration_path.read_text(encoding="utf-8")
    )
    assert loaded_calibration == calibration_report


def test_cached_grounding_verdict_resolves_critical_claim(tmp_path: Path) -> None:
    grounding_request = GroundingVerdictRequest(
        claim_hash="claim-hash-critical",
        evidence_hash="evidence-hash-critical",
        model_id="mini-check",
        settings_hash="settings-hash-critical",
        source_uri="file://verdicts/critical",
    )
    verdict = GroundingVerdict(
        request=grounding_request,
        verdict="entails",
        confidence=Decimal("0.97"),
        response_hash="response-hash-critical",
    )
    verdict_path = tmp_path / "verdict.json"
    save_grounding_verdict(verdict, verdict_path)

    claim = Claim(
        id="claim-critical",
        text="The grounding verdict supports the claim.",
        subject="grounding verdict",
        relation="supports",
        object="the claim",
        claim_type=ClaimType.FACTUAL,
        gate_relevant=True,
        critical=True,
        provenance=Provenance(
            model_id="extractor",
            content_hash="claim-hash-critical",
            source_uri="file://claim.txt",
        ),
    )
    evidence = Evidence(
        id="evidence-critical",
        kind=EvidenceKind.VERIFIER_RESULT,
        text="The cached grounding verdict entailed the claim.",
        snapshot_hash="snapshot-critical",
        provenance=Provenance(
            source_uri=f"file://{verdict_path.name}",
            content_hash=verdict.response_hash,
        ),
        verifier_result=VerifierResult(
            verifier_id="mini-check",
            determinism_tier=DeterminismTier.TIER_A,
            verdict="entails",
            confidence=Decimal("0.97"),
            settings_hash=grounding_request.settings_hash,
        ),
    )
    entity = Entity(
        id="entity-critical",
        kind="task",
        label="Grounding verification",
    )
    pack = Pack(
        id="pack-critical",
        version="0.1",
        claims=(claim,),
        evidence=(evidence,),
        entities=(entity,),
        links=(
            Link(
                id="link-critical",
                source_id=claim.id,
                relation=LinkRelation.SUPPORTS,
                target_id=evidence.id,
            ),
            Link(
                id="link-critical-about",
                source_id=claim.id,
                relation=LinkRelation.ABOUT,
                target_id=entity.id,
            ),
        ),
    )
    rulepack = RulePack(
        id="rulepack-critical",
        name="critical-grounding",
        version="0.1",
        policy_hash="policy-hash-critical",
        taxonomy_hash="taxonomy-hash-critical",
        gate_relevant_claim_types=(ClaimType.FACTUAL,),
        critical_truth_classes=(TruthClass.TC_03,),
        qualified_source_kinds=(EvidenceKind.VERIFIER_RESULT,),
        gate_ceilings={TruthClass.TC_03: 0},
        verifier_weights={},
        retrieval_permissions={},
    )

    graph_result = build_graph(pack)
    assert graph_result.graph is not None

    findings = evaluate_predicates(graph_result.graph, rulepack)
    assert all(f.truth_class is not TruthClass.TC_03 for f in findings)

    decision = decide(findings, rulepack, graph_hash=str(graph_result.graph["graph_hash"]))
    assert decision.decision is Decision.ACCEPT
