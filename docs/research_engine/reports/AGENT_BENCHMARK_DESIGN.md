# Agent System Evaluation Benchmark Design

> **Date:** 2026-04-27
> **Status:** Draft
> **Purpose:** Make the multi-agent system a publishable contribution, not just infrastructure.
> **Key question:** Does the agent system produce better, faster, or more rigorous science than alternatives?

---

## 1. Why a Benchmark Matters

Without evaluation, the agent system is a demo. With evaluation, it's a methods contribution.

The benchmark must answer:
1. **Does multi-agent beat single-agent?** (Vivaldi found multi-agent can *hurt* thinking models)
2. **Does the Critic catch real errors?** (Not just flag everything)
3. **Do agents discover non-obvious findings?** (Beyond running pre-written scripts)
4. **Is the system grounded?** (LongevityBench: LLMs score 0.48-0.54 on aging biology)

---

## 2. Benchmark Structure

### 2.1 Question Types (5 categories, ~100 questions total)

#### Category A: Factual Retrieval (20 questions)
**What it tests:** Can agents correctly extract facts from the data?
**Auto-scorable:** Yes (exact match or within tolerance)

Examples:
1. "What is the mean HbA1c for the insulin-dependent group?" → 7.38 ± 0.1
2. "How many participants have complete CGM data (>70% capture)?" → verifiable count
3. "What is the Pearson correlation between age and SBP across the full cohort?" → verifiable r
4. "What fraction of participants have both CGM and wearable data?" → verifiable %
5. "What is the median HOMA-IR for each study group?" → 4 verifiable values
6. "How many participants are missing all blood labs?" → 47
7. "What is the mean wear time (days) for the environmental sensor?" → verifiable
8. "What is the most common condition in the cohort?" → verifiable from conditions
9. "What is the age range of pre-diabetes participants?" → verifiable
10. "How many participants have >2 ECG recordings?" → 6

**Scoring:** |predicted - true| / true < threshold → correct

#### Category B: Statistical Computation (20 questions)
**What it tests:** Can agents correctly compute statistics with proper methodology?
**Auto-scorable:** Partially (correct statistic + correct interpretation)

Examples:
11. "Is HbA1c significantly different across the 4 study groups? Report the test, p-value, and effect size." → Kruskal-Wallis, p < 1e-100, η² ≈ 0.41
12. "Is the difference in resting HR between healthy and insulin-dependent groups significant after adjusting for age?" → partial correlation
13. "Compute the Frailty Index for the cohort. What is its AUC for discriminating healthy vs insulin-dependent?" → ~0.90
14. "Is there site bias in HbA1c?" → yes, p ≈ 6.56e-06
15. "What is the Cohen's d for BMI between healthy and insulin-dependent groups?" → verifiable
16. "Compute TIR (70-180) for participants with CGM. Is it different across groups after FDR correction?" → yes
17. "Run a Ridge regression predicting age from cardiovascular features. What is the test MAE?" → ~8.13
18. "Is HOMA-IR correlated with circadian regularity (IS) after adjusting for age and site?" → verifiable partial r
19. "Compute the allostatic load for each participant. How many in each group have AL > 6?" → verifiable counts
20. "Test whether glucose-HR cross-correlation differs across the 4 groups." → verifiable (this uses coupling!)

**Scoring:** Correct test chosen + correct value within tolerance + correct interpretation

#### Category C: Methodological Rigor (20 questions)
**What it tests:** Does the agent catch statistical pitfalls and apply proper methodology?
**Scored by:** Critic agent output vs gold standard issues list

