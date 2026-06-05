"""Path constants and configuration for AI-READI v3.0.0 dataset."""

from pathlib import Path

# ── Root paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path("/oak/stanford/scg/lab_twc/mazijian/aireadi")
DATA_ROOT = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"

# ── Generated result layout ────────────────────────────────────────────────
FEATURES_RESULTS_DIR = RESULTS_DIR / "features"
CLINICAL_RESULTS_DIR = RESULTS_DIR / "clinical"
CLOCK_RESULTS_DIR = RESULTS_DIR / "clocks"
EMBEDDING_RESULTS_DIR = RESULTS_DIR / "embeddings"
COUPLING_RESULTS_DIR = RESULTS_DIR / "coupling"
HYPOTHESIS_RESULTS_DIR = RESULTS_DIR / "hypotheses"
CAUSAL_RESULTS_DIR = RESULTS_DIR / "causal"
BIOMARKER_RESULTS_DIR = RESULTS_DIR / "biomarkers"
SHARD_RESULTS_DIR = RESULTS_DIR / "shards"
PRESENTATION_RESULTS_DIR = RESULTS_DIR / "presentations"
LOG_RESULTS_DIR = RESULTS_DIR / "logs"
FIGURES_RESULTS_DIR = RESULTS_DIR / "figures"

