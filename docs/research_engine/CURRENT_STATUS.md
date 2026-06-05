# Current Project Status

Date: 2026-04-29

This is the current source-of-truth status for the local repository. Older dated
documents are useful historical snapshots, but this file should be checked first
before an agent or human assumes that a feature is absent, implemented, or ready
for scientific use.

## High-Level Goal

The project is a multimodal, agent-assisted scientific discovery system for
AI-READI. The target is broader than a single aging-clock analysis:

- answer aging, phenotype, and disease-severity questions across clinical,
  CGM, wearable, environment, ECG, and retinal data
- build and compare organ/system aging clocks, including retinal and cardiac
  foundation-model clocks when artifacts are available
- study aging and diabetes as breakdowns in cross-system physiological coupling
- train multimodal representation and foundation-model scaffolds over both
  participant-level summaries and synchronized high-throughput temporal streams
- support autonomous proposal, criticism, execution, and verification of
  hypotheses across discovery rounds

## Dataset Available Locally

The local `data` path is intentionally ignored and expected to point to an
AI-READI v3.0.0 dataset checkout. The project documentation and scripts assume:

- 2,280 participants
- train/validation/test split of 1,576 / 352 / 352
- modalities: clinical OMOP tables, CGM, Garmin wearable streams, environment
  sensors, ECG, retinal OCT/OCTA/photography/FLIO
- public-release limitations: some demographic fields, especially sex, are
  redacted; methods requiring sex-specific formulas must use validated
  non-sex-specific substitutes or be marked unsupported

Generated local artifacts may include feature matrices, age-acceleration
outputs, retinal and ECG embeddings, coupling features, JEPA caches, figures,
and decks. Most generated outputs are ignored by Git.

## Current Implementation

Main analysis scripts:

- `scripts/aging_scores.py`: clinical composite scores.
- `scripts/aging_features_batch.py`: CGM, wearable, environment, and ECG
  participant features.
- `scripts/aging_clocks.py`: system and functional aging clocks.
- `scripts/retinal_age.py` and `scripts/cardiac_age.py`: imaging/ECG
  foundation-model embedding clocks.
- `scripts/cross_dimensional.py` and `scripts/unified_clock.py`: concordance,
  subtype, gradient, and unified-clock analyses.
- `scripts/coupling/`: coupling, coupling-atlas, and cross-modal
  predictability analyses.
- `scripts/hypothesis/`: hypothesis-specific feature extraction and
  postprocessing scripts.
- `scripts/reporting/`: deck, figure, and report-generation scripts.

Agent system:

- `agents/` contains modality agents, reasoning agents, a shared workspace,
  memory, critic, orchestrator, and task pipelines.
- `agents.run --task coupling_atlas` is wired to the coupling atlas task.
- The main agent CLI is still a local trusted-code workflow; it should not be
  treated as a secure sandbox.

Autonomous discovery:

- `hypothesis_driven/` contains a JSON-backed hypothesis workspace plus
  proposer, critic, executor, and verifier components.
- Current hypothesis state has 26 primary `H-*` hypotheses: 5 supported,
  1 refuted, 2 inconclusive, 5 completed with result payloads, 1 validated and
  ready for execution, and 12 critiqued.
- This package is not yet fully unified with the main `agents.run` task system.

Foundation-model scaffolds:

- `foundation_jepa/`: participant-level cross-modal JEPA prototype over existing
  summary tables and pretrained retinal/ECG embeddings.
- `foundation_jepa/sequence/`: 10-day, 5-minute sequence JEPA with missingness
  masks and static-modality encoders.
- `foundation_jepa/window/`: temporal window JEPA with aligned, wrong-day, and
  participant-shuffle controls.

The JEPA stacks are experimental. Source code and Slurm launchers belong in Git;
caches, logs, checkpoints, and generated summaries do not.

## Highest-Risk Fixes Applied On 2026-04-29

- Allostatic load no longer treats missing biomarkers as no-risk flags.
- Per-organ aging-clock outlier clipping and missingness filtering now use only
  training rows.
- Per-organ AgeAccel residualization now fits the age correction on training
  rows only.
- Unified-clock model selection no longer inspects test metrics before final
  retraining and test evaluation.
- Unified-clock AgeAccel residualization now fits on train+validation rows,
  not all rows.
- As of 2026-04-30, the multimodal/unified clock no longer trains from
  residual AgeAccel dimensions. It trains directly from raw numeric feature
  tables plus frozen retinal and ECG embeddings, while residual age gaps remain
  downstream phenotype outputs.
- Alternate split support was added on 2026-04-30. `balanced_split_v1` is a
  deterministic local split stratified by `clinical_site`, `study_group`, and
  coarse age bin while preserving the original `recommended_split`.
- All-feature multimodal-clock outlier clipping is now an explicit
  `--clip-outliers` sensitivity option. The primary run does not silently clip
  test values; raw runs that extrapolate should trigger feature/outlier audit
  rather than be patched without documentation.
- Aging-clock scripts now fail fast if the fixed train/validation/test split is
  missing, malformed, duplicated by index, or too small for evaluation.
- Environment temperature range aggregation now preserves the observed
  timestamp-to-value pairing after timezone conversion.
- JEPA sequence calories now use reset-aware kcal deltas from
  `compute_calorie_timeseries()` instead of nearest raw cumulative calorie
  counter values.
- JEPA sequence cache version was bumped to `sequence_jepa_v2` because calorie
  channel semantics changed.
- Retinal and aging-clock agent prompts no longer claim RETFound/retinal age is
  unimplemented when result artifacts may already exist.
- Coupling-atlas pilot step mapping is deterministic and the task is exposed
  through `agents.run`.

## Guardrails

- Preserve train/validation/test separation for preprocessing, residualization,
  model selection, and evaluation.
- Report negative controls for JEPA and coupling claims before presenting them
  as scientific evidence.
- Treat causal analyses as exploratory unless the method explicitly supports the
  design and confounder structure.
- Do not infer medication-regimen effects from AI-READI public fields when
  medication details are redacted.
- Do not use sex-specific formulas unless a validated input exists in the local
  release.
- Keep generated artifacts out of Git unless there is a deliberate, documented
  reason to version a small curated output.

## Documentation Map

- Current implementation status: this file.
- Documentation index: `docs/README.md`.
- Dataset and loading: `docs/reference/DATA.md`, `docs/reference/LOADING.md`.
- Derived features and caveats: `docs/reference/DERIVED_FEATURES.md`.
- Aging-clock design: `docs/design/STUDY_DESIGN_AGING_CLOCKS.md`.
- Network physiology direction: `docs/design/BRAINSTORM_NETWORK_PHYSIOLOGY.md`.
- Agent system design: `docs/design/AGENT_SYSTEM_BRAINSTORM.md`.
- Hypothesis system design: `docs/design/HYPOTHESIS_DISCOVERY_SYSTEM.md`.
- Dated project reviews and audits are historical snapshots. The stale-status
  audit from 2026-04-27 is archived under `docs/archive/`.
