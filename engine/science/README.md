# Scripts Layout

The root `scripts/` package contains stable analysis infrastructure and core
participant-level pipelines. Specialized or generated workflows live in
subpackages.

## Core Root Scripts

- `participants.py`, `participant_index.py`, `features.py`: participant and
  clinical feature tables.
- `aging_scores.py`, `aging_features_batch.py`, `aging_clocks.py`,
  `cross_dimensional.py`, `unified_clock.py`: aging-score and aging-clock
  analyses.
- `retinal_age.py`, `cardiac_age.py`: imaging/ECG foundation-model clocks.
- `causal_analysis.py`, `biomarker_prediction.py`, `cohort.py`: statistical
  and biomarker analyses.
- `multimodal.py`: lazy multimodal participant accessor.
- `loaders/`, `utils/`: shared loading and utility modules.

## Subpackages

- `coupling/`: physiological coupling, coupling atlas, coupling prediction, and
  cross-modal predictability scripts.
- `hypothesis/`: hypothesis-specific sharded feature extraction and
  postprocessing scripts. The end-to-end Phase 2 Slurm launcher is
  `scripts/hypothesis/run_hypothesis_pipeline.sh`.
- `reporting/`: deck, figure, and report-generation scripts.

Use module execution from the repository root, for example:

```bash
python -m scripts.coupling.coupling_features --limit 50
python -m scripts.hypothesis.hypothesis_timeseries --limit 10
python -m scripts.reporting.build_jepa_results_figures
bash scripts/hypothesis/run_hypothesis_pipeline.sh
```
