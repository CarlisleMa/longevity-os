"""Verifier Agent: 9 rule-based robustness checks + LLM interpretation.

Hybrid approach: mechanical checks produce pass/fail on each criterion,
then LLM synthesizes the overall verdict (supported/refuted/inconclusive).
"""

from __future__ import annotations

import json
import logging

import anthropic

from agents import config
from .schemas import CriticVerdict, Hypothesis, SensitivityCheck
from .workspace import HypothesisWorkspace

log = logging.getLogger(__name__)

INTERPRETATION_PROMPT = """\
You are a scientific results interpreter. Given a hypothesis, its results, \
and the outcome of 9 robustness checks, determine whether the hypothesis is \
SUPPORTED, REFUTED, or INCONCLUSIVE.

SUPPORTED: Primary prediction confirmed, majority of robustness checks pass, \
effect is clinically meaningful and statistically significant after adjustment.

REFUTED: Primary prediction not confirmed, effect is null or in wrong direction, \
or critical robustness checks fail.

INCONCLUSIVE: Mixed evidence — some checks pass, some fail. Effect may be real \
but not robust enough to claim support.

Respond with JSON:
{
  "verdict": "PASS" or "CONCERN" or "FAIL",
  "final_status": "supported" or "refuted" or "inconclusive",
  "statistical_rigor": 0.0-1.0,
  "biological_plausibility": 0.0-1.0,
  "novelty": 0.0-1.0,
  "importance": 0.0-1.0,
  "reproducibility": 0.0-1.0,
  "interpretation": "2-3 sentence summary of the evidence",
  "issues": ["remaining concern 1"],
  "suggestions": ["next step 1"]
}
"""


