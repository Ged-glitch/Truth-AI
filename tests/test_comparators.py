from decimal import Decimal

from truthkernel.comparators import Comparison, compare_units, intervals_overlap, unit_value


def test_decimal_units_compare_across_same_dimension() -> None:
    assert compare_units(unit_value(Decimal("100"), "cm"), unit_value(Decimal("1"), "m")) == (
        Comparison.EQUAL
    )


def test_unit_dimension_mismatch_is_reported() -> None:
    assert compare_units(unit_value(Decimal("1"), "m"), unit_value(Decimal("1"), "kg")) == (
        Comparison.DIMENSION_MISMATCH
    )


def test_utc_intervals_overlap() -> None:
    assert intervals_overlap("2026-01-01T00:00:00Z", None, "2026-06-01T00:00:00+00:00", None)


def test_utc_intervals_can_be_disjoint() -> None:
    assert not intervals_overlap(
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        "2026-03-01T00:00:00Z",
        None,
    )
