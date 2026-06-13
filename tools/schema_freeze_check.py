"""Verify exported schema hashes against the committed freeze file."""

from __future__ import annotations

import json
from pathlib import Path

from truthkernel.canonical import sha256_of

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "json"
FREEZE_FILE = ROOT / "schemas" / "schema-hashes.json"


def main() -> None:
    expected = json.loads(FREEZE_FILE.read_text(encoding="utf-8"))
    actual: dict[str, str] = {}

    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        actual[schema_path.name] = sha256_of(json.loads(schema_path.read_text(encoding="utf-8")))

    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        changed = sorted(
            name for name in set(actual).intersection(expected) if actual[name] != expected[name]
        )
        details = {
            "missing": missing,
            "unexpected": unexpected,
            "changed": changed,
        }
        raise SystemExit(f"schema freeze mismatch: {details}")


if __name__ == "__main__":
    main()
