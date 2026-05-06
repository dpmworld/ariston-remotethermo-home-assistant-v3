"""Tests for the energy/consumption helpers (issue #439)."""

import datetime as dt
from types import SimpleNamespace

import pytest
from ariston.const import ConsumptionTimeInterval, ConsumptionType

from custom_components.ariston.energy import period_last_reset, period_total


def _device(sequences):
    return SimpleNamespace(consumptions_sequences=sequences)


def test_period_total_last_day_slices_to_today_only():
    """Rolling-24h v[] for LAST_DAY: only today's slice (v[23 - hour:]) is summed.

    Reproduces the live response observed on the user's Nuos at 14:05 UTC:
    v[19] = 0.45 (today 10:00 UTC), v[4] = 0.45 (yesterday 19:00 UTC).
    Today's slice (v[9:]) sums to 0.45, NOT 0.90.
    """
    v = [0.0] * 24
    v[19] = 0.45  # today 10:00 UTC
    v[4] = 0.45   # yesterday 19:00 UTC
    sequences = [
        {
            "k": ConsumptionType.DOMESTIC_HOT_WATER_HEATING_PUMP_ELECTRICITY.value,
            "p": ConsumptionTimeInterval.LAST_DAY.value,
            "v": v,
        }
    ]
    now = dt.datetime(2026, 5, 6, 14, 5, 0, tzinfo=dt.timezone.utc)
    total = period_total(
        _device(sequences),
        ConsumptionType.DOMESTIC_HOT_WATER_HEATING_PUMP_ELECTRICITY,
        ConsumptionTimeInterval.LAST_DAY,
        now=now,
    )
    assert total == pytest.approx(0.45)


def test_period_total_last_day_at_midnight_returns_only_current_hour():
    v = [0.1] * 24  # every bucket has consumption
    v[23] = 0.05    # current hour just started
    sequences = [
        {
            "k": ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY.value,
            "p": ConsumptionTimeInterval.LAST_DAY.value,
            "v": v,
        }
    ]
    now = dt.datetime(2026, 5, 6, 0, 5, 0, tzinfo=dt.timezone.utc)
    total = period_total(
        _device(sequences),
        ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY,
        ConsumptionTimeInterval.LAST_DAY,
        now=now,
    )
    assert total == pytest.approx(0.05)


def test_period_total_last_day_at_23utc_sums_full_array():
    v = [0.1] * 24
    sequences = [
        {
            "k": ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY.value,
            "p": ConsumptionTimeInterval.LAST_DAY.value,
            "v": v,
        }
    ]
    now = dt.datetime(2026, 5, 6, 23, 59, 0, tzinfo=dt.timezone.utc)
    total = period_total(
        _device(sequences),
        ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY,
        ConsumptionTimeInterval.LAST_DAY,
        now=now,
    )
    assert total == pytest.approx(2.4)


def test_period_total_non_last_day_sums_full_array():
    """Week/month/year intervals are summed in full (no slicing yet)."""
    sequences = [
        {
            "k": ConsumptionType.DOMESTIC_HOT_WATER_ELECTRICITY.value,
            "p": ConsumptionTimeInterval.LAST_WEEK.value,
            "v": [None, 1.2, None, 0.8],
        }
    ]
    total = period_total(
        _device(sequences),
        ConsumptionType.DOMESTIC_HOT_WATER_ELECTRICITY,
        ConsumptionTimeInterval.LAST_WEEK,
    )
    assert total == pytest.approx(2.0)


def test_period_total_last_day_short_array_falls_back_to_full_sum():
    """If for some reason v[] isn't 24 elements, do not slice (defensive)."""
    sequences = [
        {
            "k": ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY.value,
            "p": ConsumptionTimeInterval.LAST_DAY.value,
            "v": [0.1, 0.2, 0.3],
        }
    ]
    now = dt.datetime(2026, 5, 6, 14, 0, 0, tzinfo=dt.timezone.utc)
    total = period_total(
        _device(sequences),
        ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY,
        ConsumptionTimeInterval.LAST_DAY,
        now=now,
    )
    assert total == pytest.approx(0.6)


def test_period_total_returns_none_when_no_sequences():
    assert (
        period_total(
            _device([]),
            ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY,
            ConsumptionTimeInterval.LAST_DAY,
        )
        is None
    )


def test_period_total_returns_none_when_no_match():
    sequences = [
        {
            "k": ConsumptionType.CENTRAL_HEATING_GAS.value,
            "p": ConsumptionTimeInterval.LAST_DAY.value,
            "v": [1.0, 2.0],
        }
    ]
    assert (
        period_total(
            _device(sequences),
            ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY,
            ConsumptionTimeInterval.LAST_DAY,
        )
        is None
    )


def test_period_total_returns_none_for_empty_buckets():
    sequences = [
        {
            "k": ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY.value,
            "p": ConsumptionTimeInterval.LAST_DAY.value,
            "v": [],
        }
    ]
    assert (
        period_total(
            _device(sequences),
            ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY,
            ConsumptionTimeInterval.LAST_DAY,
        )
        is None
    )


def test_last_reset_day_is_midnight_utc():
    now = dt.datetime(2026, 5, 6, 14, 32, 17, tzinfo=dt.timezone.utc)
    reset = period_last_reset(ConsumptionTimeInterval.LAST_DAY, now=now)
    assert reset == dt.datetime(2026, 5, 6, 0, 0, 0, tzinfo=dt.timezone.utc)


def test_last_reset_week_is_monday_midnight_utc():
    # 2026-05-06 is a Wednesday.
    now = dt.datetime(2026, 5, 6, 14, 32, 17, tzinfo=dt.timezone.utc)
    reset = period_last_reset(ConsumptionTimeInterval.LAST_WEEK, now=now)
    assert reset == dt.datetime(2026, 5, 4, 0, 0, 0, tzinfo=dt.timezone.utc)


def test_last_reset_month_is_first_of_month_utc():
    now = dt.datetime(2026, 5, 6, 14, 32, 17, tzinfo=dt.timezone.utc)
    reset = period_last_reset(ConsumptionTimeInterval.LAST_MONTH, now=now)
    assert reset == dt.datetime(2026, 5, 1, 0, 0, 0, tzinfo=dt.timezone.utc)


def test_last_reset_year_is_first_of_year_utc():
    now = dt.datetime(2026, 5, 6, 14, 32, 17, tzinfo=dt.timezone.utc)
    reset = period_last_reset(ConsumptionTimeInterval.LAST_YEAR, now=now)
    assert reset == dt.datetime(2026, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)


def test_last_reset_normalizes_naive_input_as_utc():
    now = dt.datetime(2026, 5, 6, 14, 32, 17)
    reset = period_last_reset(ConsumptionTimeInterval.LAST_DAY, now=now)
    assert reset.tzinfo == dt.timezone.utc
    assert reset.date() == dt.date(2026, 5, 6)
