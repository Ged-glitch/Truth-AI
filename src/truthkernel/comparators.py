"""Typed value comparators used by deterministic predicates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from truthkernel.schemas import Claim


class Comparison(StrEnum):
    EQUAL = "equal"
    DIFFERENT = "different"
    DIMENSION_MISMATCH = "dimension_mismatch"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class UnitValue:
    value: Decimal
    unit: str
    dimension: str


_UNIT_DIMENSIONS = {
    "mm": "length",
    "cm": "length",
    "m": "length",
    "g": "mass",
    "kg": "mass",
    "s": "time",
}

_UNIT_SCALE_TO_BASE = {
    "mm": Decimal("0.001"),
    "cm": Decimal("0.01"),
    "m": Decimal("1"),
    "g": Decimal("0.001"),
    "kg": Decimal("1"),
    "s": Decimal("1"),
}


def parse_utc_datetime(value: str) -> datetime:
    """Parse an ISO-like timestamp and normalise it to UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def intervals_overlap(
    left_start: str | None,
    left_end: str | None,
    right_start: str | None,
    right_end: str | None,
) -> bool:
    """Return whether two half-open validity intervals overlap."""
    left_start_dt = (
        parse_utc_datetime(left_start) if left_start else datetime.min.replace(tzinfo=UTC)
    )
    left_end_dt = parse_utc_datetime(left_end) if left_end else datetime.max.replace(tzinfo=UTC)
    right_start_dt = (
        parse_utc_datetime(right_start) if right_start else datetime.min.replace(tzinfo=UTC)
    )
    right_end_dt = parse_utc_datetime(right_end) if right_end else datetime.max.replace(tzinfo=UTC)
    return left_start_dt < right_end_dt and right_start_dt < left_end_dt


def decimal_equal(left: Decimal, right: Decimal, tolerance: Decimal = Decimal("0")) -> bool:
    """Compare decimals exactly or with an explicit tolerance."""
    return abs(left - right) <= tolerance


def enum_equal(left: str, right: str) -> bool:
    """Compare enum-like string values exactly."""
    return left == right


def unit_value(value: Decimal, unit: str) -> UnitValue:
    """Build a known unit value or raise for unsupported units."""
    if unit not in _UNIT_DIMENSIONS:
        raise ValueError(f"unsupported unit: {unit}")
    return UnitValue(value=value, unit=unit, dimension=_UNIT_DIMENSIONS[unit])


def compare_units(
    left: UnitValue,
    right: UnitValue,
    tolerance: Decimal = Decimal("0"),
) -> Comparison:
    """Compare supported units using a small fixed dimension table."""
    if left.dimension != right.dimension:
        return Comparison.DIMENSION_MISMATCH
    left_base = left.value * _UNIT_SCALE_TO_BASE[left.unit]
    right_base = right.value * _UNIT_SCALE_TO_BASE[right.unit]
    if decimal_equal(left_base, right_base, tolerance):
        return Comparison.EQUAL
    return Comparison.DIFFERENT


def _coerce_decimal(value: object) -> Decimal | None:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation:
            return None
    return None


def claims_conflict(left: Claim, right: Claim) -> bool:
    """Return whether two claims conflict on canonical SROM."""
    if left.subject != right.subject or left.relation != right.relation:
        return False

    left_value = left.modifiers.get("value")
    right_value = right.modifiers.get("value")
    left_unit = left.modifiers.get("unit")
    right_unit = right.modifiers.get("unit")
    left_decimal = _coerce_decimal(left_value)
    right_decimal = _coerce_decimal(right_value)
    if left_decimal is not None and right_decimal is not None:
        if isinstance(left_unit, str) and isinstance(right_unit, str):
            unit_comparison = compare_units(
                unit_value(left_decimal, left_unit),
                unit_value(right_decimal, right_unit),
            )
            return unit_comparison in {
                Comparison.DIFFERENT,
                Comparison.DIMENSION_MISMATCH,
            }
        return not decimal_equal(left_decimal, right_decimal)

    return left.object != right.object
