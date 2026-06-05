"""Hypothesis Critic Agent: validates proposed hypotheses against dataset constraints.

Single-pass LLM review — follows agents/critic.py pattern.
No code execution, no iteration.
"""

from __future__ import annotations

import json
import logging

import anthropic

from agents import config
from .schemas import CriticVerdict, Hypothesis
from .workspace import HypothesisWorkspace

log = logging.getLogger(__name__)

HYPOTHESIS_CRITIC_PROMPT = """\
You are the Hypothesis Critic for the AI-READI dataset analysis system.
You review proposed hypotheses for scientific rigor, feasibility, and grounding.

DATASET CONSTRAINTS (apply strictly):
1. GARMIN HR RESOLUTION: Averaged at 1-5min intervals, NOT beat-to-beat. \
Any hypothesis requiring sub-minute HR dynamics is INFEASIBLE.
2. MEDICATIONS REDACTED: Cannot adjust for beta-blockers, metformin, insulin timing, SGLT2i. \
Coupling-severity gradients may partly reflect medication regimens.
3. 10-DAY WINDOW: Limits multi-day frequency estimates. Circadian estimates at >8h periods \
are underpowered (~2.5 cycles). Within-person longitudinal trajectories impossible.
4. STATISTICAL POWER: N~2280, even trivial effects (d=0.1) achieve significance. \
Require d>0.2 AND clinical meaningfulness.
5. SEX REDACTED: Cannot compute eGFR, MetS, ASCVD, or sex-stratified norms. \
Any hypothesis requiring sex is FAIL.
6. SITE CONFOUNDING: 3 clinical sites (UW, UCSD, UAB). Always require site adjustment.
7. AGE CONFOUNDING: Insulin-dependent participants are older. Must adjust for age.
8. BIOLOGICAL PLAUSIBILITY: Direction of effect must make mechanistic sense. \
Hypothesis must specify expected direction, not just "differs."
9. NO MEAL TIMING: Cannot distinguish meal-driven vs spontaneous glucose excursions.
10. CROSS-SECTIONAL: Cannot make longitudinal causal claims from 10-day observational data.

REVIEW EACH HYPOTHESIS FOR:
- Is the mechanism biologically real or hand-wavy?
- Can we actually measure what's proposed with Garmin HR + CGM?
- Is the expected effect size realistic?
- Are the negative controls actually negative?
- Is this just restating an existing finding with extra steps?
- Does the 10-day window provide enough data for the proposed analysis?

OUTPUT FORMAT (respond with valid JSON):
{
  "verdict": "PASS" or "CONCERN" or "FAIL",
  "statistical_rigor": 0.0-1.0,
  "biological_plausibility": 0.0-1.0,
  "novelty": 0.0-1.0,
  "importance": 0.0-1.0,
  "reproducibility": 0.0-1.0,
  "issues": ["issue 1", "issue 2"],
  "confounders_missed": ["confounder 1"],
  "suggestions": ["suggestion 1"],
  "rationale": "2-3 sentence justification"
}
"""


class HypothesisCriticAgent:
    """Reviews proposed hypotheses against dataset constraints."""

    name = "HypothesisCriticAgent"

    def __init__(self, model: str | None = None):
        self.model = model or config.MODEL_CRITIC
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def review(self, hypothesis: Hypothesis, workspace_summary: str = "") -> CriticVerdict:
        """Review a hypothesis and return a verdict."""
        user_message = (
            f"## Hypothesis to Review\n\n{hypothesis.full_report()}\n\n"
            f"## Current Workspace State\n\n{workspace_summary}"
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=config.MAX_TOKENS,
            temperature=0.0,
            system=HYPOTHESIS_CRITIC_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text
        return self._parse_verdict(raw)

    def review_and_update(
        self, hypothesis: Hypothesis, workspace: HypothesisWorkspace
    ) -> CriticVerdict:
        """Review a hypothesis and update the workspace accordingly."""
        verdict = self.review(hypothesis, workspace.summary())

        # Compute revised priority
        revised_priority = verdict.overall_score * hypothesis.priority

        if verdict.verdict == "FAIL":
            workspace.update_status(hypothesis.id, "rejected")
            log.info("Hypothesis %s REJECTED: %s", hypothesis.id, verdict.issues[:1])
        else:
            workspace.set_priority(hypothesis.id, revised_priority)
            workspace.update_status(hypothesis.id, "validated")
            log.info(
                "Hypothesis %s VALIDATED (P=%.2f): %s",
                hypothesis.id, revised_priority, verdict.verdict,
            )

        return verdict

    def _parse_verdict(self, raw: str) -> CriticVerdict:
        """Parse LLM output into CriticVerdict."""
        # Try JSON parsing first
        try:
            # Extract JSON block if wrapped in ```json
            text = raw
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            # Find first { to last }
            start = text.index("{")
            end = text.rindex("}") + 1
            data = json.loads(text[start:end])

            overall = (
                data.get("statistical_rigor", 0.5) * 0.25
                + data.get("biological_plausibility", 0.5) * 0.20
                + data.get("novelty", 0.5) * 0.20
                + data.get("importance", 0.5) * 0.20
                + data.get("reproducibility", 0.5) * 0.15
            )

            return CriticVerdict(
                verdict=data.get("verdict", "CONCERN"),
                statistical_rigor=data.get("statistical_rigor", 0.5),
                biological_plausibility=data.get("biological_plausibility", 0.5),
                novelty=data.get("novelty", 0.5),
                importance=data.get("importance", 0.5),
                reproducibility=data.get("reproducibility", 0.5),
                issues=data.get("issues", []),
                confounders_missed=data.get("confounders_missed", []),
                suggestions=data.get("suggestions", []),
                overall_score=overall,
            )
        except (ValueError, json.JSONDecodeError, KeyError) as e:
            log.warning("Failed to parse critic JSON, falling back to text parsing: %s", e)
            return self._parse_verdict_text(raw)

    def _parse_verdict_text(self, raw: str) -> CriticVerdict:
        """Fallback text-based parsing."""
        verdict = "CONCERN"
        for label in ("PASS", "CONCERN", "FAIL"):
            if label in raw[:100]:
                verdict = label
                break

        issues, suggestions = [], []
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith(("- ", "* ")):
                content = line[2:]
                if any(w in content.lower() for w in ("should", "consider", "suggest", "recommend")):
                    suggestions.append(content)
                else:
                    issues.append(content)

        return CriticVerdict(
            verdict=verdict,
            statistical_rigor=0.5,
            biological_plausibility=0.5,
            novelty=0.5,
            importance=0.5,
            reproducibility=0.5,
            issues=issues,
            suggestions=suggestions,
            overall_score=0.5,
        )
