# Hypothesis-First Agentic Discovery System Implementation Plan

Date: 2026-05-14

This document maps the next implementation stage for the AI-READI project:
an agentic, hypothesis-first scientific discovery system over multimodal
aging, diabetes, disease burden, and synchronized physiology.

The current repository already contains two important foundations:

- `agents/`: a local multi-agent workflow with modality agents, reasoning
  agents, tasks, memory, tools, and an orchestrator.
- `hypothesis_driven/`: a JSON-backed hypothesis workspace with proposer,
  critic, executor, verifier, and structured hypothesis files.

The goal of this plan is not to create a disconnected new system. The goal is
to extend those foundations into a persistent, retrieval-aware, round-based
discovery engine where hypotheses, papers, tools, datasets, results, surprises,
and follow-up questions all become durable objects.

## 1. High-Level Thesis

The project should not be organized around "run all models" or "build an aging
clock." The higher-level objective is:

> Build an autonomous multimodal discovery system that learns how aging,
> diabetes, and disease burden emerge from breakdowns in coordinated physiology.

Chronological aging clocks are useful baselines, but they are not the central
scientific object. The stronger scientific object is a dynamic, multimodal
state of physiology:

- metabolic regulation from CGM
- autonomic tone and activity from wearable streams
- sleep and wake transitions from wearable intervals
- environmental exposure from Anura sensors
- retinal structure from imaging embeddings and derived ophthalmic features
- cardiac electrophysiology from ECG embeddings and intervals
- clinical burden from labs, exams, KDM, frailty, allostatic load, and
  homeostatic dysregulation

The agentic system should turn this into a cumulative research process:

```text
literature + tools + datasets + current results + surprises + human ideas
  -> candidate hypotheses
  -> enrichment and critique
  -> feasibility checks
  -> method plans
  -> execution
  -> verification
  -> evidence updates
  -> follow-up hypotheses
  -> next discovery round
```

Every claim should have provenance. Every result should produce either a
verdict or a new testable follow-up. Every round should make the hypothesis
database more useful.

## 2. Core Design Principles

### 2.1 Hypothesis First

Every analysis should start from a structured hypothesis, not from an
unstructured instruction to run a script.

Bad pattern:

```text
Run random forest on all features and see what predicts disease.
```

Preferred pattern:

```text
Hypothesis:
  In diabetes, activity-to-glucose recovery is delayed because insulin
  resistance and impaired metabolic flexibility reduce the ability to restore
  glycemic stability after exertion.

Prediction:
  After activity bouts, the return-to-baseline glucose time is longer in oral
  medication and insulin-dependent groups than in healthy controls, after
  adjustment for age, site, BMI, and baseline HbA1c.

Negative controls:
  Random non-activity windows should not show the same group gradient.
```

### 2.2 Mechanism Before Model

The model is not the hypothesis. A Ridge model, JEPA objective, Granger test,
or UMAP embedding is only a tool. The hypothesis must state a biological
mechanism, a direction, a timescale, a measurement, and a refutation criterion.

### 2.3 Persistent Memory, Not Loose Notes

The system should remember four types of state:

- hypotheses and hypothesis graph edges
- papers, tools, datasets, and extracted claims
- run artifacts, result tables, and verification status
- surprises, failed analyses, critic objections, and follow-up ideas

This memory must be machine-readable. Markdown summaries are useful for humans,
but agents need structured records.

### 2.4 Data-Driven Hypotheses Are Allowed, But Quarantined First

Surprising data patterns are valuable. They should not immediately become
scientific claims. They first become `HypothesisCandidate` records with clear
origin, trigger artifact, and p-hacking risk. Only after literature enrichment,
critic review, feasibility checks, and method planning can they become
registered executable hypotheses.

### 2.5 Retrieval Before Reasoning

Before proposing, criticizing, or executing a hypothesis, the relevant prior
knowledge should be retrieved:

- similar internal hypotheses
- prior supported/refuted findings
- papers and extracted claims
- known tools and methods
- external validation datasets
- project constraints and failure modes

The system should avoid rediscovering its own previous mistakes.

### 2.6 Mechanical Verification Before Narrative

The final verdict should not be based on persuasive prose. It should be based
on mechanical checks:

- split integrity
- leakage masks
- target/input separation
- covariate adjustment
- site and age balance
- FDR correction
- negative controls
- sensitivity analyses
- artifact reproducibility

The synthesis agent can write the narrative only after those checks run.

## 3. Existing Repository Anchors

The implementation should reuse these current components.

### 3.1 Existing Agent System

Current location:

```text
agents/
  run.py
  orchestrator.py
  workspace.py
  memory.py
  critic.py
  tools.py
  modality/
  reasoning/
  tasks/
```

This package is useful for interactive, task-oriented agent workflows. It has
domain agents and memory, but it is not yet the durable source of truth for
hypothesis lifecycle state.

### 3.2 Existing Hypothesis System

Current location:

```text
hypothesis_driven/
  __main__.py
  schemas.py
  workspace.py
  proposer.py
  hypothesis_critic.py
  executor.py
  verifier.py
  run_pipeline.py
  hypotheses/
  results/
```

This package is the right place to extend first. It already has:

- JSON hypothesis records
- proposer/critic/executor/verifier roles
- a hypothesis lifecycle
- 26 current hypothesis files
- stored critic verdicts

### 3.3 Existing Results And Evidence Artifacts

Current locations:

```text
results/features/
results/clocks/
results/coupling/
results/hypotheses/
results/biomarkers/
results/causal/
results/figures/
docs/reports/
foundation_jepa/
```

These contain the current empirical state. The new system should not duplicate
them. It should register them as artifacts and link them to hypotheses,
surprises, and evidence records.

## 4. Proposed System Architecture

### 4.1 Main Object Stores

The upgraded system should have four persistent stores.

```text
hypothesis_driven/
  hypotheses/              # registered executable hypotheses
  candidates/              # raw candidate hypotheses not yet approved
  knowledge/               # papers, tools, datasets, extracted claims
  runs/                    # execution and verification metadata
```

The current `hypothesis_driven/hypotheses/` directory remains the registered
hypothesis database. New subdirectories add the missing memory layers.

Recommended first implementation:

```text
hypothesis_driven/
  candidates/
    CAND-*.json
  knowledge/
    papers.jsonl
    tools.jsonl
    datasets.jsonl
    claims.jsonl
    links.jsonl
    retrieval_index.sqlite
  runs/
    RUN-*.json
    verification/
    surprises/
```

Later, these can move to a proper SQLite schema or a small local service. The
first version should stay simple and inspectable.

### 4.2 Agent List

The upgraded system should include these agents.

