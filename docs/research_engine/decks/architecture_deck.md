---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 22px; }
  h1 { font-size: 36px; color: #1a365d; }
  h2 { font-size: 28px; color: #2c5282; }
  h3 { font-size: 22px; color: #4a5568; }
  table { font-size: 18px; }
  code { font-size: 16px; }
  .columns { display: flex; gap: 2em; }
  .col { flex: 1; }
  blockquote { font-size: 18px; border-left: 4px solid #2c5282; }
---

# A Cross-Modal Foundation Model with Agentic Scientific Reasoning for Multimodal Aging Physiology

**Zijian (Carl) Ma**
Stanford University | TWC Lab

AI-READI v3.0.0 | 2,280 participants | 9 modalities

---

## The Gap

Current approaches treat representation learning and scientific reasoning as separate problems:

| Foundation Models | Agent Systems |
|---|---|
| JETS: wearable JEPA (Empirical Health) | CEREBRA: multimodal agents for dementia |
| SMB-Structure: EHR JEPA (Standard Model Bio) | PHIA: code-gen agent for wearable QA |
| RETFound: retinal FM (Moorfields) | Virtual Lab: multi-agent deliberation |
| ECGFounder: cardiac FM (Harvard-Emory) | ClockBase: aging clock mining at scale |

**No system combines a trained cross-modal alignment model with agentic reasoning over simultaneously-measured physiological data.**

LongevityBench (Insilico 2026): LLMs alone score **0.48-0.54** (chance) on aging biology. Agents must be grounded in computed representations, not parametric knowledge.

---

## AI-READI: The Dataset

**2,280 participants** | 3 sites (UW, UCSD, UAB) | 4 T2DM severity groups | ~3.82 TB

| Modality | Format | Coverage | Temporal |
|---|---|---|---|
| Clinical labs/vitals | OMOP CDM (6 CSV) | 100% | Snapshot |
| Cardiac ECG | WFDB 12-lead, 500 Hz, 11s | 98.7% | Snapshot |
| Retinal (CFP/OCT/OCTA/FLIO) | DICOM | 81-99.8% | Snapshot |
| Wearable (HR/SpO2/sleep/stress/RR) | OMH JSON, 7 streams | 95.8% | ~10 days |
| CGM (glucose) | OMH JSON, 5-min | 98.5% | ~10 days |
| Environmental sensor | CSV, 22 channels, 5-sec | 97.9% | ~10 days |

**Unique property:** ~10-day triple overlap (wearable + CGM + environment) anchored to same-day clinical + imaging snapshot. No other public dataset offers this cross-modal alignment substrate.

---

## I-JEPA: The Foundational Principle
Assran, LeCun et al. | CVPR 2023 | arXiv:2301.08243

<div class="columns"><div class="col">

**Problem:** Self-supervised visual representation learning without hand-crafted augmentations

**Data:** ImageNet-1K (1.28M images)

**Model:** Vision Transformer encoder + EMA target encoder + narrow predictor (384-d bottleneck). Predicts representations of 4 masked blocks from visible context.

**Key result:** ViT-H/14 achieves 79.3% ImageNet linear probe at 300 epochs — beats MAE (77.2% at 1600 epochs) at **10x less compute**

</div><div class="col">

**Core insight:**

```
Predict in REPRESENTATION SPACE
    → 66.9% (1% ImageNet)

Predict in PIXEL SPACE (same model)
    → 40.7%

    +26.2 points from same architecture
```

Representation-space prediction forces semantic abstraction. Pixel prediction learns textures.

**Integration:** The architectural template for all subsequent health JEPA models. Narrow bottleneck predictor + multi-target masking + L2 in latent space.

</div></div>

---

## JETS: JEPA for Wearable Health Time Series
Empirical Health | NeurIPS Workshop on Time Series for Health

<div class="columns"><div class="col">

**Problem:** Learn general wearable representations that predict blood biomarkers

**Data:** 3M de-identified person-days of wearable data, 63 channels (HR, SpO2, sleep stages, stress, RR, activity)

**Model:** Twin encoders (Transformer or Mamba blocks, d=64) with JEPA objective. Input: (timestamp, value, metric_type) triplets. 30% random masking. Predicts in latent space.

**Key results (AUROC, linear probe):**
| Task | JETS |
|---|---|
| Hypertension | 87% |
| Sick sinus syndrome | 87% |
| ME/CFS | 81% |
| Atrial flutter | 70% |

</div><div class="col">

Also predicts blood biomarkers (HbA1c, glucose, HDL, hs-CRP) from wearables alone.

**Integration:** AI-READI has the **same channels**: Garmin Vivosmart 5 produces HR, SpO2, sleep stages, stress, RR, activity. The JETS tokenization scheme is a direct recipe for our wearable data. Either:
- Use JETS weights (if released) as frozen wearable encoder
- Train a small JEPA on AI-READI's 23K person-days

The wearable infrastructure we built (sleep architecture, daily summaries, circadian metrics) provides the derived features; JETS provides the learned encoder.

</div></div>

---

## SMB-Structure: JEPA for Clinical Trajectories
Standard Model Bio | arXiv:2601.22128

<div class="columns"><div class="col">

**Problem:** Clinical LLMs reconstruct documents, not disease dynamics. Need a world model that simulates trajectory velocity.

**Data:** MSK Oncology (23K patients, 3M records) + INSPECT PE (19K patients, 225M events)

**Model:** LLaMA-3.1 8B + LoRA (167M params) + JEPA predictor (67M params). Two losses: SFT (next-token) + JEPA (L2 on masked future embeddings). 50% masking. EMA target encoder (tau=0.996).

**Critical finding — curriculum beats simultaneous:**
| Training | Disease progression AUC |
|---|---|
| SFT only | 0.727 |
| Simultaneous SFT+JEPA | 0.719 (worse!) |
| **Curriculum (SFT -> JEPA)** | **0.731** |

</div><div class="col">

Cross-disease transfer: training on PE patients **improves** oncology prediction. JEPA learns universal dynamics.

365-day mortality: 0.810 (curriculum) vs 0.802 (SFT) — long-horizon is where JEPA helps most.

**Integration:** AI-READI clinical data is OMOP CDM — the same standard SMB-Structure tokenizes. Key lessons for our pipeline:

1. **Curriculum training**: ground semantics with SFT first, then add JEPA
2. **Narrow predictor** (2 layers, bottleneck) forces abstract dynamics
3. **Cross-cohort diversity** improves single-cohort performance

Limitation for AI-READI: cross-sectional (1 visit), so no longitudinal trajectory. SMB-Structure functions as a pretrained clinical encoder, not trajectory predictor.

</div></div>

---

## CEREBRA: Multi-Agent Multimodal Dementia Assessment
Liu, Zou et al. (Stanford/NYU/UF) | arXiv:2603.21597

<div class="columns"><div class="col">

**Problem:** Integrate fragmented multimodal health records (EHR + notes + imaging) for dementia diagnosis and risk prediction

**Data:** 3M+ patients, 4 U.S. healthcare systems, 369M EHR records, 100K+ with complete multimodal data

**Architecture:**
```
Data Agent     → retrieves relevant data
Super Agent    → decomposes, assigns
Modality Agents:
  ├── Structured EHR agent
  ├── Clinical notes agent
  └── 3D imaging agent (MRI, OCT)
Dashboard      → interpretable evidence
```

LLM-backbone agnostic (GPT-4o / Claude / Gemini / open-source)

</div><div class="col">

**Key results:**
| Task | CEREBRA | LLM baselines |
|---|---|---|
| 3-year risk (AUROC) | **0.80** | 0.68 |
| Diagnosis (AUROC) | **0.86** | +16.1% |
| Survival (C-index) | **0.81** | +18.8% |

Clinician study: +17.5pp accuracy, +29.8pp sensitivity with CEREBRA assistance.

**Integration:** Our template for agent architecture:
- **Modality agents** map to our 6 data agents (clinical, wearable, glucose, cardiac, retinal, environment)
- **Missing-modality robustness** critical (FLIO 81%, wearable 96%)
- **Evidence chains** — every claim backed by specific data
- We ADD: continuous time-series agents + trained cross-modal JEPA (CEREBRA uses generic pretrained models)

</div></div>

---

## PHIA: Code-Generation Agent for Wearable Health
Google | Nature Communications 2025

<div class="columns"><div class="col">

**Problem:** Answer open-ended health questions from personal wearable data (sleep, HR, steps, HRV)

**Data:** Individual wearable time series (Fitbit/Wear OS)

**Model:** ReAct agentic loop:
```
Question
  → Thought (reason about what to compute)
  → Act (generate Python code against raw data)
  → Execute in sandbox
  → Observe output
  → Iterate until answer
```

Augmented with web search for health context.

**Key results:** 84% accuracy on numerical questions, 83% favorable on open-ended (2x best non-agentic baseline). 6,000+ responses rated by 19 annotators (650 hrs).

</div><div class="col">

**Why code gen beats pure LLM:** The agent writes `pandas` queries against actual sensor data, executes, and observes. It doesn't hallucinate statistics — it computes them.

**Integration:** The exact interface pattern for our Tier 1 agents:

```python
# Agent receives: "What's the average nocturnal
#   HR dip for insulin-dependent participants?"
# Agent generates:
from scripts.features import load_feature_matrix
from scripts.features_wearable import compute_daily_summary
fm = load_feature_matrix()
insulin = fm[fm['study_group']=='insulin_dependent']
# ... computes, observes, reports
```

Our `scripts/` API is the tool library. Each modality agent writes Python against it.

</div></div>

---

## Virtual Lab + BioMedAgent: Multi-Agent Deliberation and Tool Learning
Nature 2025 / Nature BME 2026

<div class="columns"><div class="col">

### Virtual Lab
**Problem:** Multi-agent scientific discovery (nanobody design)

**Architecture:** PI Agent + domain scientists (chemist, computational biologist, immunologist) + Critic. Structured meetings: team meetings (all discuss agenda) + individual meetings (one executes).

**Result:** 92 SARS-CoV-2 nanobodies designed, >90% expression success.

**Integration:** The deliberation protocol for our Tier 2-3:
- **PI Agent** coordinates
- **HypothesisAgent** proposes
- **CriticAgent** stress-tests (confounders, effect sizes, FDR, site bias)
- Team meetings for cross-cutting questions

</div><div class="col">

### BioMedAgent
**Problem:** Automated bioinformatics analysis via self-evolving agents

**Architecture:** Agents explore bioinformatics tools, update memory banks, chain tools into workflows. 77% success on 327 biomedical data tasks (BioMed-AQA benchmark).

**Key insight:** Tool learning + workflow memory. Agents don't just call tools — they learn which chains work and cache them.

**Integration:** Our agents should cache successful analysis workflows:

```
"To compare CGM metrics across groups:
 1. load_feature_matrix()
 2. filter by study_group
 3. compare_groups(fm, feature, adjust_for=['age'])
 4. site_bias_check()
 → Stored in workflow memory for reuse"
```

</div></div>

---

## ClockBase Agent + LongevityBench: Aging-Specific Systems
Gladyshev Lab (Harvard) / Insilico Medicine

<div class="columns"><div class="col">

### ClockBase Agent (bioRxiv 2025)
**Problem:** Mine aging interventions from public methylation/RNA-seq data at scale

**Pipeline:** Analysis Executor (parses metadata, runs statistical code) -> Biological Interpreter (literature context) -> Scorer (ranks interventions)

**Scale:** 43,602 intervention-control comparisons from 13,211 mouse studies. 206,543 code execution blocks.

**Result:** 500+ age-modifying interventions found (most missed by original investigators). Top candidate (ouabain) experimentally validated in aged mice.

**Integration:** Domain-structured pipeline for aging biology. Our agent system should include ClockBase-style automated aging analysis on AI-READI's per-organ AgeAccel profiles.

</div><div class="col">

### LongevityBench (bioRxiv Jan 2026)
**Problem:** Can LLMs reason about aging biology?

**Benchmark:** 15 LLMs tested across 7 aging biology domains (transcriptomics, epigenetics, proteomics, blood tests, biometrics, genomics, NL annotations)

**Sobering result:** On age-group classification from gene expression, all 15 LLMs scored **0.48-0.54** (indistinguishable from random).

**Integration — the non-negotiable design constraint:**

> LLMs alone cannot do aging biology. Every agent in our system must be grounded in computed features (Layer 1 embeddings, Layer 0 derived metrics) + tool execution (code gen against `scripts/` API), **never** parametric LLM reasoning alone.

</div></div>

---

## Proposed Architecture: Four Layers

```
┌──────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: LONGEVITY OS BRIDGE                                            │
│  Population findings → Person-level phenotypes → N-of-1 trial targets    │
└─────────────────────────────────┬────────────────────────────────────────┘
┌─────────────────────────────────┴────────────────────────────────────────┐
│  LAYER 2: AGENT SYSTEM (CEREBRA + PHIA + Virtual Lab pattern)            │
│                                                                          │
│  Tier 3: PI Agent (orchestrator, research log, team meetings)            │
│  Tier 2: AlignmentAgent | PhenotypeAgent | HypothesisAgent | CriticAgent │
│  Tier 1: Clinical | Wearable | Glucose | Cardiac | Retinal | Environment │
└─────────────────────────────────┬────────────────────────────────────────┘
┌─────────────────────────────────┴────────────────────────────────────────┐
│  LAYER 1: FOUNDATION MODEL (Cross-Modal JEPA)                            │
│                                                                          │
│  Frozen encoders:  RETFound | ECGFounder | JETS-style | CGM | MLP | Env  │
│  Cross-modal predictor: mask one modality → predict z from others        │
│  Downstream heads: per-organ AgeAccel | disease stage | biomarker pred   │
└─────────────────────────────────┬────────────────────────────────────────┘
┌─────────────────────────────────┴────────────────────────────────────────┐
│  LAYER 0: DATA INFRASTRUCTURE (built)                                    │
│  Loaders | Feature matrix (2280x125) | CGM metrics + AGP | Sleep arch    │
│  Daily summary | Circadian IS/IV/M10/L5/RA | Temporal alignment          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Cross-Modal JEPA — Architecture Detail

<div class="columns"><div class="col">

**Per-modality encoders (frozen):**

| Modality | Encoder | Dim | Source |
|---|---|---|---|
| Retinal CFP | RETFound | 768 | 1.6M images |
| ECG | ECGFounder | 768 | 10.7M ECGs |
| Wearable | JETS-style | 256 | 23K p-days |
| CGM | Feature vec | 260 | metrics + AGP |
| Clinical | MLP | 128 | 125-feature FM |
| Environment | Summary | 64 | daily stats |

**Cross-modal predictor:**
- Narrow transformer (2 layers, 384-d, 12 heads)
- Mask one modality per training step
- Predict masked z from remaining modalities
- L2 loss against EMA target encoder

</div><div class="col">

**Training (curriculum, per SMB-Structure):**

```
Phase A: Supervised grounding
  Joint embedding → study_group classifier
  (teaches: what do these modalities mean?)

Phase B: Add JEPA objective
  Mask each modality in turn
  Predict its z from all others
  (teaches: how are modalities coupled?)
```

**Downstream heads (linear probes):**

```
z_retinal  → Retinal AgeAccel
z_ecg      → Cardiac AgeAccel
z_cgm      → Metabolic AgeAccel
z_wearable → Autonomic AgeAccel
z_joint    → Disease stage (4-way)
z_wearable → HbA1c prediction
```

Per-person AgeAccel profile = the multi-organ aging phenotype.

</div></div>

---

## Layer 2: Agent System — How Agents Use the Foundation Model

Agents don't just call tools — they **interrogate** the trained JEPA:

**Cross-modal coupling scores:**
```python
# AlignmentAgent: "Is glucose-HR coupling weaker in insulin-dependent T2DM?"
for pid in get_person_ids(group="insulin_dependent"):
    loss = jepa.reconstruction_loss(source="wearable", target="cgm", pid=pid)
    # High loss = decoupled systems → possible insulin resistance signature
```

**Multi-organ aging profiles:**
```python
# PhenotypeAgent: cluster participants by AgeAccel pattern
profiles = pd.DataFrame({
    'retinal': [age_head_retinal(z_ret[pid]) - age[pid] for pid in all_pids],
    'cardiac': [age_head_cardiac(z_ecg[pid]) - age[pid] for pid in all_pids],
    'metabolic': [age_head_metab(z_cgm[pid]) - age[pid] for pid in all_pids],
})
# → Data-driven aging subtypes beyond the 4 study_groups
```

**Critic validation:**
```python
# CriticAgent: "Does this finding survive site adjustment?"
result = compare_groups(fm, "coupling_score", adjust_for=["age", "clinical_site"])
# Also: does JEPA reconstruction loss differ by site? (artifact check)
```

---

## Layer 3: Longevity OS Bridge

```
   AI-READI (2,280 people)              Longevity OS (1 person)
   ─────────────────────                ──────────────────────

   Population-level discovery    ──→    Person-level translation

   "Insulin-dependent T2DM shows        "Your retinal AgeAccel is +6y
    decoupled glucose-HR coupling         but cardiac is +1y.
    and retinal AgeAccel +4y above        This pattern matches the
    healthy controls"                     vascular-predominant aging
                                          subtype we found in AI-READI"
           │                                        │
           │                                        │
           ▼                                        ▼
   Statistical finding with              Imperial Physician agent
   effect sizes, FDR, critic              dispatches to:
   validation                             - Diet agent (anti-inflammatory)
                                          - Exercise agent (vascular focus)
                                          - Biomarker agent (track retinal
                                            age via fundus app)
                                          - Trial design agent (N-of-1
                                            with Bayesian STS + ITS)
```

---

## What's Novel: The Three-Way Integration

| Component alone | Exists | Missing piece |
|---|---|---|
| Wearable FM (JETS) | Wearable-only, no imaging/clinical | Cross-modal alignment |
| Clinical FM (SMB-Structure) | EHR-only, no time series | Continuous physiology |
| Multi-agent diagnosis (CEREBRA) | Agents + multimodal | No trained alignment model |
| Wearable agent (PHIA) | Code gen + single modality | Multi-agent, no FM |
| Aging clock pipeline (ClockBase) | Mining at scale | No multimodal FM |
| Personal health agents (Longevity OS) | Individual focus | No population grounding |

**This system unifies all three:**
1. **Cross-modal JEPA** on 6 simultaneously-measured modalities (no existing system has this)
2. **Agentic reasoning grounded in FM representations** (not parametric LLM knowledge)
3. **Research-to-translation pipeline** (population discovery -> individual intervention)

---

## Research Directions

**Direction 1: Dense Multimodal Aging State Vector**
- Per-organ AgeAccel profiles from cross-modal JEPA embeddings
- Cluster into data-driven aging subtypes (beyond the 4 T2DM strata)
- Do retinal and cardiac aging correlate or diverge? By disease stage?

**Direction 2: Agent-Discovered Biomarker Signatures**
- "What minimal set of non-invasive measurements (wearable + CGM) predicts clinical labs?"
- JETS showed wearables can predict HbA1c — at what accuracy in AI-READI's T2DM gradient?

**Direction 3: Cross-Modal Coupling as Aging Signal**
- Does glucose-HR coupling strength decay with diabetes severity?
- Does sleep architecture predict next-day glycemic control?
- JEPA reconstruction loss per participant = personalized coupling score

**Direction 4: Longevity OS Grounding**
- Translate population findings into N-of-1 trial targets
- Close the loop: population science -> individual intervention -> measured outcome

---

## Implementation Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| **Layer 0** | Data infrastructure: loaders, feature matrix (2280x125), CGM metrics (20+AGP), wearable daily/sleep/circadian | **Done** |
| **1a** | Extract RETFound + ECGFounder embeddings (GPU jobs) | Next |
| **1b** | Train small wearable JEPA (d=64, JETS-style) | Next |
| **1c** | Cross-modal JEPA predictor (narrow transformer, ~67M params) | 1-2 weeks |
| **1d** | Per-organ aging clock heads (linear probes) | Days |
| **2a** | Single PHIA-style ReAct agent over `scripts/` API | Days |
| **2b** | CEREBRA-style modality specialization | When context limits hit |
| **2c** | Critic + Hypothesis agents (Virtual Lab deliberation) | After 2b |
| **2d** | Evaluation benchmark (100-200 auto-scored questions) | With 2a |
| **3** | Longevity OS integration | After publication-ready results |

---

## Key Design Principles (from the literature)

> **"LLMs score at chance on aging biology"** — LongevityBench
> Agents must compute, not hallucinate

> **"Curriculum beats simultaneous"** — SMB-Structure
> Ground semantics (SFT) before learning dynamics (JEPA)

> **"Narrow predictors force abstraction"** — I-JEPA
> 384-d bottleneck outperforms 1024-d by +2.3 points

> **"The Critic is non-negotiable"** — Virtual Lab, CellAgent
> Every finding stress-tested for confounders, FDR, site bias, effect size

> **"Start single-agent, grow multi-agent"** — PHIA
> Single agent already gets 84%. Split when context limits force it.

> **"The patient is not a moving document"** — SMB-Structure
> Predict where the state is going, not what someone would write about it

---

## References

1. Assran M et al. I-JEPA. *CVPR* 2023. arXiv:2301.08243
2. JETS. Empirical Health. NeurIPS TS4H Workshop. empirical.health/blog/wearable-foundation-model-jets
3. Adam I et al. SMB-Structure. arXiv:2601.22128. standardmodelbio/SMB-v1-8B-Structure
4. Liu S, Zou J et al. CEREBRA. arXiv:2603.21597. github.com/shengliu66/Cerebra
5. PHIA. Google. *Nature Communications* 2025. doi:10.1038/s41467-025-67922-y
6. The Virtual Lab. *Nature* 2025. doi:10.1038/s41586-025-09442-9
7. BioMedAgent. *Nature Biomedical Engineering* 2026. doi:10.1038/s41551-026-01634-6
8. ClockBase Agent. Gladyshev Lab. *bioRxiv* 2025. doi:10.1101/2023.02.28.530532
9. LongevityBench. Insilico Medicine. *bioRxiv* 2026. doi:10.64898/2026.01.12.698650
10. Zhou Y et al. RETFound. *Nature* 2023;622:156-163. PMID 37704728
11. Li J et al. ECGFounder. *NEJM AI* 2025. arXiv:2410.04133
12. AI-READI Dataset v3.0.0. doi:10.60775/fairhub.3
