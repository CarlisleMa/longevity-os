"""Critic agent: validates every finding before it enters memory.

Single-pass review — no code execution, no iteration.
Inspired by Virtual Lab's Scientific Critic.
"""

import anthropic

from . import config
from .workspace import CriticVerdict


CRITIC_PROMPT = """\
You are the Critic for an AI-READI health data analysis system. You review \
statistical findings and their supporting code/output to identify methodological \
problems. You do NOT execute code — you reason about methodology.

CHECK EACH OF THE FOLLOWING:

1. CONFOUNDER ADJUSTMENT
   Was age adjusted for? Age correlates with nearly every clinical feature AND with \
study_group (insulin-dependent participants are older on average). If the analysis \
compares groups without age adjustment, this is a CONCERN.

2. SITE BIAS
   Were results checked across the 3 clinical sites (UW, UCSD, UAB)? \
If not, the finding could be a site artifact. Use site_bias_check() or stratify.

3. MULTIPLE COMPARISONS
   If more than one statistical test was performed, was FDR correction (e.g. \
Benjamini-Hochberg) applied? If not and multiple tests were run, this is a CONCERN.

4. EFFECT SIZE
   Is the effect clinically meaningful, not just statistically significant?
   Cohen's d: 0.2=small, 0.5=medium, 0.8=large
   Eta-squared: <0.01=negligible, 0.01-0.06=small, 0.06-0.14=medium, >0.14=large
   Pearson r: 0.1=small, 0.3=medium, 0.5=large
   With N=2280, even trivial effects achieve p<0.05.

5. SAMPLE SIZE
   How many participants had complete data for this analysis? If N < 100 in any \
group, flag low statistical power. Report the actual N used.

6. MISSING DATA
   Was missingness handled appropriately? Were participants dropped? How many? \
Could missingness be non-random (e.g. sicker patients more likely to have missing CGM)?

7. SEX REDACTION
   Does this analysis implicitly require sex? eGFR (CKD-EPI 2021), metabolic syndrome \
(ATP III), ASCVD risk score, and sex-stratified lab norms all require sex. \
If sex is needed, this is a FAIL.

8. CLINICAL PLAUSIBILITY
   Does the direction of the effect make clinical sense? For example:
   - HbA1c should INCREASE from healthy to insulin-dependent
   - TIR should DECREASE from healthy to insulin-dependent
   - Resting HR should be HIGHER in less fit individuals
   If the direction is reversed, flag for investigation.

OUTPUT FORMAT:
Respond with exactly one of these verdicts, followed by your reasoning:

PASS — Finding is methodologically sound.
CONCERN — Finding is plausible but has caveats that should be noted. List them.
FAIL — Finding has a critical methodological flaw. Explain what must be fixed.

Then list specific issues and suggestions.
"""


class CriticAgent:
    """Reviews findings for methodological validity. No code execution."""

    name = "CriticAgent"

    def __init__(self, model: str | None = None):
        self.model = model or config.MODEL_CRITIC
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def review(self, finding_id: str, finding_text: str, code_history: str) -> CriticVerdict:
        """Review a finding and return a verdict.

        Args:
            finding_id: ID of the finding in the workspace
            finding_text: The finding's interpretation/summary
            code_history: The code blocks and outputs that produced the finding
        """
        user_message = (
            f"## Finding to Review\n{finding_text}\n\n"
            f"## Code and Output\n{code_history}"
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=config.MAX_TOKENS,
            temperature=0.0,
            system=CRITIC_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text

        # Parse verdict
        status = "CONCERN"  # default if parsing fails
        for label in ("PASS", "CONCERN", "FAIL"):
            if label in raw_text[:50]:
                status = label
                break

        # Extract issues and suggestions (best-effort parsing)
        issues = []
        suggestions = []
        for line in raw_text.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                content = line[2:]
                if any(w in content.lower() for w in ("should", "recommend", "consider", "suggest")):
                    suggestions.append(content)
                else:
                    issues.append(content)

        return CriticVerdict(
            finding_id=finding_id,
            status=status,
            issues=issues,
            suggestions=suggestions,
            raw_text=raw_text,
        )
