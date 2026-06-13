import ast
import json
from collections.abc import Callable
from pathlib import Path

from truthkernel.graph import build_graph
from truthkernel.predicates import tc01, tc02, tc03, tc04, tc05, tc07, tc08
from truthkernel.predicates.context import PredicateContext
from truthkernel.predicates.evaluate import evaluate_predicates
from truthkernel.schemas import (
    Claim,
    ClaimType,
    Entity,
    Evidence,
    EvidenceKind,
    Finding,
    Link,
    LinkRelation,
    Pack,
    Provenance,
    RulePack,
    TruthClass,
)

ROOT = Path(__file__).resolve().parents[1]


Predicate = Callable[[PredicateContext, RulePack], tuple[Finding, ...]]


def _rulepack() -> RulePack:
    return RulePack.model_validate_json(
        (ROOT / "rulepacks" / "strict-default" / "rulepack.json").read_text(encoding="utf-8")
    )


def _claim(
    claim_id: str = "claim-a",
    *,
    subject: str = "subject",
    relation: str = "is",
    obj: str = "object",
    critical: bool = False,
    content_hash: str | None = "claim-content",
    valid_from: str | None = None,
    valid_to: str | None = None,
) -> Claim:
    return Claim(
        id=claim_id,
        text=f"{subject} {relation} {obj}",
        subject=subject,
        relation=relation,
        object=obj,
        claim_type=ClaimType.FACTUAL,
        gate_relevant=True,
        critical=critical,
        valid_from=valid_from,
        valid_to=valid_to,
        provenance=Provenance(model_id="test-model", content_hash=content_hash),
    )


def _evidence(
    evidence_id: str = "evidence-a",
    *,
    kind: EvidenceKind = EvidenceKind.DOCUMENT_SEGMENT,
    valid_from: str | None = None,
    valid_to: str | None = None,
) -> Evidence:
    return Evidence(
        id=evidence_id,
        kind=kind,
        text="Evidence text.",
        snapshot_hash=f"{evidence_id}-snapshot",
        valid_from=valid_from,
        valid_to=valid_to,
        provenance=Provenance(
            source_uri=f"fixture://{evidence_id}",
            content_hash="evidence-content",
        ),
    )


def _support(
    claim: Claim,
    evidence: Evidence,
    relation: LinkRelation = LinkRelation.SUPPORTS,
) -> Link:
    return Link(
        id=f"link-{claim.id}-{evidence.id}-{relation.value}",
        source_id=claim.id,
        relation=relation,
        target_id=evidence.id,
    )


def _about(claim: Claim) -> tuple[Entity, Link]:
    entity = Entity(id=f"entity-{claim.id}", kind="topic", label=claim.subject)
    link = Link(
        id=f"link-{claim.id}-about",
        source_id=claim.id,
        relation=LinkRelation.ABOUT,
        target_id=entity.id,
    )
    return entity, link


def _context(pack: Pack) -> PredicateContext:
    result = build_graph(pack)
    assert result.graph is not None
    return PredicateContext.from_graph(result.graph)


def _evaluate(predicate: Predicate, pack: Pack) -> tuple[Finding, ...]:
    return predicate(_context(pack), _rulepack())


def _supported_pack(claim: Claim, evidence: Evidence | None = None) -> Pack:
    selected_evidence = evidence or _evidence()
    entity, about = _about(claim)
    return Pack(
        id=f"pack-{claim.id}",
        version="0.1",
        claims=(claim,),
        evidence=(selected_evidence,),
        entities=(entity,),
        links=(_support(claim, selected_evidence), about),
    )


def test_tc01_unsupported_claim_positive_and_negative() -> None:
    claim = _claim()
    entity, about = _about(claim)
    positive = Pack(
        id="pack-tc01-pos",
        version="0.1",
        claims=(claim,),
        entities=(entity,),
        links=(about,),
    )

    assert _evaluate(tc01.evaluate, positive)[0].truth_class == TruthClass.TC_01
    assert _evaluate(tc01.evaluate, _supported_pack(claim)) == ()


def test_tc02_stale_evidence_positive_and_negative() -> None:
    claim = _claim(valid_from="2026-01-01T00:00:00Z")
    stale = _evidence(valid_to="2025-01-01T00:00:00Z")
    fresh = _evidence(valid_from="2025-01-01T00:00:00Z")

    assert _evaluate(tc02.evaluate, _supported_pack(claim, stale))[0].truth_class == (
        TruthClass.TC_02
    )
    assert _evaluate(tc02.evaluate, _supported_pack(claim, fresh)) == ()


def test_tc03_unqualified_critical_claim_positive_and_negative() -> None:
    claim = _claim(critical=True)
    unqualified = _evidence(kind=EvidenceKind.RETRIEVAL_SNIPPET)
    qualified = _evidence(kind=EvidenceKind.DOCUMENT_SEGMENT)

    assert _evaluate(tc03.evaluate, _supported_pack(claim, unqualified))[0].truth_class == (
        TruthClass.TC_03
    )
    assert _evaluate(tc03.evaluate, _supported_pack(claim, qualified)) == ()