| Agent | Primary responsibility | Writes durable records? |
|---|---|---|
| Literature / Dataset / Tool Scout | Collects papers, methods, tools, external datasets, and extracted claims relevant to hypotheses | Yes: paper/tool/dataset/claim records |
| Data Profiler | Checks local modality coverage, missingness, splits, target availability, and known dataset constraints | Yes: feasibility and data-profile records |
| Proposer | Generates candidate mechanistic hypotheses from literature, current results, memory, and human ideas | Yes: candidate hypothesis records |
| Surprise Miner | Scans results for unexpected patterns, failures, direction flips, modality domination, and negative-control failures | Yes: surprise records and candidate hypotheses |
| Critic | Attacks candidates for confounding, leakage, biological implausibility, weak design, and unsupported causal language | Yes: critic review records |
| Feasibility Agent | Determines whether AI-READI has the required modalities, sample size, labels, and time resolution | Yes: feasibility review records |
| Methods Agent | Converts a validated candidate into an executable test plan with covariates, controls, split choice, and artifacts | Yes: method plan records |
| Registrar / Memory Agent | Owns the hypothesis database, creates IDs, links parents/children, updates statuses, prevents duplicates | Yes: hypothesis and graph records |
| Executor | Runs or submits analysis code; records command, environment, input artifacts, output artifacts, and logs | Yes: run records |
| Verifier | Recomputes key checks, validates artifacts, checks leakage/splits/FDR/controls, and assigns evidence level | Yes: verification records |
| Synthesis Agent | Writes human-readable summaries, slide notes, and next-round recommendations from verified records | Yes: synthesis records and docs |
| Human PI Interface | Allows a human to deposit ideas, approve high-risk runs, and override priorities with explicit provenance | Yes: human-origin candidate records |

The critical addition is that the scout, surprise miner, and registrar all
write structured state. They should not only produce prose.

### 4.3 System Loop

One discovery round should look like this:

```text
Round N
  1. Sync local state
     - load hypotheses
     - load candidate queue
     - load knowledge registry
     - load recent result artifacts

  2. Retrieve context
     - prior related hypotheses
     - papers and extracted claims
     - tools and external datasets
     - previous failures and constraints

  3. Select work
     - execute top queued hypothesis
     - or verify completed run
     - or enrich/critique candidate
     - or mine surprises if no execution candidate is ready

  4. Run one bounded action
     - keep state transitions atomic

  5. Record outputs
     - candidate/hypothesis status update
     - run metadata
     - result artifacts
     - verification decisions
     - follow-up candidates

  6. Reprioritize
     - update scores and evidence levels
```

The loop should avoid doing everything at once. Each round should have a
bounded action so failures are recoverable and the state remains auditable.

## 5. Data Model

### 5.1 Hypothesis Candidate

Candidates are ideas that have not yet passed the quality gates.

Suggested JSON schema:

```json
{
  "candidate_id": "CAND-20260514-0001",
  "created_at": "2026-05-14T00:00:00Z",
  "origin_type": "surprise_finding",
  "origin_agent": "SurpriseMiner",
  "origin_detail": "Recommended-split raw all-feature clock failed while balanced/clipped variants were stable.",
  "trigger_artifacts": [
    "results/clocks/multimodal_clock_performance.csv",
    "results/clocks/multimodal_clock_performance__balanced_split_v1.csv"
  ],
  "title": "High-dimensional clock extrapolation is driven by split-specific outlier structure",
  "claim": "Extreme modality-specific feature values in the recommended test split cause unstable age extrapolation in the all-feature Ridge clock.",
  "mechanism": "When a high-dimensional model uses 2,192 features, a small number of out-of-training-range retinal, ECG, or clinical features can dominate predictions even after standard scaling.",
  "expected_direction": "Removing or robustly transforming the offending modality/features should reduce impossible predictions and improve test stability.",
  "required_modalities": ["clinical", "retinal_embeddings", "cardiac_embeddings"],
  "primary_outcome": "test prediction range and MAE stability",
  "confounders": ["age", "clinical_site", "study_group"],
  "negative_controls": [
    "balanced_split_v1 no-clipping run",
    "feature-block leave-one-out runs"
  ],
  "leakage_risks": [
    "must not inspect test labels while choosing transformation",
    "must fit clipping or robust scaling on train rows only"
  ],
  "status": "candidate",
  "priority": 0.75,
  "needs": ["critic_review", "feasibility_review", "method_plan"]
}
```

Candidate statuses:

```text
candidate
  -> enriched
  -> critiqued
  -> feasible
  -> method_planned
  -> registered
  -> rejected
  -> archived_duplicate
```

### 5.2 Registered Hypothesis

Registered hypotheses are executable and should be assigned stable IDs.

Suggested JSON additions to the current hypothesis schema:

```json
{
  "id": "H-NEW19",
  "title": "Activity-to-glucose recovery is delayed with diabetes severity",
  "claim": "After activity bouts, glucose returns to baseline more slowly in diabetes than in healthy controls.",
  "mechanism": "Insulin resistance and impaired metabolic flexibility reduce the speed of post-activity glycemic stabilization.",
  "origin": {
    "origin_type": "critic_revised_candidate",
    "candidate_id": "CAND-20260514-0007",
    "origin_agent": "Registrar",
    "human_requested": false
  },
  "graph": {
    "parent_hypotheses": ["H-NEW10"],
    "child_hypotheses": [],
    "supports": [],
    "contradicts": [],
    "derived_from_artifacts": [
      "results/hypotheses/h_new10_activity_glucose.csv"
    ]
  },
  "required_modalities": ["cgm", "wearable"],
  "required_data_fields": [
    "cgm glucose time series",
    "wearable steps or active calories",
    "age",
    "clinical_site",
    "study_group",
    "hba1c",
    "bmi"
  ],
  "test_plan": {
    "primary_method": "event_aligned_mixed_effects_or_participant_summary",
    "split_column": "balanced_split_v1",
    "primary_metric": "post_activity_glucose_recovery_time_minutes",
    "comparison": "ordinal diabetes severity trend",
    "covariates": ["age", "clinical_site", "bmi", "baseline_hba1c"],
    "negative_controls": [
      "random non-activity windows matched by time of day",
      "participant-shuffled activity labels"
    ],
    "sensitivity_checks": [
      "awake-only",
      "exclude overnight windows",
      "minimum CGM coverage",
      "site-stratified estimates"
    ]
  },
  "decision_rule": {
    "support": "FDR < 0.05, monotonic severity trend, negative controls null, direction matches prediction",
    "refute": "effect absent or direction reversed with adequate sample and passing QC",
    "inconclusive": "sample/coverage/control failure prevents interpretation"
  },
  "evidence_level": "E1",
  "status": "queued"
}
```

### 5.3 Paper Record

Papers should be stored as reusable evidence objects.

