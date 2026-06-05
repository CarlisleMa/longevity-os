# Hypothesis-Driven Scientific Discovery System

## Systematic Design for Agentic Multi-Modal Physiological Analysis

---

## 1. Design Philosophy

### 1.1 Why Hypothesis-Driven

Traditional computational biology workflows follow a **feature-first** pipeline:

```
Raw signals → Extract features → Test all pairwise associations → Report significant ones
```

This approach has three fundamental problems:

1. **Information loss**: Compressing a 2,880-point time series into a scalar (mean, CV, TIR) discards temporal dynamics, event responses, frequency structure, and coupling architecture.
2. **Arbitrary analysis choices**: Which features to compute, what lag to test, which pairs to correlate — each choice is a researcher degree of freedom that inflates false discovery rates.
3. **Post-hoc interpretation**: Patterns are found first and explained after, inverting the scientific method and making confirmation bias inevitable.

Our system inverts this: **mechanism first, measurement second**.

```
Physiological mechanism → Specific prediction → Designed test → Structured result → Verdict
```

This aligns with the classical hypothetico-deductive method, but augmented by LLM agents for scalable hypothesis generation and automated execution.

### 1.2 Dual-Mode Discovery: Theory-Driven and Data-Driven

We implement two complementary hypothesis generation modes:

| Mode | Source | Strength | Risk |
|---|---|---|---|
| **Theory-driven** | Literature, known physiology, mechanistic reasoning | Interpretable, grounded, publishable | Misses novel patterns, limited by existing knowledge |
| **Data-driven** | Observed anomalies, unexpected results, null findings | Can discover genuinely new phenomena | Risk of p-hacking dressed as hypothesis |

**Theory-driven example**: "Autonomic neuropathy in diabetes causes progressive vagal denervation → impaired parasympathetic HR buffering → post-excursion HR response should be blunted, strongest 15-90 min after glucose excursions, weaker during sleep."

**Data-driven example**: "H-MIG01 showed broadband coupling increases with severity (d=0.585). But H-NEW01 revealed this masks a directional flip: fast coupling *decreases*. This unexpected pattern generates a new hypothesis: fast and slow coupling may reflect distinct disease processes."

**Key principle**: Data-driven observations are legitimate *seeds* for hypotheses, but every seed must be formalized into a mechanistic, falsifiable claim before testing. The transition from observation to hypothesis is where the Proposer Agent adds mechanism, direction, timescale, and controls.

### 1.3 Positioning Among Existing Systems

| System | Approach | Key Difference from Ours |
|---|---|---|
| AI Scientist (Anthropic/Sakana, 2024) | Fully autonomous paper generation | No domain grounding; generic ML experiments |
| Virtual Lab (MIT, 2024) | Multi-agent with human PI | Our system adds structured hypothesis lifecycle tracking |
| SciAgents (Wiley, 2025) | Knowledge graph reasoning | We use time-series computation, not just graph traversal |
| Agent Laboratory (2025) | Literature → experiment → writeup | We add a Verifier with 9 mechanical robustness checks |
| **This system** | Hypothesis lifecycle with dual-mode generation, automated Slurm execution, and rule-based verification | Domain-specific to physiological coupling, grounded in both literature AND computed features |

---

## 2. System Architecture

### 2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYPOTHESIS WORKSPACE                         │
│              (JSON-backed persistent state store)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ proposed │→│ critiqued│→│ validated│→│ executing│→ ...      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │ read/write
    ┌────────────────────┼────────────────────────┐
    │                    │                        │
    ▼                    ▼                        ▼
┌────────┐         ┌──────────┐            ┌──────────┐
│PROPOSER│────────→│  CRITIC  │            │ VERIFIER │
│ Agent  │ propose │  Agent   │            │  Agent   │
└────────┘         └──────────┘            └──────────┘
    ▲                    │                      ▲
    │                    │ validate              │ verify
    │                    ▼                      │
    │              ┌──────────┐                 │
    │              │ EXECUTOR │─────────────────┘
    │              │  Agent   │ execute → complete
    │              └──────────┘
    │                    │
    │                    │ Slurm cluster
    │                    ▼
    │         ┌──────────────────────┐
    │         │  32-shard parallel   │
    │         │  feature extraction  │
    │         │  + postprocess       │
    │         └──────────────────────┘
    │
    └──── Feedback: null results, surprises, new patterns
          inform next proposal cycle