def test_tc04_orphan_claim_positive_and_negative() -> None:
    claim = _claim()
    evidence = _evidence()
    positive = Pack(
        id="pack-tc04-pos",
        version="0.1",
        claims=(claim,),
        evidence=(evidence,),
        links=(_support(claim, evidence),),
    )

    assert _evaluate(tc04.evaluate, positive)[0].truth_class == TruthClass.TC_04
    assert _evaluate(tc04.evaluate, _supported_pack(claim)) == ()


def test_tc05_missing_provenance_positive_and_negative() -> None:
    positive = _supported_pack(_claim(content_hash=None))
    negative = _supported_pack(_claim(content_hash="claim-content"))

    assert _evaluate(tc05.evaluate, positive)[0].truth_class == TruthClass.TC_05
    assert _evaluate(tc05.evaluate, negative) == ()


def test_tc07_ledger_contradiction_positive_and_negative() -> None:
    claim = _claim()
    ledger_fact = _evidence(kind=EvidenceKind.LEDGER_FACT)
    entity, about = _about(claim)
    positive = Pack(
        id="pack-tc07-pos",
        version="0.1",
        claims=(claim,),
        evidence=(ledger_fact,),
        entities=(entity,),
        links=(_support(claim, ledger_fact, LinkRelation.CONTRADICTS), about),
    )

    assert _evaluate(tc07.evaluate, positive)[0].truth_class == TruthClass.TC_07
    assert _evaluate(tc07.evaluate, _supported_pack(claim, ledger_fact)) == ()


def test_tc08_self_contradiction_positive_and_negative() -> None:
    left = _claim("claim-left", subject="pump", relation="status", obj="open")
    right = _claim("claim-right", subject="pump", relation="status", obj="closed")
    same = _claim("claim-same", subject="pump", relation="status", obj="open")

    positive = Pack(id="pack-tc08-pos", version="0.1", claims=(left, right))
    negative = Pack(id="pack-tc08-neg", version="0.1", claims=(left, same))

    assert _evaluate(tc08.evaluate, positive)[0].truth_class == TruthClass.TC_08
    assert _evaluate(tc08.evaluate, negative) == ()


def test_precedence_keeps_critical_class_for_same_claim() -> None:
    claim = _claim(critical=True)
    entity, about = _about(claim)
    pack = Pack(
        id="pack-precedence",
        version="0.1",
        claims=(claim,),
        entities=(entity,),
        links=(about,),
    )
    result = build_graph(pack)
    assert result.graph is not None

    findings = evaluate_predicates(result.graph, _rulepack())

    assert tuple(item.truth_class for item in findings) == (TruthClass.TC_03,)


def test_positive_fixtures_fail_against_noop_mutant() -> None:
    def noop(context: PredicateContext, rulepack: RulePack) -> tuple[Finding, ...]:
        return ()

    positives: tuple[tuple[Predicate, Pack], ...] = (
        (tc01.evaluate, Pack(id="m-tc01", version="0.1", claims=(_claim(),))),
        (
            tc02.evaluate,
            _supported_pack(
                _claim(valid_from="2026-01-01T00:00:00Z"),
                _evidence(valid_to="2025-01-01T00:00:00Z"),
            ),
        ),
        (
            tc03.evaluate,
            _supported_pack(
                _claim(critical=True),
                _evidence(kind=EvidenceKind.RETRIEVAL_SNIPPET),
            ),
        ),
        (tc04.evaluate, Pack(id="m-tc04", version="0.1", claims=(_claim(),))),
        (tc05.evaluate, _supported_pack(_claim(content_hash=None))),
        (
            tc07.evaluate,
            Pack(
                id="m-tc07",
                version="0.1",
                claims=(_claim(),),
                evidence=(_evidence(kind=EvidenceKind.LEDGER_FACT),),
                links=(
                    _support(
                        _claim(),
                        _evidence(kind=EvidenceKind.LEDGER_FACT),
                        LinkRelation.CONTRADICTS,
                    ),
                ),
            ),
        ),
        (
            tc08.evaluate,
            Pack(
                id="m-tc08",
                version="0.1",
                claims=(
                    _claim("a", subject="x", relation="is", obj="one"),
                    _claim("b", subject="x", relation="is", obj="two"),
                ),
            ),
        ),
    )

    for predicate, pack in positives:
        assert _evaluate(predicate, pack) != _evaluate(noop, pack)


def test_predicate_modules_do_not_import_nondeterministic_apis() -> None:
    banned = {"datetime", "os", "random", "requests", "socket", "urllib", "uuid", "httpx"}
    predicate_dir = ROOT / "src" / "truthkernel" / "predicates"

    for path in sorted(predicate_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert imports.isdisjoint(banned), path


def test_strict_default_rulepack_is_valid_json() -> None:
    data = json.loads((ROOT / "rulepacks" / "strict-default" / "rulepack.json").read_text())

    assert RulePack.model_validate(data).name == "strict-default"
