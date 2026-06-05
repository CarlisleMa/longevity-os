"""Tier E: Cross-Modal Health Insights.

Goal: Discover relationships invisible in any single modality.
"""

from ..orchestrator import Orchestrator


CROSS_MODAL_QUESTIONS = [
    {
        "name": "cardiac_metabolic_coupling",
        "question": "Does cardiac electrical age correlate with metabolic age?",
    },
    {
        "name": "circadian_metabolic_alignment",
        "question": (
            "Are individuals whose circadian rhythms (Garmin) and glucose rhythms (CGM) "
            "are well-aligned healthier across other modalities?"
        ),
    },
    {
        "name": "cross_modal_discordance",
        "question": (
            "Identify participants with discordant cross-modal profiles: "
            "well-controlled glucose (high TIR) but poor cardiovascular markers "
            "(high resting HR, prolonged QTc), or vice versa. "
            "What characterizes these discordant phenotypes?"
        ),
    },
    {
        "name": "environment_physiology",
        "question": (
            "Does personal environmental exposure (PM2.5, evening light, temperature) "
            "associate with glycemic variability and circadian disruption? "
            "Test associations adjusting for age and diabetes severity."
        ),
    },
    {
        "name": "sleep_glucose_vision_triad",
        "question": (
            "Test the pathway: poor sleep -> glucose instability -> worse visual acuity. "
            "Use mediation analysis with sleep efficiency as exposure, "
            "CGM coefficient of variation as mediator, and logMAR as outcome."
        ),
    },
]


def run_cross_modal_analysis(orchestrator: Orchestrator,
                              questions: list[str] | None = None) -> dict:
    """Run cross-modal analyses using the orchestrator's natural decomposition.

    Unlike the other task pipelines, cross-modal questions are open-ended enough
    that we let the orchestrator decompose them rather than pre-specifying the pipeline.

    Args:
        questions: list of question names (default: all)

    Returns:
        dict mapping question name to orchestrator result
    """
    results = {}
    targets = CROSS_MODAL_QUESTIONS
    if questions:
        targets = [q for q in CROSS_MODAL_QUESTIONS if q["name"] in questions]

    for cq in targets:
        answer = orchestrator.run(cq["question"])
        results[cq["name"]] = answer

    return results
