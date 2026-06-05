"""Clinical feature matrix builder.

Pivots OMOP long-format tables into a one-row-per-person wide DataFrame
combining labs, vitals, vision, cognition, conditions, and lifestyle.

Usage:
    from scripts.features import build_feature_matrix
    fm = build_feature_matrix()  # 2280 rows × 125 columns
    fm.to_parquet("results/features/feature_matrix.parquet")
"""

import numpy as np
import pandas as pd

from .config import RESULTS_DIR, result_path
from .participants import load_participants
from .loaders.clinical import load_measurements, load_observations, load_conditions

OUTPUT_PATH = result_path("feature_matrix.parquet")

# ── Concept ID → column name mappings ──────────────────────────────────────
# Organized by clinical category.

_LABS = {
    3004410: "hba1c",
    3004501: "glucose",
    3016244: "insulin",
    3010084: "c_peptide",
    3027114: "total_cholesterol",
    3007070: "hdl",
    3028288: "ldl",
    3022192: "triglycerides",
    3010156: "crp",
    40769783: "troponin_t",
    3029187: "nt_probnp",
    3013682: "bun",
    3016723: "creatinine",
    4112223: "bun_cr_ratio",
    3019550: "sodium",
    3023103: "potassium",
    3014576: "chloride",
    3015632: "co2",
    3006906: "calcium",
    3006923: "alt",
    3013721: "ast",
    3035995: "alk_phos",
    3024128: "bilirubin_total",
    3024561: "albumin",
    3021886: "globulin",
    3020630: "total_protein",
    4288601: "ag_ratio",
    3012516: "urine_albumin",
    3017250: "urine_creatinine",
    2005200182: "wbc",
    2005200183: "rbc",
    3000963: "hemoglobin",
    3009542: "hematocrit",
    3024731: "mcv",
    3035941: "mch",
    3003338: "mchc",
    3002385: "rdw",
    3007461: "platelets",
}

# Vitals: these have 2 readings per person — we average them
_VITALS = {
    3004249: "sbp",
    3012888: "dbp",
    4239408: "heart_rate",
}

_ANTHROPOMETRY = {
    3036277: "height_cm",
    3025315: "weight_kg",
    4245997: "bmi",
    4172830: "waist_cm",
    4111665: "hip_cm",
    44809433: "whr",
}

# Vision: laterality encoded in concept_id
_VISION = {
    2005200042: "va_letter_photopic_od",
    2005200043: "va_letter_photopic_os",
    2005200052: "logmar_photopic_od",
    2005200053: "logmar_photopic_os",
    2005200056: "va_letter_mesopic_od",
    2005200057: "va_letter_mesopic_os",
    2005200336: "logmar_mesopic_od",
    2005200337: "logmar_mesopic_os",
    2005200155: "log_contrast_plcs_od",
    2005200156: "log_contrast_plcs_os",
    2005200552: "log_contrast_mlcs_od",
    2005200553: "log_contrast_mlcs_os",
    2005200338: "contrast_final_letter_od",
    2005200340: "contrast_final_letter_os",
    2005200486: "llva_final_letter_od",
    2005200488: "llva_final_letter_os",
    3000744: "autorefract_sphere_od",
    3003500: "autorefract_sphere_os",
    3033346: "autorefract_cylinder_od",
    3002343: "autorefract_cylinder_os",
    3034190: "autorefract_axis_od",
    3001254: "autorefract_axis_os",
}

# Cognition (MoCA): scores and timed components
_MOCA_SCORES = {
    37174522: "moca_total",
    2005200344: "moca_trails",
    2005200346: "moca_cube",
    2005200348: "moca_clock",
    2005200350: "moca_naming",
    2005200352: "moca_memory1",
    2005200354: "moca_memory2",
    2005200356: "moca_digitspan",
    2005200358: "moca_lettera",
    2005200360: "moca_subtraction",
    2005200362: "moca_repetition",
    2005200364: "moca_fluency",
    2005200366: "moca_abstraction",
    2005200368: "moca_delayed_recall",
    2005200370: "moca_orientation",
    2005200373: "moca_combined_mis",
}

# Neuropathy monofilament
_NEUROPATHY = {
    2005200159: "monofilament_right_felt",
    2005200161: "monofilament_left_felt",
}

# Conditions: concept_id → boolean column name
_CONDITIONS = {
    2005200547: "has_elevated_a1c",
    316866: "has_hypertension",
    4159131: "has_dyslipidemia",
    4291025: "has_arthritis",
    201826: "has_t2dm",
    433736: "has_obesity",
    4036620: "has_dry_eye",
    4317977: "has_cataracts",
    37018196: "has_prediabetes",
    81902: "has_urinary_problems",
    4201745: "has_digestive_problems",
    4194405: "has_cancer",
    439378: "has_hearing_impairment",
    2005200627: "has_other_cardiac",
    4186898: "has_chronic_pulmonary",
    80502: "has_osteoporosis",
    2005200017: "has_renal_problems",
    2005200015: "has_circulation_problems",
    437541: "has_glaucoma",
    46271045: "has_neuro_other",
    317002: "has_hypotension",
    4329847: "has_mi",
    374028: "has_amd",
    2005200628: "has_stroke",
    4174977: "has_diabetic_retinopathy",
    439795: "has_mci",
    440392: "has_rvo",
    374919: "has_ms",
    381270: "has_parkinsons",
    4182210: "has_dementia",
}

