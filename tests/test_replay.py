from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from truthkernel.replay import replay_golden
from truthkernel.schemas import (
    Decision,
    DecisionBundle,
    Finding,
    RemedyType,
    Severity,
    TruthClass,
)


def test_m2_and_m4_replay_runs_byte_equal() -> None:
    golden_dir = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

    replay_golden(golden_dir=golden_dir, runs=3, byte_equal=True)


def test_replay_is_hash_seed_independent() -> None:
    golden_dir = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

    first = run_truth_replay(golden_dir, "1")
    second = run_truth_replay(golden_dir, "2")

    assert first.stdout == second.stdout == "replay passed\n"
    assert first.stderr == second.stderr == ""


def test_replay_rejects_noncanonical_bundle_fixture(tmp_path: Path) -> None:
    golden_dir = tmp_path / "golden"
    m4_dir = golden_dir / "m4"
    m4_dir.mkdir(parents=True)

    bundle = sample_bundle()
    payload = bundle.model_dump(mode="json")
    (m4_dir / "bad.bundle.json").write_text(
        json.dumps(payload, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="decision bundle is not canonical"):
        replay_golden(golden_dir=golden_dir, runs=1, byte_equal=True)


def run_truth_replay(golden_dir: Path, seed: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = seed
    return subprocess.run(
        [
            "uv",
            "run",
            "truth",
            "replay",
            str(golden_dir),
            "--runs",
            "2",
            "--byte-equal",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def sample_bundle() -> DecisionBundle:
    return DecisionBundle(
        id="bundle-replay",
        pack_hash="pack-replay",
        claim_graph_hash="graph-replay",
        evidence_snapshot_hashes=("snapshot-replay",),
        ledger_root=None,
        policy_hash="policy-replay",
        taxonomy_hash="taxonomy-replay",
        kernel_version="0.1.0",
        compiler_id="replay-test",
        verifier_ids=("verifier-a",),
        verifier_weights={},
        findings=(
            Finding(
                id="finding-replay",
                truth_class=TruthClass.TC_01,
                severity=Severity.MAJOR,
                claim_ids=("claim-replay",),
                evidence_ids=("evidence-replay",),
                message="Replay test bundle",
                remedy_type=RemedyType.SUPPLY_EVIDENCE,
                conflicting_ledger_entry_ids=(),
            ),
        ),
        finding_counts={TruthClass.TC_01: 1},
        decision=Decision.REJECT,
        repair_contract_id=None,
    )
