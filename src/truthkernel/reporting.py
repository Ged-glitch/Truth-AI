"""M10 evaluation report and integration demo helpers."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from pathlib import Path

from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.contract import build_repair_contract
from truthkernel.gate import build_decision_bundle, decide
from truthkernel.graph import build_graph
from truthkernel.predicates.evaluate import evaluate_predicates
from truthkernel.replay import replay_golden
from truthkernel.schemas import (
    Claim,
    ClaimType,
    Decision,
    Entity,
    Evidence,
    EvidenceKind,
    Link,
    LinkRelation,
    Pack,
    Provenance,
    RulePack,
    TruthClass,
)
from truthkernel.schemas.models import StrictBaseModel

ROOT = Path(__file__).resolve().parents[2]
RULEPACK_PATH = ROOT / "rulepacks" / "strict-default" / "rulepack.json"
GOLDEN_DIR = ROOT / "fixtures" / "golden"


class AttemptSummary(StrictBaseModel):
    label: str
    decision: Decision
    graph_hash: str
    decision_bundle_id: str
    total_findings: int
    critical_count: int
    finding_counts: dict[TruthClass, int]
    repair_contract_id: str | None = None


class DemoSummary(StrictBaseModel):
    name: str
    brief: str
    attempts: tuple[AttemptSummary, ...]
    iterations_to_acceptance: int
    accepted_on_attempt: int
    final_decision: Decision
    per_class_findings: dict[TruthClass, int]


class FaultCaseSummary(StrictBaseModel):
    name: str
    expected_classes: tuple[TruthClass, ...]
    observed_classes: tuple[TruthClass, ...]
    decision: Decision


class FaultSuiteSummary(StrictBaseModel):
    precision: Decimal
    recall: Decimal
    true_positives: int
    false_positives: int
    false_negatives: int
    cases: tuple[FaultCaseSummary, ...]
    per_class_findings: dict[TruthClass, int]


class EvaluationReport(StrictBaseModel):
    title: str
    demos: tuple[DemoSummary, ...]
    fault_suite: FaultSuiteSummary
    replay_runs: int
    replay_byte_equal: bool
    development_cost_notes: tuple[str, ...]
    runtime_cost_notes: tuple[str, ...]

    @property
    def report_hash(self) -> str:
        return sha256_of(self)


def build_m10_report() -> EvaluationReport:
    """Build the deterministic M10 evaluation report."""
    replay_golden(GOLDEN_DIR, runs=30, byte_equal=True)
    demos = (
        build_openclaw_demo(),
        build_hermes_demo(),
        build_dcir_demo(),
    )
    fault_suite = build_fault_suite()
    return EvaluationReport(
        title="Truth-AI M10 evaluation report",
        demos=demos,
        fault_suite=fault_suite,
        replay_runs=30,
        replay_byte_equal=True,
        development_cost_notes=(
            "Milestone executed locally with deterministic kernel and committed fixtures.",
            "No external model calls were required to produce the report artefacts.",
        ),
        runtime_cost_notes=(
            "Report generation replays committed golden fixtures and evaluates static demo packs.",
            "Runtime cost is bounded by local graph construction, predicate evaluation and replay.",
        ),
    )


def _rulepack() -> RulePack:
    return RulePack.model_validate_json(RULEPACK_PATH.read_text(encoding="utf-8"))


def build_openclaw_demo() -> DemoSummary:
    """OpenClaw-style memory-write verification demo."""
    rulepack = _rulepack()
    accepted_pack = _memory_write_pack("openclaw")
    attempts = (_summarise_attempt("memory-write", accepted_pack, rulepack, "openclaw-demo"),)
    return _demo_summary(
        name="OpenClaw memory-write verification",
        brief="Hardware/GARK-style memory write admitted only after deterministic verification.",
        attempts=attempts,
    )


def build_hermes_demo() -> DemoSummary:
    """Hermes-style tool integration demo."""
    rulepack = _rulepack()
    rejected_pack = _research_summary_pack("hermes", qualified=False, critical=True)
    repaired_pack = _research_summary_pack("hermes", qualified=True, critical=True)
    attempts = (
        _summarise_attempt("tool-write-1", rejected_pack, rulepack, "hermes-demo"),
        _summarise_attempt("tool-write-2", repaired_pack, rulepack, "hermes-demo"),
    )
    return _demo_summary(
        name="Hermes tool integration",
        brief="Research-summary tool output is repaired until the memory write satisfies policy.",
        attempts=attempts,
    )


def build_dcir_demo() -> DemoSummary:
    """DCIR-A repair loop demo."""
    rulepack = _rulepack()
    attempts = (
        _summarise_attempt(
            "dcir-1",
            _ops_brief_pack("dcir", variant="missing-evidence"),
            rulepack,
            "dcir-demo",
        ),
        _summarise_attempt(
            "dcir-2",
            _ops_brief_pack("dcir", variant="missing-provenance"),
            rulepack,
            "dcir-demo",
        ),
        _summarise_attempt(
            "dcir-3",
            _ops_brief_pack("dcir", variant="accepted"),
            rulepack,
            "dcir-demo",
        ),
    )
    return _demo_summary(
        name="DCIR-A repair loop",
        brief="Ops/business claims move from raw output to an accepted kernel-gated answer.",
        attempts=attempts,
    )


def write_report(report: EvaluationReport, output_dir: Path) -> tuple[Path, Path]:
    """Write the committed report as markdown and canonical JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "evaluation-report.md"
    json_path = output_dir / "evaluation-report.json"
    markdown_path.write_text(render_report_markdown(report), encoding="utf-8")
    json_path.write_text(canonical_text(report) + "\n", encoding="utf-8")
    return markdown_path, json_path