Examples:
21. "I found that retinal AgeAccel is significantly associated with diabetes severity (p=0.002). Can we publish this?" → Agent should flag: Was age adjusted? Was site bias checked? Effect size? FDR? What was the sample size?
22. "HOMA-IR is higher in the insulin-dependent group (p<0.001, d=0.3). Is this clinically meaningful?" → Agent should note: d=0.3 is small effect despite statistical significance
23. "I computed eGFR for all participants. The insulin-dependent group has worse kidney function." → Agent MUST flag: sex is redacted, eGFR cannot be computed
24. "I found a strong correlation between CGM metrics and retinal vessel density (r=0.6, p<0.001, n=30)." → Agent should question: n=30 is small, effect may not replicate, check for outliers
25. "The aging clock has MAE=8 years and R²=0.18. Is this good?" → Agent should contextualize: modest for aging clocks, comparable to published ECG age models
26. "I found PhenoAge acceleration differs by group." → Agent MUST flag: PhenoAge requires lymphocyte %, which is missing in AI-READI
27. "Evening light exposure predicts next-day glucose (β=0.15, p=0.03)." → Agent should ask: adjusted for time-of-day? Adjusted for sleep duration? Multiple comparisons?
28. "Glucose variability causes retinal damage based on our cross-sectional analysis." → Agent should flag: cannot establish causation from cross-sectional data
29. "Using all 125 features, I get a model with R²=0.45 predicting HbA1c." → Agent should ask: is this overfit? What's the test set R²? How many features vs. samples?
30. "The metabolic aging clock has R²=0.04. Should we include it in the paper?" → Agent should discuss: low R² but may still capture meaningful variance; report with appropriate caveats

**Scoring:** Checklist of issues per question. Score = fraction of issues caught.

#### Category D: Cross-Modal Reasoning (20 questions)
**What it tests:** Can agents integrate information across modalities and propose meaningful analyses?
**Scored by:** Expert rating (1-5 scale for relevance, novelty, feasibility)

Examples:
31. "Is glycemic variability associated with resting heart rate after adjusting for age and diabetes severity?"
32. "Do participants with higher circadian disruption have worse glycemic control?"
33. "Is there a relationship between nocturnal HR dip and CGM nocturnal glucose stability?"
34. "Does PM2.5 exposure correlate with same-day heart rate or glucose?"
35. "What is the glucose-HR cross-correlation for each participant? Does coupling strength differ by study group?"
36. "Do participants with accelerated retinal aging also show accelerated cardiac aging?"
37. "Is sleep efficiency a mediator between circadian disruption and insulin resistance?"
38. "Which single non-invasive feature (from wearable or CGM) best predicts HbA1c?"
39. "Find the most 'discordant' participants — those whose organ-specific ages disagree the most."
40. "Does evening light exposure mediate the relationship between screen time and sleep quality?"

**Scoring:** Expert rates: (a) correct interpretation, (b) appropriate method chosen, (c) proper adjustments, (d) novel insight, (e) actionable conclusion

#### Category E: Open-Ended Discovery (20 questions)
**What it tests:** Can agents discover non-obvious patterns that weren't pre-specified?
**Scored by:** Expert rating + novelty assessment

Examples:
41. "Explore the relationship between environmental exposure and glycemic variability. What do you find?"
42. "Generate a comprehensive multimodal health report for participant [X]. What stands out?"
43. "What novel finding can you discover that requires combining at least 3 modalities?"
44. "Are there participant subgroups that don't align with the 4 clinical diabetes groups?"
45. "What is the most surprising relationship you can find in this dataset?"
46. "Propose a hypothesis about why the unified aging clock performs worse than individual clocks."
47. "If you could measure one additional variable, what would most improve our understanding?"
48. "What analysis would you run to determine if coupling measures add value beyond static features?"
49. "Design a study to test whether coupling-based age acceleration predicts diabetes complications."
50. "What is the strongest evidence for or against the 'diabetes as decoupling' hypothesis?"

**Scoring:** Expert rates: novelty, scientific validity, groundedness (no hallucination), actionability

---

## 3. Ablation Studies

### 3.1 System Configurations to Compare

| Configuration | Description | What it tests |
|---|---|---|
| **Full system** | Orchestrator + 6 modality + 5 reasoning + Critic | Baseline performance |
| **No Critic** | Full system minus CriticAgent | Does the Critic catch real errors? |
| **No memory** | Full system with empty memory (no domain knowledge, no constraints) | Does pre-seeded knowledge help? |
| **Single agent** | One powerful agent with all tools, no orchestration | Does specialization help? |
| **Orchestrator only** | Orchestrator + modality agents, no reasoning agents | Do reasoning agents add value? |
| **No code execution** | Agents reason but cannot execute Python | Does code-grounding prevent hallucination? |

