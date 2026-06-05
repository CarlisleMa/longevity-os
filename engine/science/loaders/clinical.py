"""OMOP CDM clinical data loaders.

Handles the 6 CSV files in clinical_data/:
  person.csv, visit_occurrence.csv, measurement.csv,
  observation.csv, condition_occurrence.csv, procedure_occurrence.csv

Key quirks handled:
  - measurement.csv and observation.csv have a leading phantom "" index column
  - condition_source_value contains RFC 4180 quoted text with embedded commas
  - concept IDs are opaque integers; use utils.concepts for human labels
"""

import pandas as pd
from ..config import (
    PERSON_CSV, VISIT_CSV, MEASUREMENT_CSV,
    OBSERVATION_CSV, CONDITION_CSV, PROCEDURE_CSV,
)

_cache = {}


# ── Raw table loaders ──────────────────────────────────────────────────────

def _load_csv(path, key, has_phantom_index=False):
    if key in _cache:
        return _cache[key]
    df = pd.read_csv(path, dtype={"person_id": str}, low_memory=False)
    if has_phantom_index and df.columns[0] in ("", "Unnamed: 0"):
        df = df.drop(columns=[df.columns[0]])
    df["person_id"] = df["person_id"].astype(str)
    _cache[key] = df
    return df


def load_persons() -> pd.DataFrame:
    return _load_csv(PERSON_CSV, "person")


def load_visits() -> pd.DataFrame:
    return _load_csv(VISIT_CSV, "visit")


def load_measurements() -> pd.DataFrame:
    return _load_csv(MEASUREMENT_CSV, "measurement", has_phantom_index=True)


def load_observations() -> pd.DataFrame:
    return _load_csv(OBSERVATION_CSV, "observation", has_phantom_index=True)


def load_conditions() -> pd.DataFrame:
    return _load_csv(CONDITION_CSV, "condition")


def load_procedures() -> pd.DataFrame:
    return _load_csv(PROCEDURE_CSV, "procedure")


# ── Per-person query functions ─────────────────────────────────────────────

def get_measurements(person_id: str, concept_ids: list[int] | None = None) -> pd.DataFrame:
    """Get measurement rows for a person, optionally filtered by concept_id."""
    df = load_measurements()
    mask = df["person_id"] == person_id
    if concept_ids is not None:
        mask &= df["measurement_concept_id"].isin(concept_ids)
    return df[mask].copy()


def get_observations(person_id: str, concept_ids: list[int] | None = None) -> pd.DataFrame:
    """Get observation rows for a person, optionally filtered by concept_id."""
    df = load_observations()
    mask = df["person_id"] == person_id
    if concept_ids is not None:
        mask &= df["observation_concept_id"].isin(concept_ids)
    return df[mask].copy()


def get_conditions(person_id: str) -> pd.DataFrame:
    """Get condition_occurrence rows for a person."""
    df = load_conditions()
    return df[df["person_id"] == person_id].copy()


def get_lab_value(person_id: str, concept_id: int) -> float | None:
    """Get a single lab measurement value for a person.

    Returns the value_as_number for the first matching row, or None.
    """
    rows = get_measurements(person_id, concept_ids=[concept_id])
    if rows.empty:
        return None
    return rows.iloc[0]["value_as_number"]


def get_condition_flags(person_id: str) -> dict[int, bool]:
    """Get a dict of condition_concept_id → True for all conditions a person has."""
    rows = get_conditions(person_id)
    return {cid: True for cid in rows["condition_concept_id"].unique()}


# ── Cohort-level summaries ─────────────────────────────────────────────────

def measurement_summary(concept_id: int) -> pd.DataFrame:
    """Summarize a measurement across the cohort: person_id, value, date."""
    df = load_measurements()
    sub = df[df["measurement_concept_id"] == concept_id][
        ["person_id", "value_as_number", "measurement_date"]
    ].copy()
    sub["measurement_date"] = pd.to_datetime(sub["measurement_date"])
    return sub


def condition_prevalence() -> pd.DataFrame:
    """Count condition prevalence across cohort."""
    df = load_conditions()
    counts = df.groupby("condition_concept_id")["person_id"].nunique()
    counts = counts.sort_values(ascending=False)
    total = df["person_id"].nunique()
    result = pd.DataFrame({
        "n_persons": counts,
        "prevalence": counts / total,
    })
    # Add source labels
    labels = df.drop_duplicates("condition_concept_id").set_index(
        "condition_concept_id"
    )["condition_source_value"]
    result["source_value"] = labels
    return result
