# Project Direction Review: AI-READI Multimodal Physiology

Date: 2026-04-27

Archive note, 2026-04-29: this review is preserved as a dated project snapshot.
For current repository status and corrected stale documentation claims, use
`docs/CURRENT_STATUS.md`.

Scope: local repository review, local dataset/output inventory, documentation review, implementation audit, and literature-grounded brainstorming for the next scientific direction.

## Executive Take

The strongest direction is to pivot the center of gravity from "static multi-organ aging clocks" to "network physiology of diabetes": how glucose, autonomic/cardiac physiology, sleep, activity, light, air quality, retinal structure, ECG, and clinical chemistry coordinate or decouple across the diabetes severity gradient.

The reason is empirical, not just conceptual. The current static age-acceleration clocks mostly predict chronological age weakly and do not discriminate severe diabetes as well as simple clinical deficit summaries. In contrast, the dataset has an unusually valuable synchronized 10-day window across CGM, wearable, and home environment for more than 2,000 people. That window is the thing AI-READI has that most aging and diabetes datasets do not.

Recommended thesis:

> Type 2 diabetes is not only a disorder of glucose level or single-organ aging. It is a disorder of physiological coordination. AI-READI can map the breakdown of cross-system coupling across the diabetes spectrum.

Static aging clocks should remain in the project, but as secondary outcomes and descriptive phenotype axes. They should not be the flagship claim unless coupling-based features substantially improve age, disease-stage, or structural-damage prediction.

## Local Data Inventory

Local dataset symlink:

- `data -> /oak/stanford/scg/lab_twc/Albert/wearable/dataset`
- AI-READI v3.0.0, 3.82 TB, 356,343 files, DOI 10.60775/fairhub.3
- Local participant table: 2,280 rows x 15 columns
- Study visit dates: 2023-07-18 to 2025-05-01
- Age: 40 to 94, mean 60.85, SD 11.23

Participant counts:

| Group | N |
|---|---:|
| Healthy | 776 |
| Pre-diabetes/lifestyle controlled | 560 |
| Oral/non-insulin medication controlled | 686 |
| Insulin dependent | 258 |

Site counts:

| Site | N |
|---|---:|
| UAB | 800 |
| UW | 798 |
| UCSD | 682 |

Recommended splits:

| Split | N |
|---|---:|
| Train | 1,576 |
| Validation | 352 |
| Test | 352 |

Modality coverage from the actual `participants.tsv`:

| Modality | N | Coverage |
|---|---:|---:|
| Clinical data | 2,280 | 100.0% |
| Retinal photography | 2,275 | 99.8% |
| Retinal OCT | 2,266 | 99.4% |
| Retinal OCTA | 2,264 | 99.3% |
| Cardiac ECG | 2,251 | 98.7% |
| CGM | 2,245 | 98.5% |
| Environment | 2,231 | 97.9% |
| Wearable activity monitor | 2,184 | 95.8% |
| Retinal FLIO | 1,847 | 81.0% |

Manifest/table sizes verified locally:

| Source | Rows | Columns |
|---|---:|---:|
| `cardiac_ecg/manifest.tsv` | 2,257 | 22 |
| `environment/manifest.tsv` | 2,231 | 9 |
| `retinal_flio/manifest.tsv` | 7,968 | 10 |
| `retinal_oct/manifest.tsv` | 56,477 | 15 |
| `retinal_octa/manifest.tsv` | 24,560 | 47 |
| `retinal_photography/manifest.tsv` | 93,920 | 11 |
| `wearable_activity_monitor/manifest.tsv` | 2,184 | 27 |
| `wearable_blood_glucose/manifest.tsv` | 2,245 | 8 |
| `clinical_data/measurement.csv` | 242,279 | 26 |
| `clinical_data/observation.csv` | 707,126 | 22 |
| `clinical_data/condition_occurrence.csv` | 12,375 | 16 |
| `clinical_data/procedure_occurrence.csv` | 49,879 | 16 |
| `clinical_data/visit_occurrence.csv` | 4,519 | 17 |
| `clinical_data/person.csv` | 2,280 | 18 |

