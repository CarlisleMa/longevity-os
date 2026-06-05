"""The 24-hour day: activities + a synthesized glucose/HR signal that reacts to them.

The per-event "body response" text is authored in the user's record; the continuous
glucose/HR curve is generated here so it lines up with the day's meals and workouts.
"""

from __future__ import annotations

import math
from typing import Optional

from . import store

STEP = 10  # minutes between signal samples


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _asleep_rest(t: int, events: list[dict]) -> Optional[float]:
    for e in events:
        if e.get("type") == "sleep" and _mins(e["start"]) <= t < _mins(e["end"]):
            return float(e.get("hrRest", 50))
    return None


def _glucose(t: int, events: list[dict]) -> float:
    g = 86.0 + 3.0 * math.sin((t - 360) / 1440 * 2 * math.pi)  # gentle circadian drift
    for e in events:
        if e.get("type") == "meal" and "gPeak" in e:
            s = _mins(e["start"])
            g += e["gPeak"] * math.exp(-(((t - (s + 40)) ** 2) / (2 * 45**2)))
        if "gDip" in e and e.get("type") in ("activity", "exercise"):
            en = _mins(e["end"])
            g -= e["gDip"] * math.exp(-(((t - en) ** 2) / (2 * 35**2)))
    return round(g, 1)


def _hr(t: int, events: list[dict]) -> int:
    rest = _asleep_rest(t, events)
    hr = rest if rest is not None else 60.0 + 2.0 * math.sin((t - 420) / 1440 * 2 * math.pi)
    for e in events:
        if e.get("type") == "exercise" and "hrPeak" in e:
            s, en = _mins(e["start"]), _mins(e["end"])
            c = s + (en - s) * 0.7
            hr += (e["hrPeak"] - 60) * math.exp(-(((t - c) ** 2) / (2 * 15**2)))
        if "hrBump" in e:
            s = _mins(e["start"])
            hr += e["hrBump"] * math.exp(-(((t - (s + 15)) ** 2) / (2 * 20**2)))
    return round(hr)


def day(user_id: str) -> Optional[dict]:
    kb = store.load_kb(user_id)
    if kb is None:
        return None
    d = kb.get("day")
    if not d:
        return None
    events = d.get("events", [])
    signals = [
        {"t": t, "glucose": _glucose(t, events), "hr": _hr(t, events)}
        for t in range(0, 1441, STEP)
    ]
    glus = [s["glucose"] for s in signals]
    hrs = [s["hr"] for s in signals]
    return {
        "date": d.get("date"),
        "events": events,
        "signals": signals,
        "summary": {
            "glucose_min": min(glus),
            "glucose_max": max(glus),
            "hr_min": min(hrs),
            "hr_max": max(hrs),
            "meals": sum(1 for e in events if e.get("type") == "meal"),
            "workouts": sum(1 for e in events if e.get("type") == "exercise"),
        },
    }
