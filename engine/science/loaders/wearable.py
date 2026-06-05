"""Garmin Vivosmart 5 wearable data loader.

Handles 7 sub-modalities with different JSON schemas:
  heart_rate, oxygen_saturation, respiratory_rate, stress,
  sleep, physical_activity, physical_activity_calorie

Sentinel values filtered: HR=0, stress=-1, respiratory_rate<0.
"""

import json
from pathlib import Path

import pandas as pd

from ..config import WEARABLE_DIR, WEARABLE_MANIFEST, WEARABLE_SUBMODALITIES

_manifest_cache = {}

# Maps sub-modality → (body_key, value_extraction_fn, sentinel_filter_fn)
# Each extraction fn takes a record and returns (timestamp_or_interval, value_dict)
_SCHEMAS = {
    "heart_rate": {
        "body_key": "heart_rate",
        "record_type": "point",
        "extract": lambda r: {
            "timestamp": r["effective_time_frame"]["date_time"],
            "value": r["heart_rate"]["value"],
            "unit": "beats/min",
        },
        "sentinel": lambda v: v > 0,
    },
    "oxygen_saturation": {
        "body_key": "breathing",
        "record_type": "point",
        "extract": lambda r: {
            "timestamp": r["effective_time_frame"]["date_time"],
            "value": r["oxygen_saturation"]["value"],
            "unit": "%",
        },
        "sentinel": lambda v: True,
    },
    "respiratory_rate": {
        "body_key": "breathing",
        "record_type": "point",
        "extract": lambda r: {
            "timestamp": r["effective_time_frame"]["date_time"],
            "value": r["respiratory_rate"]["value"],
            "unit": "breaths/min",
        },
        "sentinel": lambda v: v > 0,
    },
    "stress": {
        "body_key": "stress",
        "record_type": "point",
        "extract": lambda r: {
            "timestamp": r["effective_time_frame"]["date_time"],
            "value": r["stress"]["value"],
            "unit": "stress_level",
        },
        "sentinel": lambda v: v >= 0,
    },
    "sleep": {
        "body_key": "sleep",
        "record_type": "interval",
        "extract": lambda r: {
            "start_time": r["effective_time_frame"]["time_interval"]["start_date_time"],
            "end_time": r["effective_time_frame"]["time_interval"]["end_date_time"],
            "value": r["sleep_stage_state"],
            "unit": "stage",
        },
        "sentinel": lambda v: True,
    },
    "physical_activity": {
        "body_key": "activity",
        "record_type": "interval",
        "extract": lambda r: {
            "start_time": r["effective_time_frame"]["time_interval"]["start_date_time"],
            "end_time": r["effective_time_frame"]["time_interval"]["end_date_time"],
            "value": r["base_movement_quantity"]["value"] if r["base_movement_quantity"]["value"] != "" else float("nan"),
            "activity_name": r.get("activity_name", ""),
            "unit": "steps",
        },
        "sentinel": lambda v: True,
    },
    "physical_activity_calorie": {
        "body_key": "activity",
        "record_type": "point",
        "extract": lambda r: {
            "timestamp": r["effective_time_frame"]["date_time"],
            "value": r["calories_value"]["value"],
            "unit": "kcal",
        },
        "sentinel": lambda v: True,
    },
}

# Filename suffix per sub-modality
_FILENAMES = {
    "heart_rate": "heartrate",
    "oxygen_saturation": "oxygensaturation",
    "respiratory_rate": "respiratoryrate",
    "stress": "stress",
    "sleep": "sleep",
    "physical_activity": "activity",
    "physical_activity_calorie": "calorie",
}


def load_wearable_manifest() -> pd.DataFrame:
    """Load wearable_activity_monitor/manifest.tsv."""
    if "df" in _manifest_cache:
        return _manifest_cache["df"]
    df = pd.read_csv(WEARABLE_MANIFEST, sep="\t", dtype={"person_id": str})
    _manifest_cache["df"] = df
    return df


def _get_json_path(person_id: str, submodality: str) -> Path:
    fname = f"{person_id}_{_FILENAMES[submodality]}.json"
    return WEARABLE_DIR / submodality / "garmin_vivosmart5" / person_id / fname


def load_wearable_submodality(person_id: str, submodality: str) -> pd.DataFrame:
    """Load a single wearable sub-modality for a participant.

    Returns DataFrame with columns depending on record_type:
      point:    timestamp (index), value, unit
      interval: start_time, end_time, value, unit [, activity_name]
    """
    if submodality not in _SCHEMAS:
        raise ValueError(f"Unknown sub-modality: {submodality}. Valid: {list(_SCHEMAS)}")

    schema = _SCHEMAS[submodality]
    json_path = _get_json_path(person_id, submodality)
    if not json_path.exists():
        return pd.DataFrame()

    with open(json_path) as f:
        data = json.load(f)

    body = data["body"].get(schema["body_key"], [])
    records = []
    for entry in body:
        try:
            rec = schema["extract"](entry)
            if schema["sentinel"](rec["value"]):
                records.append(rec)
        except (KeyError, TypeError):
            continue

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    if schema["record_type"] == "point":
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp").set_index("timestamp")
    else:
        df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
        df["end_time"] = pd.to_datetime(df["end_time"], utc=True)
        df = df.sort_values("start_time")
    return df


def load_wearable(person_id: str) -> dict[str, pd.DataFrame]:
    """Load all wearable sub-modalities for a participant.

    Returns dict mapping sub-modality name → DataFrame.
    Missing sub-modalities return empty DataFrames.
    """
    return {
        sub: load_wearable_submodality(person_id, sub)
        for sub in WEARABLE_SUBMODALITIES
    }
