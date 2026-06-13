"""Replay checks for committed golden fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from truthkernel.canonical import sha256_of


def replay_golden(golden_dir: Path, runs: int, byte_equal: bool) -> None:
    """Replay graph golden fixtures for byte-equal determinism."""
    if not byte_equal:
        raise ValueError("M2 replay only supports byte-equal mode")
    if runs < 1:
        raise ValueError("runs must be at least 1")

    m2_dir = golden_dir / "m2"
    expected = json.loads((m2_dir / "hashes.json").read_text(encoding="utf-8"))

    for _ in range(runs):
        actual = {
            path.name.removesuffix(".graph.json"): str(
                json.loads(path.read_text(encoding="utf-8"))["graph_hash"]
            )
            for path in sorted(m2_dir.glob("*.graph.json"))
        }
        if actual != expected:
            raise ValueError("golden graph hash mismatch")
        for path in sorted(m2_dir.glob("*.graph.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload_without_hash = {
                key: value for key, value in payload.items() if key != "graph_hash"
            }
            if sha256_of(payload_without_hash) != payload["graph_hash"]:
                raise ValueError(f"graph hash mismatch in {path}")
