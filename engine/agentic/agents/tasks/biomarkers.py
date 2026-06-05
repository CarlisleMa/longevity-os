"""Tier D: Digital Biomarker Discovery.

Goal: Find novel non-invasive biomarkers that predict clinical outcomes.
"""

from ..orchestrator import Orchestrator


BIOMARKER_TARGETS = [
    {
        "name": "wearable_predicts_hba1c",
        "description": "Can wearable features predict HbA1c?",
        "pipeline": [
            {
                "agent": "WearableAgent",
                "task": (
                    "Compute per-person wearable feature vector: circadian IS/IV/RA, "
                    "cosinor_amplitude, resting_hr, nocturnal_hr_dip, mean sleep_efficiency, "
                    "mean daily_steps, mean stress. "
                    "Store as workspace.dataframes['wearable_features_all']."
                ),
                "depends_on": [],
            },
            {
                "agent": "AgingClockAgent",
                "task": (
                    "Using workspace.dataframes['wearable_features_all'] as predictors "
                    "and HbA1c from the feature matrix as the target, "
                    "train an ElasticNet model (train split) and evaluate (test split). "
                    "Report R², MAE, and top 5 predictors by coefficient magnitude. "
                    "Also report AUROC for binary classification: HbA1c >= 6.5 (diabetic threshold)."
                ),
                "depends_on": [0],
            },
            {
                "agent": "CriticAgent",
                "task": "Review biomarker prediction methodology.",
                "depends_on": [1],
            },
        ],
    },
    {
        "name": "circadian_predicts_insulin_resistance",
        "description": "Does circadian disruption predict insulin resistance?",
        "pipeline": [
            {
                "agent": "WearableAgent",
                "task": (
                    "Compute circadian metrics (IS, IV, RA, cosinor) for all participants. "
                    "Store as workspace.dataframes['circadian_all']."
                ),
                "depends_on": [],
            },
            {
                "agent": "ClinicalAgent",
                "task": (
                    "Compute HOMA-IR for all participants with insulin and glucose values. "
                    "Store as workspace.dataframes['homa_ir_all']."
                ),
                "depends_on": [],
            },
            {
                "agent": "CausalAgent",
                "task": (
                    "Merge circadian_all and homa_ir_all. Test association between "
                    "circadian RA and HOMA-IR using partial correlation, adjusting for age and BMI. "
                    "Also test IS vs HOMA-IR, and cosinor_amplitude vs HOMA-IR. "
                    "Stratify by study_group."
                ),
                "depends_on": [0, 1],
            },
            {
                "agent": "CriticAgent",
                "task": "Review circadian-IR findings.",
                "depends_on": [2],
            },
        ],
    },
    {
        "name": "cgm_predicts_retinal",
        "description": "Do CGM metrics predict retinal pathology indicators?",
        "pipeline": [
            {
                "agent": "GlucoseAgent",
                "task": (
                    "Compute per-person CGM feature vector: cv, mage, tir, tar_vhigh, "
                    "lbgi, hbgi, gri, duration_days. "
                    "Store as workspace.dataframes['cgm_features_all']."
                ),
                "depends_on": [],
            },
            {
                "agent": "RetinalAgent",
                "task": (
                    "From the feature matrix, extract vision-related features: "
                    "logmar_photopic_od/os, va_letter_photopic_od/os. "
                    "These are proxies for retinal health (direct OCTA vessel density "
                    "not yet computed). Store as workspace.dataframes['retinal_features_all']."
                ),
                "depends_on": [],
            },
            {
                "agent": "CausalAgent",
                "task": (
                    "Merge cgm_features_all and retinal_features_all. "
                    "Test whether glycemic variability (CV, MAGE) associates with "
                    "worse visual acuity (higher logMAR), adjusting for age. "
                    "This is a proxy test until OCTA vessel density is available."
                ),
                "depends_on": [0, 1],
            },
            {
                "agent": "CriticAgent",
                "task": "Review CGM-retinal biomarker findings.",
                "depends_on": [2],
            },
        ],
    },
]


def run_biomarker_discovery(orchestrator: Orchestrator,
                            targets: list[str] | None = None) -> dict:
    """Run biomarker discovery for specified targets.

    Args:
        targets: list of target names (default: all)

    Returns:
        dict mapping target name to result string
    """
    results = {}
    active = BIOMARKER_TARGETS
    if targets:
        active = [t for t in BIOMARKER_TARGETS if t["name"] in targets]

    for target in active:
        completed = set()
        t_results = []

        for i, spec in enumerate(target["pipeline"]):
            for dep in spec.get("depends_on", []):
                if dep not in completed:
                    continue
            result = orchestrator.dispatch(spec)
            t_results.append(f"[{spec['agent']}] {result.answer[:500]}")
            completed.add(i)

        results[target["name"]] = "\n".join(t_results)

    return results