Generated artifacts already present:

- `results/feature_matrix.parquet`: 2,280 x 125
- `results/participant_index.parquet`: 2,280 x 39
- `results/clinical_scores.parquet`: 2,280 x 10
- `results/multimodal_features.parquet`: 2,280 x 48
- `results/age_accel.parquet`: 2,280 x 27
- `results/retinal_embeddings.parquet`: 2,274 x 1024
- `results/cardiac_embeddings.parquet`: 2,251 x 1024
- `results/retinal_age_accel.parquet`: 2,274 x 4
- `results/cardiac_age_accel.parquet`: 2,251 x 4
- `results/unified_age_accel.parquet`: 2,280 x 2
- causal, biomarker, subtype, gradient, concordance, and figure outputs are already generated.

Local model weights are available:

- `models/RETFound_cfp_weights.pth`: 1.2 GB
- `models/retfound_cfp/pytorch_model.bin`: 1.2 GB
- `models/ecgfounder/12_lead_ECGFounder.pth`: 353 MB

## Current Implementation State

The repository is much more advanced than the older roadmap wording suggests.

Implemented:

- Loaders for participants, clinical OMOP, ECG, CGM, wearable, environment, retinal manifests, DICOM metadata/pixels, temporal alignment, and multimodal per-participant access.
- Clinical feature matrix with 125 columns.
- Clinical composite scores: KDM biological age, homeostatic dysregulation, allostatic load, frailty index, HOMA-IR, TyG, QUICKI, pulse pressure, UACR.
- Batch multimodal features: CGM metrics, circadian metrics, sleep architecture summaries, HR/activity summaries, environment summaries, ECG interval features.
- Thirteen system/functional clocks from clinical and multimodal features.
- RETFound retinal embeddings and retinal age head.
- ECGFounder cardiac embeddings and cardiac age head.
- Cross-dimensional analysis: concordance matrix, concordance SD, KMeans subtypes, diabetes gradient, predictive hierarchy.
- Unified clock from age-acceleration dimensions.
- Baseline causal analyses: sleep-glucose Granger, glucose-HR cross-correlation, PM2.5-HR lag regression, PCMCI code path.
- Baseline digital biomarker analyses.
- Multi-agent research scaffolding over local scripts.

Important local result summary:

| Result | Current value |
|---|---:|
| Best static/functional individual clock | Cardiovascular, test MAE 8.134, R2 0.194 |
| Retinal age clock | test MAE 6.028, R2 0.527, Pearson r 0.730 |
| Cardiac age clock | test MAE 8.888, R2 0.081, Pearson r 0.311 |
| Multimodal feature clock | test MAE 5.200, R2 0.650, Pearson r 0.812 |
| Unified age-accel stacking clock | test MAE 8.193, R2 0.168, Pearson r 0.428 |
| Wearable-only HbA1c prediction | test R2 0.060, MAE 0.798, AUROC 0.649 for HbA1c >= 6.5 |
| Multimodal features -> HbA1c | test R2 0.557, MAE 0.475 |

Healthy vs insulin-dependent discrimination:

| Measure | AUC |
|---|---:|
| Frailty index | 0.896 |
| Allostatic load | 0.823 |
| KDM age acceleration | 0.759 |
| Metabolic age acceleration | 0.711 |
| CGM metabolic age acceleration | 0.693 |
| Cardiovascular age acceleration | 0.656 |
| Retinal age acceleration | 0.634 |
| Unified age acceleration | 0.475 |

Interpretation:

- The strongest disease-stage discriminators are not the trained static clocks. They are deficit accumulation and clinical composite burden.
- The static per-organ clocks are useful descriptors, but they are weak as the main novelty.
- Retinal age is a real signal and worth retaining.
- The multimodal feature clock has good chronological-age performance, but it needs careful interpretation because chronological age prediction is not the same as diabetes biology.
- The unified clock based on already residualized AgeAccel dimensions is not currently compelling as a disease-stage marker.

## Implementation Gaps And Risks

1. Biomarker column-name drift exists.

