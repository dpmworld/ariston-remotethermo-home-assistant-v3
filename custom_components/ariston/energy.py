"""Helpers to compute energy/consumption sensor values from Ariston cloud data.

Workaround for upstream issue #439. The library getter
`_get_consumption_sequence_last_value` returns only the last bucket of the
`v[]` time-series (e.g. just the last hour of the LAST_DAY interval),
which makes the sensor look like it is reporting a constant ~hourly power
reading instead of an accumulating consumption value. Combined with a
`last_reset` timestamp that the library rewrites to `now - 1h` whenever the
sequences rotate, the HA Energy Dashboard sees frequent fake resets.

This module accesses `device.consumptions_sequences` directly and exposes:

  - `period_total(device, consumption_type, time_interval)` returns the
    sum of `v[]` for the matching `k`/`p` entry, i.e. the full period
    total instead of just the last bucket.
  - `period_last_reset(time_interval)` returns a stable UTC timestamp at
    the start of the period so the HA Energy Dashboard treats one full
    period as a single accumulating window.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from ariston.const import ConsumptionTimeInterval, ConsumptionType


def period_total(
    device,
    consumption_type: ConsumptionType,
    time_interval: ConsumptionTimeInterval,
    *,
    now: Optional[dt.datetime] = None,
) -> Optional[float]:
    """Sum of bucket values for the given consumption type and period.

    Live API inspection (2026-05-06) showed that `v[]` for `LAST_DAY` is a
    rolling 24-hour series of hourly buckets where `v[23]` is the current
    hour and `v[0]` is 23 hours ago. Summing the whole array therefore
    produces a rolling-24h total, not "today so far", and bleeds yesterday
    into today's reading.

    For `LAST_DAY` we slice to today's portion only (UTC), so the value
    pairs cleanly with `last_reset = midnight UTC` for HA's Energy
    Dashboard. For other intervals (week / month / year) we sum the whole
    `v[]`; refining those is left for future work.

    Returns None if the device has not yet fetched any sequences or the
    expected (k, p) tuple is not present or has empty data.
    """
    sequences = getattr(device, "consumptions_sequences", None)
    if not sequences:
        return None
    for sequence in sequences:
        if (
            sequence.get("k") == consumption_type.value
            and sequence.get("p") == time_interval.value
        ):
            buckets = sequence.get("v") or []
            if not buckets:
                return None
            if time_interval == ConsumptionTimeInterval.LAST_DAY and len(buckets) == 24:
                current = now if now is not None else dt.datetime.now(dt.timezone.utc)
                if current.tzinfo is None:
                    current = current.replace(tzinfo=dt.timezone.utc)
                else:
                    current = current.astimezone(dt.timezone.utc)
                # v[23] = current hour; today's slice covers hours
                # [23 - utc_hour .. 23] inclusive (utc_hour + 1 buckets).
                start = 23 - current.hour
                buckets = buckets[start:]
            total = 0.0
            for value in buckets:
                if value is None:
                    continue
                total += float(value)
            return total
    return None


def period_last_reset(
    time_interval: ConsumptionTimeInterval,
    *,
    now: Optional[dt.datetime] = None,
) -> dt.datetime:
    """Return a stable UTC start-of-period timestamp.

    The Ariston cloud rolls hourly buckets within `LAST_DAY`, daily
    buckets within `LAST_WEEK`/`LAST_MONTH`, and so on. Anchoring
    `last_reset` to the start of the period (UTC midnight, week start,
    etc.) means HA sees one reset per period instead of one per cloud
    fetch.
    """
    current = now if now is not None else dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    else:
        current = current.astimezone(dt.timezone.utc)

    midnight = current.replace(hour=0, minute=0, second=0, microsecond=0)

    if time_interval == ConsumptionTimeInterval.LAST_DAY:
        return midnight
    if time_interval == ConsumptionTimeInterval.LAST_WEEK:
        # ISO weekday: Monday = 0
        return midnight - dt.timedelta(days=current.weekday())
    if time_interval == ConsumptionTimeInterval.LAST_MONTH:
        return midnight.replace(day=1)
    if time_interval == ConsumptionTimeInterval.LAST_YEAR:
        return midnight.replace(month=1, day=1)
    return midnight
