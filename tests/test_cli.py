from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from truthkernel.canonical import canonical_text
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

ROOT = Path(__file__).resolve().parents[1]
RULEPACK = ROOT / "rulepacks" / "strict-default" / "rulepack.json"
MINIMAL_PACK = ROOT / "fixtures" / "golden" / "m1" / "minimal-supported.pack.json"


def test_truth_version_smoke() -> None:
    result = run_truth("--version")

    assert result.returncode == 0
    assert result.stdout.strip() == "0.1.0"


def test_truth_verify_accepts_and_writes_ledger(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger"
    result = run_truth(
        "verify",
        str(MINIMAL_PACK),
        str(RULEPACK),
        str(ledger_path),
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "accept"

    facts = run_truth("ledger", "facts", str(ledger_path), "--json")
    payload = json.loads(facts.stdout)
    assert payload and payload[0]["claim_id"] == "claim-alpha"

    snapshot = run_truth("ledger", "snapshot", str(ledger_path), "--json")
    snapshot_payload = json.loads(snapshot.stdout)
    assert snapshot_payload["facts"][0]["claim_id"] == "claim-alpha"

    show = run_truth("ledger", "show", str(ledger_path), "--json")
    show_payload = json.loads(show.stdout)
    assert show_payload["head_hash"] == snapshot_payload["head_hash"]


def test_truth_verify_rejects_and_returns_exit_one(tmp_path: Path) -> None:
    pack_path = tmp_path / "reject.pack.json"
    pack_path.write_text(canonical_text(reject_pack()) + "\n", encoding="utf-8")

    result = run_truth("verify", str(pack_path), str(RULEPACK), str(tmp_path / "ledger"))

    assert result.returncode == 1
    assert result.stdout.strip() == "reject"


def test_truth_fixtures_make_writes_bundle(tmp_path: Path) -> None:
    output_path = tmp_path / "fixtures" / "bundle.json"
    result = run_truth(
        "fixtures",
        "make",
        str(MINIMAL_PACK),
        str(RULEPACK),
        str(output_path),
        "--json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["output_path"] == str(output_path)
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").endswith("\n")


def run_truth(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "1"
    return subprocess.run(
        ["uv", "run", "truth", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def reject_pack() -> Pack:
    claim = Claim(
        id="claim-reject",
        text="The system uses an unqualified critical claim.",
        subject="system",
        relation="uses",
        object="critical claim",
        claim_type=ClaimType.FACTUAL,
        gate_relevant=True,
        critical=True,
        provenance=Provenance(model_id="test"),
    )
    evidence = Evidence(
        id="evidence-reject",
        kind=EvidenceKind.RETRIEVAL_SNIPPET,
        text="Snippet used for rejection smoke testing.",
        snapshot_hash="snapshot-reject",
        provenance=Provenance(source_uri="fixture://reject", content_hash="content-reject"),
    )
    entity = Entity(id="entity-reject", kind="system", label="Reject test")
    link = Link(
        id="link-reject",
        source_id=claim.id,
        relation=LinkRelation.SUPPORTS,
        target_id=evidence.id,
    )
    return Pack(
        id="pack-reject",
        version="0.1",
        claims=(claim,),
        evidence=(evidence,),
        entities=(entity,),
        links=(link,),
    )