`scripts/biomarker_prediction.py` expects some stale names:

- Circadian IR expects `circ_ra`, `circ_is`, `circ_iv`, `cosinor_amplitude`, but the current multimodal feature table has `wear_ra`, `wear_is`, `wear_iv`, `wear_cosinor_amplitude`, etc. The current output falls back to `heart_rate`, so it is not actually testing the intended circadian features.
- CGM visual analysis requests `cgm_cv`, but the current column is `cgm_cv_glucose`, so CV is silently omitted.

This should be fixed before using biomarker outputs in a paper.

2. Cross-dimensional analysis does not include imaging clocks.

`scripts/cross_dimensional.py` currently operates on the 13 system/functional clocks in `age_accel.parquet`. Retinal and cardiac clocks are included later in `scripts/unified_clock.py`, but subtype/gradient/concordance analyses are not fully rerun in the same framework with imaging included.

3. The unified clock target is conceptually weak.

The model uses age-acceleration residuals as features to predict chronological age. Because those inputs have been residualized against age, this is not the cleanest modeling objective. If the goal is disease biology, train directly toward diabetes severity, HOMA-IR, HbA1c, frailty, retinal/cardiac structural outcomes, or future follow-up when available. If the goal is age, train on raw multimodal features or embeddings, not residualized clocks.

4. Current causal analysis is useful but preliminary.

- Sleep-glucose Granger uses roughly 4 to 10 daily observations per person. No sleep->glucose or glucose->sleep tests survive FDR.
- Glucose-HR coupling shows a group difference, but absolute correlations are small and the stronger coupling in oral/insulin groups may reflect disease-related sympathetic activation, treatment, meals, sensor artifacts, or confounding rather than simple "healthy coupling."
- PM2.5-HR results show many FDR-significant per-person associations, but these regressions need stronger autocorrelation handling, participant-level robust errors, day/time/season controls, exposure quality filters, and negative controls.
- PCMCI was not regenerated in the current targeted summary.

5. Several docs are stale.

`docs/reference/LOADING.md` still lists derived features and cross-modal coupling as "not yet implemented", but many are now implemented. `docs/design/IMPLEMENTATION_ROADMAP.md` lists files to create that already exist. Updating docs will reduce future confusion.

6. Public-release limitations matter.

Sex, race/ethnicity, and medications are redacted. This blocks sex-specific formulas such as eGFR/CKD-EPI and prevents medication adjustment for insulin, beta-blockers, GLP-1 agonists, metformin, and other strong physiological confounders. Any coupling interpretation must acknowledge this.

## Literature Position

The literature supports the coupling pivot.

AI-READI context:

- FAIRhub lists v3.0.0 as 3.82 TB, 356,343 files, DOI 10.60775/fairhub.3, released 2025-11-17: https://fairhub.io/datasets/3
- AI-READI's official site describes the goal as an AI-ready, ethically sourced type 2 diabetes dataset focused on salutogenic pathways: https://aireadi.org/
- The Nature Metabolism overview frames AI-READI as a multimodal data-generation project for AI research in T2D: https://www.nature.com/articles/s42255-024-01165-x
- The BMJ Open protocol describes a cross-sectional 4,000-person target, balanced by diabetes severity, sex, and race/ethnicity in the broader study design: https://bmjopen.bmj.com/content/15/2/e097449
- The 2026 manual of procedures further emphasizes multimodal, cross-sectional AI-ready data for reconstructing T2D development and salutogenesis: https://www.medrxiv.org/content/10.64898/2026.03.30.26349552v1

Network physiology and dynamic coupling:

