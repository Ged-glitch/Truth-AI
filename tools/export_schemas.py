"""Export Pydantic JSON Schemas and their freeze hashes."""

from __future__ import annotations

import json
from pathlib import Path

from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.schemas.models import schema_models_by_name

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "json"
FREEZE_FILE = ROOT / "schemas" / "schema-hashes.json"


def main() -> None:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}

    for name, model in schema_models_by_name().items():
        schema = model.model_json_schema()
        path = SCHEMA_DIR / f"{name}.schema.json"
        path.write_text(canonical_text(schema) + "\n", encoding="utf-8")
        hashes[path.name] = sha256_of(schema)

    FREEZE_FILE.parent.mkdir(parents=True, exist_ok=True)
    FREEZE_FILE.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
