"""Unified multimodal accessor for per-participant data.

get_participant(person_id) returns all available modalities for one person
in a structured dict, loading data lazily.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .participants import load_participants
from .loaders import clinical, ecg, cgm, wearable, environment, retinal
from .utils.temporal import align_timeseries, compute_overlap_stats


@dataclass
class ParticipantData:
    """Container for all modalities of a single participant."""

    person_id: str
    clinical_site: str = ""
    study_group: str = ""
    age: int = 0
    study_visit_date: Any = None
    recommended_split: str = ""

    # Loaded on demand
    _measurements: pd.DataFrame | None = field(default=None, repr=False)
    _observations: pd.DataFrame | None = field(default=None, repr=False)
    _conditions: pd.DataFrame | None = field(default=None, repr=False)
    _ecg: list | None = field(default=None, repr=False)
    _cgm: tuple | None = field(default=None, repr=False)  # (DataFrame, header_meta)
    _wearable: dict | None = field(default=None, repr=False)
    _environment: tuple | None = field(default=None, repr=False)

    @property
    def measurements(self) -> pd.DataFrame:
        if self._measurements is None:
            self._measurements = clinical.get_measurements(self.person_id)
        return self._measurements

    @property
    def observations(self) -> pd.DataFrame:
        if self._observations is None:
            self._observations = clinical.get_observations(self.person_id)
        return self._observations

    @property
    def conditions(self) -> pd.DataFrame:
        if self._conditions is None:
            self._conditions = clinical.get_conditions(self.person_id)
        return self._conditions

    @property
    def ecg_recordings(self) -> list[tuple[np.ndarray, dict]]:
        if self._ecg is None:
            try:
                self._ecg = ecg.load_ecg(self.person_id)
            except FileNotFoundError:
                self._ecg = []
        return self._ecg

    @property
    def ecg_signal(self) -> np.ndarray | None:
        recs = self.ecg_recordings
        return recs[0][0] if recs else None

    @property
    def cgm_data(self) -> pd.DataFrame:
        if self._cgm is None:
            try:
                self._cgm = cgm.load_cgm(self.person_id)
            except FileNotFoundError:
                self._cgm = (pd.DataFrame(), {})
        return self._cgm[0]

    @property
    def cgm_header(self) -> dict:
        """CGM header metadata including timezone."""
        _ = self.cgm_data  # ensure loaded
        return self._cgm[1]

    @property
    def cgm_metrics(self) -> dict:
        return cgm.compute_cgm_metrics(self.cgm_data)

    @property
    def wearable_data(self) -> dict[str, pd.DataFrame]:
        if self._wearable is None:
            self._wearable = wearable.load_wearable(self.person_id)
        return self._wearable

    @property
    def environment_data(self) -> tuple[pd.DataFrame, dict]:
        if self._environment is None:
            try:
                self._environment = environment.load_environment(self.person_id)
            except FileNotFoundError:
                self._environment = (pd.DataFrame(), {})
        return self._environment

    # Retinal: return manifest rows (file listings), not pixels
    @property
    def oct_files(self) -> pd.DataFrame:
        return retinal.get_oct_files(self.person_id)

    @property
    def octa_files(self) -> pd.DataFrame:
        return retinal.get_octa_files(self.person_id)

    @property
    def photography_files(self) -> pd.DataFrame:
        return retinal.get_photography_files(self.person_id)

    @property
    def flio_files(self) -> pd.DataFrame:
        return retinal.get_flio_files(self.person_id)

    def aligned_timeseries(self, freq: str = "5min") -> pd.DataFrame:
        """Align CGM, HR, and environment onto a common time grid."""
        sources = {}
        if not self.cgm_data.empty:
            sources["cgm"] = self.cgm_data[["glucose_mg_dl"]]
        hr = self.wearable_data.get("heart_rate")
        if hr is not None and not hr.empty:
            sources["hr"] = hr[["value"]].rename(columns={"value": "bpm"})
        env_df, _ = self.environment_data
        if not env_df.empty:
            sources["env"] = env_df[["temp", "hum", "pm2.5"]]
        return align_timeseries(sources, freq=freq)

    def overlap_stats(self) -> dict:
        """Compute temporal overlap stats for continuous modalities."""
        hr = self.wearable_data.get("heart_rate")
        env_df, _ = self.environment_data
        return compute_overlap_stats(
            cgm=self.cgm_data if not self.cgm_data.empty else None,
            wearable_hr=hr if hr is not None and not hr.empty else None,
            environment=env_df if not env_df.empty else None,
        )


def get_participant(person_id: str) -> ParticipantData:
    """Load a ParticipantData object for a given person_id.

    All modality data is loaded lazily on first access.
    """
    df = load_participants()
    if person_id not in df.index:
        raise KeyError(f"person_id={person_id} not found in participants.tsv")

    row = df.loc[person_id]
    return ParticipantData(
        person_id=person_id,
        clinical_site=row["clinical_site"],
        study_group=row["study_group"],
        age=int(row["age"]),
        study_visit_date=row["study_visit_date"],
        recommended_split=row["recommended_split"],
    )
