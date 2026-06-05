"""Tier C: N-of-1 Multimodal Phenotyping.

Goal: Generate per-person multimodal health profiles from the ~10-day window.
Cluster 2,280 participants into data-driven subtypes.
"""

from ..orchestrator import Orchestrator


PHENOTYPING_PIPELINE = [
    {
        "agent": "ClinicalAgent",
        "task": (
            "Extract key clinical features for phenotyping: age, bmi, hba1c, glucose, "
            "insulin, triglycerides, hdl, ldl, sbp, dbp, crp. "
            "Compute HOMA-IR. Store as workspace.dataframes['pheno_clinical']."
        ),
        "depends_on": [],
    },
    {
        "agent": "GlucoseAgent",
        "task": (
            "Compute per-person CGM summary: mean_glucose, cv, tir, mage, gmi. "
            "Store as workspace.dataframes['pheno_cgm']."
        ),
        "depends_on": [],
    },
    {
        "agent": "WearableAgent",
        "task": (
            "Compute per-person wearable summary: circadian IS/IV/RA, "
            "mean resting_hr, mean sleep_efficiency, mean daily_steps, "
            "nocturnal_hr_dip. Store as workspace.dataframes['pheno_wearable']."
        ),
        "depends_on": [],
    },
    {
        "agent": "CardiacAgent",
        "task": (
            "Extract per-person ECG features: ecg_rate, ecg_qtc. "
            "Store as workspace.dataframes['pheno_cardiac']."
        ),
        "depends_on": [],
    },
    {
        "agent": "PhenotypeAgent",
        "task": (
            "Merge all pheno_* DataFrames from workspace on person_id. "
            "Standardize features, handle missing data (drop features >30% missing, "
            "impute rest with median). Run PCA for variance explained. "
            "Cluster with KMeans (k=3,4,5,6) and report silhouette scores. "
            "Characterize the best clustering: per-cluster feature means, "
            "comparison to study_group (chi-squared), identification of interesting "
            "phenotypes (e.g., 'metabolically healthy but circadian-disrupted'). "
            "Store cluster labels as workspace.dataframes['phenotype_clusters']."
        ),
        "depends_on": [0, 1, 2, 3],
    },
    {
        "agent": "HypothesisAgent",
        "task": (
            "Review the phenotype clusters found by PhenotypeAgent. "
            "Propose hypotheses about what mechanisms drive the cluster structure. "
            "Are the clusters driven by disease severity, or by orthogonal factors "
            "like circadian health, environmental exposure, or fitness level?"
        ),
        "depends_on": [4],
    },
    {
        "agent": "CriticAgent",
        "task": "Review phenotyping methodology and findings.",
        "depends_on": [4, 5],
    },
]


def run_phenotyping_pipeline(orchestrator: Orchestrator) -> str:
    """Execute the multimodal phenotyping pipeline."""
    results = []
    completed = set()

    for i, spec in enumerate(PHENOTYPING_PIPELINE):
        for dep in spec.get("depends_on", []):
            if dep not in completed:
                results.append(f"[SKIP] {spec['agent']}: dependency {dep} not completed")
                continue
        result = orchestrator.dispatch(spec)
        results.append(f"[{spec['agent']}] {result.answer[:500]}")
        completed.add(i)

    return "\n\n---\n\n".join(results)