```

### 2.2 Agent Specifications

| Agent | Type | LLM Calls | Code Execution | Input | Output |
|---|---|---|---|---|---|
| **Proposer** | BaseAgent subclass | Yes (text generation) | No | Workspace summary, memory, existing findings | `list[Hypothesis]` with status="proposed" |
| **Critic** | CriticAgent pattern | Yes (single-pass review) | No | Hypothesis + workspace context | `CriticVerdict` (PASS/CONCERN/FAIL + scores) |
| **Executor** | BaseAgent subclass | Yes (code generation) | Yes (write scripts) | Validated hypothesis with TestPlan | Slurm job IDs → `HypothesisResult` |
| **Verifier** | Hybrid (rules + LLM) | Yes (interpretation) | No | Completed hypothesis with results | Final status: supported/refuted/inconclusive |

### 2.3 The Hypothesis Workspace

The workspace is the central state store. Every agent reads from and writes to it. It enforces the lifecycle state machine:

```
proposed → critiqued → validated → queued → executing → completed → verified
                     ↘ rejected                                    ↙ ↓ ↘
                                                           supported  refuted  inconclusive
```

**Persistence**: Each hypothesis is a JSON file (`H-XXXX.json`). The workspace loads all files on init and caches in memory. Mutations write through to disk immediately.

**Concurrency**: File-level locking via `filelock.FileLock` prevents race conditions when multiple pipeline instances run.

---

## 3. The Discovery Workflow

### 3.1 The Full Cycle

```
CYCLE START
    │
    ├── Any completed hypotheses awaiting verification?
    │   YES → Verifier: run 9 rule checks + LLM interpretation
    │         → Update status: supported / refuted / inconclusive
    │
    ├── Any validated hypotheses in execution queue?
    │   YES → Executor: generate script → submit Slurm → wait → collect
    │         → Update status: completed
    │
    ├── Queue empty?
    │   YES → Proposer: generate N new hypotheses
    │         → Critic: review each → validate or reject
    │         → Replenish queue
    │
    └── Log cycle summary → CYCLE END
```

Each cycle performs exactly **one action**: verify, execute, or propose. This ensures atomic state transitions and clean logging.

### 3.2 Proposal Phase (Theory-Driven + Data-Driven)

The Proposer Agent generates hypotheses from two source types:

**Theory-driven generation** (primary mode):
- Input: Literature knowledge embedded in the system prompt (Network Physiology: Bashan et al. 2012; Loss of Complexity: Lipsitz & Goldberger 1992; Autonomic Neuropathy: Vinik & Ziegler 2007; etc.)
- Process: LLM reasons about what physiological mechanisms should produce detectable patterns in CGM + wearable data
- Quality: Mechanism is specified *before* prediction; the hypothesis could be tested on any similar dataset

**Data-driven generation** (secondary mode, triggered by results):
- Input: Surprising or null results from previous cycles (injected via workspace summary)
- Process: LLM identifies unexpected patterns and formalizes them into testable claims
- Quality: Observation comes first, but mechanism must be added before the hypothesis is deposited
- Example: "Broadband coupling increase (d=0.585) masks a frequency-dependent flip. This suggests fast and slow coupling are distinct processes — testable by correlating per-person fast-band coherence with excursion HR blunting."

**The key safeguard**: Both modes produce hypotheses in the same structured format with the same quality requirements. The Critic cannot distinguish the source — it evaluates feasibility and rigor identically.

### 3.3 Critique Phase (Quality Gate)

Every hypothesis passes through the Critic before entering the execution queue. The Critic enforces **10 dataset-specific constraints**:

| # | Constraint | What it catches |
|---|---|---|
| 1 | Garmin HR resolution (1-5min, not beat-to-beat) | Hypotheses requiring sub-minute HR dynamics |
| 2 | Medications redacted | Claims about medication effects |
| 3 | 10-day window limit | Underpowered multi-day frequency estimates |
| 4 | Statistical power (N~2280) | Trivial effect sizes passed off as findings |
| 5 | Sex redacted | Analyses requiring sex-stratified norms |
| 6 | Site confounding (3 sites) | Missing site adjustment |
| 7 | Age confounding | Missing age adjustment |
| 8 | Biological plausibility | Effects in wrong direction |
| 9 | No meal timing | Misattribution of glucose excursion etiology |
| 10 | Cross-sectional design | Causal claims from observational data |

**Output**: Dimensional scores (0-1) for statistical rigor, biological plausibility, novelty, importance, reproducibility. Weighted composite becomes the execution priority.

**Decision rule**:
- PASS/CONCERN → status = "validated", enters execution queue
- FAIL → status = "rejected", archived with rationale

### 3.4 Execution Phase (Slurm-Parallel Computation)

The Executor translates a hypothesis TestPlan into runnable code:

```
TestPlan                      Generated Code
─────────                     ──────────────
primary_method:               Python script with:
  "spectral_coherence"          - argparse (--num-shards, --shard-index)
                                - load aligned time series per participant