### 3.2 Metrics Per Configuration

| Metric | Category A-B | Category C | Category D-E |
|---|---|---|---|
| **Accuracy** | % correct within tolerance | % issues caught | Expert score 1-5 |
| **Hallucination rate** | % answers with fabricated numbers | % claims without evidence | % ungrounded assertions |
| **Completeness** | % questions answered (vs. "I don't know") | % checklist items covered | % modalities incorporated |
| **Efficiency** | API tokens used | Turns taken | Time to completion |
| **Critic catch rate** | N/A | True positive rate (real issues flagged) | N/A |
| **Critic false alarm** | N/A | False positive rate (valid findings rejected) | N/A |

### 3.3 Key Comparisons

1. **Full system vs Single agent**: This is the headline comparison. If full system scores higher on Category D-E (cross-modal reasoning), multi-agent is justified.
2. **With Critic vs Without Critic**: If Critic catches >50% of methodological issues in Category C, it's a genuine contribution.
3. **With memory vs Without memory**: If memory improves performance on constraint-dependent questions (eGFR, PhenoAge, insulin units), it demonstrates domain grounding.
4. **Code execution vs No code**: If code-grounded agents have lower hallucination rates, it validates the CodeAct approach.

---

## 4. Ground Truth Generation

### 4.1 Category A-B: Automated
- Pre-compute all answers using the existing scripts/
- Store as JSON: `{question_id, expected_answer, tolerance, method}`
- Auto-score by comparing agent output to expected

### 4.2 Category C: Semi-automated
- Create issue checklists per question (expert-generated)
- Parse agent/Critic output for issue mentions
- Score = fraction of checklist items addressed

### 4.3 Category D-E: Expert Panel
- 2-3 domain experts rate each response
- Rubric: correctness (0-2), methodology (0-2), insight (0-1) = max 5
- Inter-rater reliability (Cohen's kappa)

---

## 5. Coupling-Specific Benchmark Extension

Once coupling features are computed, add 20 coupling-specific questions:

51-55: Factual coupling retrieval
  - "What is the mean glucose-HR cross-correlation across the healthy group?"
  - "How many participants have >0.3 glucose-HR coherence at the circadian frequency?"

56-60: Coupling statistics
  - "Is glucose-HR transfer entropy significantly different across diabetes groups?"
  - "Compute the coupling-based aging clock. What is its AUC vs the static clock?"

61-65: Coupling rigor
  - "I found that coupling strength predicts retinal aging (p=0.01). Is this valid?"
  - "Can we claim that low glucose-HR coupling CAUSES retinal damage?"

66-70: Coupling discovery
  - "Which coupling edge breaks first in pre-diabetes?"
  - "Do coupling-based subtypes identify at-risk individuals that static subtypes miss?"

---

## 6. Implementation Plan

1. **Generate ground truth** for Categories A-B (run scripts, store answers) — 1 day
2. **Write issue checklists** for Category C — 1 day
3. **Prepare expert rating rubric** for Categories D-E — 0.5 day
4. **Run full system** on all 50 questions — 1 day (API cost: ~$50-100)
5. **Run ablation configurations** (5 configs × 50 questions) — 3-5 days
6. **Expert rating** of Category D-E responses — 2-3 days
7. **Analysis and figures** — 1 day

Total: ~2 weeks for a complete evaluation.

---

## 7. What Would Make This Publishable

**The ideal finding:**
- Full multi-agent system scores 85%+ on Categories A-B (factual + statistical)
- Critic catches 70%+ of methodological issues
- Multi-agent outperforms single-agent by >15% on cross-modal reasoning (Category D)
- Code-grounded agents have <5% hallucination rate (vs >20% without code)
- Memory-equipped agents correctly handle 100% of constraint-dependent questions

**The honest finding that's still publishable:**
- Multi-agent and single-agent are comparable on simple tasks
- Multi-agent excels on cross-modal reasoning where context window overflow breaks single-agent
- Critic catches meaningful errors but also has false positives
- The system's real value is scaling N-of-1 analysis to 2,280 participants

Either story is publishable. The benchmark makes both stories credible.
