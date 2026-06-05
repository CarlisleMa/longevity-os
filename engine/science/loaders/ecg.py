"""Cardiac ECG (WFDB) loader.

Loads 12-lead ECG recordings from Philips PageWriter TC30.
Fixed format: 12 channels × 500 Hz × 5500 samples (11 sec), int16 LE.

Returns signal as numpy array in millivolts and metadata dict parsed from .hea.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import DATA_ROOT, ECG_DATA_DIR, ECG_MANIFEST, ECG_GAIN, ECG_NUM_LEADS, ECG_NUM_SAMPLES, ECG_LEAD_NAMES

_manifest_cache = {}


def load_ecg_manifest() -> pd.DataFrame:
    """Load cardiac_ecg/manifest.tsv."""
    if "df" in _manifest_cache:
        return _manifest_cache["df"]
    df = pd.read_csv(ECG_MANIFEST, sep="\t", dtype={"person_id": str})
    # Convert numeric measurement columns
    for col in ["Rate", "PR", "QRSD", "QT", "QTc", "P", "QRS", "T"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    _manifest_cache["df"] = df
    return df


def _parse_hea_comments(hea_path: Path) -> dict:
    """Parse comment lines (# key: value) from a .hea file."""
    meta = {}
    with open(hea_path) as f:
        for line in f:
            line = line.rstrip()
            m = re.match(r"^#\s*(\w[\w_]*)\s*:\s*(.*)", line)
            if m:
                key, val = m.group(1), m.group(2).strip()
                meta[key] = val
    return meta


def load_ecg(person_id: str) -> list[tuple[np.ndarray, dict]]:
    """Load ECG recording(s) for a participant.

    Returns list of (signal, metadata) tuples.
    signal: np.ndarray of shape (5500, 12) in millivolts.
    metadata: dict with keys from .hea comments + 'lead_names'.

    Most participants have 1 recording; 6 have 2.
    """
    manifest = load_ecg_manifest()
    rows = manifest[manifest["person_id"] == person_id]
    if rows.empty:
        raise FileNotFoundError(f"No ECG data for person_id={person_id}")

    results = []
    for _, row in rows.iterrows():
        hea_rel = row["wfdb_hea_filepath"]
        dat_rel = row["wfdb_dat_filepath"]
        # Paths in manifest are relative from DATA_ROOT with leading /
        hea_path = DATA_ROOT / hea_rel.lstrip("/")
        dat_path = DATA_ROOT / dat_rel.lstrip("/")

        # Read binary signal
        raw = np.fromfile(dat_path, dtype="<i2")
        signal = raw.reshape(ECG_NUM_SAMPLES, ECG_NUM_LEADS)
        signal_mv = signal.astype(np.float32) / ECG_GAIN

        # Parse metadata from .hea
        meta = _parse_hea_comments(hea_path)
        meta["lead_names"] = ECG_LEAD_NAMES
        # Add manifest measurements
        for col in ["Rate", "PR", "QRSD", "QT", "QTc", "P", "QRS", "T"]:
            meta[col] = row[col]
        meta["participant_position"] = row.get("participant_position", "")

        results.append((signal_mv, meta))
    return results


def load_ecg_signal(person_id: str) -> np.ndarray:
    """Load first ECG signal for a participant as (5500, 12) array in mV.

    Convenience wrapper when you only need the waveform.
    """
    recordings = load_ecg(person_id)
    return recordings[0][0]
