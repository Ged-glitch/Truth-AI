"""Replay checks for committed golden fixtures."""

from __future__ import annotations

import json
import locale
import os
import time
from pathlib import Path

from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.schemas import DecisionBundle


def replay_golden(golden_dir: Path, runs: int, byte_equal: bool) -> None:
    """Replay graph and decision-bundle fixtures for byte-equal determinism."""
    enforce_runtime_environment()
    if not byte_equal:
        raise ValueError("replay only supports byte-equal mode")
    if runs < 1:
        raise ValueError("runs must be at least 1")

    expected = _snapshot_golden(golden_dir)

    for _ in range(runs):
        actual = _snapshot_golden(golden_dir)
        if actual != expected:
            raise ValueError("golden replay bytes mismatch")


def enforce_runtime_environment() -> None:
    """Pin locale and timezone for deterministic replay output."""
    locale.setlocale(locale.LC_ALL, "C")
    os.environ["TZ"] = "UTC"
    if hasattr(time, "tzset"):
        time.tzset()


def _snapshot_golden(golden_dir: Path) -> tuple[tuple[str, bytes], ...]:
    snapshots: list[tuple[str, bytes]] = []
    snapshots.extend(_snapshot_graphs(golden_dir / "m2"))
    snapshots.extend(_snapshot_bundles(golden_dir / "m4"))
    return tuple(sorted(snapshots, key=lambda item: item[0]))


def _snapshot_graphs(m2_dir: Path) -> tuple[tuple[str, bytes], ...]:
    if not m2_dir.exists():
        return ()

    snapshots: list[tuple[str, bytes]] = []
    for path in sorted(m2_dir.glob("*.graph.json")):
        raw = path.read_bytes()
        normalised = _normalise_newlines(raw)
        payload = json.loads(raw.decode("utf-8"))
        canonical = (canonical_text(payload) + "\n").encode("utf-8")
        if normalised != canonical:
            raise ValueError(f"graph fixture is not canonical: {path}")
        payload_without_hash = {key: value for key, value in payload.items() if key != "graph_hash"}
        if sha256_of(payload_without_hash) != payload["graph_hash"]:
            raise ValueError(f"graph hash mismatch in {path}")
        snapshots.append((f"m2/{path.name}", canonical))
    return tuple(snapshots)


def _snapshot_bundles(m4_dir: Path) -> tuple[tuple[str, bytes], ...]:
    if not m4_dir.exists():
        return ()

    snapshots: list[tuple[str, bytes]] = []
    for path in sorted(m4_dir.glob("*.bundle.json")):
        raw = path.read_bytes()
        normalised = _normalise_newlines(raw)
        bundle = DecisionBundle.model_validate_json(raw.decode("utf-8"))
        canonical = (canonical_text(bundle) + "\n").encode("utf-8")
        if normalised != canonical:
            raise ValueError(f"decision bundle is not canonical: {path}")
        snapshots.append((f"m4/{path.name}", canonical))
    return tuple(snapshots)


def _normalise_newlines(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n")