```json
{
  "paper_id": "PAPER-20260514-0001",
  "title": "DunedinPACE, a DNA methylation biomarker of the pace of aging",
  "authors": ["Belsky", "Caspi", "Moffitt"],
  "year": 2022,
  "doi": "10.xxxx/example",
  "url": "https://...",
  "source_type": "primary_paper",
  "source_status": "full_text_read",
  "topics": ["aging_clock", "pace_of_aging", "longitudinal"],
  "modalities": ["DNA methylation"],
  "methods": ["elastic_net", "longitudinal_slope_target"],
  "datasets": ["Dunedin Study"],
  "main_findings": [
    "Pace-of-aging clocks target longitudinal decline rather than chronological age."
  ],
  "limitations": [
    "Requires longitudinal phenotypic change labels not currently available in AI-READI."
  ],
  "relevance": [
    {
      "hypothesis_id": "SECOND_GENERATION_CLOCK_PROGRAM",
      "relationship": "defines target class",
      "note": "Supports separating chronological age head from biological burden head."
    }
  ],
  "collected_by": "LiteratureScout",
  "collected_at": "2026-05-14T00:00:00Z",
  "verified_by_human": false
}
```

Important rule: the system should store metadata and short extracted claims, not
copyrighted full texts. If PDFs are used locally, store only path metadata and
extract short, compliant notes.

### 5.4 Extracted Claim Record

Papers are too coarse for retrieval. The system also needs extracted claims.

```json
{
  "claim_id": "CLAIM-20260514-0001",
  "paper_id": "PAPER-20260514-0001",
  "claim_text": "Second-generation aging clocks target mortality, healthspan, disease burden, or longitudinal pace rather than chronological age.",
  "claim_type": "field_definition",
  "topics": ["second_generation_clock", "aging_clock"],
  "supports": ["SECOND_GENERATION_CLOCK_PROGRAM"],
  "contradicts": [],
  "confidence": 0.9,
  "source_status": "manually_verified"
}
```

### 5.5 Tool Record

Tools should be discoverable by task, input requirement, and known failure mode.

```json
{
  "tool_id": "TOOL-20260514-0001",
  "name": "PCMCI",
  "category": "time_series_causal_discovery",
  "package": "tigramite",
  "url": "https://github.com/jakobrunge/tigramite",
  "purpose": "Lagged conditional independence discovery in multivariate time series.",
  "input_requirements": [
    "regular time grid",
    "sufficient time points",
    "careful choice of lag range",
    "stationarity assumptions should be assessed"
  ],
  "outputs": [
    "lagged graph",
    "conditional dependence statistics",
    "p-values"
  ],
  "validation_status": "candidate",
  "local_install_status": "unknown",
  "known_failure_modes": [
    "confounding by common circadian rhythms",
    "sensitivity to autocorrelation",
    "causal language unsafe without design support"
  ],
  "related_hypotheses": ["H-NEW02"],
  "related_papers": []
}
```

### 5.6 Dataset Record

External datasets should be stored so the system can later propose validation
or replication.

```json
{
  "dataset_id": "DATASET-20260514-0001",
  "name": "NHANES",
  "population": "US population survey",
  "modalities": ["clinical_labs", "questionnaires", "wearable_subset"],
  "sample_size": "varies by cycle",
  "available_outcomes": [
    "mortality linkage in some releases",
    "clinical biomarkers",
    "activity accelerometry in selected cycles"
  ],
  "access_status": "public",
  "can_validate": [
    "clinical allostatic load",
    "phenotypic aging scores",
    "mortality-linked clinical burden"
  ],
  "cannot_validate": [
    "AI-READI retinal embeddings",
    "synchronized CGM-wearable-environment coupling"
  ],
  "limitations": [
    "not the same synchronized multimodal design",
    "cycle-specific missingness"
  ]
}
```

### 5.7 Surprise Record

Surprises are first-class records because they are a major source of follow-up
hypotheses.

```json
{
  "surprise_id": "SURPRISE-20260514-0001",
  "detected_at": "2026-05-14T00:00:00Z",
  "detected_by": "SurpriseMiner",
  "trigger_artifact": "results/clocks/multimodal_clock_performance.csv",
  "surprise_type": "model_failure",
  "description": "Recommended-split no-clipping all-feature age clock has validation MAE 4.78 but test MAE 9.83 and test R2 -47.52.",
  "expected_pattern": "Validation and test performance should be similar under a stable split.",
  "observed_pattern": "Test extrapolation failure under recommended split; balanced split and clipped sensitivity are stable.",
  "risk": "May indicate feature outliers, split imbalance, site artifacts, or target leakage in preprocessing assumptions.",
  "candidate_hypotheses_created": [
    "CAND-20260514-0001"
  ],
  "status": "triaged"
}
```

### 5.8 Execution Run Record

Every run should be reproducible from metadata.

```json
{
  "run_id": "RUN-20260514-0001",
  "hypothesis_id": "H-NEW10",
  "created_at": "2026-05-14T00:00:00Z",
  "executor": "ExecutorAgent",
  "command": "python -m scripts.hypothesis.hypothesis_new10 --split-column balanced_split_v1",
  "environment": {
    "python": "/home/mazijian/miniforge3/envs/aireadi/bin/python",
    "git_commit": "7476a9a",
    "branch": "main"
  },
  "input_artifacts": [
    "results/features/feature_matrix.parquet",
    "results/features/multimodal_features.parquet"
  ],
  "output_artifacts": [
    "results/hypotheses/h_new10_activity_glucose.csv"
  ],
  "split_column": "balanced_split_v1",
  "status": "completed",
  "logs": []
}
```

## 6. Hypothesis Graph

The hypothesis system should be graph-shaped, not only a flat queue.

### 6.1 Edge Types

Recommended edge types:

```text
parent_of
follow_up_of
supports
contradicts
refines
generalizes
specializes
method_control_for
negative_control_for
replicates
fails_to_replicate
shares_artifact_with
shares_mechanism_with
```

### 6.2 Example Graph

```text
H-MIG01: Glucose-HR coupling increases with diabetes severity
  -> refined_by H-NEW01: timescale-selective coupling
  -> follow_up H-NEW02: causal direction asymmetry
  -> follow_up H-NEW03: post-excursion HR recovery
  -> follow_up H-NEW17: circadian flattening

H-NEW01: timescale-selective coupling
  -> supports PROGRAM_DYNAMIC_COUPLING_RIGIDITY
  -> follow_up CAND: fast-band coupling as autonomic buffering score

H-MIG05: coupling features predict retinal/cardiac damage
  -> refuted
  -> contradicts simple structural-damage bridge
  -> follow_up CAND: coupling is metabolic/autonomic state, not structural damage
```

### 6.3 Graph Use Cases

The graph should support these queries:

