"""Timezone lookup derived from clinical_site.

Why not the JSON headers: 43 wearable files have no header at all (3 UAB, 39 UCSD,
1 UW), and CGM/wearable headers encode timezone as "pst"/"cst" strings that aren't
IANA-compliant. Clinical site → IANA is 1-to-1 for this cohort and more robust.

Mapping verified 2026-04-16 against participants.tsv:
  UW   (Seattle)     → America/Los_Angeles  (PST/PDT)
  UCSD (San Diego)   → America/Los_Angeles  (PST/PDT)
  UAB  (Birmingham)  → America/Chicago      (CST/CDT)
"""

import pandas as pd

from ..participants import load_participants

_SITE_TIMEZONE = {
    "UW": "America/Los_Angeles",
    "UCSD": "America/Los_Angeles",
    "UAB": "America/Chicago",
}


def get_timezone(person_id: str) -> str:
    """Return IANA timezone string for a participant."""
    df = load_participants()
    site = df.loc[person_id, "clinical_site"]
    return _SITE_TIMEZONE[site]


def to_local(index_or_series, person_id: str):
    """Convert a UTC DatetimeIndex or Series of timestamps to participant local time.

    Works with either a DatetimeIndex (from a DataFrame's index) or a Series of
    datetimes. Returns the same type with the timezone converted.
    """
    tz = get_timezone(person_id)
    if isinstance(index_or_series, pd.DatetimeIndex):
        return index_or_series.tz_convert(tz)
    return index_or_series.dt.tz_convert(tz)