RESULT_FILE_MAP = {
    # Feature and cohort tables.
    "participant_index.parquet": FEATURES_RESULTS_DIR / "participant_index.parquet",
    "feature_matrix.parquet": FEATURES_RESULTS_DIR / "feature_matrix.parquet",
    "multimodal_features.parquet": FEATURES_RESULTS_DIR / "multimodal_features.parquet",
    "clinical_scores.parquet": FEATURES_RESULTS_DIR / "clinical_scores.parquet",
    "all_features_by_study_group.csv": FEATURES_RESULTS_DIR / "all_features_by_study_group.csv",
    "all_features_by_study_group_age_adjusted.csv": FEATURES_RESULTS_DIR / "all_features_by_study_group_age_adjusted.csv",
    "table1_by_study_group.csv": FEATURES_RESULTS_DIR / "table1_by_study_group.csv",
    "site_bias_check.csv": FEATURES_RESULTS_DIR / "site_bias_check.csv",
    "study_summary.json": FEATURES_RESULTS_DIR / "study_summary.json",
    "split_assignments.parquet": FEATURES_RESULTS_DIR / "split_assignments.parquet",
    "split_balance_report.csv": FEATURES_RESULTS_DIR / "split_balance_report.csv",
    "split_balance_summary.json": FEATURES_RESULTS_DIR / "split_balance_summary.json",
    "hba1c_by_study_group_results.json": CLINICAL_RESULTS_DIR / "hba1c_by_study_group_results.json",
    # Learned embeddings and age-clock outputs.
    "retinal_embeddings.parquet": EMBEDDING_RESULTS_DIR / "retinal_embeddings.parquet",
    "cardiac_embeddings.parquet": EMBEDDING_RESULTS_DIR / "cardiac_embeddings.parquet",
    "age_accel.parquet": CLOCK_RESULTS_DIR / "age_accel.parquet",
    "clock_performance.csv": CLOCK_RESULTS_DIR / "clock_performance.csv",
    "retinal_age_accel.parquet": CLOCK_RESULTS_DIR / "retinal_age_accel.parquet",
    "cardiac_age_accel.parquet": CLOCK_RESULTS_DIR / "cardiac_age_accel.parquet",
    "multimodal_clock_age_accel.parquet": CLOCK_RESULTS_DIR / "multimodal_clock_age_accel.parquet",
    "multimodal_clock_performance.csv": CLOCK_RESULTS_DIR / "multimodal_clock_performance.csv",
    "multimodal_clock_feature_importance.csv": CLOCK_RESULTS_DIR / "multimodal_clock_feature_importance.csv",
    "unified_age_accel.parquet": CLOCK_RESULTS_DIR / "unified_age_accel.parquet",
    "unified_clock_performance.csv": CLOCK_RESULTS_DIR / "unified_clock_performance.csv",
    "concordance_matrix.csv": CLOCK_RESULTS_DIR / "concordance_matrix.csv",
    "aging_subtypes.csv": CLOCK_RESULTS_DIR / "aging_subtypes.csv",
    "diabetes_gradient.csv": CLOCK_RESULTS_DIR / "diabetes_gradient.csv",
    "predictive_hierarchy.csv": CLOCK_RESULTS_DIR / "predictive_hierarchy.csv",
    "pairwise_effect_sizes.csv": CLOCK_RESULTS_DIR / "pairwise_effect_sizes.csv",
    # Coupling and cross-modal predictability outputs.
    "coupling_features.parquet": COUPLING_RESULTS_DIR / "coupling_features.parquet",
    "coupling_features_env.parquet": COUPLING_RESULTS_DIR / "coupling_features_env.parquet",
    "coupling_features_pilot20.parquet": COUPLING_RESULTS_DIR / "coupling_features_pilot20.parquet",
    "coupling_atlas.csv": COUPLING_RESULTS_DIR / "coupling_atlas.csv",
    "coupling_atlas_sensitivity.csv": COUPLING_RESULTS_DIR / "coupling_atlas_sensitivity.csv",
    "coupling_damage.csv": COUPLING_RESULTS_DIR / "coupling_damage.csv",
    "coupling_prediction_performance.csv": COUPLING_RESULTS_DIR / "coupling_prediction_performance.csv",
    "coupling_predictions.parquet": COUPLING_RESULTS_DIR / "coupling_predictions.parquet",
    "coupling_env_atlas.csv": COUPLING_RESULTS_DIR / "coupling_env_atlas.csv",
    "coupling_env_damage.csv": COUPLING_RESULTS_DIR / "coupling_env_damage.csv",
    "coupling_env_prediction_performance.csv": COUPLING_RESULTS_DIR / "coupling_env_prediction_performance.csv",
    "coupling_env_predictions.parquet": COUPLING_RESULTS_DIR / "coupling_env_predictions.parquet",
    "cross_modal_predictability.parquet": COUPLING_RESULTS_DIR / "cross_modal_predictability.parquet",
    "cross_modal_predictability_pilot20.parquet": COUPLING_RESULTS_DIR / "cross_modal_predictability_pilot20.parquet",
    "cross_modal_predictability_atlas.csv": COUPLING_RESULTS_DIR / "cross_modal_predictability_atlas.csv",
    "cross_modal_predictability_damage.csv": COUPLING_RESULTS_DIR / "cross_modal_predictability_damage.csv",
    # Hypothesis-specific outputs.
    "hypothesis_timeseries_features.parquet": HYPOTHESIS_RESULTS_DIR / "hypothesis_timeseries_features.parquet",
    "hypothesis_phase2_features.parquet": HYPOTHESIS_RESULTS_DIR / "hypothesis_phase2_features.parquet",
    "h_new01_frequency_coupling.csv": HYPOTHESIS_RESULTS_DIR / "h_new01_frequency_coupling.csv",
    "h_new03_excursion_hr.csv": HYPOTHESIS_RESULTS_DIR / "h_new03_excursion_hr.csv",
    "h_new05_incremental_prediction.csv": HYPOTHESIS_RESULTS_DIR / "h_new05_incremental_prediction.csv",
    "h_new05_partial_correlations.csv": HYPOTHESIS_RESULTS_DIR / "h_new05_partial_correlations.csv",
    "h_new05_severity_gradient.csv": HYPOTHESIS_RESULTS_DIR / "h_new05_severity_gradient.csv",
    "h_new06_nocturnal_coupling.csv": HYPOTHESIS_RESULTS_DIR / "h_new06_nocturnal_coupling.csv",
    "h_new10_activity_glucose.csv": HYPOTHESIS_RESULTS_DIR / "h_new10_activity_glucose.csv",
    "h_new13_sleepwake_transition.csv": HYPOTHESIS_RESULTS_DIR / "h_new13_sleepwake_transition.csv",
    "h_new17_diurnal_coupling.csv": HYPOTHESIS_RESULTS_DIR / "h_new17_diurnal_coupling.csv",
    "hero_excursion_profiles.json": HYPOTHESIS_RESULTS_DIR / "hero_excursion_profiles.json",
    # Causal and biomarker result tables.
    "causal_sleep_glucose.csv": CAUSAL_RESULTS_DIR / "causal_sleep_glucose.csv",
    "causal_glucose_hr.csv": CAUSAL_RESULTS_DIR / "causal_glucose_hr.csv",
    "causal_pm25_hr.csv": CAUSAL_RESULTS_DIR / "causal_pm25_hr.csv",
    "causal_summary.json": CAUSAL_RESULTS_DIR / "causal_summary.json",
    "biomarker_wearable_hba1c.csv": BIOMARKER_RESULTS_DIR / "biomarker_wearable_hba1c.csv",
    "biomarker_circadian_ir.csv": BIOMARKER_RESULTS_DIR / "biomarker_circadian_ir.csv",
    "biomarker_cgm_vision.csv": BIOMARKER_RESULTS_DIR / "biomarker_cgm_vision.csv",
    "biomarker_panel.csv": BIOMARKER_RESULTS_DIR / "biomarker_panel.csv",
}