- Bashan et al. established network physiology as a way to study interactions among organ systems and linked network topology to physiological state: https://www.nature.com/articles/ncomms1705
- Ivanov's "Human Physiolome" article explicitly argues for dynamic network biomarkers from synchronous physiological recordings: https://www.frontiersin.org/articles/10.3389/fnetp.2021.711778/full
- Vallat et al. showed that sleep slow-oscillation/spindle coupling predicts next-day glucose control and is mediated partly through autonomic activity: https://pmc.ncbi.nlm.nih.gov/articles/PMC10394167/
- Glucose and physical activity coupling has been studied with CGM and activity monitors in T1D: https://www.nature.com/articles/s41598-022-09728-2
- Glucose dynamics complexity is decreased in diabetes using multiscale entropy of CGM: https://pubmed.ncbi.nlm.nih.gov/24808497/
- HRV in sleep stages is associated with metabolic function and glycemic control in T2D: https://www.frontiersin.org/articles/10.3389/fphys.2023.1157270/full

Multi-organ aging context:

- Tian et al. showed heterogeneous aging across multiple organ systems and multiorgan aging networks in UK Biobank: https://www.nature.com/articles/s41591-023-02296-6
- Oh et al. showed organ-specific aging signatures from plasma proteins, with some individuals accelerated in one organ and fewer in multiple organs: https://www.nature.com/articles/s41586-023-06802-1

Foundation models and multimodal signals:

- RETFound is a retinal foundation model trained on 1.6 million retinal images and adapted to ocular/systemic disease tasks: https://www.nature.com/articles/s41586-023-06555-x
- ECGFounder has public code/weights and was built on more than 10 million ECGs: https://github.com/PKUDigitalHealth/ECGFounder and https://pubmed.ncbi.nlm.nih.gov/40771651/
- Carletti et al. showed multimodal glucose-spike phenotyping in normoglycemia, prediabetes, and T2D, and showed HbA1c misses meaningful variability: https://www.nature.com/articles/s41591-025-03849-7
- Metwally et al. showed insulin resistance can be predicted from wearables plus routine blood biomarkers, with AUROC around 0.80 for a multimodal model: https://www.nature.com/articles/s41586-026-10179-2

Causal-method caution:

- Runge/PCMCI style time-series causal discovery is relevant but should be used carefully with autocorrelation, nonlinearities, and latent confounders: https://proceedings.mlr.press/v124/runge20a.html
- CausalRivers 2025 highlights how real-world time-series causal discovery remains hard and benchmark-dependent: https://proceedings.iclr.cc/paper_files/paper/2025/hash/a205fda871b0f6c1e18a7ad7325eb6cf-Abstract-Conference.html

## Recommended Scientific Direction

### Direction 1: Flagship paper - Network Physiology of Type 2 Diabetes

Central question:

Do cross-system physiological couplings degrade, reorganize, or become more rigid across the diabetes severity spectrum?

Core feature set:

- Nodes: CGM glucose, HR, activity, sleep/wake or nightly sleep metrics, PM2.5, light, temperature, humidity.
- Edges: glucose-HR, glucose-activity, glucose-sleep, glucose-light, glucose-PM2.5, HR-activity, HR-sleep, HR-PM2.5, HR-light, sleep-environment.
- Measures per edge:
  - zero-lag and peak lagged correlation
  - cross-predictability with blocked cross-validation
  - wavelet coherence by time scale
  - transfer entropy or PCMCI after baseline validation
  - entropy/complexity per signal and cross-recurrence for selected pairs

Main outcomes:

- Diabetes severity trend.
- HbA1c, HOMA-IR, allostatic load, frailty.
- Retinal age acceleration and eventual OCTA/FLIO vascular/metabolic features.
- Cardiac age acceleration and ECG interval/HRV features.

Primary claim if supported:

Specific physiological edges break, strengthen pathologically, or become rigid before static organ-aging measures show large effects. Diabetes severity is reflected in network topology and cross-modal predictability.

Why this is worth pursuing:

- It exploits AI-READI's unique synchronized 10-day window.
- It is less dependent on redacted sex/race/medication variables than many clinical formulas.
- It differentiates this project from standard organ-age or retinal-age papers.
- It can produce practical biomarkers: "which physiological relationship is failing for this person?"

### Direction 2: Digital metabolic biomarkers from multimodal physiology

The current `biomarker_panel.csv` already shows multimodal features predict HbA1c with R2 0.557 on the test set, largely driven by CGM. That is expected, but useful. The more interesting challenge is what non-CGM physiology adds beyond CGM and standard labs.

