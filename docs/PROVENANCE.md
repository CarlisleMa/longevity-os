# Provenance

`engine/` and `docs/research_engine/` are a **curated copy** of the AI-READI research workspace.
This file records exactly what was copied, from where, so you can pull fixes later and so the
boundary between "research engine" and "new product" stays clear.

## Source

- **Repo:** `git@github.com:CarlisleMa/aireadi.git`
- **Local path:** `/oak/stanford/scg/lab_twc/mazijian/aireadi`
- **Commit:** `1530e4c8a9031272bcdb196bed23c8a6186499ea` — *"Add guarded execution workflow and JEPA updates"* (2026-05-21)
- **Copied:** 2026-06-04

## What was copied

| LongevityOS path | AI-READI source | Contents |
| --- | --- | --- |
| `engine/foundation_model/` | `foundation_jepa/` | JEPA model/data/train code + READMEs (participant, sequence, window, window_v2). **Artifacts, caches, checkpoints, logs excluded.** |
| `engine/agentic/agentic_discovery/` | `agentic_discovery/` | Claude-SDK discovery framework, guarded tools, reviewer gates, schemas, store, retrieval. **`*.sqlite` index and run logs excluded.** |
| `engine/agentic/agents/` | `agents/` | Modality + reasoning agents, orchestrator, critic, memory, task pipelines. |
| `engine/hypothesis/` | `hypothesis_driven/` | Proposer/critic/executor/verifier + **27 stored hypotheses** (`hypotheses/*.json`) + `results/critic_verdicts.json`. |
| `engine/science/` | `scripts/` | Loaders, feature formulas, coupling, aging-clock scoring, utils, reporting. |
| `engine/neuro/` | `neuro_moca_mapping/` | Eye–brain–metabolism (MoCA) mapping direction (was uncommitted in AI-READI). |
| `docs/research_engine/` | `docs/**/*.md` | Design docs, JEPA summaries, current status, references. **Markdown only** (images/decks/pptx excluded). |

## What was deliberately NOT copied

- **AI-READI participant data** (`data` symlink → the dataset). Forbidden by the data use
  agreement. LongevityOS uses synthetic demo users and the user's own uploads.
- **Model weights** (`models/`, ~2.7 GB: RETFound, ECGFounder). Local-only; referenced via
  `model_artifacts/` and gitignored. Copy them into `model_artifacts/weights/` locally to enable
  Scoring-live mode.
- **Generated artifacts / caches / checkpoints / logs** (gitignored in AI-READI too).
- **SLURM batch configs** and cohort-scale reporting — not needed for a single-user app.

## Pulling updates from AI-READI later

The copy is a one-way snapshot, not a live link. To refresh a module after AI-READI changes:

```bash
SRC=/oak/stanford/scg/lab_twc/mazijian/aireadi
DST=/oak/stanford/scg/lab_twc/mazijian/LongevityOS
EXCL="--exclude=__pycache__ --exclude=*.pyc --exclude=artifacts --exclude=logs --exclude=*.sqlite --exclude=*.pth"
rsync -a $EXCL "$SRC"/foundation_jepa/ "$DST"/engine/foundation_model/   # example: refresh FM code
```

Then bump the commit hash recorded above. Prefer refreshing whole modules over cherry-picking
files, so the provenance stays accurate.

## License / attribution note

The research engine code originated in the AI-READI analysis workspace (author: Carl Ma,
Stanford). Findings were validated on the AI-READI v3.0.0 dataset
([DOI 10.60775/fairhub.3](https://doi.org/10.60775/fairhub.3)). If LongevityOS is published or
demoed publicly, attribute the dataset and keep the "not medical advice" framing.