```text
What hypotheses support the dynamic coupling rigidity program?
Which hypotheses were refuted because of missing data?
Which candidates came from a specific surprise?
What follow-up hypotheses should be executed after H-NEW10?
Which papers support hypotheses about autonomic neuropathy?
Which hypotheses require CGM + wearable but not retinal data?
Which findings depend on HbA1c as both covariate and target?
```

## 7. Knowledge Retrieval

### 7.1 Retrieval Requirements

The system needs both structured and semantic retrieval.

Structured retrieval:

```text
topic = "second_generation_clock"
modality contains "CGM"
method = "transfer_entropy"
dataset access_status = "public"
hypothesis status = "refuted"
evidence_level >= E3
```

Semantic retrieval:

```text
"glucose heart rate coupling autonomic neuropathy"
"aging clock trained on frailty instead of chronological age"
"activity bout glucose recovery insulin resistance wearable CGM"
```

### 7.2 Practical First Version

Use simple local files plus SQLite:

```text
hypothesis_driven/knowledge/
  papers.jsonl
  tools.jsonl
  datasets.jsonl
  claims.jsonl
  links.jsonl
  retrieval_index.sqlite
```

`retrieval_index.sqlite` can use SQLite FTS5 for text search over titles,
abstract-like summaries, extracted claims, tool descriptions, and dataset
limitations.

Embeddings can be added later if needed, but FTS5 plus structured tags is
enough for a robust first version.

### 7.3 Retrieval API

Proposed module:

```text
hypothesis_driven/retrieval.py
```

Proposed functions:

```python
search_papers(query: str, tags: list[str] | None = None, limit: int = 10)
search_claims(query: str, tags: list[str] | None = None, limit: int = 10)
search_tools(task: str, modality: str | None = None, limit: int = 10)
search_datasets(required_modalities: list[str], outcomes: list[str])
related_hypotheses(text: str, status: str | None = None, limit: int = 10)
retrieve_context_for_candidate(candidate_id: str)
retrieve_context_for_hypothesis(hypothesis_id: str)
```

### 7.4 Retrieval Output Contract

Agents should receive compact context, not entire papers or huge result tables.

Example:

```json
{
  "query": "activity glucose recovery insulin resistance",
  "hypotheses": [
    {
      "id": "H-NEW10",
      "status": "validated",
      "title": "Activity-glucose coupling direction reverses between exercise and recovery phases",
      "relevance": 0.91
    }
  ],
  "claims": [
    {
      "claim_id": "CLAIM-...",
      "text": "Post-exercise glucose response can vary by insulin sensitivity and activity intensity.",
      "paper_id": "PAPER-...",
      "confidence": 0.8
    }
  ],
  "tools": [
    {
      "tool_id": "TOOL-...",
      "name": "event-aligned mixed effects model",
      "known_failure_modes": ["time-of-day confounding", "activity intensity confounding"]
    }
  ],
  "constraints": [
    "No meal timing in AI-READI.",
    "Medications are redacted.",
    "Garmin HR is not beat-to-beat."
  ]
}
```

## 8. Agent Responsibilities In Detail

### 8.1 Literature / Dataset / Tool Scout

Purpose:

Collect reusable external knowledge before agents propose or execute analyses.

Inputs:

- user topic
- candidate hypothesis
- registered hypothesis
- failed analysis
- surprise record

Outputs:

- `papers.jsonl`
- `claims.jsonl`
- `tools.jsonl`
- `datasets.jsonl`
- links from evidence to hypotheses

Questions it must answer:

```text
Is this idea already known?
What is the closest published evidence?
What labels/outcomes were used?
What methods were used?
What tools can implement the method?
What external datasets could validate it?
What limitations or contradictions are known?
Does literature suggest the hypothesized direction is plausible?
```

Rules:

- Prefer primary papers and official tool documentation.
- Store provenance for every claim.
- Mark whether only abstract was read or full text was inspected.
- Do not store long copyrighted text.
- Extract concise claims, methods, limitations, and dataset names.
- Record uncertainty.

Example trigger:

```text
Candidate: Train second-generation aging clock on allostatic load.

Scout retrieval/deposit:
  - PhenoAge paper
  - GrimAge paper
  - DunedinPACE paper
  - KDM/BioAge methods
  - frailty/allostatic load literature
  - NHANES as possible external clinical validation dataset
  - leakage warning: if allostatic-load inputs are used as predictors, the task
    becomes formula replication
```

### 8.2 Data Profiler Agent

Purpose:

Ground each candidate in the actual local AI-READI artifacts.

Checks:

- modality coverage
- feature availability
- target availability
- split availability
- missingness
- group/site/age balance
- time-series overlap
- expected sample size after joins
- known unit caveats
- local artifact paths

Outputs:

```text
feasibility profile:
  required data exists / missing
  expected n
  missingness by split and group
  failure risks
  recommended fallback
```

Example:

```text
Candidate requires PhenoAge.

Profiler:
  albumin: available
  creatinine: available
  glucose: available
  CRP: available
  MCV: available
  RDW: available
  ALP: available as alk_phos
  WBC: available
  lymphocyte percent: not available

Verdict:
  canonical PhenoAge blocked; modified PhenoAge possible but should be labeled
  non-canonical. Prefer KDM/allostatic/frailty for first second-generation proxy.
```

### 8.3 Proposer Agent

Purpose:

Generate candidate hypotheses with mechanism, direction, timescale, controls,
and expected artifacts.

Allowed sources:

- literature claims
- existing supported hypotheses
- refuted hypotheses
- current result tables
- model failures
- human notes
- unsolved project goals

Output:

`HypothesisCandidate` records, not directly registered hypotheses.

Quality requirements:

- specific direction
- timescale or event window when relevant
- required data
- primary outcome
- confounders
- negative controls
- leakage risks
- refutation criterion
- why AI-READI is uniquely useful

### 8.4 Surprise Miner Agent

Purpose:

Continuously scan artifacts for unexpected but actionable patterns.

Inputs:

- `results/**/*.csv`
- `results/**/*.json`
- selected parquet metadata
- JEPA summaries
- clock performance tables
- coupling tables
- hypothesis result tables

Surprise classes:

```text
model_failure
direction_flip
split_instability
modality_domination
negative_control_failure
unexpected_null
unexpected_strong_signal
subgroup_heterogeneity
result_doc_mismatch
artifact_missing
```

Examples from current workspace:

```text
1. Recommended-split no-clipping all-feature clock fails catastrophically.
   Candidate: out-of-distribution modality/features drive extrapolation failure.

2. Retinal embeddings are high-dimensional and dominate summed coefficient mass.
   Candidate: retinal embeddings capture a broad structural aging axis but need
   leave-one-modality-out and permutation contribution tests.

3. Coupling predicts insulin-vs-healthy but not retinal/cardiac structural damage.
   Candidate: coupling reflects metabolic/autonomic state more than structural
   retinal/cardiac damage.

4. Sequence JEPA age/severity remains strong when sequences are shuffled but
   static modalities remain.
   Candidate: supervised age/severity heads are static shortcuts, not temporal
   physiology objectives.

5. Window JEPA aligned loss beats wrong-day and participant-shuffle controls.
   Candidate: short-window temporal synchrony contains real physiological
   coordination signal.
```

### 8.5 Critic Agent

Purpose:

Prevent weak, leaky, confounded, or biologically implausible candidates from
becoming executable hypotheses.

Critic dimensions:

```text
biological_plausibility
statistical_rigor
data_feasibility
negative_controls
confounding_plan
leakage_plan
novelty
importance
reproducibility
scope_control
```

Common hard stops:

- requires sex-specific formula with no sex variable
- claims medication effect despite redacted medication details
- claims meal effects without meal timing
- uses target-defining variables as predictors without labeling formula
  replication
- chooses test transformations based on test labels
- makes causal language from cross-sectional observational data
- ignores site, age, or study-group confounding
- lacks negative controls for temporal coupling

Output:

```json
{
  "candidate_id": "CAND-...",
  "decision": "revise",
  "scores": {
    "biological_plausibility": 0.8,
    "statistical_rigor": 0.5,
    "data_feasibility": 0.9,
    "negative_controls": 0.3,
    "leakage_plan": 0.4
  },
  "blocking_concerns": [
    "Target leakage mask is not specified."
  ],
  "required_revisions": [
    "List all target-defining input features and exclude them from the leakage-controlled model."
  ]
}
```

### 8.6 Feasibility Agent

Purpose:

Turn a candidate into a data-grounded execution estimate.

Checks:

- local artifact existence
- row counts
- modality coverage
- target non-null count
- split counts
- by-site and by-group coverage
- time-series overlap
- compute cost
- whether Slurm is needed

Output:

```text
feasible
feasible_with_modification
blocked
```

### 8.7 Methods Agent

Purpose:

Translate a candidate into an executable test plan.

The Methods Agent should specify:

- target
- predictors
- leakage mask
- split column
- preprocessing plan
- covariates
- primary model or statistical test
- sensitivity models
- negative controls
- metrics
- decision rule
- artifact names
- expected runtime
- whether the test is exploratory, confirmatory, or diagnostic

For second-generation clocks, the Methods Agent must produce both:

```text
formula-replication upper bound:
  allows target-defining variables

leakage-controlled discovery model:
  excludes target-defining variables
```

### 8.8 Registrar / Memory Agent

Purpose:

Own the state machine and prevent the workspace from becoming cluttered.

Responsibilities:

- create stable IDs
- prevent duplicate hypotheses
- register candidates only after gates pass
- link parents and children
- link papers/tools/datasets/claims
- update evidence level
- archive rejected or duplicate candidates
- maintain graph integrity
- update summary indexes

Registration rules:

```text
A candidate can become a registered hypothesis only if:
  - it has a clear mechanism
  - it has a primary test
  - it has a feasibility profile
  - it has a critic review
  - it has a leakage/confounding plan
  - it has at least one negative control or a documented reason none is possible
  - it has provenance
```

### 8.9 Executor Agent

Purpose:

Run the approved method plan and write reproducible run records.

Execution modes:

```text
local_python
slurm_array
slurm_single_job
report_only
dry_run
```

Executor requirements:

- record git commit
- record exact command
- record input artifacts
- record output artifacts
- record split column
- do not overwrite canonical artifacts unless explicitly intended
- use suffixed artifact names for variants
- never silently clip, filter, or transform without recording the method

### 8.10 Verifier Agent

Purpose:

Check whether the result supports the hypothesis.

Mechanical checks:

```text
1. Input artifacts exist and match expected schema.
2. Split column exists and has train/val/test where required.
3. Preprocessing was fit without test rows.
4. Target-defining variables were excluded for leakage-controlled analyses.
5. Covariates include required age/site/group/HbA1c/BMI where relevant.
6. Negative controls ran and behaved as expected.
7. Multiple testing correction was applied where needed.
8. Sensitivity checks agree or disagreement is explained.
9. Result files are readable and row counts match expectations.
10. The conclusion language matches the design: association, prediction,
    proxy, or causal claim.
```

Evidence levels:

```text
E0: idea only
E1: data feasible
E2: association or model result found
E3: survives covariates, FDR, and negative controls
E4: held-out predictive value or robust ablation value within AI-READI
E5: externally replicated or longitudinally validated
```

### 8.11 Synthesis Agent

Purpose:

Convert verified records into human-readable outputs.

Outputs:

- short finding summaries
- next-round recommendations
- paper-style result notes
- slide/deck tables
- status doc updates
- hypothesis graph summaries

Rules:

- Use only verified artifacts for strong claims.
- Clearly label exploratory, sensitivity, diagnostic, and failed results.
- Avoid SOTA or causal claims unless evidence level supports them.

## 9. Scientific Programs

The hypothesis graph should be organized into programs. Programs are not single
hypotheses; they are clusters of related hypotheses and evidence.

### 9.1 Program A: Dynamic Coupling And Rigidity

Core idea:

Diabetes and aging reduce flexible physiological coordination. The body becomes
more rigid, less adaptive, or pathologically coupled.

Current related hypotheses:

- H-MIG01: glucose-HR coupling increases with diabetes severity
- H-MIG02: glucose-activity coupling shifts with diabetes severity
- H-MIG03: coupling features predict insulin-dependent diabetes
- H-MIG04: coupling features link to clinical burden
- H-NEW01: coupling is timescale-selective
- H-NEW17: diurnal coupling rhythm flattening

Next candidates:

- coupling instability predicts frailty
- fast-band coupling reflects autonomic buffering
- slow-band coupling reflects metabolic rigidity
- day-to-day coupling flexibility declines with burden

### 9.2 Program B: Perturbation And Recovery

Core idea:

Aging and diabetes show up in response dynamics after events, not only in
baseline levels.

Current related hypotheses:

- H-NEW03: post-excursion HR recovery
- H-NEW10: activity-glucose direction and recovery
- H-NEW13: sleep-wake transition reorganization

Next candidates:

- recovery from glucose excursions is slower with diabetes severity
- activity bouts reveal hidden glycemic instability
- sleep-wake transitions expose autonomic switching impairment
- dawn-window physiology differs by disease stage

### 9.3 Program C: Second-Generation Aging Phenotypes

Core idea:

Chronological age is a useful benchmark, but the meaningful target is biological
burden, disease risk, resilience, or healthspan proxy.

Targets currently available:

- frailty index
- allostatic load
- homeostatic dysregulation
- KDM age acceleration
- HbA1c
- HOMA-IR
- TyG
- study-group severity

Required guardrail:

Every target needs a leakage mask. If the target is computed from clinical
variables, a leakage-controlled model must exclude those variables.

Initial tests:

- clinical upper-bound model
- leakage-controlled multimodal model
- modality-only models
- leave-one-modality-out models
- permutation contribution
- split sensitivity

### 9.4 Program D: Multiorgan Aging Axes

Core idea:

There is not one aging axis. Retinal, cardiac, metabolic, inflammatory,
cognitive, sleep, circadian, and coupling dimensions may diverge.

Current related artifacts:

- per-system clocks
- retinal and cardiac age accelerations
- concordance matrix
- aging subtype table
- diabetes gradient table

Next candidates:

- retinal age captures vascular/neural axis distinct from metabolic burden
- ECG/cardiac age captures autonomic/electrophysiologic aging
- coupling age captures dynamic resilience rather than structural damage
- subtype membership predicts disease burden beyond chronological age

### 9.5 Program E: Foundation Model Objective Discovery

Core idea:

JEPA and foundation-model objectives should be chosen to avoid static shortcuts
and to learn synchronized temporal physiology.

Current lessons:

- participant and sequence age/severity heads can be dominated by static
  clinical/imaging shortcuts
- window-level aligned JEPA losses beat wrong-day and participant-shuffle
  controls

Next candidates:

- event-window JEPA improves recovery phenotype prediction
- masked modality prediction learns coupling states
- static-to-dynamic alignment should be secondary and explicitly controlled
- representation quality should be tested on second-generation burden targets,
  not only chronological age

## 10. Initial Implementation Milestones

### Milestone 0: Protect Current State

Goal:

Do not break the existing hypothesis system while extending it.

Tasks:

- keep existing `hypothesis_driven/hypotheses/H-*.json`
- keep existing `hypothesis_driven/README.md`
- add new schema fields in backward-compatible way
- add migration utilities rather than hand-editing all old files at once
- make all new commands support `--dry-run`

Definition of done:

- existing hypothesis summary still loads
- no existing hypothesis file is invalidated
- old proposer/critic/executor/verifier code can still run or fails with a
  clear migration message

### Milestone 1: Add Registry Directories And Schemas

New files/modules:

```text
hypothesis_driven/registry.py
hypothesis_driven/retrieval.py
hypothesis_driven/knowledge.py
hypothesis_driven/candidates.py
hypothesis_driven/graph.py
```

New directories:

```text
hypothesis_driven/candidates/
hypothesis_driven/knowledge/
hypothesis_driven/runs/
```

New schemas:

- `HypothesisCandidate`
- `PaperRecord`
- `ExtractedClaim`
- `ToolRecord`
- `DatasetRecord`
- `SurpriseRecord`
- `ExecutionRun`
- `VerificationRecord`
- `HypothesisEdge`

Definition of done:

- can create and list candidate records
- can create and list paper/tool/dataset records
- can link a paper or tool to a candidate
- all records validate before writing

### Milestone 2: Implement Retrieval

First version:

- JSONL persistence
- SQLite FTS5 index
- structured tag filters
- `retrieve_context_for_candidate()`
- `retrieve_context_for_hypothesis()`

CLI examples:

```bash
python -m hypothesis_driven.knowledge index
python -m hypothesis_driven.knowledge search "glucose HR coupling autonomic neuropathy"
python -m hypothesis_driven.knowledge related H-NEW10
```

Definition of done:

- retrieval returns relevant hypotheses, papers, claims, tools, datasets, and
  constraints
- retrieval output is short enough to fit in agent context
- each retrieved item includes ID and provenance

### Milestone 3: Implement Candidate Deposit

Deposit sources:

- human idea
- literature scout
- surprise miner
- critic objection
- failed analysis
- result table
- model residual pattern

CLI examples:

```bash
python -m hypothesis_driven.candidates deposit \
  --origin human \
  --title "Leakage-controlled second-generation clock" \
  --claim "Multimodal physiology predicts frailty beyond target-defining clinical variables."

python -m hypothesis_driven.candidates list --status candidate
python -m hypothesis_driven.candidates show CAND-20260514-0001
```

Definition of done:

- human can deposit a candidate from CLI
- agent can deposit a candidate from a surprise or paper
- candidate gets a stable ID
- candidate stores origin and trigger artifacts

### Milestone 4: Add Scout, Critic, Feasibility, And Methods Gates

Workflow:

```text
candidate
  -> scout enriches with papers/tools/datasets
  -> critic reviews
  -> feasibility checks local data
  -> methods agent writes test plan
  -> registrar decides whether to register
```

CLI examples:

```bash
python -m hypothesis_driven.run_candidate CAND-20260514-0001 --stage enrich
python -m hypothesis_driven.run_candidate CAND-20260514-0001 --stage critic
python -m hypothesis_driven.run_candidate CAND-20260514-0001 --stage feasibility
python -m hypothesis_driven.run_candidate CAND-20260514-0001 --stage methods
python -m hypothesis_driven.run_candidate CAND-20260514-0001 --stage register
```

Definition of done:

- no candidate can register without a critic review and feasibility profile
- registered hypothesis includes test plan and decision rule
- duplicate detection checks existing hypotheses and candidates

### Milestone 5: Surprise Miner

First target artifacts:

```text
results/clocks/*performance*.csv
results/coupling/*performance*.csv
results/coupling/*damage*.csv
results/hypotheses/*.csv
foundation_jepa/**/summary.csv
foundation_jepa/**/summary.json
```

Initial surprise detectors:

- large train/val/test performance gap
- negative test R2 after good validation R2
- sensitivity result much better than primary
- feature/modality coefficient domination
- direction flip across timescales
- negative control better than aligned run
- unexpected null where prior hypothesis predicted strong effect
- report metric disagrees with current artifact

CLI example:

```bash
python -m hypothesis_driven.surprise scan --write-candidates
```

Definition of done:

- scan writes `SurpriseRecord` files
- high-priority surprises deposit candidate hypotheses
- surprise records link to trigger artifacts

### Milestone 6: Execution And Verification Integration

Executor should run only registered hypotheses with method plans.

Verifier should write a `VerificationRecord` and update evidence level.

CLI examples:

```bash
python -m hypothesis_driven.rounds run --max-actions 1
python -m hypothesis_driven.rounds run --action execute --hypothesis H-NEW10
python -m hypothesis_driven.rounds run --action verify --run RUN-20260514-0001
```

Definition of done:

- run metadata is saved before execution
- output artifacts are registered after execution
- verifier can mark supported/refuted/inconclusive
- verifier can deposit follow-up candidates

