"""Proposer Agent: generates scientifically grounded hypotheses from literature and existing findings.

Subclass of BaseAgent. Text-only (no code execution).
Deposits structured Hypothesis objects into the workspace.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from agents.base import BaseAgent
from agents.workspace import Workspace
from agents.memory import Memory

from .schemas import (
    CATEGORIES,
    FeasibilityAssessment,
    Hypothesis,
    LiteratureRef,
    TestPlan,
)
from .workspace import HypothesisWorkspace

log = logging.getLogger(__name__)

PROPOSER_PROMPT = """\
You are a Hypothesis Proposer for the AI-READI multimodal health dataset.
Your job is to generate scientifically grounded, mechanistically specific, \
falsifiable hypotheses testable with this dataset.

DATASET:
- 2,280 participants across 4 diabetes severity groups
- 10-day synchronized: CGM (5-min), Garmin wearable (HR, activity, sleep, SpO2), \
environmental sensors (PM2.5, temp, humidity, light)
- Single-timepoint: 12-lead ECG (11-sec), retinal imaging (OCT, OCTA, fundus), \
clinical labs (HbA1c, fasting glucose, insulin, lipids, kidney, liver)
- Constraints: sex REDACTED, medications REDACTED, Garmin HR is 1-5min averaged \
(not beat-to-beat), 11-sec ECG (RMSSD only for HRV)

EVERY HYPOTHESIS MUST SPECIFY:
1. Expected DIRECTION (not just "differs")
2. Expected LAG or TIMESCALE (5-60min acute, 1-8h ultradian, 12-36h circadian)
3. REFUTATION CRITERION (what result kills this hypothesis)
4. NEGATIVE CONTROL (what comparison should show NO effect)
5. CONFOUNDERS to adjust for (age, site, HbA1c, BMI minimum)
6. What part of AI-READI UNIQUELY ENABLES this test
7. Primary analytical METHOD
8. Expected EFFECT SIZE

CATEGORIES (use exactly one per hypothesis):
temporal_coupling, frequency_coupling, causal_architecture, event_dynamics, \
circadian_organization, environmental_modulation, physiotype_discovery, \
structural_dynamic, complexity_loss, resilience

