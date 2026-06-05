"""Load and query the participants.tsv master table."""

import pandas as pd
from .config import PARTICIPANTS_TSV

_BOOL_COLS = [
    "cardiac_ecg", "clinical_data", "environment", "retinal_flio",
    "retinal_oct", "retinal_octa", "retinal_photography",
    "wearable_activity_monitor", "wearable_blood_glucose",
]

_cache = {}


def load_participants(*, force_reload: bool = False) -> pd.DataFrame:
    """Load participants.tsv into a DataFrame with proper types.

    Returns DataFrame with person_id as string index, boolean modality columns,
    and study_visit_date as datetime.
    """
    if "df" in _cache and not force_reload:
        return _cache["df"]

    df = pd.read_csv(
        PARTICIPANTS_TSV,
        sep="\t",
        dtype={"person_id": str},
    )
    for col in _BOOL_COLS:
        df[col] = df[col].astype(str).str.strip().str.upper().map({"TRUE": True, "FALSE": False}).fillna(False)
    df["study_visit_date"] = pd.to_datetime(df["study_visit_date"])
    df = df.set_index("person_id")
    _cache["df"] = df
    return df


def get_split(split: str) -> pd.DataFrame:
    """Return participants in the given split ('train', 'val', or 'test')."""
    df = load_participants()
    return df[df["recommended_split"] == split]


def get_group(group: str) -> pd.DataFrame:
    """Return participants in the given study_group."""
    df = load_participants()
    return df[df["study_group"] == group]


def get_site(site: str) -> pd.DataFrame:
    """Return participants from the given clinical_site (UW, UCSD, UAB)."""
    df = load_participants()
    return df[df["clinical_site"] == site]


def participants_with_modality(modality: str) -> pd.DataFrame:
    """Return participants where the given modality is available."""
    df = load_participants()
    if modality not in _BOOL_COLS:
        raise ValueError(f"Unknown modality: {modality}. Valid: {_BOOL_COLS}")
    return df[df[modality]]


def get_person_ids(
    split: str | None = None,
    group: str | None = None,
    site: str | None = None,
    modalities: list[str] | None = None,
) -> list[str]:
    """Return person_ids matching all given filters."""
    df = load_participants()
    if split:
        df = df[df["recommended_split"] == split]
    if group:
        df = df[df["study_group"] == group]
    if site:
        df = df[df["clinical_site"] == site]
    if modalities:
        for m in modalities:
            if m not in _BOOL_COLS:
                raise ValueError(f"Unknown modality: {m}. Valid: {_BOOL_COLS}")
            df = df[df[m] == True]
    return list(df.index)
