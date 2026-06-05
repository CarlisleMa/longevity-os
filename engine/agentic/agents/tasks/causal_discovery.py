"""Tier B: Cross-Modal Causal Discovery.

Goal: Use the ~10-day continuous multimodal overlap to discover causal
relationships between physiological systems.
"""

from ..orchestrator import Orchestrator


CAUSAL_QUESTIONS = [
    {
        "name": "sleep_glucose",
        "question": "Does poor sleep quality cause next-day glucose dysregulation?",
        "pipeline": [
            {
                "agent": "WearableAgent",
                "task": (
                    "For 50 participants with both wearable and CGM data, compute per-night "
                    "sleep_efficiency using compute_sleep_architecture(). Store as "
                    "workspace.dataframes['per_night_sleep']."
                ),
                "depends_on": [],
            },
            {
                "agent": "GlucoseAgent",
                "task": (
                    "For the same 50 participants, compute per-day CGM metrics: "
                    "daily TIR, daily mean glucose, daily CV. Segment CGM by date. "
                    "Store as workspace.dataframes['per_day_glucose']."
                ),
                "depends_on": [],
            },
            {
                "agent": "CausalAgent",
                "task": (
                    "Using workspace per_night_sleep and per_day_glucose DataFrames, "
                    "test bidirectional Granger causality: "
                    "1. Does last night's sleep_efficiency predict today's TIR? "
                    "2. Does yesterday's TIR predict tonight's sleep_efficiency? "
                    "Use maxlag=2 (days). Aggregate results across participants. "
                    "Report: how many show significant sleep->glucose vs glucose->sleep?"
                ),
                "depends_on": [0, 1],
            },
            {
                "agent": "CriticAgent",
                "task": "Review causal findings for sleep-glucose relationship.",
                "depends_on": [2],
            },
        ],
    },
    {
        "name": "glucose_hr_coupling",
        "question": "Is glucose-HR coupling weaker in more severe diabetes?",
        "pipeline": [
            {
                "agent": "CausalAgent",
                "task": (
                    "For 20 participants from each study_group (80 total), load aligned "
                    "time series via get_participant(pid).aligned_timeseries(). "
                    "Compute per-person Pearson correlation between cgm_glucose_mg_dl and hr_bpm. "
                    "Compare the distribution of correlation coefficients across the 4 study_groups "
                    "using Kruskal-Wallis. Store results as workspace.dataframes['coupling_by_group']. "
                    "Also compute the optimal lag (in 5-min steps) for each person."
                ),
                "depends_on": [],
            },
            {
                "agent": "CriticAgent",
                "task": "Review glucose-HR coupling findings.",
                "depends_on": [0],
            },
        ],
    },
    {
        "name": "pm25_hr",
        "question": "Does PM2.5 exposure cause acute HR changes?",
        "pipeline": [
            {
                "agent": "CausalAgent",
                "task": (
                    "For 30 participants with environment + wearable data, load aligned "
                    "time series (5-min grid). Test lagged regression: does PM2.5 at time t "
                    "predict HR at time t+30min, t+1h, t+2h? "
                    "Adjust for time-of-day (both PM2.5 and HR have diurnal patterns). "
                    "Aggregate across participants."
                ),
                "depends_on": [],
            },
            {
                "agent": "CriticAgent",
                "task": "Review PM2.5-HR findings.",
                "depends_on": [0],
            },
        ],
    },
]


def run_causal_battery(orchestrator: Orchestrator, questions: list[str] | None = None) -> dict:
    """Run the causal discovery battery.

    Args:
        questions: list of question names to run (default: all)

    Returns:
        dict mapping question name to result string
    """
    results = {}
    targets = CAUSAL_QUESTIONS
    if questions:
        targets = [q for q in CAUSAL_QUESTIONS if q["name"] in questions]

    for cq in targets:
        completed = set()
        q_results = []

        for i, spec in enumerate(cq["pipeline"]):
            for dep in spec.get("depends_on", []):
                if dep not in completed:
                    continue
            result = orchestrator.dispatch(spec)
            q_results.append(f"[{spec['agent']}] {result.answer[:500]}")
            completed.add(i)

        results[cq["name"]] = "\n".join(q_results)

    return results
