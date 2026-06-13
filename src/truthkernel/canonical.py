"""Canonical JSON and SHA-256 helpers."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel


class CanonicalisationError(TypeError):
    """Raised when a value cannot be represented in Truth-AI canonical JSON."""


def _normalise(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _normalise(value.model_dump(mode="python", by_alias=False, exclude_none=False))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalisationError("non-finite decimals are forbidden")
        return format(value, "f")
    if isinstance(value, float):
        raise CanonicalisationError("binary floats are forbidden in hashed payloads")
    if isinstance(value, dict):
        normalised: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalisationError("canonical JSON object keys must be strings")
            normalised[key] = _normalise(item)
        return {key: normalised[key] for key in sorted(normalised)}
    if isinstance(value, (list, tuple)):
        return [_normalise(item) for item in value]
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise CanonicalisationError(f"unsupported canonical JSON value: {type(value).__name__}")


def canonicalise(obj: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes for a supported object."""
    normalised = _normalise(obj)
    text = json.dumps(
        normalised,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return text.encode("utf-8")


def canonical_text(obj: Any) -> str:
    """Return canonical JSON as text."""
    return canonicalise(obj).decode("utf-8")


def sha256_of(obj: Any) -> str:
    """Return the SHA-256 hex digest of an object's canonical JSON form."""
    return hashlib.sha256(canonicalise(obj)).hexdigest()
