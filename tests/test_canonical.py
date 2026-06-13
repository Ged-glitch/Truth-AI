from decimal import Decimal

import pytest

from truthkernel.canonical import CanonicalisationError, canonical_text, sha256_of


def test_canonical_json_sorts_keys_and_serialises_decimals_as_strings() -> None:
    payload = {"z": Decimal("4.20"), "a": {"b": True}}

    assert canonical_text(payload) == '{"a":{"b":true},"z":"4.20"}'


def test_sha256_is_stable_for_equal_payloads_with_different_key_order() -> None:
    left = {"b": "two", "a": "one"}
    right = {"a": "one", "b": "two"}

    assert sha256_of(left) == sha256_of(right)


def test_binary_floats_are_rejected() -> None:
    with pytest.raises(CanonicalisationError):
        canonical_text({"value": 1.2})


def test_non_finite_decimals_are_rejected() -> None:
    with pytest.raises(CanonicalisationError):
        canonical_text({"value": Decimal("NaN")})