### Milestone 7: First Scientific Use Case

Recommended first use case:

```text
Leakage-controlled second-generation phenotypic aging clock
```

Why:

- strategically important
- immediately available data
- directly addresses current project direction
- forces implementation of leakage masks and modality ablations
- produces a clear example of candidate -> registered hypothesis -> execution
  -> verification -> follow-up

Expected hypotheses:

```text
H-SG01:
  Multimodal physiology predicts frailty index beyond target-defining clinical
  variables.

H-SG02:
  Dynamic coupling features add incremental value for allostatic load beyond
  static clinical burden.

H-SG03:
  Retinal embeddings contribute to homeostatic dysregulation prediction through
  a structural aging axis distinct from glucose burden.
```

Required analyses:

- target leakage maps
- target availability summary
- clinical upper-bound model
- leakage-controlled all-modality model
- modality-only models
- leave-one-modality-out models
- permutation importance by modality
- split sensitivity
- clipped vs unclipped sensitivity only if explicitly labeled

Definition of done:

- second-generation clock results are not confused with chronological age clock
- every target has an input exclusion mask
- result table includes both upper-bound and leakage-controlled models
- verifier produces evidence levels and next hypotheses

## 11. CLI Surface

The CLI should expose small, composable actions.

### 11.1 Knowledge Commands

```bash
python -m hypothesis_driven.knowledge add-paper --doi DOI --topic aging_clock
python -m hypothesis_driven.knowledge add-tool --name PCMCI --category time_series_causal_discovery
python -m hypothesis_driven.knowledge add-dataset --name NHANES
python -m hypothesis_driven.knowledge index
python -m hypothesis_driven.knowledge search "frailty allostatic load aging clock"
```

### 11.2 Candidate Commands

```bash
python -m hypothesis_driven.candidates deposit --origin human --title TITLE --claim CLAIM
python -m hypothesis_driven.candidates list
python -m hypothesis_driven.candidates show CAND-ID
python -m hypothesis_driven.candidates enrich CAND-ID
python -m hypothesis_driven.candidates critique CAND-ID
python -m hypothesis_driven.candidates feasibility CAND-ID
python -m hypothesis_driven.candidates plan CAND-ID
python -m hypothesis_driven.candidates register CAND-ID
```

### 11.3 Graph Commands

```bash
python -m hypothesis_driven.graph show H-NEW10
python -m hypothesis_driven.graph children H-MIG01
python -m hypothesis_driven.graph program dynamic_coupling
python -m hypothesis_driven.graph export --format mermaid
```

### 11.4 Round Commands

```bash
python -m hypothesis_driven.rounds status
python -m hypothesis_driven.rounds run --max-actions 1
python -m hypothesis_driven.rounds run --program second_generation_clock --max-actions 3
python -m hypothesis_driven.rounds verify-pending
python -m hypothesis_driven.rounds mine-surprises
```

## 12. Human Interface

The system should make human ideas easy to deposit without losing structure.

Minimal markdown-to-candidate format:

```markdown
# Candidate: Activity-glucose recovery and diabetes severity

Origin: human
Program: perturbation_recovery

Claim:
After activity bouts, glucose recovery is delayed in diabetes.

Mechanism:
Insulin resistance and impaired metabolic flexibility slow return to baseline.

Required data:
CGM, wearable activity, study group, age, site, BMI, HbA1c.

Negative controls:
Random non-activity windows matched by time of day.

Refutation:
No monotonic severity trend or direction opposite after adequate QC.
```

The Registrar should parse this into a candidate JSON file and mark missing
fields for later enrichment.

## 13. Guardrails Specific To AI-READI

These constraints should be loaded into every relevant agent context.

### 13.1 Hard Dataset Constraints

- Public demographic fields are limited; sex-specific formulas are unsupported
  unless a validated sex variable becomes available.
- Medication details are redacted; do not infer medication-regimen effects.
- Meal timing is not available; do not attribute glucose excursions to meals
  without caveats.
- AI-READI is cross-sectional at participant visit level; 10-day monitoring
  supports within-person temporal analysis but not long-term disease trajectory.
- Garmin HR is not beat-to-beat; avoid sub-minute autonomic claims.
- Site confounding is real; site adjustment or site sensitivity should be
  considered by default.

### 13.2 Clock-Specific Guardrails

- Chronological age clocks are first-generation benchmarks.
- Second-generation proxy clocks must be labeled as proxy if they target
  frailty, allostatic load, homeostatic dysregulation, or disease burden rather
  than mortality or longitudinal pace.
- Canonical PhenoAge is blocked unless lymphocyte percentage becomes available
  or a modified non-canonical version is explicitly labeled.
- Target-defining variables must be excluded from leakage-controlled models.
- Clipping and winsorization must be explicit sensitivity analyses.

### 13.3 Foundation Model Guardrails

- Age/severity heads can become static shortcuts.
- Static-only and sequence-shuffled controls are required before claims about
  synchronized temporal physiology.
- Window-level aligned runs should be compared against wrong-day and
  participant-shuffle controls.
- JEPA representation quality should be tested against mechanistic downstream
  tasks, not only chronological age.

## 14. Priority Backlog

### P0: Registry And Candidate Infrastructure

Reason:

Without this, new ideas remain in chat or markdown and cannot feed future
rounds.

Deliverables:

- candidate schema
- paper/tool/dataset/claim schema
- JSONL persistence
- CLI deposit/list/show
- docs update

### P1: Retrieval For Candidate Context

Reason:

Agents should retrieve relevant hypotheses, papers, tools, datasets, and
constraints before proposing or criticizing.

Deliverables:

- SQLite FTS index
- `retrieve_context_for_candidate`
- `retrieve_context_for_hypothesis`
- compact retrieval report

### P2: Registrar And Graph Edges

Reason:

The system needs provenance, parent/child relationships, and duplicate control.

Deliverables:

- graph edge schema
- duplicate detection
- register candidate -> hypothesis
- graph export

### P3: Leakage-Controlled Second-Generation Clock Program

Reason:

This is the highest-value first scientific program and stress-tests the entire
agentic workflow.

Deliverables:

- target definitions
- leakage masks
- modality ablations
- verified result artifacts
- follow-up candidate generation

### P4: Surprise Miner

Reason:

This creates autonomous follow-up hypotheses from result artifacts.

Deliverables:

- clock surprise detectors
- coupling surprise detectors
- JEPA surprise detectors
- candidate deposition

### P5: Round Runner

Reason:

The system should run controlled discovery rounds.

Deliverables:

- `rounds status`
- `rounds run --max-actions`
- pending verification queue
- round summary JSON

## 15. Example End-To-End Round

### 15.1 Human Deposits Idea

