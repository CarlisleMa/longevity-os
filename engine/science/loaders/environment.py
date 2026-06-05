"""LeeLab Anura environmental sensor loader.

Parses CSV files with 45-line comment header.
Handles NaN in nox column and humidity unit discrepancy (header says 0-1 but data is 0-100%).

Sensor records: 22 columns at 5-second intervals over ~10 days.
"""

import re
from pathlib import Path

import pandas as pd

from ..config import ENV_DATA_DIR, ENV_MANIFEST, ENV_HEADER_LINES

_manifest_cache = {}


def load_environment_manifest() -> pd.DataFrame:
    """Load environment/manifest.tsv."""
    if "df" in _manifest_cache:
        return _manifest_cache["df"]
    df = pd.read_csv(ENV_MANIFEST, sep="\t", dtype={"person_id": str})
    _manifest_cache["df"] = df
    return df


def _parse_env_header(csv_path: Path) -> dict:
    """Parse metadata from the 45-line comment header."""
    meta = {}
    with open(csv_path) as f:
        for i, line in enumerate(f):
            if i >= ENV_HEADER_LINES:
                break
            line = line.strip()
            if line.startswith("#"):
                m = re.match(r"^#\s*([\w_.]+)\s*:\s*(.*)", line)
                if m:
                    key, val = m.group(1), m.group(2).strip()
                    meta[key] = val
    return meta


def load_environment(person_id: str) -> tuple[pd.DataFrame, dict]:
    """Load environmental sensor data for a participant.

    Returns (data_df, metadata_dict).

    data_df columns:
      - ts (UTC datetime, as index)
      - lch0..lch11: 10 spectral channels (relative intensity 0-1)
      - pm1, pm2.5, pm4, pm10: particulate matter (µg/m³)
      - hum: relative humidity (%, 0-100 — NOT 0-1 despite what the header says)
      - temp: ambient temperature (°C)
      - voc: VOC index (1-500)
      - nox: NOx index (1-500, frequent NaN)
      - screen: screen state (0/1)
      - ff: flicker frequency (Hz)
      - inttemp: internal case temperature (°C)
    """
    csv_path = ENV_DATA_DIR / person_id / f"{person_id}_ENV.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No environment data for person_id={person_id}: {csv_path}")

    metadata = _parse_env_header(csv_path)

    df = pd.read_csv(
        csv_path,
        comment="#",
        parse_dates=["ts"],
        na_values=["nan", "NaN", ""],
    )
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.set_index("ts").sort_index()

    return df, metadata


def load_environment_light(person_id: str) -> pd.DataFrame:
    """Load only the 10 spectral light channels for a participant."""
    df, _ = load_environment(person_id)
    light_cols = [c for c in df.columns if c.startswith("lch")]
    return df[light_cols]


def load_environment_air_quality(person_id: str) -> pd.DataFrame:
    """Load only air quality columns (PM, VOC, NOx, humidity, temp)."""
    df, _ = load_environment(person_id)
    aq_cols = ["pm1", "pm2.5", "pm4", "pm10", "hum", "temp", "voc", "nox"]
    return df[aq_cols]
