from __future__ import annotations

import json
from pathlib import Path

from truthkernel.schemas import DecisionBundle

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "fixtures" / "golden" / "m4"


def test_m4_golden_bundles_are_stable_across_30_runs() -> None:
    expected = json.loads((GOLDEN_DIR / "hashes.json").read_text(encoding="utf-8"))

    for _ in range(30):
        actual: dict[str, str] = {}
        for path in sorted(GOLDEN_DIR.glob("*.bundle.json")):
            case_name = path.name.removesuffix(".bundle.json")
            bundle = DecisionBundle.model_validate_json(path.read_text(encoding="utf-8"))
            actual[case_name] = bundle.id
        assert actual == expected
