"""Live inspection of consSequencesApi8 response shape.

Goal: figure out whether `v[]` for `LAST_DAY` is calendar-day-aligned
(24 hourly buckets 00:00-23:00 UTC/local) or rolling-24h. This determines
whether `last_reset=midnight UTC` in the HA energy sensors is correct.

Usage:
    ARISTON_USER=... ARISTON_PASS=... .venv/bin/python scripts/inspect_consumptions.py
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import sys

from ariston import async_hello, async_discover
from ariston.const import DeviceAttribute


def _mask(s: str) -> str:
    if not s or len(s) < 6:
        return "***"
    return s[:3] + "..." + s[-3:]


async def main() -> int:
    user = os.environ.get("ARISTON_USER")
    pwd = os.environ.get("ARISTON_PASS")
    if not user or not pwd:
        print("set ARISTON_USER and ARISTON_PASS env vars", file=sys.stderr)
        return 2

    devices = await async_discover(user, pwd)
    if not devices:
        print("no devices", file=sys.stderr)
        return 3
    gw = devices[0][DeviceAttribute.GW]
    print(f"gateway: {_mask(gw)}")

    device = await async_hello(user, pwd, gw)
    print(f"class: {type(device).__name__}")
    print(f"consumption_type: {device.consumption_type}")

    print("\n=== UPDATE_ENERGY (calls /consSequencesApi8) ===")
    await device.async_update_energy()

    seqs = device.consumptions_sequences
    print(f"\nsequences count: {len(seqs)}")

    now_utc = dt.datetime.now(dt.timezone.utc)
    print(f"now UTC: {now_utc.isoformat()}")

    for i, seq in enumerate(seqs):
        v = seq.get("v") or []
        k = seq.get("k")
        p = seq.get("p")
        # other suspect keys observed in similar APIs: 'lt', 'lstUpd', 't0', 'd0'
        meta = {kk: vv for kk, vv in seq.items() if kk != "v"}
        print(f"\n--- seq[{i}] k={k} p={p} ---")
        print(f"meta: {json.dumps(meta, default=str)}")
        print(f"len(v) = {len(v)}")
        print(f"v = {v}")
        # If 24 buckets, label them as if calendar-day (00..23) and as if rolling
        if len(v) == 24:
            cal = " ".join(f"{h:02d}={v[h]}" for h in range(24))
            roll = " ".join(
                f"{(now_utc.hour - 23 + h) % 24:02d}={v[h]}" for h in range(24)
            )
            print(f"calendar-day labeling: {cal}")
            print(f"rolling-24h labeling : {roll}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