confounders_to_adjust:          - compute hypothesis-specific features
  [age, site, HbA1c, BMI]      - save per-shard parquet

time_window:                  Postprocess script with:
  "full 10-day"                 - merge shards
                                - join metadata
sensitivity_checks:             - Kruskal-Wallis + trend + Cohen's d
  [awake/sleep, bootstrap]      - FDR correction
                                - write JSON summary
```

**Slurm pattern**: Array job (8-32 shards based on computational cost) + postprocess dependency job. Each shard processes ~60-240 participants.

### 3.5 Verification Phase (Rule-Based + LLM)

The Verifier applies **9 mechanical robustness checks**:

| Check | Criterion | Rationale |
|---|---|---|
| 1. Covariate adjustment | age + HbA1c + BMI in confounders | Prevents trivial confounding |
| 2. Negative control | Random windows show no effect | Confirms signal is hypothesis-specific |
| 3. Dose-response | Monotonic across 4 severity groups | Biological gradient, not artifact |
| 4. Bootstrap CI | 95% CI excludes zero | Effect is not a statistical fluke |
| 5. Sample size | N ≥ 100 per group | Adequate power |
| 6. Effect size | \|d\| ≥ 0.2 | Clinically meaningful, not trivially significant |
| 7. FDR significance | FDR p < 0.05 | Survives multiple testing |
| 8. Site bias | Site in covariates or sensitivity checks | Not a site artifact |
| 9. Sensitivity survival | ≥ 67% of sensitivity checks pass | Robust to analytical choices |

**Decision rule**:
- ≥ 7/9 checks pass AND LLM says PASS → **supported**
- ≤ 3/9 checks pass OR LLM says FAIL → **refuted**
- Otherwise → **inconclusive**

**Override mechanism**: If the LLM and rule checks strongly disagree (e.g., LLM says refuted but 8/9 checks pass), the rule checks take precedence. Mechanical evidence outweighs LLM judgment.

---

## 4. Hypothesis Schema (Structured Output)

Every hypothesis is a self-contained scientific claim with full provenance:

### 4.1 Required Fields

```
┌──────────────────────────────────────────────────────┐
│  HYPOTHESIS                                          │
├──────────────────────────────────────────────────────┤
│  Identity                                            │
│    id: H-NEW03                                       │
│    title: Post-excursion HR blunting in diabetes      │
│    category: event_dynamics                          │
│    source: proposer | migrated | data-driven         │
├──────────────────────────────────────────────────────┤
│  Scientific Content                                  │
│    statement: [falsifiable claim with direction]      │
│    mechanism: [biological WHY]                       │
│    predictions: [list of testable predictions]       │
├──────────────────────────────────────────────────────┤
│  Grounding                                           │
│    literature: [2-4 papers with specific findings]   │
│    feasibility: {modalities, coverage, power, ...}   │
├──────────────────────────────────────────────────────┤
│  Test Plan                                           │
│    primary_method: [analytical technique]            │
│    time_window: [specific temporal scope]            │
│    confounders: [minimum: age, site, HbA1c, BMI]    │
│    expected_effect_size: [quantitative prediction]   │
│    success_criterion: [what supports it]             │
│    refutation_criterion: [what kills it]             │
│    sensitivity_checks: [robustness tests]            │
├──────────────────────────────────────────────────────┤
│  Results (filled after execution)                    │
│    primary_value, effect_size, p_value, fdr_p_value  │
│    group_values, group_ns, sensitivity_checks        │
│    interpretation, surprises                         │
├──────────────────────────────────────────────────────┤
│  Verdict (filled after verification)                 │
│    verdict: PASS | CONCERN | FAIL                    │
│    dimensional_scores: rigor, plausibility, ...      │
│    overall_score: weighted composite                 │
│  Status: supported | refuted | inconclusive          │
├──────────────────────────────────────────────────────┤
│  Relationships                                       │
│    depends_on: [prerequisite hypothesis IDs]         │
│    supports: [corroborating hypothesis IDs]          │
│    contradicts: [conflicting hypothesis IDs]         │
└──────────────────────────────────────────────────────┘
```

### 4.2 The 7 Quality Requirements

Every hypothesis MUST specify these before entering the execution queue:

| # | Requirement | Purpose | Example (H-NEW03) |
|---|---|---|---|
| 1 | **Direction** | Prevents vague "differs" claims | "HR peak is *blunted* (lower) in insulin-dependent" |
| 2 | **Timescale** | Forces mechanistic specificity | "Strongest 15-90 min after glucose excursions" |
| 3 | **Refutation criterion** | Makes hypothesis falsifiable | "No group difference after adjusting for excursion magnitude and activity" |
| 4 | **Negative control** | Separates signal from noise | "Random non-excursion windows show no group difference" |
| 5 | **Confounders** | Prevents trivial explanations | "Age, site, HbA1c, BMI, glucose mean, HR mean" |
| 6 | **Unique enabler** | Justifies using this dataset | "Only AI-READI has synchronized CGM + wearable at N > 2000" |
| 7 | **Expected effect size** | Prevents fishing expeditions | "Cohen's d ~ 0.3-0.5 for insulin vs healthy" |

### 4.3 Hypothesis Categories

10 categories organized by the type of physiological question:

| Category | Question | Timescale | Methods |
|---|---|---|---|
| temporal_coupling | At what timescale does coupling change? | Variable | Cross-correlation, partial correlation |
| frequency_coupling | Which frequency bands carry the signal? | Multi-scale | Spectral coherence, wavelet |
| causal_architecture | What is the direction of information flow? | Acute-medium | Transfer entropy, CCM, Granger |
| event_dynamics | What happens after a perturbation? | 5-90 min | Event-triggered averaging |
| circadian_organization | Are rhythms aligned across systems? | 12-36 h | Cosinor, phase coherence |
| environmental_modulation | Does environment modulate coupling? | Hours-days | Distributed lag models |
| physiotype_discovery | Are there coupling-based subtypes? | Aggregate | Clustering, UMAP |
| structural_dynamic | Does coupling predict structural damage? | Cross-modal | Mediation, prediction |
| complexity_loss | Is signal complexity degraded? | Multi-scale | Multiscale entropy, DFA |
| resilience | How fast does the system recover? | Minutes-hours | Recovery kinetics, transition dynamics |

---

## 5. Feedback and Refinement Mechanisms

### 5.1 The Refinement Loop

The system is designed to learn from its own results through four feedback mechanisms:

```
                    ┌─────────────────────────┐
                    │   HYPOTHESIS WORKSPACE   │
                    │   (accumulates evidence) │
                    └─────────┬───────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
   ┌──────────┐       ┌──────────┐       ┌──────────┐
   │ Null      │       │ Surprise │       │ Supported│
   │ Result    │       │ Finding  │       │ Finding  │
   │ Feedback  │       │ Feedback │       │ Feedback │
   └─────┬────┘       └─────┬────┘       └─────┬────┘
         │                   │                   │
         ▼                   ▼                   ▼
   Close related       Seed new              Deepen:
   hypotheses;         data-driven           more specific
   update proposer     hypothesis            sub-hypotheses
   constraints
