# Multi-Agent System for AI-READI: Research Synthesis & Design Brainstorm

> **Date:** 2026-04-24
> **Status:** Historical brainstorm / design seed. For current status, see `docs/CURRENT_STATUS.md`.
> **Scope:** Agent system (Layer 2) design, with forward-looking integration to foundation model layer (Layer 1).
> **Current implementation note:** Agents now operate on loaders, feature matrices, derived metrics, retinal/ECG embeddings when available, coupling tasks, and experimental JEPA scaffolds. Production-quality foundation-model/agent integration remains incomplete.

---

## Table of Contents

1. [Design Constraints](#1-design-constraints)
2. [Landscape: What Exists](#2-landscape-what-exists)
3. [Foundation Model + Agent Integration](#3-foundation-model--agent-integration)
4. [Proposed Architecture](#4-proposed-architecture)
5. [Downstream Tasks](#5-downstream-tasks-what-the-agents-do)
6. [Agent-Data Interaction Design](#6-agent-data-interaction-design)
7. [Concrete Research Questions](#7-concrete-research-questions-the-agents-would-tackle)
8. [Implementation Plan](#8-implementation-plan)
9. [Open Questions](#9-open-questions)

---

## 1. Design Constraints

These are non-negotiable, drawn from the literature and our dataset properties:

| Constraint | Source |
|---|---|
| **Agents must compute, never hallucinate statistics.** LLMs score 0.48-0.54 (chance) on aging biology tasks. | LongevityBench (Insilico 2026) |
| **Code generation is the primary action mode.** Agents write Python against our `scripts/` API, execute in sandbox, observe results. | PHIA (Google 2025), CodeAct (ICML 2024) |
| **Every finding must survive critique.** Confounders (age, site), FDR correction, effect sizes, not just p-values. | Virtual Lab, CellAgent |
| **Missing modalities are normal.** FLIO coverage is 81%, ECG 98.7%. The system must degrade gracefully. | CEREBRA |
| **Cross-sectional data, not longitudinal.** One visit per person. No trajectory prediction. But the ~10-day continuous window enables within-person causal analysis. | AI-READI v3.0.0 |
| **Sex is redacted in the public release.** Blocks eGFR, MetS, ASCVD scores. Agents must know this. | AI-READI data use agreement |

---

## 2. Landscape: What Exists

### 2.1 Multi-Agent Health AI Systems (2024-2026)

| System | Venue | Architecture | Task | Key Innovation | Limitation |
|---|---|---|---|---|---|
| **CEREBRA** | arXiv 2603 (Stanford/NYU) | Data Agent -> Super Agent -> Modality Agents (EHR, Notes, Imaging) | Dementia diagnosis/risk | Missing-modality robustness; evidence chains; clinician dashboard | No trained alignment model; no continuous time series |
| **PHIA** | Nature Comms 2025 (Google) | Single ReAct agent + code gen + web search | Wearable QA | 84% numerical accuracy via code execution, not parametric reasoning | Single agent; wearable only; no clinical integration |
| **Virtual Lab** | Nature 2025 (Stanford/Zou) | PI Agent + Expert Agents + Scientific Critic | Nanobody design | Structured deliberation protocol (team meetings + individual meetings) | Domain-specific; no health data |
| **BioMedAgent** | Nature BME 2026 | Planning Agent + Coding Agent + Execution Agent | Biomedical data analysis | Self-evolving memory: caches successful tool chains, improves 52% -> 77% | 23% failure rate |
| **CellAgent** | bioRxiv 2024 | Planner -> Executor -> Evaluator | scRNA-seq analysis | Hierarchical with quality-gated iteration | Narrow to single-cell |
| **ClockBase Agent** | bioRxiv 2025 (Harvard/Gladyshev) | Metadata Parser -> Hypothesis Generator -> Statistical Executor -> Literature Reviewer -> Scorer | Aging intervention mining | 43K comparisons, 500+ interventions, ouabain validated in vivo | Public data quality varies; one candidate validated |
| **K-Dense** | bioRxiv 2025 (Gladyshev) | Guided multi-agent system | Transcriptomic aging clock design | First clock with calibrated uncertainty (R^2=0.854, MAE=4.26y) | RNA-seq only |
| **Vivaldi** | arXiv 2603 | Orchestrator + DoctorAgent + CoderAgent + ConsultantAgent | ED vital signs interpretation | Role-structured team for continuous physiological time series | Agentic orchestration sometimes *hurt* thinking models |
| **MATMCD** | ACL 2025 (NEC Labs) | Data Augmentation Agent + Causal Constraint Agent + Graph Refiner | Causal discovery | 66.7% reduction in causal inference errors via multi-modal augmentation | General-purpose, not health-specific |
| **MRAgent** | Brief Bioinform 2025 | Single LLM agent + PubMed + GWAS databases | Mendelian randomization | Automated bidirectional MR analysis at scale | Genomic data only |
| **CARE-AD** | npj Dig Med 2025 | Multi-agent virtual consultation (domain specialists) | Alzheimer's 10-year prediction | Simulates multidisciplinary team from EHR notes | Notes only; no imaging/wearable |
| **Microsoft Healthcare Orchestrator** | 2025 | Azure orchestrator + Radiology/Pathology/Staging/Guidelines/Trials agents | Cancer care | Production deployment at Stanford, JHU, Mass General | Proprietary; oncology-focused |
| **Mount Sinai Multi-Agent** | npj Health Systems 2026 | Multi-agent orchestration | Clinical AI at scale | 65x compute reduction vs single-agent at clinical volume | Not open source |
| **SleepFM** | Nature Medicine 2026 (Zou/Mignot) | LOO contrastive learning across 4 PSG modalities (EEG/EOG, ECG, EMG, respiratory) | Disease prediction from sleep | 585K hours, 65K participants; predicts 130 diseases (Alzheimer's C=0.91, mortality C=0.84) | Sleep-only; no wearable/CGM/retinal |
| **Delphi-2M** | Nature 2025 (Gerstung) | GPT-2 with continuous age encoding + time-to-event head | Disease trajectory generation | 2.2M params, 403K UK Biobank individuals; 1000+ diseases; AUC 0.97 death; zero-shot transfer UK->Denmark | EHR codes only; no continuous signals |

### 2.2 Key Architectural Patterns Emerging

1. **Hierarchical orchestration** is dominant (CEREBRA, Microsoft, Mount Sinai, Vivaldi). Orchestrator decomposes; specialists execute.
2. **Code-as-action** outperforms JSON tool calls by ~20% (CodeAct, ICML 2024). Agents write executable Python, not structured API calls.
3. **Scientific Critic is non-negotiable** for research systems (Virtual Lab, CellAgent). Every finding gets stress-tested.
4. **Self-evolving memory** (BioMedAgent) improves from 52% to 77% by caching successful workflows. Our agents should learn which analysis patterns work.
5. **65x compute savings** from multi-agent vs monolithic (Mount Sinai). Specialization isn't just elegant -- it's necessary at scale.

### 2.3 Aging Clocks & Downstream Task Landscape

| Clock Type | State of the Art | MAE | Mortality Signal | Available for AI-READI? |
|---|---|---|---|---|
| **Retinal age** (fundus) | RETFound probes, Zhu 2023, RAG models | 2.78-3.39 y | +1y RAG -> higher mortality, CVD, dementia | Yes (CFP) |
| **Retinal age** (OCT+fundus multimodal) | 2026 multimodal retinal clock | improved over fundus-only | Charlson Comorbidity Index | Yes (OCT + CFP) |
| **ECG age** (heart age) | ECGFounder probes, 2024 npj Dig Med | 6.9-8.4 y | +7y -> 62% higher mortality, 2x MACE | Yes (12-lead ECG) |
| **Wearable age** (PPG/activity) | PpgAge (Apple Watch), AI-PPG | ~2.4 y | +9y gap -> 2.37x MACE | Yes (Garmin HR/activity) |
| **Circadian age** (CosinorAge) | npj Dig Med 2024 | N/A (risk metric) | +1y -> 8-12% higher mortality; 2.86x dementia | Yes (Garmin activity rhythms) |
| **CGM metabolic age** | **Does not exist yet** | -- | GV correlates with CVD, sarcopenia | Yes (Dexcom G6 CGM) |
| **FLIO metabolic age** | **Does not exist yet** | -- | AGE/lipofuscin accumulation precedes structural damage | Yes (Heidelberg FLIO) |
| **Clinical lab age** | LifeClock (Nature Med 2025), proteomic clocks | varies | Predicts disease years before symptoms | Yes (125-feature matrix) |
| **Environmental exposure age** | **Does not exist yet** | -- | PM2.5/light spectrum as aging modifiers | Yes (Anura sensor) |
| **Multimodal unified age** | **Does not exist yet** | -- | -- | **AI-READI is the first dataset that could build this** |

### 2.4 Multi-Organ Aging

Foundational work: Oh et al. (Nature 2023) built plasma proteomic organ clocks and showed ~20% of people have accelerated aging in one organ, with 20-50% higher mortality. Tian et al. (Nature Medicine 2023) demonstrated heterogeneous multi-organ aging profiles and disease prediction. Wen, Tian et al. (Nature Aging 2024) characterized the genetic architecture of biological age across 9 organ systems. MRI-based multi-organ clocks (Nature Medicine 2025) developed 7 organ-specific clocks from UK Biobank imaging.

**The gap:** All existing multi-organ clocks use MRI or proteomics. No one has built organ-specific aging clocks from *functional signals* (ECG, CGM, wearable activity, retinal imaging). AI-READI has these signals.

---

## 3. Foundation Model + Agent Integration

This is the core design question: **how does the agent layer (LLM reasoning) interact with the foundation model layer (learned representations)?** The 7 reference papers collectively define the design space.

### 3.1 The Fundamental Lesson: LLMs Cannot Do Biology Alone

**LongevityBench** (Insilico Medicine, bioRxiv 2026) tested 15 frontier LLMs across 17 aging biology tasks spanning 7 data modalities:

| Task Domain | Best LLM | Accuracy | vs Random (0.50) |
|---|---|---|---|
| Clinical biomarker survival | Gemini 3 Pro | **0.882** | Strong |
| Multi-mutant lifespan | Gemini 3 Pro | 0.781 | Moderate |
| Gene expression trajectory | Gemini 3 Pro | 0.742 | Moderate |
| DNA methylation age | Gemini 3 Pro | 0.724 | Moderate |
| Cancer survival (RNAseq) | Claude Sonnet 4.5 | 0.697 | Weak |
| Proteomics age | GPT 5.2 | 0.676 | Weak |
| **Transcriptomics age** | **All models** | **0.48-0.52** | **Random chance** |

**Key findings:**
- LLMs are strongest on clinical biomarkers (well-represented in training data) and weakest on raw omics (never seen in pretraining)
- No single model excels across all modalities -- different architectures have different "biological senses"
- **Transcriptomics is a total failure** -- all 15 LLMs at chance level
- This proves agents MUST be grounded in specialized encoders, not parametric LLM knowledge

**Design implication:** The agent layer provides *reasoning, planning, and synthesis*. The FM layer provides *perception and representation*. Neither works alone.

### 3.2 What Each Foundation Model Teaches Us

#### I-JEPA (Assran/LeCun, CVPR 2023) -- The Architectural Template

Core design choices that transfer to health data:
- **Narrow bottleneck predictor** (384-d, 2 layers) forces semantic abstraction. Wider predictors learn shortcuts.
- **Multi-block masking** (predict 4 target blocks from context) learns spatial/temporal dependencies
- **Predict in representation space, not pixel/signal space:** +26.2 points on 1% ImageNet (66.9% vs 40.7%)
- **Linear probes on frozen representations** -- downstream tasks require minimal adaptation

**For our system:** The cross-modal JEPA predictor should use a narrow bottleneck. When masking one modality (e.g., CGM), predict its latent representation from the other 5 modalities. The bottleneck forces the predictor to learn *what information transfers across modalities* -- the cross-modal coupling the agents need to reason about.

#### JETS (Empirical Health) -- The Wearable Encoder

- **Tokenization:** Irregularly-sampled wearable data as (timestamp, value, metric_type) triplets -> tokens with d=64
- **JEPA objective** with 30% random masking on 63-channel wearable streams
- **Biomarker prediction from wearables alone:** HbA1c, glucose, HDL, hs-CRP (high absolute error but meaningful signal)
- Authors note predicting *changes* in biomarkers (given baseline + wearable) is more promising than absolute prediction

**For our system:** AI-READI's Garmin data has the same channels as JETS training data. Either use JETS weights (if released) as a frozen wearable encoder, or train a small JEPA on AI-READI's ~23K person-days. The wearable embeddings become inputs to the cross-modal predictor AND tools the WearableAgent can query.

#### SMB-Structure (Standard Model Bio, 2025) -- The Training Recipe

Critical insight: **Curriculum beats simultaneous training.**
- SFT-only: 0.727 AUC (disease progression)
- Simultaneous SFT+JEPA: 0.719 (**worse** than SFT alone!)
- **Curriculum (SFT then JEPA): 0.731** (best)

Why: SFT grounds clinical semantics first (what do these tokens mean?). JEPA then refines representations toward dynamic prediction (where is the state going?). Doing both simultaneously creates optimization conflict.

Additional insights:
- 365-day mortality: 0.810 (curriculum) vs 0.802 (SFT) -- JEPA helps most on *long-horizon* prediction
- Cross-disease transfer: training on pulmonary embolism patients *improves* oncology prediction -- JEPA learns universal dynamics
- Counterfactual planning acknowledged as future direction: "extend this framework to intervention-conditioned world models"

**For our system:** When we build the cross-modal JEPA (Layer 1), use curriculum training:
- Phase A: Supervised grounding (joint embedding -> study_group classifier)
- Phase B: Add JEPA objective (mask each modality, predict from others)

#### SleepFM (Zou/Mignot, Nature Medicine 2026) -- Multimodal Biosignal FM

**Architecture:** Leave-One-Out Contrastive Learning (LOO-CL) on 4 PSG modalities:
1. 1D CNN encoder (6 layers, 1->128 channels) per modality for 5-second segments
2. Attention-based channel pooling (handles variable channel configurations)
3. Temporal transformer (3 layers, 8 heads) over 5-minute windows
4. 128-dim embedding per modality

**From a single overnight sleep recording:**
- All-cause mortality: C-Index 0.84; Alzheimer's: C-Index 0.91; Parkinson's: 0.89; Heart failure: 0.80
- 130 diseases with C-Index >= 0.75

**Why this matters for our design:**
- LOO contrastive learning is an *alternative* to JEPA masking for cross-modal alignment -- closely resembles our cross-modal JEPA design
- **Channel-agnostic design** handles missing channels gracefully -- directly relevant to AI-READI's variable coverage (FLIO 81%, ECG 98.7%)
- **Different modalities matter for different diseases:** brain signals best for neuro/mental, ECG for cardiovascular, respiratory for metabolic -- supports modality-specific agents
- SleepFM uses clinical PSG; we have consumer Garmin. Complementary, not competing.

#### Delphi-2M (Gerstung et al., Nature 2025) -- Disease Trajectory Simulator

**Architecture:** Modified GPT-2 (only 2.2M params) with:
- 1,270-token vocabulary: 1,257 ICD-10 codes + 9 lifestyle + 2 sex tokens
- Continuous age encoding via sine/cosine basis (1/365 days)
- Time-to-event prediction head (exponential waiting time)

**Key results:**
- AUC 0.97 for death prediction; ~0.76 average across all diagnoses
- **Zero-shot UK -> Denmark transfer** (1.93M people) with no parameter changes
- Generates realistic synthetic 20-year health trajectories
- Synthetic-data-only models achieve AUC 0.74

**Why this matters for our design:**
- Delphi provides **trajectory simulation** for the agent system. Our data is cross-sectional, but Delphi can project forward: "Given this participant's current disease codes, what is their 10-year trajectory?"
- Agents could use trajectory generation for **counterfactual reasoning**: "If we modify this person's metabolic profile, how does their trajectory change?"
- Continuous age encoding could be adopted for our temporal alignment

#### CEREBRA (Liu/Zou, 2026) -- The Agent Template

- Modality agents use **pre-existing specialized models** (not a unified FM)
- Super Agent coordinates but does not access learned representations -- operates on agent *outputs*
- **Gap CEREBRA leaves open:** No cross-modal alignment model. Agents reason about modalities independently. Our cross-modal JEPA fills this gap.

### 3.3 The Integration: How Agents Use the Foundation Model

The FM provides three capabilities the agent layer cannot:

```
WHAT THE FM PROVIDES (that agents cannot compute from raw data)
───────────────────────────────────────────────────────────────
1. DENSE EMBEDDINGS per modality per person
   z_retinal, z_ecg, z_cgm, z_wearable, z_clinical, z_env
   → Agents query like a database: "How similar is participant
     1046's cardiac embedding to the healthy control centroid?"

2. CROSS-MODAL RECONSTRUCTION LOSS
   JEPA(mask=cgm, predict_from=others) → loss per person
   → High loss = glucose poorly predicted by other modalities
     = DECOUPLED systems = possible insulin resistance signature

3. PER-ORGAN AGING CLOCK HEADS (linear probes on embeddings)
   z_retinal → retinal AgeAccel
   z_ecg → cardiac AgeAccel
   z_cgm → metabolic AgeAccel
   → Agents reason about multi-organ aging PROFILES
```

What the agent layer provides (that the FM cannot):

```
WHAT AGENTS PROVIDE (that the FM cannot)
───────────────────────────────────────────────────────────────
1. DOMAIN REASONING — "This retinal AgeAccel of +6y is clinically
   significant per Nusinovici 2022. Check age adjustment."

2. HYPOTHESIS GENERATION — "Cross-modal loss for CGM is highest
   in insulin-dependent group. Hypothesis: insulin resistance
   decouples glucose from other physiological systems."

3. CAUSAL ANALYSIS — "Test Granger causality: sleep quality →
   glucose control or glucose instability → poor sleep?"

4. CRITIQUE — "Cohen's d=0.15. Statistically significant but
   clinically negligible. Also: check site bias within UAB."

5. TRAJECTORY PROJECTION (via Delphi-2M) — "Project participant
   1046's 10-year trajectory. How does it change if metabolic
   AgeAccel is reduced by 3y?"

6. SYNTHESIS — "Generate multi-organ aging report integrating
   retinal, cardiac, metabolic, and autonomic age estimates."
```

### 3.4 Phased Integration: Agent-First, FM-Later

The agent system is useful BEFORE the FM exists:

| Phase | Agent Layer | FM Layer | Capabilities Unlocked |
|---|---|---|---|
| **0 (now)** | Single PHIA-style agent | None (raw features only) | Query feature matrix, statistics, group comparisons |
| **1** | Modality agents + Critic | Pretrained encoders (RETFound, ECGFounder) | Per-organ age estimation, cross-modal correlation |
| **2** | + Reasoning agents | + Cross-modal JEPA | Reconstruction loss as coupling score, multi-organ AgeAccel clustering |
| **3** | + Trajectory agent | + Delphi-2M integration | Disease trajectory projection, counterfactual reasoning |
| **4** | Full system | + Fine-tuned JEPA + aging heads | Complete agentic scientific reasoning grounded in learned representations |

### 3.5 Benchmark Alignment (from LongevityBench)

LongevityBench is omics-heavy; AI-READI is signal-heavy. But the underlying capability -- "translate low-level biodata into phenotype-level conclusions" -- is identical.

| LongevityBench Domain | Our System's Approach | Phase |
|---|---|---|
| Clinical biomarker survival | ClinicalAgent + Cox regression | 0 |
| DNA methylation / proteomics / transcriptomics age | Not in AI-READI | N/A |
| **Disease prediction from biosignals** | SleepFM-style from ECG+wearable; JEPA embeddings | 1-2 |
| **Multimodal biological age** | Per-organ aging clocks from retinal+ECG+CGM+wearable+clinical | 1-2 |

**Contribution opportunity:** A *signal-level* LongevityBench for wearable + imaging + clinical data, complementing the omics-focused original.

---

## 4. Proposed Architecture

### 4.1 Overview

```
                         ┌─────────────────────────────┐
                         │        USER / PI AGENT       │
                         │  Research question in natural │
                         │  language or structured query │
                         └──────────────┬──────────────┘
                                        │
                         ┌──────────────▼──────────────┐
                         │      ORCHESTRATOR AGENT      │
                         │  Decomposes question         │
                         │  Routes to specialist agents │
                         │  Maintains shared workspace  │
                         │  Synthesizes final answer    │
                         └──────────────┬──────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
    ┌─────────▼─────────┐   ┌──────────▼──────────┐   ┌─────────▼─────────┐
    │  MODALITY AGENTS   │   │  REASONING AGENTS    │   │  VALIDATION AGENT │
    │  (Tier 1)          │   │  (Tier 2)            │   │  (Critic)         │
    │                    │   │                      │   │                   │
    │  ClinicalAgent     │   │  HypothesisAgent     │   │  Checks:          │
    │  GlucoseAgent      │   │  CausalAgent         │   │  - Confounders    │
    │  CardiacAgent      │   │  PhenotypeAgent       │   │  - Site bias      │
    │  WearableAgent     │   │  AgingClockAgent      │   │  - FDR            │
    │  RetinalAgent      │   │  LiteratureAgent      │   │  - Effect sizes   │
    │  EnvironmentAgent  │   │                      │   │  - Reproducibility │
    └─────────┬─────────┘   └──────────┬──────────┘   └─────────┬─────────┘
              │                         │                         │
              └─────────────────────────┼─────────────────────────┘
                                        │
                         ┌──────────────▼──────────────┐
                         │     SHARED WORKSPACE         │
                         │  StatisticalFinding(...)     │
                         │  ModalityObservation(...)    │
                         │  Hypothesis(...)             │
                         │  CausalGraph(...)            │
                         │  WorkflowMemory(...)         │
                         └──────────────┬──────────────┘
                                        │
                         ┌──────────────▼──────────────┐
                         │  LAYER 0: DATA INFRASTRUCTURE│
                         │  scripts/ API                │
                         │  load_feature_matrix()       │
                         │  get_participant()           │
                         │  compare_groups()            │
                         │  aligned_timeseries()        │
                         └─────────────────────────────┘
```

### 3.2 Agent Roles

#### Tier 1: Modality Agents (data-facing, code-generating)

Each modality agent is an expert on one data type. It generates Python code against `scripts/`, executes in a sandbox, and returns structured findings.

| Agent | Data Access | Core Capabilities |
|---|---|---|
| **ClinicalAgent** | `load_feature_matrix()`, `loaders/clinical.py` | Query 125 clinical features, compute HOMA-IR/QUICKI/TyG, compare across groups, flag missing/redacted fields |
| **GlucoseAgent** | `loaders/cgm.py`, `features.py` | CGM metrics (TIR, GRI, MAGE, AGP, dawn phenomenon), temporal patterns, glycemic variability profiles |
| **CardiacAgent** | `loaders/ecg.py` | ECG intervals (QTc, PR, QRS), HRV (RMSSD, HF power via neurokit2), signal quality, embeddings (ECGFounder when available) |
| **WearableAgent** | `loaders/wearable.py`, `features_wearable.py` | Sleep architecture, circadian metrics (IS/IV/M10/L5/RA/cosinor), HR patterns, SpO2, activity/sedentary |
| **RetinalAgent** | `loaders/retinal.py` | Manifest queries, image metadata, OCTA vessel density, retinal age (when RETFound probes available), FLIO metadata |
| **EnvironmentAgent** | `loaders/environment.py` | PM2.5/AQI, light spectrum analysis, temperature comfort, screen time, circadian light dose |

#### Tier 2: Reasoning Agents (insight-generating)

These agents don't directly touch raw data. They consume Tier 1 outputs from the shared workspace and generate higher-order insights.

| Agent | Role | Example Query |
|---|---|---|
| **HypothesisAgent** | Proposes testable hypotheses from observed patterns | "GlucoseAgent found TIR differs by group. HypothesisAgent proposes: insulin resistance mediates this via HOMA-IR. Test: compare TIR after adjusting for HOMA-IR." |
| **CausalAgent** | Designs and interprets causal analyses (Granger, transfer entropy, mediation) | "Does sleep quality Granger-cause next-day glucose control? Design: use WearableAgent's per-night SE and GlucoseAgent's per-day TIR, test with statsmodels." |
| **PhenotypeAgent** | Clusters participants into data-driven subtypes beyond the 4 study groups | "Using aging clock profiles from all modalities, identify concordant vs discordant agers." |
| **AgingClockAgent** | Coordinates per-organ aging estimation and cross-organ analysis | "Compute retinal age, cardiac age, metabolic age proxies. Analyze concordance. Do some organs age faster in T2DM?" |
| **LiteratureAgent** | Provides domain context, known thresholds, and citation support | "What is the clinical significance of MAGE > 60 mg/dL? What do Battelino 2023 consensus guidelines say?" |

#### Validation: Critic Agent

Inspired by Virtual Lab's Scientific Critic. **Every finding passes through the Critic before being reported.**

Checks performed:
1. **Confounder adjustment**: Was age adjusted for? (Age correlates with almost everything.)
2. **Site bias**: Does the finding hold within each of the 3 sites (UW, UCSD, UAB)?
3. **Multiple comparisons**: FDR correction applied?
4. **Effect size**: Is Cohen's d or eta-squared meaningful, not just p < 0.05?
5. **Missing data**: What fraction of participants had complete data for this analysis?
6. **Sensitivity analysis**: Does the result change if outliers are removed or thresholds shift?
7. **Known confound flag**: Sex is redacted -- does this analysis implicitly require sex?

### 3.3 Orchestration Pattern

**Hierarchical with deliberation for validation** (synthesized from CEREBRA + Virtual Lab + ClinicalAgents):

1. User/PI asks a research question in natural language.
2. **Orchestrator** decomposes into sub-questions, identifies which modality agents are needed.
3. **Modality agents** execute in parallel (CodeAct -- generate Python, run in sandbox, return structured results).
4. Results written to **shared workspace** as typed entries.
5. **Reasoning agents** consume workspace entries, propose interpretations/hypotheses.
6. **Critic agent** stress-tests every finding.
7. **Orchestrator** synthesizes validated findings into a coherent answer.

For exploratory sessions (brainstorming, not answering a specific question):
- Use **Virtual Lab-style team meetings**: Orchestrator sets agenda, each agent contributes, Critic challenges, iterate N rounds.

### 3.4 Memory System

Inspired by BioMedAgent's self-evolving memory:

| Memory Type | Contents | Example |
|---|---|---|
| **Workflow Memory** | Successful analysis patterns (tool chains that worked) | "To compare CGM metrics across groups: load_feature_matrix() -> filter -> compare_groups(adjust_for=['age', 'clinical_site']) -> site_bias_check()" |
| **Finding Memory** | Validated statistical findings from prior sessions | "HbA1c differs significantly across all 4 groups (Kruskal-Wallis p < 1e-100, eta^2 = 0.52). Survived site-bias check." |
| **Domain Memory** | Clinical thresholds, consensus guidelines, known relationships | "TIR target is >70% per Battelino 2023. CV >= 36% = unstable per consensus." |
| **Constraint Memory** | Dataset-specific limitations agents must respect | "Sex is redacted. eGFR requires sex. Do not attempt eGFR computation." |

---

## 5. Downstream Tasks: What the Agents Do

### 4.1 Tier A: Multimodal Aging Clock Construction (highest novelty + impact)

**Goal:** Build the first unified multimodal aging clock from functional signals.

**Per-organ clocks the agents would construct or coordinate:**

| Organ System | Data Source | Clock Approach | Agent Responsible |
|---|---|---|---|
| **Retinal/neurovascular** | CFP, OCT, OCTA | RETFound embedding -> age regression head; OCTA vessel density age model | RetinalAgent + AgingClockAgent |
| **Cardiac electrical** | 12-lead ECG | ECGFounder embedding -> age regression; or HRV + interval features -> regression | CardiacAgent + AgingClockAgent |
| **Metabolic** | CGM + clinical labs | **Novel:** glucose dynamics features (TIR, CV, MAGE, dawn phenomenon, AGP shape) + HOMA-IR/TyG -> age regression | GlucoseAgent + ClinicalAgent + AgingClockAgent |
| **Autonomic/fitness** | Wearable HR, activity, sleep | CosinorAge-style circadian metrics + resting HR + sleep architecture -> age regression | WearableAgent + AgingClockAgent |
| **Vascular** | OCTA flow maps | Vessel density, FAZ area, fractal dimension -> age regression | RetinalAgent + AgingClockAgent |
| **Environmental exposure** | Anura sensor | **Novel:** cumulative PM2.5 dose, circadian light disruption score, temperature exposure -> age modifier | EnvironmentAgent + AgingClockAgent |

**Cross-organ analysis (the unique contribution):**
- Compute AgeAccel (predicted age - chronological age) per organ per person
- Cluster participants by AgeAccel profile -> **data-driven aging subtypes**
- Test whether aging subtypes align with or cut across the 4 diabetes severity groups
- Test concordance: do all organs age together, or do some organs age independently?
- Identify "discordant agers" (e.g., young retina + old heart) and characterize them

**Key references to build on:**
- Tian et al. Nature Medicine 2023 (multi-organ aging concept)
- Oh et al. Nature 2023 (proteomic organ clocks)
- CosinorAge, npj Digital Medicine 2024 (circadian aging)
- PpgAge, Nature Communications 2025 (wearable aging)

### 4.2 Tier B: Cross-Modal Causal Discovery (highest scientific novelty)

**Goal:** Use the ~10-day continuous multimodal overlap to discover causal relationships between physiological systems.

AI-READI's unique property: CGM + Garmin + environmental sensor are simultaneously measured for ~10 days in the same person. This enables within-person causal analysis that cross-sectional snapshots cannot.

**Causal questions the agents would test:**

| Question | Method | Agents Involved |
|---|---|---|
| Does poor sleep *cause* next-day glucose dysregulation, or vice versa? | Bidirectional Granger causality + transfer entropy on per-night SE vs per-day TIR | WearableAgent + GlucoseAgent + CausalAgent |
| Does physical activity improve same-day glycemic control? At what lag? | Time-lagged cross-correlation of hourly steps vs glucose | WearableAgent + GlucoseAgent + CausalAgent |
| Does PM2.5 exposure cause acute HR/HRV changes? | Lagged regression of 5-min PM2.5 on HR (aligned_timeseries) | EnvironmentAgent + WearableAgent + CausalAgent |
| Does evening light exposure delay sleep onset and worsen glucose control? | Mediation: evening melanopic EDI -> sleep onset -> next-day TIR | EnvironmentAgent + WearableAgent + GlucoseAgent + CausalAgent |
| Does circadian misalignment mediate environment -> metabolic health? | Structural equation modeling | All Tier 1 + CausalAgent |
| Is glucose-HR coupling weaker in more severe diabetes? | Per-person cross-correlation at aligned 5-min grid, compare across groups | GlucoseAgent + WearableAgent + CausalAgent + ClinicalAgent |
| Does autonomic dysfunction (HRV) mediate glycemic variability -> retinal damage? | Causal mediation: GV -> HRV -> OCTA vessel density | GlucoseAgent + CardiacAgent + RetinalAgent + CausalAgent |

**Methods the CausalAgent would deploy:**
- Granger causality (`statsmodels.tsa.stattools.grangercausalitytests`)
- Transfer entropy (`pyinform`, `Tigramite`)
- PCMCI (Runge et al., Sci Adv 2019) for time-lagged causal discovery
- Causal mediation analysis (`semopy`, `pingouin`)
- DYNOTEARS for dynamic Bayesian network learning

### 4.3 Tier C: N-of-1 Multimodal Phenotyping

**Goal:** Generate per-person multimodal health profiles from the ~10-day window.

For each of the 2,280 participants, extract:

| Dimension | Features | Agent |
|---|---|---|
| **Circadian fingerprint** | IS, IV, M10, L5, RA, cosinor amplitude/acrophase/mesor | WearableAgent |
| **Glucose response pattern** | Dawn phenomenon magnitude, postprandial kinetics, nocturnal stability, AGP shape | GlucoseAgent |
| **Cardiac profile** | Resting HR, RMSSD, nocturnal HR dip, QTc | CardiacAgent + WearableAgent |
| **Sleep architecture** | TST, SE, WASO, REM%, Deep%, sleep midpoint, night-to-night variability | WearableAgent |
| **Environmental exposure** | Daily PM2.5 dose, bright light hours, evening light, indoor temperature | EnvironmentAgent |
| **Cross-modal coupling** | Glucose-HR correlation, sleep-glucose reactivity, activity-glucose response | CausalAgent |

**What the PhenotypeAgent does with this:**
- Cluster the 2,280 multimodal profiles (UMAP + HDBSCAN or similar)
- Identify subtypes that cut across the 4 diabetes severity groups
- Find "metabolically healthy but physiologically old" vs "metabolically unhealthy but physiologically young" phenotypes
- Generate per-person deviation reports: "Participant 1046 is +2 SD on circadian disruption and -1.5 SD on sleep efficiency relative to age-matched controls, but glucose control is average"

### 4.4 Tier D: Digital Biomarker Discovery

**Goal:** Find novel non-invasive biomarkers that predict clinical outcomes.

| Discovery Target | Approach | Novelty |
|---|---|---|
| **Wearable features that predict HbA1c** | JETS showed this is possible (87% AUROC for hypertension). Train on AI-READI's wearable -> HbA1c/HOMA-IR | Validates JETS finding in T2DM-enriched cohort |
| **CGM metrics that predict retinal damage** | Correlate glycemic variability metrics with OCTA vessel density | **Novel cross-modal biomarker** |
| **Circadian disruption -> insulin resistance** | CosinorAge-style metrics vs HOMA-IR/TyG | Extends CosinorAge to metabolic endpoints |
| **Environmental exposure -> glycemic variability** | PM2.5/light spectrum vs CGM metrics | **Novel environmental biomarker** |
| **Composite digital health index** | Combine circadian regularity + HRV + TIR + sleep efficiency + activity into single score | **No existing composite** |
| **FLIO-derived metabolic biomarkers** | Deep learning on FLIO decay curves for diabetes staging | **FLIO + diabetes staging is underexplored** |

### 4.5 Tier E: Cross-Modal Health Insights

**Goal:** Discover relationships invisible in any single modality.

These are the "emergence" findings that justify having all 6 modalities:

- **Retinal-metabolic coupling:** Does greater CGM glycemic variability associate with accelerated retinal vascular aging (OCTA)? Does FLIO metabolic status correlate with CGM-derived metabolic health?
- **Cardiac-metabolic coupling:** Does ECG age correlate with CGM metabolic age? Is the relationship mediated by autonomic function (HRV)?
- **Environment-retinal-metabolic axis:** Does personal PM2.5/VOC exposure associate with retinal changes and glycemic variability?
- **Sleep-glucose-retinal triad:** Poor sleep -> glucose instability -> retinal damage. Can cross-sectional data capture this causal chain?
- **Circadian-metabolic-vascular alignment:** Are individuals whose circadian, glucose, and HR rhythms are well-aligned healthier across all modalities?
- **Diabetes severity through cross-modal discordance:** Some people have well-controlled glucose but already show retinal damage (or vice versa). Identifying these discordant phenotypes is clinically actionable.

---

## 6. Agent-Data Interaction Design

### 5.1 Code-as-Action Pattern

Agents generate executable Python, not JSON tool calls. This is the consensus from PHIA, CodeAct, and Anthropic's PTC.

**Example: Orchestrator receives "Is glycemic variability associated with retinal vascular aging?"**

```
Orchestrator:
  "I need GlucoseAgent to compute per-person GV metrics,
   RetinalAgent to get OCTA vessel density,
   then CausalAgent to test the association."

GlucoseAgent generates:
  from scripts.features import load_feature_matrix
  fm = load_feature_matrix()
  gv_metrics = fm[['cv_glucose', 'mage', 'tir']].dropna()
  # Returns: DataFrame with 2245 rows, 3 columns

RetinalAgent generates:
  from scripts.loaders.retinal import load_octa_manifest
  manifest = load_octa_manifest()
  # Extract vessel density from enface images (if pre-computed)
  # Or: flag that validated OCTA vessel density extraction is still unavailable

CausalAgent generates:
  import pandas as pd
  from scipy.stats import spearmanr
  from scripts.cohort import compare_groups
  merged = gv_metrics.join(vessel_density, how='inner')
  r, p = spearmanr(merged['cv_glucose'], merged['vessel_density'])
  # Also: partial correlation adjusting for age
  # Also: stratify by study_group

Critic:
  "Was age adjusted? Yes (partial correlation). Site bias? Need to check.
   FDR? Single test, no correction needed. Effect size? Report r, not just p.
   Missing data? How many had both CGM and OCTA? Flag if < 1500."
```

### 5.2 What the Agent Sees vs What It Computes

| Data | Agent receives in prompt | Agent computes via code |
|---|---|---|
| Feature matrix schema | Column names, dtypes, shape (2280x125), group counts, basic stats | Actual filtering, joins, statistical tests |
| Participant data | Metadata (which modalities available, date ranges) | Actual signal loading, feature extraction |
| CGM timeseries | Summary (n_readings, duration, mean_glucose) | Full time-series analysis (AGP, MAGE, cross-correlation) |
| ECG waveform | Header metadata (Rate, QTc, position) | Waveform processing (R-peaks, HRV via neurokit2) |
| Retinal image | Manifest metadata (device, laterality, dimensions) | Pixel-level analysis (vessel density, RNFL thickness) |
| Statistical results | Nothing -- must compute | p-values, effect sizes, confidence intervals |

### 5.3 Tool Registry

Each function in `scripts/` becomes a tool. The agent sees the function signature + docstring in its prompt, then calls it via generated code.

```python
# Tool registry (what agents see)
TOOLS = {
    "load_feature_matrix": {
        "module": "scripts.features",
        "signature": "load_feature_matrix() -> pd.DataFrame",
        "description": "2280x125 clinical feature matrix. Index=person_id. Columns include hba1c, glucose, insulin, sbp, dbp, hdl, ldl, triglycerides, waist_cm, bmi, ...",
        "returns": "DataFrame[2280 rows x 125 cols]"
    },
    "get_participant": {
        "module": "scripts.multimodal",
        "signature": "get_participant(person_id: str) -> ParticipantAccessor",
        "description": "Lazy multimodal accessor. Properties: .ecg_signal, .cgm_df, .wearable, .environment, .clinical, .cgm_metrics, .aligned_timeseries()",
    },
    "compare_groups": {
        "module": "scripts.cohort",
        "signature": "compare_groups(fm: DataFrame, feature: str, adjust_for: list[str] = None) -> ComparisonResult",
        "description": "Kruskal-Wallis + pairwise Mann-Whitney across study_group. Returns p-values, effect sizes, group means, CIs.",
    },
    "aligned_timeseries": {
        "module": "scripts.multimodal",
        "signature": "ParticipantAccessor.aligned_timeseries(freq='5min') -> DataFrame",
        "description": "CGM glucose + HR + environment on common time grid. Columns: glucose_mg_dl, heart_rate, pm2_5, temp, ...",
    },
    # ... one entry per public function in scripts/
}
```

### 5.4 Sandbox and Execution

Options (ranked by recommendation for our research lab setting):

| Framework | Sandboxing | Multi-Agent | Effort | Best For |
|---|---|---|---|---|
| **Claude Code + Claude Agent SDK** | Native (PTC sandbox) | Subagent spawning | Low | We're already using Claude Code. Start here. |
| **smolagents** (HuggingFace) | E2B / Docker / Pyodide | Single-agent (build coordination yourself) | Low | Quick prototype of single modality agent |
| **LangGraph + Claude** | E2B / Docker | Full graph-based orchestration, checkpointing, replay | Medium | Production multi-agent with state management |
| **AutoGen** (Microsoft) | Docker | GroupChat-based coordination | Medium | Iterative code gen + review |
| **CrewAI** | Limited | Role-based DSL | Low | Quick prototype, not production |

**Recommended path:**
1. **Start:** Single PHIA-style ReAct agent using Claude Code / Claude Agent SDK. Wrap `scripts/` functions as tools. Validate that the agent can correctly answer data questions.
2. **Grow:** Add modality specialization when context limits are hit (a single agent can't hold all modality documentation).
3. **Scale:** Migrate to LangGraph for orchestration + checkpointing when multi-agent coordination becomes complex.

---

## 7. Concrete Research Questions the Agents Would Tackle

### Round 1: Validate the infrastructure (single agent, simple queries)

1. "What is the mean HbA1c for each study group? Are the differences significant?"
2. "How many participants have complete data across all 6 modalities?"
3. "What is the distribution of CGM wear time? How many have < 70% data capture?"
4. "Plot the AGP (ambulatory glucose profile) for a representative participant from each group."
5. "What is the correlation between HOMA-IR and TIR across the full cohort?"

### Round 2: Cross-modal analysis (multi-agent, combining modalities)

6. "Is glycemic variability (CV) associated with resting heart rate after adjusting for age and diabetes severity?"
7. "Do participants with higher circadian disruption (low IS/RA) have worse glycemic control?"
8. "Is there a relationship between nocturnal HR dip and CGM nocturnal glucose stability?"
9. "Does PM2.5 exposure correlate with same-day heart rate or HRV?"
10. "What is the glucose-HR cross-correlation for each participant? Does coupling strength differ by study group?"

### Round 3: Aging clock construction (specialist agents)

11. "Compute retinal age using RETFound embeddings. What is the retinal AgeAccel distribution?"
12. "Build a cardiac age model from ECG features (HR, QTc, RMSSD). What is cardiac AgeAccel?"
13. "Build a metabolic age proxy from CGM features + clinical labs. What drives metabolic aging?"
14. "Compute CosinorAge from Garmin activity data. How does circadian aging relate to metabolic aging?"
15. "Cluster participants by their multi-organ AgeAccel profile. How many aging subtypes emerge?"

### Round 4: Causal discovery (reasoning agents)

16. "Does last night's sleep quality Granger-cause today's TIR? Test bidirectionally."
17. "Use transfer entropy to test directionality: glucose -> HR or HR -> glucose?"
18. "Does evening light exposure mediate the relationship between screen time and sleep quality?"
19. "Build a causal DAG linking sleep, activity, glucose, HR, and environmental exposure."
20. "Does autonomic dysfunction (RMSSD) mediate the effect of glycemic variability on retinal vessel density?"

### Round 5: Discovery (open-ended, agent-driven)

21. "What is the single best non-invasive predictor of HbA1c from wearable + CGM data?"
22. "Find the most 'discordant' participants -- those whose organ-specific ages disagree the most. What characterizes them?"
23. "Generate a comprehensive multimodal health report for participant 1046."
24. "What novel finding can you discover that requires combining at least 3 modalities?"

---

## 8. Implementation Plan

### Phase 1: Single Agent Prototype (Days)

**Goal:** One PHIA-style ReAct agent that can answer Round 1 questions.

- Wrap `scripts/` functions as a tool registry
- Agent generates Python, executes in sandbox, observes output
- Use Claude (via Claude Code or Agent SDK) as the backbone
- Test on 10-20 structured questions with known answers
- **Deliverable:** Working single agent that correctly computes statistics

### Phase 2: Modality Specialization (1-2 Weeks)

**Goal:** Split into Tier 1 modality agents when context limits force it.

- Each modality agent gets: its loader documentation, relevant derived features catalog section, domain-specific system prompt
- Orchestrator routes questions to the right agent(s)
- Shared workspace for inter-agent communication
- Add Critic agent for validation
- **Deliverable:** Multi-agent system answering Round 2 questions

### Phase 3: Reasoning Agents + Aging Clocks (2-4 Weeks)

**Goal:** Add Tier 2 reasoning agents, build aging clock pipeline.

- AgingClockAgent coordinates per-organ age estimation
- CausalAgent deploys Granger/transfer entropy/PCMCI
- PhenotypeAgent runs clustering on multi-organ AgeAccel profiles
- HypothesisAgent proposes and tests cross-modal hypotheses
- **Deliverable:** Multi-agent system answering Rounds 3-4

### Phase 4: Memory + Self-Evolution (Ongoing)

**Goal:** BioMedAgent-style workflow caching.

- Successful analysis workflows stored in WorkflowMemory
- Validated findings stored in FindingMemory
- Agents can recall and adapt prior workflows to new questions
- **Deliverable:** System that improves with use

### Phase 5: Evaluation Benchmark (Parallel with Phases 1-3)

**Goal:** 100-200 auto-scored questions across all rounds.

- Mix of factual (verifiable answer), statistical (correct computation), and open-ended (expert-rated)
- Track accuracy, hallucination rate, and Critic catch rate
- Compare: single agent vs multi-agent, with/without Critic, with/without memory

---

## 9. Open Questions

1. **Which LLM backbone?** Claude Opus for reasoning quality vs Sonnet for speed on routine queries? Can we mix (Opus for orchestrator/reasoning, Sonnet for modality agents)?

2. **How to handle the 2,280-person scale?** Some analyses need per-person computation (e.g., per-person glucose-HR correlation). That's 2,280 code executions. Batch processing vs agent-driven loop?

3. **When do we need the foundation model (Layer 1)?** The agent system can operate on hand-crafted features (Layer 0) today. The cross-modal JEPA adds learned embeddings. At what point does the FM become necessary vs nice-to-have?

4. **Evaluation methodology:** How do we measure whether the agent system produces *scientifically valid* findings, not just *technically correct* computations? Peer review simulation? Comparison to published AI-READI analyses?

5. **Vivaldi's warning:** For "thinking" models, agentic orchestration sometimes *degraded* explanation quality. Does our multi-agent system add genuine value over a single powerful agent with all tools?

6. **Privacy and safety:** If we generate per-person health reports, how do we handle the ethics of AI-generated health interpretations, even in a research context?

7. **Novelty framing for publication:** Is the contribution (a) the multi-agent architecture itself, (b) the multimodal aging clock findings, (c) the causal discovery results, or (d) the unified system? Likely need to focus.

---

## References

### Multi-Agent Systems
- CEREBRA: Liu, Zou et al., arXiv 2603.21597 (2026)
- PHIA: Google, Nature Communications (2025), arXiv 2406.06464
- Virtual Lab: Zou Group, Nature (2025), doi:10.1038/s41586-025-09442-9
- BioMedAgent: Nature BME (2026), doi:10.1038/s41551-026-01634-6
- CellAgent: arXiv 2407.09811 (2024)
- ClockBase Agent: Gladyshev Lab, PMC 12667862 (2025)
- K-Dense: Gladyshev Lab, bioRxiv 2025.09.08.674588
- Vivaldi: arXiv 2603.04142 (2026)
- MATMCD: ACL Findings (2025)
- MRAgent: Briefings in Bioinformatics 26(2) (2025)
- CARE-AD: npj Digital Medicine 8(1):541 (2025)
- Microsoft Healthcare Orchestrator (2025)
- Mount Sinai Multi-Agent: npj Health Systems (2026)
- ClinicalAgents: arXiv 2603.26182 (2026)

### Foundation Models (Health/Biosignal)
- I-JEPA: Assran, LeCun et al., CVPR 2023, arXiv 2301.08243
- JETS: Empirical Health, NeurIPS TS4H Workshop, empirical.health/blog/wearable-foundation-model-jets
- SMB-Structure: Adam et al., arXiv 2601.22128
- SleepFM: Thapa, Zou, Mignot et al., Nature Medicine 2026;32(2):752-762, doi:10.1038/s41591-025-04133-4
- Delphi-2M: Shmatko, Gerstung et al., Nature 2025;647(8088):248-256, doi:10.1038/s41586-025-09529-3
- RETFound: Zhou et al., Nature 2023;622:156-163
- ECGFounder: Li et al., NEJM AI 2025, arXiv 2410.04133

### Agent Frameworks
- CodeAct: ICML 2024, arXiv 2402.01030
- Anthropic PTC: platform.claude.com/docs
- smolagents: HuggingFace, github.com/huggingface/smolagents
- LangGraph-CodeAct: github.com/langchain-ai/langgraph-codeact

### Aging Clocks & Longevity
- Tian et al., Nature Medicine 2023 (multi-organ aging)
- Oh et al., Nature 2023 (proteomic organ clocks)
- MRI multi-organ clocks: Nature Medicine 2025
- CosinorAge: npj Digital Medicine 2024
- PpgAge: Nature Communications 2025
- AI-PPG: Communications Medicine 2025
- LifeClock: Nature Medicine 2025
- Retinal age: Zhu et al., Br J Ophthalmol 2023; Nusinovici, Age Ageing 2022
- ECG age: npj Digital Medicine 2024
- WEAR-ME (wearable IR prediction): Nature 2026
- LongevityBench: Insilico Medicine, bioRxiv 2026

### Causal Discovery
- Tigramite/PCMCI: Runge et al., Sci Adv 2019
- Transfer entropy: Schreiber, Phys Rev Lett 2000
- Granger causality: Granger, Econometrica 1969
- DYNOTEARS: Dynamic Bayesian network learning

### Datasets & Benchmarks
- AI-READI v3.0.0: doi:10.60775/fairhub.3
- PhysioCGM: PMC 12630648 (2025)
- BIG IDEAs Lab: CGM + wearable dataset
