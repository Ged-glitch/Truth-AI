"""Write M4 decision-bundle golden fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from m4_examples import build_bundle_case, bundle_cases

from truthkernel.canonical import canonical_text

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "fixtures" / "golden" / "m4"


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}

    for name, case in bundle_cases().items():
        bundle = build_bundle_case(case)
        (GOLDEN_DIR / f"{name}.bundle.json").write_text(
            canonical_text(bundle) + "\n",
            encoding="utf-8",
        )
        hashes[name] = bundle.id

    (GOLDEN_DIR / "hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
