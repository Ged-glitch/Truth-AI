"""Write M2 graph golden fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from m1_examples import example_packs

from truthkernel.canonical import canonical_text
from truthkernel.graph import build_graph

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "fixtures" / "golden" / "m2"


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}

    for name, pack in example_packs().items():
        result = build_graph(pack)
        if result.graph is None:
            raise RuntimeError(f"example pack is malformed: {name}")
        (GOLDEN_DIR / f"{name}.graph.json").write_text(
            canonical_text(result.graph) + "\n",
            encoding="utf-8",
        )
        hashes[name] = str(result.graph["graph_hash"])

    (GOLDEN_DIR / "hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