def render_report_markdown(report: EvaluationReport) -> str:
    """Render the report in a deterministic markdown layout."""
    lines = [f"# {report.title}", ""]
    lines.extend(
        [
            "## Demos",
            "",
        ]
    )
    for demo in report.demos:
        lines.extend(
            [
                f"### {demo.name}",
                demo.brief,
                "",
                f"- Iterations to acceptance: {demo.iterations_to_acceptance}",
                f"- Final decision: {demo.final_decision.value}",
                f"- Accepted on attempt: {demo.accepted_on_attempt}",
                "- Per-class findings:",
                *(
                    f"  - {truth_class.value}: {count}"
                    for truth_class, count in demo.per_class_findings.items()
                ),
                "- Attempts:",
            ]
        )
        for attempt in demo.attempts:
            lines.extend(
                [
                    (
                        f"  - {attempt.label}: {attempt.decision.value} "
                        f"(findings={attempt.total_findings}, critical={attempt.critical_count})"
                    ),
                    f"    - graph hash: {attempt.graph_hash}",
                    f"    - decision bundle: {attempt.decision_bundle_id}",
                ]
            )
            if attempt.repair_contract_id is not None:
                lines.append(f"    - repair contract: {attempt.repair_contract_id}")
        lines.append("")

    lines.extend(
        [
            "## Injected Fault Suite",
            "",
            (f"- Precision: {report.fault_suite.precision}"),
            f"- Recall: {report.fault_suite.recall}",
            f"- True positives: {report.fault_suite.true_positives}",
            f"- False positives: {report.fault_suite.false_positives}",
            f"- False negatives: {report.fault_suite.false_negatives}",
            "- Per-class findings:",
        ]
    )
    lines.extend(
        f"  - {truth_class.value}: {count}"
        for truth_class, count in report.fault_suite.per_class_findings.items()
    )
    lines.append("")
    lines.extend(["## Fault Cases", ""])
    for case in report.fault_suite.cases:
        expected = ", ".join(item.value for item in case.expected_classes) or "none"
        observed = ", ".join(item.value for item in case.observed_classes) or "none"
        lines.extend(
            [
                f"- {case.name}",
                f"  - expected: {expected}",
                f"  - observed: {observed}",
                f"  - decision: {case.decision.value}",
            ]
        )
    lines.extend(
        [
            "",
            "## Replay Evidence",
            "",
            f"- `uv run truth replay fixtures/golden --runs {report.replay_runs} --byte-equal`: "
            f"{'passed' if report.replay_byte_equal else 'failed'}",
            "",
            "## Cost Notes",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in report.development_cost_notes)
    lines.extend(f"- {note}" for note in report.runtime_cost_notes)
    lines.append("")
    return "\n".join(lines)


def demo_payload(name: str) -> DemoSummary:
    """Return a demo summary by name."""
    demos = {
        "openclaw": build_openclaw_demo(),
        "hermes": build_hermes_demo(),
        "dcir": build_dcir_demo(),
    }
    try:
        return demos[name]
    except KeyError as exc:  # pragma: no cover - validated by CLI selection
        raise ValueError(f"unknown demo: {name}") from exc


def _demo_summary(
    *,
    name: str,
    brief: str,
    attempts: tuple[AttemptSummary, ...],
) -> DemoSummary:
    per_class: Counter[TruthClass] = Counter()
    accepted_on_attempt = len(attempts)
    final_decision = attempts[-1].decision
    for index, attempt in enumerate(attempts, start=1):
        for truth_class, count in attempt.finding_counts.items():
            per_class[truth_class] += count
        if attempt.decision is Decision.ACCEPT:
            accepted_on_attempt = index
            final_decision = attempt.decision
            break
    return DemoSummary(
        name=name,
        brief=brief,
        attempts=attempts,
        iterations_to_acceptance=accepted_on_attempt,
        accepted_on_attempt=accepted_on_attempt,
        final_decision=final_decision,
        per_class_findings=_truth_class_counts(per_class),
    )


def _summarise_attempt(
    label: str,
    pack: Pack,
    rulepack: RulePack,
    compiler_id: str,
) -> AttemptSummary:
    graph_result = build_graph(pack)
    if graph_result.graph is None:
        raise ValueError("pack failed pre-graph validation")
    graph_hash = str(graph_result.graph["graph_hash"])
    findings = evaluate_predicates(graph_result.graph, rulepack)
    decision = decide(findings, rulepack, graph_hash=graph_hash)
    bundle = build_decision_bundle(
        pack=pack,
        claim_graph_hash=graph_hash,
        evidence_snapshot_hashes=tuple(evidence.snapshot_hash for evidence in pack.evidence),
        ledger_root=None,
        rulepack=rulepack,
        findings=findings,
        decision=decision.decision,
        compiler_id=compiler_id,
    )
    repair_contract = (
        None
        if decision.decision is Decision.ACCEPT
        else build_repair_contract(
            decision_bundle_id=bundle.id,
            findings=findings,
            rulepack=rulepack,
        )
    )
    return AttemptSummary(
        label=label,
        decision=decision.decision,
        graph_hash=graph_hash,
        decision_bundle_id=bundle.id,
        total_findings=decision.total_findings,
        critical_count=decision.critical_count,
        finding_counts=_truth_class_counts(decision.finding_counts),
        repair_contract_id=None if repair_contract is None else repair_contract.id,
    )


def _fault_case_summary(
    name: str,
    pack: Pack,
    rulepack: RulePack,
    expected_classes: tuple[TruthClass, ...],
) -> FaultCaseSummary:
    graph_result = build_graph(pack)
    if graph_result.graph is None:
        raise ValueError("pack failed pre-graph validation")
    findings = evaluate_predicates(graph_result.graph, rulepack)
    observed_classes = tuple(finding.truth_class for finding in findings)
    decision = decide(findings, rulepack, graph_hash=str(graph_result.graph["graph_hash"]))
    return FaultCaseSummary(
        name=name,
        expected_classes=expected_classes,
        observed_classes=observed_classes,
        decision=decision.decision,
    )


def build_fault_suite() -> FaultSuiteSummary:
    """Summarise a deterministic injected-fault suite."""
    rulepack = _rulepack()
    cases = (
        _fault_case_summary(
            "tc01-unsupported",
            _brief_pack("fault-tc01", include_evidence=False),
            rulepack,
            (TruthClass.TC_01,),
        ),
        _fault_case_summary(
            "tc03-unqualified-critical",
            _research_summary_pack("fault-tc03", qualified=False, critical=True),
            rulepack,
            (TruthClass.TC_03,),
        ),
        _fault_case_summary(
            "tc04-orphan",
            _brief_pack("fault-tc04", include_about=False),
            rulepack,
            (TruthClass.TC_04,),
        ),
        _fault_case_summary(
            "tc05-missing-provenance",
            _brief_pack("fault-tc05", missing_provenance=True),
            rulepack,
            (TruthClass.TC_05,),
        ),
        _fault_case_summary(
            "healthy-control",
            _ops_brief_pack("fault-control", variant="accepted"),
            rulepack,
            (),
        ),
    )
    tp = fp = fn = 0
    per_class: Counter[TruthClass] = Counter()
    for case in cases:
        for observed_class in case.observed_classes:
            per_class[observed_class] += 1
        expected_classes = set(case.expected_classes)
        observed_classes = set(case.observed_classes)
        tp += len(expected_classes & observed_classes)
        fp += len(observed_classes - expected_classes)
        fn += len(expected_classes - observed_classes)
    precision = Decimal("1") if tp + fp == 0 else Decimal(tp) / Decimal(tp + fp)
    recall = Decimal("1") if tp + fn == 0 else Decimal(tp) / Decimal(tp + fn)
    return FaultSuiteSummary(
        precision=precision,
        recall=recall,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        cases=cases,
        per_class_findings=_truth_class_counts(per_class),
    )


def _memory_write_pack(label: str) -> Pack:
    claim = _claim(
        label,
        "Truth-AI stores accepted claims in an append-only ledger.",
        "Truth-AI",
        "stores",
        "accepted claims in an append-only ledger",
    )
    evidence = _evidence(
        label,
        EvidenceKind.DOCUMENT_SEGMENT,
        "Accepted claims are appended to an append-only, bitemporal ledger.",
        "spec://truth-ai/ledger",
    )
    return _supported_pack(label, claim, evidence)


def _research_summary_pack(label: str, *, qualified: bool, critical: bool = False) -> Pack:
    claim = _claim(
        label,
        "The report cites a frozen evidence snapshot.",
        "the report",
        "cites",
        "a frozen evidence snapshot",
        claim_type=ClaimType.CITATION,
        critical=critical,
    )
    evidence_kind = EvidenceKind.DOCUMENT_SEGMENT if qualified else EvidenceKind.RETRIEVAL_SNIPPET
    evidence = _evidence(
        label,
        evidence_kind,
        "Evidence snapshots are frozen, hashed and stored.",
        "spec://truth-ai/evidence",
    )
    return _supported_pack(label, claim, evidence)


def _ops_brief_pack(label: str, *, variant: str) -> Pack:
    if variant == "missing-evidence":
        claim = _claim(
            label,
            "The ops brief requires verified outputs.",
            "ops brief",
            "requires",
            "verified outputs",
        )
        entity, about = _entity_and_about(label, claim)
        return Pack(
            id=_hash("pack", label, variant),
            version="0.1",
            claims=(claim,),
            entities=(entity,),
            links=(about,),
        )
    if variant == "missing-provenance":
        claim = _claim(
            label,
            "The ops brief requires verified outputs.",
            "ops brief",
            "requires",
            "verified outputs",
        )
        evidence = _evidence(
            label,
            EvidenceKind.TOOL_OUTPUT,
            '{"pipeline":"verified","result":"accepted"}',
            "tool://ops",
            include_provenance=False,
        )
        return _supported_pack(label, claim, evidence)
    claim = _claim(
        label,
        "The ops brief requires verified outputs.",
        "ops brief",
        "requires",
        "verified outputs",
    )
    evidence = _evidence(
        label,
        EvidenceKind.TOOL_OUTPUT,
        '{"pipeline":"verified","result":"accepted"}',
        "tool://ops",
    )
    return _supported_pack(label, claim, evidence)


def _brief_pack(
    label: str,
    *,
    include_evidence: bool = True,
    include_about: bool = True,
    missing_provenance: bool = False,
) -> Pack:
    claim = _claim(
        label,
        "Truth-AI stores accepted claims in an append-only ledger.",
        "Truth-AI",
        "stores",
        "accepted claims in an append-only ledger",
    )
    entity, about = _entity_and_about(label, claim)
    links: tuple[Link, ...]
    evidence: Evidence | None = None
    if include_evidence:
        evidence = _evidence(
            label,
            EvidenceKind.DOCUMENT_SEGMENT,
            "Accepted claims are appended to an append-only, bitemporal ledger.",
            "spec://truth-ai/ledger",
            include_provenance=not missing_provenance,
        )
        links = (_support_link(label, claim, evidence),)
    else:
        links = ()
    if include_about:
        links = (*links, about)
    return Pack(
        id=_hash("pack", label),
        version="0.1",
        claims=(claim,),
        evidence=(() if evidence is None else (evidence,)),
        entities=(entity,),
        links=links,
    )


def _supported_pack(label: str, claim: Claim, evidence: Evidence) -> Pack:
    entity, about = _entity_and_about(label, claim)
    return Pack(
        id=_hash("pack", label, claim.id, evidence.id),
        version="0.1",
        claims=(claim,),
        evidence=(evidence,),
        entities=(entity,),
        links=(_support_link(label, claim, evidence), about),
    )


def _entity_and_about(label: str, claim: Claim) -> tuple[Entity, Link]:
    entity = Entity(
        id=_hash("entity", label, claim.subject),
        kind="topic",
        label=claim.subject,
    )
    about = Link(
        id=_hash("link", label, claim.id, entity.id, "about"),
        source_id=claim.id,
        relation=LinkRelation.ABOUT,
        target_id=entity.id,
    )
    return entity, about


def _support_link(label: str, claim: Claim, evidence: Evidence) -> Link:
    return Link(
        id=_hash("link", label, claim.id, evidence.id, "supports"),
        source_id=claim.id,
        relation=LinkRelation.SUPPORTS,
        target_id=evidence.id,
    )


def _claim(
    label: str,
    text: str,
    subject: str,
    relation: str,
    obj: str,
    *,
    claim_type: ClaimType = ClaimType.FACTUAL,
    critical: bool = False,
) -> Claim:
    return Claim(
        id=_hash("claim", label, text),
        text=text,
        subject=subject,
        relation=relation,
        object=obj,
        claim_type=claim_type,
        gate_relevant=True,
        critical=critical,
        provenance=Provenance(
            model_id="report-generator",
            content_hash=_hash("claim-content", label, text),
        ),
    )


def _evidence(
    label: str,
    kind: EvidenceKind,
    text: str,
    source_uri: str,
    *,
    include_provenance: bool = True,
) -> Evidence:
    provenance = Provenance(
        source_uri=source_uri,
        content_hash=_hash("evidence-content", label, text),
    )
    if not include_provenance:
        provenance = Provenance(source_uri=source_uri)
    return Evidence(
        id=_hash("evidence", label, text),
        kind=kind,
        text=text,
        snapshot_hash=_hash("snapshot", label, text),
        provenance=provenance,
    )


def _hash(*parts: object) -> str:
    return sha256_of(parts)


def _truth_class_counts(
    counter: Counter[TruthClass] | dict[TruthClass, int],
) -> dict[TruthClass, int]:
    return {truth_class: counter.get(truth_class, 0) for truth_class in TruthClass}
