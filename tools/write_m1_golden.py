"""Write M1 canonical golden pack fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from m1_examples import example_pack_hashes, example_packs

from truthkernel.canonical import canonical_text

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "fixtures" / "golden" / "m1"


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    for name, pack in example_packs().items():
        (GOLDEN_DIR / f"{name}.pack.json").write_text(canonical_text(pack) + "\n", encoding="utf-8")

    (GOLDEN_DIR / "hashes.json").write_text(
        json.dumps(example_pack_hashes(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
