"""Tier A: Multimodal Aging Clock Construction.

Goal: Build the first unified multimodal aging clock from functional signals.
Per-organ clocks: metabolic, cardiac, autonomic/fitness, retinal, environmental.
Cross-organ analysis: concordance, discordance, aging subtypes.
"""

from ..workspace import Workspace
from ..memory import Memory
from ..orchestrator import Orchestrator


AGING_CLOCK_PIPELINE = [
    {
        "agent": "ClinicalAgent",
        "task": (
            "Load the feature matrix. Extract per-person: age, hba1c, glucose, insulin, "
            "c_peptide, triglycerides, hdl, ldl, crp, bmi, waist_cm, sbp, dbp. "
            "Compute HOMA-IR = (insulin * glucose) / 405 and "
            "TyG = ln(triglycerides * glucose) / 2 for each person (/2 OUTSIDE the ln). "
            "Store as workspace.dataframes['clinical_aging_features']. "
            "Report how many participants have complete data for these features."
        ),
        "depends_on": [],
    },
    {
        "agent": "GlucoseAgent",
        "task": (
            "For all participants with CGM data, compute CGM metrics using compute_cgm_metrics(). "
            "Collect per-person: mean_glucose, cv, tir, mage, gmi, lbgi, hbgi. "
            "Also compute circadian metrics (dawn_phenomenon, nocturnal_mean) for a sample of 100 participants. "
            "Store as workspace.dataframes['cgm_aging_features']. "
            "Report summary statistics and how many participants have complete CGM features."
        ),
        "depends_on": [],
    },
    {
        "agent": "WearableAgent",
        "task": (
            "For all participants with wearable data, compute: "
            "1. compute_circadian_metrics(pid) -> IS, IV, RA, cosinor_amplitude, cosinor_acrophase "
            "2. compute_daily_summary(pid) -> mean resting_hr, nocturnal_hr_dip, daily_steps, sleep_hours "
            "3. compute_sleep_architecture(pid) -> mean sleep_efficiency, mean tst_min "
            "Start with a sample of 50 participants to verify, then scale to all. "
            "Store as workspace.dataframes['wearable_aging_features']. "
            "Report summary statistics."
        ),
        "depends_on": [],
    },
    {
        "agent": "CardiacAgent",
        "task": (
            "From the ECG manifest or participant_index, extract per-person: "
            "ecg_rate (heart rate), ecg_qtc, ecg_pr, ecg_qrsd. "
            "These are already available in load_participant_index() without signal processing. "
            "Store as workspace.dataframes['cardiac_aging_features']. "
            "Report summary statistics and completeness."
        ),
        "depends_on": [],
    },
    {
        "agent": "AgingClockAgent",
        "task": (
            "Using the feature DataFrames stored in workspace by the modality agents "
            "(clinical_aging_features, cgm_aging_features, wearable_aging_features, "
            "cardiac_aging_features), build per-organ aging clocks: "
            "1. Metabolic clock: CGM features + HOMA-IR + TyG + HbA1c -> age "
            "2. Cardiac clock: ECG intervals (HR, QTc, PR, QRS) -> age "
            "3. Autonomic/fitness clock: circadian metrics + resting HR + sleep efficiency + steps -> age "
            "Use Ridge regression. Train on recommended_split='train', evaluate on 'test'. "
            "Report MAE and R² for each clock. "
            "Compute AgeAccel = predicted_age - chronological_age for all participants. "
            "Store per-organ AgeAccel as workspace.dataframes['age_accel']. "
            "Then analyze cross-organ concordance: correlation matrix of AgeAccels, "
            "per-person SD (concordance score), and test whether AgeAccel differs by study_group."
        ),
        "depends_on": [0, 1, 2, 3],
    },
    {
        "agent": "PhenotypeAgent",
        "task": (
            "Using workspace.dataframes['age_accel'] from AgingClockAgent, "
            "cluster participants by their multi-organ AgeAccel profile. "
            "Use KMeans with k=3,4,5 and report silhouette scores. "
            "Characterize each cluster: which organs age fastest? "
            "Test whether clusters align with study_group (chi-squared). "
            "Identify 'discordant agers' (high SD across organ AgeAccels)."
        ),
        "depends_on": [4],
    },
    {
        "agent": "CriticAgent",
        "task": "Review all aging clock findings.",
        "depends_on": [4, 5],
    },
]


def run_aging_clock_pipeline(orchestrator: Orchestrator) -> str:
    """Execute the full aging clock pipeline."""
    results = []
    completed = set()

    for i, spec in enumerate(AGING_CLOCK_PIPELINE):
        # Check dependencies
        for dep in spec.get("depends_on", []):
            if dep not in completed:
                results.append(f"[SKIP] {spec['agent']}: dependency {dep} not completed")
                continue

        result = orchestrator.dispatch(spec)
        results.append(f"[{spec['agent']}] {result.answer[:500]}")
        completed.add(i)

    return "\n\n---\n\n".join(results)