RESPOND WITH A JSON ARRAY of hypothesis objects:
[{
  "title": "Short title",
  "category": "one_of_categories",
  "statement": "Specific falsifiable claim with direction",
  "mechanism": "Biological mechanism (WHY)",
  "predictions": ["Prediction 1 with direction", "Negative control prediction"],
  "literature": [{"title": "...", "authors": "First et al.", "journal": "...", \
"year": 2023, "key_finding": "...", "relevance": "...", "doi": "", "url": ""}],
  "feasibility": {"required_modalities": ["cgm", "wearable_hr"], \
"participant_coverage": 0.85, "time_resolution_needed": "5-min", \
"analysis_timescale": "acute (15-90 min)", "computational_cost": "medium", \
"statistical_power": "N~1900, well-powered for d>0.3", \
"key_challenges": ["..."], "dataset_limitations": ["..."]},
  "test_plan": {"primary_method": "...", "implementation_steps": ["Step 1", "Step 2"], \
"confounders_to_adjust": ["age", "clinical_site", "HbA1c", "BMI"], \
"time_window": "...", "frequency_bands": [], \
"expected_effect_size": "Cohen's d ~0.3-0.5", \
"success_criterion": "...", "refutation_criterion": "...", \
"sensitivity_checks": ["..."], "secondary_methods": []}
}]
"""


class ProposerAgent(BaseAgent):
    """Generates hypotheses from literature and existing findings."""

    name = "ProposerAgent"
    system_prompt = PROPOSER_PROMPT
    can_execute_code = False

    def __init__(
        self,
        hyp_workspace: HypothesisWorkspace,
        memory: Memory,
        model: str | None = None,
    ):
        # BaseAgent requires agents.workspace.Workspace — create a thin one
        ws = Workspace()
        super().__init__(workspace=ws, memory=memory, model=model)
        self.hyp_workspace = hyp_workspace

    def _build_full_prompt(self, task: str) -> str:
        """Override to inject hypothesis workspace state."""
        parts = [self.system_prompt]

        # Inject hypothesis workspace summary (what's been found, what's null)
        ws_summary = self.hyp_workspace.summary()
        parts.append(f"\n\nCURRENT HYPOTHESIS WORKSPACE:\n{ws_summary}")

        # Inject relevant memory (domain knowledge, constraints, prior findings)
        mem_context = self.memory.get_relevant(task)
        if mem_context:
            parts.append(f"\n\nRELEVANT DOMAIN KNOWLEDGE:\n{mem_context}")

        return "\n".join(parts)

    def propose_batch(self, n: int = 5) -> list[Hypothesis]:
        """Generate a batch of hypotheses.

        Args:
            n: Number of hypotheses to generate.

        Returns:
            List of Hypothesis objects with status="proposed".
        """
        task = (
            f"Generate {n} new hypotheses that are NOT redundant with existing ones. "
            f"Focus on the most promising unexplored directions based on the current "
            f"workspace state. Prioritize hypotheses where AI-READI's unique 10-day "
            f"synchronized multimodal window provides an advantage no other dataset can match."
        )

        result = self.run(task)
        return self._parse_hypotheses(result.answer)

    def _parse_hypotheses(self, text: str) -> list[Hypothesis]:
        """Parse LLM output into Hypothesis objects."""
        # Extract JSON array from response
        try:
            # Handle ```json blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            # Find array bounds
            start = text.index("[")
            end = text.rindex("]") + 1
            data = json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError) as e:
            log.error("Failed to parse proposer output as JSON: %s", e)
            log.debug("Raw output: %s", text[:500])
            return []

        hypotheses = []
        for i, item in enumerate(data):
            try:
                h = self._dict_to_hypothesis(item, i)
                hypotheses.append(h)
                log.info("Proposed: %s — %s", h.id, h.title)
            except Exception as e:
                log.warning("Failed to parse hypothesis %d: %s", i, e)

        return hypotheses

    def _dict_to_hypothesis(self, d: dict, index: int) -> Hypothesis:
        """Convert a parsed dict into a Hypothesis object."""
        # Build literature refs
        literature = []
        for ref in d.get("literature", []):
            literature.append(LiteratureRef(
                title=ref.get("title", ""),
                authors=ref.get("authors", ""),
                journal=ref.get("journal", ""),
                year=ref.get("year", 2024),
                key_finding=ref.get("key_finding", ""),
                relevance=ref.get("relevance", ""),
                doi=ref.get("doi", ""),
                url=ref.get("url", ""),
            ))

        # Build feasibility
        feas = d.get("feasibility", {})
        feasibility = FeasibilityAssessment(
            required_modalities=feas.get("required_modalities", []),
            participant_coverage=feas.get("participant_coverage", 0.85),
            time_resolution_needed=feas.get("time_resolution_needed", "5-min"),
            analysis_timescale=feas.get("analysis_timescale", ""),
            computational_cost=feas.get("computational_cost", "medium"),
            statistical_power=feas.get("statistical_power", ""),
            key_challenges=feas.get("key_challenges", []),
            dataset_limitations=feas.get("dataset_limitations", []),
        )

        # Build test plan
        tp = d.get("test_plan", {})
        test_plan = TestPlan(
            primary_method=tp.get("primary_method", ""),
            implementation_steps=tp.get("implementation_steps", []),
            confounders_to_adjust=tp.get("confounders_to_adjust", ["age", "clinical_site"]),
            time_window=tp.get("time_window", ""),
            frequency_bands=tp.get("frequency_bands", []),
            expected_effect_size=tp.get("expected_effect_size", ""),
            success_criterion=tp.get("success_criterion", ""),
            refutation_criterion=tp.get("refutation_criterion", ""),
            sensitivity_checks=tp.get("sensitivity_checks", []),
            secondary_methods=tp.get("secondary_methods", []),
        )

        return Hypothesis(
            title=d.get("title", f"Untitled hypothesis {index}"),
            category=d.get("category", "temporal_coupling"),
            statement=d.get("statement", ""),
            mechanism=d.get("mechanism", ""),
            predictions=d.get("predictions", []),
            literature=literature,
            feasibility=feasibility,
            priority=0.5,  # Initial; critic will revise
            status="proposed",
            test_plan=test_plan,
            source="proposer",
            created=datetime.now().isoformat(),
            updated=datetime.now().isoformat(),
        )

    def propose_and_deposit(self, n: int = 5) -> list[str]:
        """Generate hypotheses and deposit them into the workspace.

        Returns list of hypothesis IDs.
        """
        hypotheses = self.propose_batch(n)
        ids = []
        for h in hypotheses:
            hid = self.hyp_workspace.add(h)
            ids.append(hid)
        log.info("Deposited %d hypotheses into workspace", len(ids))
        return ids