def result_path(filename: str) -> Path:
    """Return the canonical path for a generated result artifact."""
    path = RESULT_FILE_MAP.get(filename, RESULTS_DIR / filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def result_variant_path(filename: str, variant: str | None = None) -> Path:
    """Return a canonical result path, optionally namespaced by variant.

    Use variants for alternate split/model runs so they do not overwrite the
    default artifacts consumed by downstream scripts.
    """
    path = result_path(filename)
    if not variant or variant in {"recommended", "recommended_split"}:
        return path
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in variant)
    return path.with_name(f"{path.stem}__{safe}{path.suffix}")


def ensure_result_parent(path: Path) -> Path:
    """Create the parent directory for a generated result path and return it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

# ── Root-level files ────────────────────────────────────────────────────────
PARTICIPANTS_TSV = DATA_ROOT / "participants.tsv"
PARTICIPANTS_JSON = DATA_ROOT / "participants.json"

# ── Clinical data (OMOP CDM) ───────────────────────────────────────────────
CLINICAL_DIR = DATA_ROOT / "clinical_data"
PERSON_CSV = CLINICAL_DIR / "person.csv"
VISIT_CSV = CLINICAL_DIR / "visit_occurrence.csv"
MEASUREMENT_CSV = CLINICAL_DIR / "measurement.csv"
OBSERVATION_CSV = CLINICAL_DIR / "observation.csv"
CONDITION_CSV = CLINICAL_DIR / "condition_occurrence.csv"
PROCEDURE_CSV = CLINICAL_DIR / "procedure_occurrence.csv"
DQD_JSON = CLINICAL_DIR / "dqd_omop.json"

# ── Cardiac ECG (WFDB) ─────────────────────────────────────────────────────
ECG_DIR = DATA_ROOT / "cardiac_ecg"
ECG_DATA_DIR = ECG_DIR / "ecg_12lead" / "philips_tc30"
ECG_MANIFEST = ECG_DIR / "manifest.tsv"

# ── Retinal imaging ────────────────────────────────────────────────────────
OCT_DIR = DATA_ROOT / "retinal_oct"
OCT_MANIFEST = OCT_DIR / "manifest.tsv"

OCTA_DIR = DATA_ROOT / "retinal_octa"
OCTA_MANIFEST = OCTA_DIR / "manifest.tsv"

PHOTO_DIR = DATA_ROOT / "retinal_photography"
PHOTO_MANIFEST = PHOTO_DIR / "manifest.tsv"

FLIO_DIR = DATA_ROOT / "retinal_flio"
FLIO_MANIFEST = FLIO_DIR / "manifest.tsv"

# ── Wearable activity monitor ──────────────────────────────────────────────
WEARABLE_DIR = DATA_ROOT / "wearable_activity_monitor"
WEARABLE_MANIFEST = WEARABLE_DIR / "manifest.tsv"
WEARABLE_SUBMODALITIES = [
    "heart_rate", "oxygen_saturation", "physical_activity",
    "physical_activity_calorie", "respiratory_rate", "sleep", "stress",
]
WEARABLE_DEVICE_DIR = WEARABLE_DIR  # sub-dirs are {submodality}/garmin_vivosmart5/{pid}/

# ── Continuous glucose monitoring ───────────────────────────────────────────
CGM_DIR = DATA_ROOT / "wearable_blood_glucose"
CGM_MANIFEST = CGM_DIR / "manifest.tsv"
CGM_DATA_DIR = CGM_DIR / "continuous_glucose_monitoring" / "dexcom_g6"

# ── Environmental sensor ───────────────────────────────────────────────────
ENV_DIR = DATA_ROOT / "environment"
ENV_MANIFEST = ENV_DIR / "manifest.tsv"
ENV_DATA_DIR = ENV_DIR / "environmental_sensor" / "leelab_anura"

# ── ECG constants ──────────────────────────────────────────────────────────
ECG_SAMPLE_RATE = 500       # Hz
ECG_NUM_SAMPLES = 5500      # 11 seconds
ECG_NUM_LEADS = 12
ECG_GAIN = 200              # ADU per mV
ECG_LEAD_NAMES = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]

# ── CGM constants ──────────────────────────────────────────────────────────
CGM_SAMPLE_INTERVAL_MIN = 5
CGM_TIR_LOW = 70            # mg/dL
CGM_TIR_HIGH = 180          # mg/dL

# ── Environmental sensor constants ─────────────────────────────────────────
ENV_HEADER_LINES = 45
ENV_SAMPLE_INTERVAL_SEC = 5
ENV_LIGHT_CHANNELS = ["lch0", "lch1", "lch2", "lch3", "lch6", "lch7", "lch8", "lch9", "lch10", "lch11"]
ENV_LIGHT_WAVELENGTHS_NM = [415, 445, 480, 515, 555, 590, 630, 680, None, 910]  # None = clear/no filter
