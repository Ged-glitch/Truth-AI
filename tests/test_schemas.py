import json
from decimal import Decimal
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from truthkernel.canonical import canonical_text, sha256_of
from truthkernel.schemas import Claim, ClaimType, Pack, Provenance
from truthkernel.schemas.models import schema_model_names

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "fixtures" / "golden" / "m1"
SCHEMA_DIR = ROOT / "schemas" / "json"


identifier = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="-_"),
    min_size=1,
    max_size=32,
)


@given(
    claim_id=identifier,
    subject=identifier,
    relation=identifier,
    obj=identifier,
    claim_type=st.sampled_from(tuple(ClaimType)),
    critical=st.booleans(),
    amount=st.decimals(allow_nan=False, allow_infinity=False, places=2),
)
@settings(max_examples=50)
def test_pack_round_trip_property(
    claim_id: str,
    subject: str,
    relation: str,
    obj: str,
    claim_type: ClaimType,
    critical: bool,
    amount: Decimal,
) -> None:
    claim = Claim(
        id=claim_id,
        text=f"{subject} {relation} {obj}",
        subject=subject,
        relation=relation,
        object=obj,
        modifiers={"amount": amount},
        claim_type=claim_type,
        gate_relevant=claim_type in (ClaimType.FACTUAL, ClaimType.CALCULATION, ClaimType.CITATION),
        critical=critical,
        provenance=Provenance(model_id="hypothesis"),
    )
    pack = Pack(id=f"pack-{claim_id}", version="0.1", claims=(claim,))

    encoded = canonical_text(pack)
    reparsed = Pack.model_validate_json(encoded)

    assert reparsed == pack
    assert canonical_text(reparsed) == encoded


def test_all_schema_models_are_exported() -> None:
    exported = sorted(
        path.stem.removesuffix(".schema") for path in SCHEMA_DIR.glob("*.schema.json")
    )

    assert exported == list(schema_model_names())


def test_schema_freeze_hashes_match_exports() -> None:
    frozen = json.loads((ROOT / "schemas" / "schema-hashes.json").read_text(encoding="utf-8"))
    actual = {
        path.name: sha256_of(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(SCHEMA_DIR.glob("*.schema.json"))
    }

    assert actual == frozen


def test_m1_golden_pack_hashes_are_stable_across_30_runs() -> None:
    expected = json.loads((GOLDEN_DIR / "hashes.json").read_text(encoding="utf-8"))

    for _ in range(30):
        actual = {}
        for path in sorted(GOLDEN_DIR.glob("*.pack.json")):
            name = path.name.removesuffix(".pack.json")
            pack = Pack.model_validate_json(path.read_text(encoding="utf-8"))
            actual[name] = sha256_of(pack)
        assert actual == expected