class VerifierAgent:
    """Verifies completed hypotheses with rule-based checks + LLM interpretation."""

    name = "VerifierAgent"

    def __init__(self, model: str | None = None):
        self.model = model or config.MODEL_CRITIC
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # ── Rule-based checks ─────────────────────────────────────────────

    def _check_covariate_adjustment(self, h: Hypothesis) -> tuple[bool, str]:
        """Verify age, site, HbA1c, BMI are in confounders_adjusted."""
        if not h.results:
            return False, "No results available"
        required = {"age", "hba1c", "bmi"}
        adjusted = {c.lower().replace(" ", "_") for c in h.results.confounders_adjusted}
        # Also accept partial matches
        adjusted_flat = " ".join(h.results.confounders_adjusted).lower()
        missing = [r for r in required if r not in adjusted and r not in adjusted_flat]
        if not missing:
            return True, f"Adjusted for: {', '.join(h.results.confounders_adjusted)}"
        return False, f"Missing adjustment for: {', '.join(missing)}"

    def _check_negative_control(self, h: Hypothesis) -> tuple[bool, str]:
        """Check if a negative control was run and showed null."""
        if not h.results or not h.results.sensitivity_checks:
            return False, "No sensitivity checks recorded"
        for sc in h.results.sensitivity_checks:
            name_lower = sc.name.lower()
            if any(kw in name_lower for kw in ("negative control", "random window", "null", "control")):
                if sc.passed:
                    return True, f"Negative control passed: {sc.details}"
                return False, f"Negative control FAILED: {sc.details}"
        return False, "No negative control found in sensitivity checks"

    def _check_dose_response(self, h: Hypothesis) -> tuple[bool, str]:
        """Check monotonic dose-response across 4 severity groups."""
        if not h.results or not h.results.group_values:
            return False, "No group values available"
        groups = ["healthy", "pre_diabetes", "oral_medication", "insulin_dependent"]
        vals = []
        for g in groups:
            for key, v in h.results.group_values.items():
                if g[:6] in key.lower():
                    vals.append(v)
                    break
        if len(vals) < 3:
            return False, f"Only {len(vals)} groups have values"
        increasing = all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))
        decreasing = all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))
        if increasing or decreasing:
            return True, f"Monotonic trend: {' → '.join(f'{v:.3f}' for v in vals)}"
        return False, f"Non-monotonic: {' → '.join(f'{v:.3f}' for v in vals)}"

    def _check_bootstrap_ci(self, h: Hypothesis) -> tuple[bool, str]:
        """Check if confidence interval excludes zero."""
        if not h.results or not h.results.confidence_interval:
            return False, "No confidence interval available"
        lo, hi = h.results.confidence_interval
        if (lo > 0 and hi > 0) or (lo < 0 and hi < 0):
            return True, f"CI [{lo:.3f}, {hi:.3f}] excludes zero"
        return False, f"CI [{lo:.3f}, {hi:.3f}] includes zero"

    def _check_sample_size(self, h: Hypothesis) -> tuple[bool, str]:
        """Verify N >= 100 per group."""
        if not h.results or not h.results.group_ns:
            if h.results and h.results.sample_size >= 500:
                return True, f"Total N = {h.results.sample_size}"
            return False, "No group Ns available"
        min_n = min(h.results.group_ns.values())
        if min_n >= 100:
            return True, f"Min group N = {min_n}"
        return False, f"Min group N = {min_n} (< 100)"

    def _check_effect_size(self, h: Hypothesis) -> tuple[bool, str]:
        """Verify effect size > 0.2 for clinical meaningfulness."""
        if not h.results:
            return False, "No results"
        d = abs(h.results.effect_size)
        if d >= 0.2:
            return True, f"|d| = {d:.3f} (>= 0.2, clinically meaningful)"
        return False, f"|d| = {d:.3f} (< 0.2, trivial effect)"

    def _check_fdr(self, h: Hypothesis) -> tuple[bool, str]:
        """Verify FDR-corrected p-value < 0.05."""
        if not h.results:
            return False, "No results"
        fdr = h.results.fdr_p_value
        if fdr < 0.05:
            return True, f"FDR p = {fdr:.2e} (< 0.05)"
        return False, f"FDR p = {fdr:.2e} (>= 0.05)"

    def _check_site_bias(self, h: Hypothesis) -> tuple[bool, str]:
        """Check if site was adjusted for."""
        if not h.results:
            return False, "No results"
        adjusted = " ".join(h.results.confounders_adjusted).lower()
        if "site" in adjusted or "clinical_site" in adjusted:
            return True, "Site included in covariates"
        # Check sensitivity checks
        for sc in h.results.sensitivity_checks:
            if "site" in sc.name.lower():
                return True, f"Site checked in sensitivity: {sc.name}"
        return False, "Site not adjusted for"

    def _check_sensitivity_survival(self, h: Hypothesis) -> tuple[bool, str]:
        """Check if >= 2/3 of sensitivity checks passed."""
        if not h.results or not h.results.sensitivity_checks:
            return False, "No sensitivity checks"
        checks = h.results.sensitivity_checks
        passed = sum(1 for sc in checks if sc.passed)
        total = len(checks)
        ratio = passed / total if total > 0 else 0
        if ratio >= 0.67:
            return True, f"{passed}/{total} sensitivity checks passed ({ratio:.0%})"
        return False, f"{passed}/{total} sensitivity checks passed ({ratio:.0%}, < 67%)"

    # ── Main verification flow ────────────────────────────────────────

    def run_rule_checks(self, h: Hypothesis) -> list[tuple[str, bool, str]]:
        """Run all 9 robustness checks."""
        checks = [
            ("Covariate adjustment", self._check_covariate_adjustment),
            ("Negative control", self._check_negative_control),
            ("Dose-response monotonicity", self._check_dose_response),
            ("Bootstrap CI", self._check_bootstrap_ci),
            ("Sample size", self._check_sample_size),
            ("Effect size", self._check_effect_size),
            ("FDR significance", self._check_fdr),
            ("Site bias", self._check_site_bias),
            ("Sensitivity survival", self._check_sensitivity_survival),
        ]
        results = []
        for name, fn in checks:
            passed, details = fn(h)
            results.append((name, passed, details))
            log.debug("  %s: %s — %s", name, "PASS" if passed else "FAIL", details)
        return results

    def interpret(
        self, h: Hypothesis, check_results: list[tuple[str, bool, str]]
    ) -> tuple[CriticVerdict, str]:
        """LLM interprets the results + check outcomes. Returns (verdict, final_status)."""
        checks_text = "\n".join(
            f"  {'PASS' if passed else 'FAIL'}: {name} — {details}"
            for name, passed, details in check_results
        )
        n_passed = sum(1 for _, p, _ in check_results if p)

        user_message = (
            f"## Hypothesis\n{h.statement}\n\n"
            f"## Results\n"
            f"Primary metric: {h.results.primary_metric} = {h.results.primary_value}\n"
            f"Effect size: {h.results.effect_size} ({h.results.effect_size_type})\n"
            f"FDR p-value: {h.results.fdr_p_value}\n"
            f"Interpretation: {h.results.interpretation}\n\n"
            f"## Robustness Checks ({n_passed}/9 passed)\n{checks_text}"
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=config.MAX_TOKENS,
            temperature=0.0,
            system=INTERPRETATION_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text

        # Parse JSON
        try:
            text = raw
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
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

            verdict = CriticVerdict(
                verdict=data.get("verdict", "CONCERN"),
                statistical_rigor=data.get("statistical_rigor", 0.5),
                biological_plausibility=data.get("biological_plausibility", 0.5),
                novelty=data.get("novelty", 0.5),
                importance=data.get("importance", 0.5),
                reproducibility=data.get("reproducibility", 0.5),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                overall_score=overall,
            )
            final_status = data.get("final_status", "inconclusive")
            return verdict, final_status

        except (ValueError, json.JSONDecodeError) as e:
            log.warning("Failed to parse verifier JSON: %s", e)
            # Fallback based on rule checks
            if n_passed >= 7:
                return CriticVerdict(verdict="PASS", overall_score=0.8), "supported"
            if n_passed <= 3:
                return CriticVerdict(verdict="FAIL", overall_score=0.3), "refuted"
            return CriticVerdict(verdict="CONCERN", overall_score=0.5), "inconclusive"

    def verify(self, h: Hypothesis, workspace: HypothesisWorkspace) -> str:
        """Full verification: rule checks + LLM interpretation + workspace update.

        Returns final status: "supported", "refuted", or "inconclusive".
        """
        if not h.results:
            log.warning("Cannot verify %s: no results", h.id)
            return "inconclusive"

        log.info("Verifying %s: %s", h.id, h.title)

        # 1. Run mechanical checks
        check_results = self.run_rule_checks(h)
        n_passed = sum(1 for _, p, _ in check_results if p)
        log.info("  Rule checks: %d/9 passed", n_passed)

        # 2. LLM interpretation
        verdict, final_status = self.interpret(h, check_results)

        # 3. Override LLM if rule checks strongly disagree
        if n_passed >= 7 and final_status == "refuted":
            log.warning("  LLM said refuted but 7+ checks pass — overriding to supported")
            final_status = "supported"
        elif n_passed <= 3 and final_status == "supported":
            log.warning("  LLM said supported but <=3 checks pass — overriding to inconclusive")
            final_status = "inconclusive"

        # 4. Update workspace
        workspace.set_verdict(h.id, verdict)
        workspace.update_status(h.id, final_status)

        log.info("  Final verdict: %s (score=%.2f)", final_status, verdict.overall_score)
        return final_status