Better framing:

- Predict HOMA-IR, HbA1c, TIR, GRI, and visual/cardiac/retinal outcomes.
- Compare feature blocks:
  - demographics/age only
  - CGM only
  - wearable only
  - environment only
  - CGM + wearable
  - CGM + wearable + environment
  - clinical labs + dynamic features
- Evaluate marginal gain, not just absolute performance.

The wearable-only HbA1c signal is currently weak, but that does not kill the direction. It means the correct question is "what does wearable add beyond CGM/labs, and what outcomes are actually wearable-sensitive?"

### Direction 3: Structural damage as the anchor outcome

Retinal imaging is the bridge from dynamic physiology to organ damage.

Best next questions:

- Does glucose-HR or glucose-activity coupling predict retinal age acceleration after adjusting for age, HbA1c, and site?
- Does glycemic complexity or nocturnal glucose burden associate with visual acuity, OCT/OCTA features, or FLIO features?
- Does environmental light/PM exposure associate with retinal or cardiac features through HR/autonomic mediation?

This is more compelling than "retinal age clock alone" because retinal clocks already exist. AI-READI can ask whether dynamic 10-day physiology explains retinal/cardiac structure.

### Direction 4: Foundation model or JEPA as later-stage infrastructure

The architecture deck's cross-modal JEPA idea is strategically interesting, but it should not be the first flagship deliverable. With 2,280 people, the most defensible near-term path is:

1. Hand-crafted and interpretable coupling features.
2. Strong statistical controls and negative controls.
3. Then learned embeddings or JEPA reconstruction loss as a second-generation coupling measure.

Use foundation models where they are already available and justified:

- RETFound for CFP.
- ECGFounder for ECG.
- Lightweight sequence encoders for CGM/wearable only after classical features establish the signal.

## Immediate Work Plan

1. Repair the biomarker scripts.

- Rename stale circadian columns to the current `wear_*` names.
- Include `cgm_cv_glucose` in visual/cardiometabolic analyses.
- Save regression metrics, AUROC, feature block comparisons, and plots in a structured summary JSON.

2. Add `scripts/coupling/coupling_features.py`.

Output: `results/coupling_features.parquet`, one row per participant.

Minimum viable columns:

- data-quality: n common points, overlap days, CGM completeness, HR completeness, env completeness.
- glucose-HR: zero-lag r, peak absolute r, signed peak r, optimal lag minutes, day-only/night-only versions.
- glucose-activity: same, plus activity bout response if feasible.
- sleep-glucose: previous-night TST/SE/WASO to next-day mean glucose/TIR/CV correlations.
- environment-HR/glucose: PM2.5, light, temp lagged coefficients with stronger time controls.
- entropy: glucose MSE proxy, HR MSE proxy, glucose coefficient of variation by day/night.
- phase: circadian phase alignment between HR/activity/glucose/light.

3. Build `scripts/coupling_analysis.py`.

Analyses:

- group trend tests with FDR correction
- age/site adjustment
- device/site sensitivity
- train/test disease-stage prediction
- comparison against static clocks and clinical scores
- structural outcome prediction using retinal/cardiac AgeAccel

4. Add negative controls.

- Circularly shift HR relative to glucose within participant.
- Pair each participant's glucose with another participant's HR from same site/date band.
- Test environment features against implausible targets.
- Use same pipeline on shuffled study labels.

5. Update docs.

- Mark completed files in `IMPLEMENTATION_ROADMAP.md`.
- Refresh `LOADING.md` "not yet implemented" section.
- Add a new "Network Physiology" implementation roadmap.

## Bottom Line

The project has the data and infrastructure for a genuinely distinctive study. The static aging-clock work is useful scaffolding, but the highest-value contribution is likely a coupling atlas: diabetes as a progressive reorganization of physiological communication across metabolic, autonomic, behavioral, environmental, retinal, and cardiac systems.

That direction is worth pursuing first because it is both scientifically differentiated and directly enabled by the dataset's rare synchronized multimodal window.