```

### 5.2 Mechanism 1: Null Result Learning

When a hypothesis is **refuted**, the Proposer's context includes this null result. This prevents:
- Re-proposing the same hypothesis in different words
- Proposing variants that would fail for the same reason

**Example**: H-NEW06 (nocturnal coupling → next-day glucose) was refuted (rho = -0.004, p = 0.67). The workspace summary now includes this null, and the Proposer knows not to propose nocturnal coupling variants unless the mechanism is fundamentally different.

### 5.3 Mechanism 2: Surprise Escalation

When a result contradicts the prediction but is still significant, it becomes a **data-driven seed**:

**Example**: H-MIG01 predicted coupling would decrease with diabetes (the "decoupling" hypothesis from network physiology literature). The result showed coupling **increases**. This surprise seeded H-NEW01 (frequency decomposition), which revealed the true story: fast coupling decreases while slow coupling increases. The broadband increase was an artifact of averaging.

The Proposer's context includes `surprises` fields from completed hypotheses, explicitly flagging unexpected results for follow-up.

### 5.4 Mechanism 3: Hypothesis Deepening

When a hypothesis is **supported**, it generates sub-hypotheses that drill deeper:

```
H-MIG01: Broadband coupling increases (SUPPORTED)
    ├── H-NEW01: Is this timescale-selective? (PARTIALLY SUPPORTED — direction flips)
    │       ├── H-NEW03: Is the fast coupling loss event-triggered? (SUPPORTED — d=0.80)
    │       └── [future] Does fast-band coherence correlate with excursion HR blunting?
    └── H-NEW17: Is this time-of-day dependent? (PARTIALLY SUPPORTED — daytime only)