# Observation-based features
_OBS_CESD = 1761347       # CES-D-10 total score
_OBS_SMOKED = 40766306    # "Have you smoked at least 100 cigarettes"
_OBS_ALCOHOL = 40772145   # "Have you ever consumed alcohol"


def _pivot_measurements(m: pd.DataFrame, concept_map: dict, agg: str = "first") -> pd.DataFrame:
    """Pivot measurement rows into wide format using a concept_id → column_name map."""
    all_cids = list(concept_map.keys())
    sub = m[m["measurement_concept_id"].isin(all_cids)][
        ["person_id", "measurement_concept_id", "value_as_number"]
    ].copy()
    sub["col_name"] = sub["measurement_concept_id"].map(concept_map)

    if agg == "mean":
        pivoted = sub.groupby(["person_id", "col_name"])["value_as_number"].mean().unstack("col_name")
    else:
        pivoted = sub.groupby(["person_id", "col_name"])["value_as_number"].first().unstack("col_name")

    return pivoted


def _build_condition_flags(c: pd.DataFrame) -> pd.DataFrame:
    """Build boolean condition flags per person."""
    all_cids = list(_CONDITIONS.keys())
    sub = c[c["condition_concept_id"].isin(all_cids)][
        ["person_id", "condition_concept_id"]
    ].copy()
    sub["col_name"] = sub["condition_concept_id"].map(_CONDITIONS)
    sub["present"] = True

    pivoted = sub.groupby(["person_id", "col_name"])["present"].first().unstack("col_name")
    pivoted = pivoted.fillna(False)
    return pivoted


def _build_observation_features(o: pd.DataFrame) -> pd.DataFrame:
    """Extract CES-D total and lifestyle flags from observations."""
    rows = []
    for pid, grp in o.groupby("person_id"):
        rec = {"person_id": pid}

        # CES-D total
        cesd = grp[grp["observation_concept_id"] == _OBS_CESD]
        if not cesd.empty:
            rec["cesd_total"] = cesd.iloc[0]["value_as_number"]

        # Ever smoked (value_as_number: 1=yes, 0=no typically)
        smoked = grp[grp["observation_concept_id"] == _OBS_SMOKED]
        if not smoked.empty:
            rec["ever_smoked"] = smoked.iloc[0]["value_as_number"] == 1.0

        # Ever consumed alcohol
        alcohol = grp[grp["observation_concept_id"] == _OBS_ALCOHOL]
        if not alcohol.empty:
            rec["ever_alcohol"] = alcohol.iloc[0]["value_as_number"] == 1.0

        rows.append(rec)

    return pd.DataFrame(rows).set_index("person_id")


def build_feature_matrix(save: bool = True) -> pd.DataFrame:
    """Build the one-row-per-person clinical feature matrix.

    Columns organized as:
      - Demographics: clinical_site, study_group, age, recommended_split
      - Labs: hba1c, glucose, insulin, c_peptide, lipids, CBC, metabolic, hepatic, cardiac, renal
      - Vitals: sbp, dbp, heart_rate (averaged from 2 readings)
      - Anthropometry: height_cm, weight_kg, bmi, waist_cm, hip_cm, whr
      - Vision: VA and contrast for OD/OS, autorefraction
      - Cognition: moca_total + subscores
      - Mood: cesd_total
      - Neuropathy: monofilament felt counts
      - Conditions: 30 boolean flags
      - Lifestyle: ever_smoked, ever_alcohol

    Returns DataFrame indexed by person_id (str).
    """
    participants = load_participants()
    m = load_measurements()
    o = load_observations()
    c = load_conditions()

    # Pivot each category
    labs = _pivot_measurements(m, _LABS)
    vitals = _pivot_measurements(m, _VITALS, agg="mean")  # average 2 readings
    anthropometry = _pivot_measurements(m, _ANTHROPOMETRY)
    vision = _pivot_measurements(m, _VISION)
    moca = _pivot_measurements(m, _MOCA_SCORES)
    neuropathy = _pivot_measurements(m, _NEUROPATHY)
    conditions = _build_condition_flags(c)
    obs_features = _build_observation_features(o)

    # Join all onto participants
    fm = participants[["clinical_site", "study_group", "age", "study_visit_date", "recommended_split"]].copy()

    for block in [labs, vitals, anthropometry, vision, moca, neuropathy, conditions, obs_features]:
        if not block.empty:
            fm = fm.join(block, how="left")

    # Fill condition booleans that were NaN (person had no conditions at all)
    cond_cols = list(_CONDITIONS.values())
    for col in cond_cols:
        if col in fm.columns:
            fm[col] = fm[col].fillna(False).astype(bool)

    if save:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        fm.to_parquet(OUTPUT_PATH)

    return fm


def load_feature_matrix() -> pd.DataFrame:
    """Load the pre-built feature matrix from Parquet."""
    if not OUTPUT_PATH.exists():
        return build_feature_matrix(save=True)
    return pd.read_parquet(OUTPUT_PATH)