```bash
python -m hypothesis_driven.candidates deposit \
  --origin human \
  --program second_generation_clock \
  --title "Leakage-controlled multimodal frailty clock" \
  --claim "Retinal, ECG, wearable, CGM, and environment features predict frailty beyond target-defining clinical variables."
```

Creates:

```text
hypothesis_driven/candidates/CAND-20260514-0001.json
```

### 15.2 Scout Enriches Candidate

Scout retrieves and deposits:

- frailty index literature
- second-generation aging clock literature
- AI-READI feature constraints
- external validation dataset candidates
- methods for leakage-controlled prediction and ablation

Candidate status:

```text
candidate -> enriched
```

### 15.3 Critic Reviews

Critic flags:

- frailty target includes BMI, HbA1c, depression, cognition, neuropathy, vision,
  and clinical conditions
- leakage-controlled model must exclude those inputs
- retinal vision variables used in frailty definition must be separated from
  retinal image embeddings
- age must be handled carefully if target is age-associated burden

Candidate status:

```text
enriched -> critiqued
```

### 15.4 Feasibility Agent Checks Data

Feasibility profile:

- frailty index available for 2,280 participants
- retinal embeddings available for 2,274
- cardiac embeddings available for 2,251
- balanced split available
- target-defining variables can be masked

Candidate status:

```text
critiqued -> feasible
```

### 15.5 Methods Agent Writes Plan

Plan:

- target: `frailty_index`
- split: `balanced_split_v1`
- models:
  - upper-bound clinical formula replication
  - leakage-controlled all-modality model
  - retinal only
  - cardiac only
  - dynamic summaries only
  - all except retinal
  - all except cardiac
  - all except dynamic
- metrics: R2, MAE, Pearson/Spearman, calibration by group
- controls: shuffled target, site-stratified performance
- artifacts:
  - `results/second_generation/frailty_clock_performance.csv`
  - `results/second_generation/frailty_clock_modality_ablation.csv`
  - `results/second_generation/frailty_clock_feature_importance.csv`

Candidate status:

```text
feasible -> method_planned
```

### 15.6 Registrar Registers Hypothesis

Creates:

```text
hypothesis_driven/hypotheses/H-SG01.json
```

Candidate status:

```text
method_planned -> registered
```

Hypothesis status:

```text
queued
```

### 15.7 Executor Runs

Executor records:

```text
hypothesis_driven/runs/RUN-20260514-0001.json
```

Hypothesis status:

```text
queued -> executing -> completed
```

### 15.8 Verifier Checks

Verifier tests:

- leakage mask applied
- split respected
- negative controls run
- target shuffled model near null
- no test preprocessing leakage
- modality ablation table present
- conclusions match evidence

Hypothesis status:

```text
completed -> supported/refuted/inconclusive
```

Evidence level:

```text
E4 if held-out predictive value survives leakage masks and controls
E3 if association survives controls but prediction is weak
E2 if only exploratory association is present
```

### 15.9 Follow-Up Candidates

If supported:

```text
CAND: retinal embeddings predict frailty through vascular aging axis
CAND: dynamic coupling improves frailty prediction beyond static clinical burden
CAND: second-generation burden representation predicts diabetes severity
```

If refuted:

```text
CAND: frailty in AI-READI is primarily formula-defined clinical burden and not
captured by imaging or dynamic physiology after leakage control
```

Either way, the round produces new structured hypotheses.

## 16. Documentation Outputs

The implementation should update docs without making stale claims.

Recommended docs:

```text
docs/reference/HYPOTHESIS_REGISTRY.md
docs/reference/KNOWLEDGE_REGISTRY.md
docs/design/HYPOTHESIS_FIRST_AGENTIC_IMPLEMENTATION.md
docs/CURRENT_STATUS.md
```

Generated human summaries should be clearly labeled:

```text
docs/reports/hypothesis_rounds/round_YYYYMMDD.md
docs/reports/hypothesis_rounds/round_YYYYMMDD.json
```

Each round summary should include:

- candidates created
- hypotheses registered
- runs executed
- verification outcomes
- evidence-level changes
- surprises detected
- next queue

## 17. What Not To Do

- Do not let the system generate unsupported claims directly into reports.
- Do not allow literature notes without source IDs.
- Do not let candidates become hypotheses without critic and feasibility checks.
- Do not use target-defining inputs in leakage-controlled models.
- Do not overwrite canonical result artifacts with sensitivity runs.
- Do not make mortality or healthspan claims from cross-sectional proxy targets.
- Do not treat JEPA age performance as proof of temporal physiology.
- Do not use ignored local deck files as source of truth.

## 18. Immediate Next Engineering Tasks

If implementing this now, the first concrete tasks should be:

1. Add `HypothesisCandidate`, `PaperRecord`, `ToolRecord`, `DatasetRecord`,
   `ExtractedClaim`, `SurpriseRecord`, `ExecutionRun`, and `HypothesisEdge`
   schemas in `hypothesis_driven/schemas.py` or a new
   `hypothesis_driven/registry_schemas.py`.

2. Add persistence helpers:

   ```text
   hypothesis_driven/registry.py
   hypothesis_driven/candidates.py
   hypothesis_driven/knowledge.py
   hypothesis_driven/graph.py
   ```

3. Add directories:

   ```text
   hypothesis_driven/candidates/
   hypothesis_driven/knowledge/
   hypothesis_driven/runs/
   ```

4. Add CLI commands for:

   ```text
   candidates deposit/list/show
   knowledge add/search/index
   graph show/export
   ```

5. Seed the knowledge registry with project-specific constraints already known
   from `results/agent_memory/constraints.json` and docs:

   - sex redacted
   - medication details redacted
   - no meal timing
   - cross-sectional visit design
   - 10-day time-series window
   - Garmin HR resolution
   - site confounding
   - insulin unit conversion caveat
   - canonical PhenoAge blocked by missing lymphocyte percentage

6. Deposit first human candidate:

   ```text
   Leakage-controlled second-generation phenotypic aging clock
   ```

7. Build the first Methods Agent plan for that candidate.

8. Implement the second-generation clock script only after the candidate has a
   leakage mask and method plan.

## 19. Success Criteria

The upgraded system is successful when:

- A new human idea can be deposited as a candidate in one command.
- The system can retrieve related papers, tools, datasets, constraints, and old
  hypotheses before acting.
- A candidate cannot become executable without critic, feasibility, and method
  records.
- A completed run always leaves behind run metadata, result artifacts, and a
  verification record.
- Surprising results automatically create follow-up candidates with provenance.
- The hypothesis graph can answer why a hypothesis exists, what it depends on,
  what it supports, what refuted it, and what should be tested next.
- Reports are generated from verified records rather than from memory or loose
  prose.

The final product should feel less like a collection of analyses and more like
a living scientific operating system for multimodal aging discovery.