```

The `depends_on` and `supports` fields in the hypothesis schema make these chains explicit. The Proposer can traverse the relationship graph to identify where the deepest open questions are.

### 5.5 Mechanism 4: Critic Feedback Integration

The Critic's `suggestions` field directly informs the next proposal cycle:

**Critic said (H-NEW01)**: "Drop the >8h band — 10 days is insufficient for circadian coherence. Replace <30min negative control with surrogate-based test."

**Next cycle Proposer sees**: These suggestions in the workspace summary. If proposing a follow-up to H-NEW01, it inherits the Critic's constraints automatically.

### 5.6 Cross-Hypothesis Synthesis

After multiple cycles, the Verifier can identify **cross-cutting patterns**:

- H-NEW01 (fast coupling decreases) + H-NEW03 (excursion HR blunts) + H-NEW17 (effect is daytime only) → **Unified finding**: Diabetes selectively destroys daytime fast autonomic coupling.

This synthesis currently happens in the pipeline's logging and reporting. In future, a dedicated **Synthesizer Agent** would formalize cross-hypothesis integration.

---

## 6. Hypothesis Overview Table

### 6.1 Current Inventory (26 hypotheses, 7 tested)

| ID | Category | Status | d (H vs ID) | FDR | Verdict | Key Finding |
|---|---|---|---:|---|---|---|
| **H-NEW03** | event_dynamics | supported | **-0.80** | <0.001 | 9/9 pass | Post-excursion HR blunting — flagship |
| **H-MIG01** | temporal_coupling | supported | +0.59 | 1e-19 | — | Broadband coupling increase |
| **H-NEW17** | circadian_org | completed | +0.47 | <0.001 | — | Elevation, not flattening; daytime only |
| **H-NEW01** | frequency_coupling | completed | +0.38 / -0.22 | <0.001 | 5/9 | Direction flips at 2h timescale |
| **H-MIG03** | temporal_coupling | supported | — | — | — | Coupling AUROC = 0.805 |
| **H-MIG04** | temporal_coupling | supported | — | — | — | Links to frailty (r=0.15) |
| **H-NEW05** | complexity_loss | completed | +0.18 | <0.001 | — | Entropy adds <1% R² beyond HbA1c |
| **H-NEW06** | temporal_coupling | completed | -0.02 | n.s. | — | **Clean null** — nocturnal prediction fails |
| **H-NEW13** | resilience | completed | -0.06 | n.s. | — | **Null** — 5-min resolution too coarse |
| **H-MIG05** | structural_dynamic | refuted | — | n.s. | — | No retinal/cardiac structural link |
| H-NEW02 | causal_architecture | critiqued | — | — | — | TE/CCM at 5-min: feasibility concern |
| H-NEW08 | physiotype_discovery | critiqued | — | — | — | Clustering needs strong validation |
| H-NEW10 | event_dynamics | validated | — | — | — | Next in queue |
| *12 more* | *various* | *critiqued* | — | — | — | *Awaiting modification or execution* |

### 6.2 Reading the Table

- **d (H vs ID)**: Cohen's d comparing healthy to insulin-dependent. Negative = lower in diabetes.
- **FDR**: Benjamini-Hochberg corrected p-value across all features tested.
- **Verdict**: Number of robustness checks passed (X/9) for fully verified hypotheses.
- **Status progression**: Each hypothesis moves strictly through the lifecycle. No skipping.

---

## 7. Design Principles

### 7.1 Mechanism Before Measurement

Every hypothesis specifies the biological mechanism (WHY) before the statistical test (WHAT). This prevents the "significant but meaningless" problem where p < 0.05 results lack interpretation.

### 7.2 Falsification Over Confirmation

Every hypothesis includes a **refutation criterion** and a **negative control**. The system is designed to find nulls as readily as positives. Null results are informative and preserved (H-NEW06, H-NEW13).

### 7.3 Mechanical Verification Over LLM Judgment

The Verifier's 9 rule-based checks take precedence over LLM interpretation. If 8/9 checks pass but the LLM says "refuted," the rule checks win. This prevents LLM hallucination from overriding empirical evidence.

### 7.4 Structured Provenance

Every result links back to: the hypothesis that motivated it, the test plan that specified the analysis, the confounders that were adjusted for, the sensitivity checks that were run, and the verdict that was reached. No orphaned findings.

### 7.5 Atomic State Transitions

Each pipeline cycle performs exactly one action (verify OR execute OR propose). The workspace state is always consistent — no half-executed hypotheses, no unreviewed proposals in the queue.

### 7.6 Dataset Constraints as First-Class Citizens

The Critic's 10 constraint checks are not afterthoughts — they are hard-coded into the review process. A hypothesis requiring beat-to-beat HR is rejected before it wastes cluster time, not discovered to be infeasible after execution.

### 7.7 Dual-Mode Complementarity

Theory-driven and data-driven hypotheses are treated identically in the pipeline. The Critic cannot distinguish their source. This prevents bias toward either mode while allowing both to contribute.

---

## 8. Future Extensions

### 8.1 Synthesizer Agent

A new agent that operates across hypotheses rather than within them:
- Identifies clusters of related findings (fast coupling + excursion response + daytime specificity)
- Proposes unified mechanistic models
- Identifies contradictions that need resolution

### 8.2 JEPA Integration

The foundation model (Layer 1) provides learned features that the agent system (Layer 2) can hypothesize about:
- JEPA cross-modal prediction error as a learned coupling measure
- JEPA latent clusters as learned physiotypes
- Agent validates JEPA-derived features with the same robustness pipeline

### 8.3 Literature RAG Pipeline

Replace the Proposer's prompt-embedded literature with a retrieval-augmented generation pipeline over a curated corpus of network physiology, autonomic neuropathy, and CGM dynamics papers.

### 8.4 Longitudinal Extension

When AI-READI Year 4 follow-up data arrives (~10% of cohort), the system can test prognostic hypotheses: "Does coupling-based phenotype at baseline predict 2-year HbA1c trajectory?"

---

## References

- Bashan et al. (2012). Network physiology reveals relations between network topology and physiological function. *Nature Communications*, 3, 702.
- Lipsitz & Goldberger (1992). Loss of 'complexity' and aging. *JAMA*, 267(13), 1806-1809.
- Hackett et al. (2014). Disruption of multisystem responses to stress in type 2 diabetes. *PNAS*, 111(44), 15693-15698.
- Vinik & Ziegler (2007). Diabetic cardiovascular autonomic neuropathy. *Circulation*, 115(3), 387-397.
- Lu et al. (2024). The AI Scientist: Towards fully automated open-ended scientific discovery. arXiv:2408.06292.
- Swanson et al. (2024). Virtual Lab: AI agents design new SARS-CoV-2 nanobodies. arXiv:2407.21783.
- Survey: Agentic AI for Scientific Discovery (ICLR 2025). arXiv:2503.08979.
