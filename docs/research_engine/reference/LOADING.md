# AI-READI Data Loading Infrastructure

> Complete reference for the data loading, feature extraction, and cohort analysis infrastructure built for the AI-READI v3.0.0 dataset (2,280 participants, 9 modalities, 3.82 TB).

## Table of Contents

1. [Setup](#1-setup)
2. [Architecture Overview](#2-architecture-overview)
3. [Quick Start](#3-quick-start)
4. [Module Reference](#4-module-reference)
   - [config.py](#41-configpy)
   - [participants.py](#42-participantspy)
   - [loaders/clinical.py](#43-loadersclinicalpy)
   - [loaders/ecg.py](#44-loadersecgpy)
   - [loaders/cgm.py](#45-loaderscgmpy)
   - [loaders/wearable.py](#46-loaderswearablepy)
   - [loaders/environment.py](#47-loadersenvironmentpy)
   - [loaders/retinal.py](#48-loadersretinalpy)
   - [utils/concepts.py](#49-utilsconceptspy)
   - [utils/temporal.py](#410-utilstemporalpy)
   - [participant_index.py](#411-participant_indexpy)
   - [multimodal.py](#412-multimodalpy)
   - [features.py](#413-featurespy)
   - [cohort.py](#414-cohortpy)
5. [Feature Matrix Schema](#5-feature-matrix-schema)
6. [Data Quirks and Known Issues](#6-data-quirks-and-known-issues)
7. [Missingness Patterns](#7-missingness-patterns)
8. [Caching Behavior](#8-caching-behavior)
9. [Current Limitations](#9-current-limitations)

---

## 1. Setup

### Environment

```bash
# Create the conda environment (if not already done)
mamba create -n aireadi python=3.11 pandas numpy scipy scikit-learn \
    pydicom wfdb matplotlib seaborn jupyterlab pyarrow -y

# Activate
conda activate aireadi
```

### Python path

All scripts assume they are imported from the project root:

```python
import sys
sys.path.insert(0, "/oak/stanford/scg/lab_twc/mazijian/aireadi")

from scripts.features import load_feature_matrix
from scripts.multimodal import get_participant
```

### Data location

The dataset is symlinked at `data/` → `/oak/stanford/scg/lab_twc/Albert/wearable/dataset`. All paths in `config.py` are absolute and derived from this symlink. No path configuration is needed.

---

## 2. Architecture Overview

```
scripts/                          ~1,970 lines total
├── config.py                     Path constants, modality constants
├── participants.py               participants.tsv loader + filters
├── features.py                   Clinical feature matrix (2280 × 125 Parquet)
├── cohort.py                     Stratified comparison, effect sizes, FDR
├── participant_index.py          Unified per-person Parquet joining all manifests
├── multimodal.py                 get_participant() → lazy ParticipantData object
├── loaders/
│   ├── clinical.py               6 OMOP CDM CSV tables
│   ├── ecg.py                    WFDB 12-lead ECG (.hea/.dat)
│   ├── cgm.py                    Dexcom G6 CGM (OMH JSON) + glycemic metrics
│   ├── wearable.py               7 Garmin Vivosmart 5 sub-modalities (OMH JSON)
│   ├── environment.py            LeeLab Anura environmental sensor (CSV)
│   └── retinal.py                4 retinal manifests + lazy DICOM loading
└── utils/
    ├── concepts.py               OMOP concept_id → human label mapping
    └── temporal.py               Cross-modal time alignment + overlap computation
```

### Design principles

1. **Manifest-first.** File discovery goes through `manifest.tsv`, never by walking directories.
2. **Lazy loading for imaging.** Retinal manifests are parsed eagerly; pixel data is loaded on demand via `load_dicom(filepath)`.
3. **Parquet for derived tables.** Feature matrix and participant index are saved as Parquet in `results/` for fast reload.
4. **Sentinel values filtered at load time.** Each loader strips its modality's sentinel values and documents what was removed.
5. **UTC timestamps.** All timestamps stored as UTC. Timezone metadata (pst/cst) is preserved in header dicts but not applied to timestamps.
6. **person_id as string.** Consistent across all modules. The index of participants.tsv and feature matrix.

---

## 3. Quick Start

### Load the feature matrix (most common entry point)

```python
from scripts.features import load_feature_matrix
fm = load_feature_matrix()  # 2280 × 125, from results/features/feature_matrix.parquet
fm.loc["1001", "hba1c"]     # → 5.6
```

### Compare a feature across diabetes severity groups

```python
from scripts.cohort import compare_groups
result = compare_groups(fm, "hba1c")
print(result["group_stats"])        # mean, std, median, n per group
print(result["pvalue"])             # Kruskal-Wallis p-value
print(result["pairwise"])           # pairwise Cohen's d
```

### Compare all features with FDR correction

```python
from scripts.cohort import compare_all_features
summary = compare_all_features(fm, adjust_for=["age"])
significant = summary[summary["significant"]]
```

### Load all modalities for one participant

```python
from scripts.multimodal import get_participant
p = get_participant("1046")

p.study_group       # → 'pre_diabetes_lifestyle_controlled'
p.cgm_metrics       # → {'mean_glucose': 121.25, 'cv': 0.1791, 'tir': 0.9877, ...}
p.ecg_signal.shape  # → (5500, 12) — 11 sec × 12 leads in mV
p.cgm_header        # → {'timezone': 'pst', ...}

# Aligned CGM × HR × environment on 5-min grid
aligned = p.aligned_timeseries(freq="5min")  # → DataFrame (2828, 5)

# Retinal file listings (no pixel loading)
p.oct_files          # → DataFrame of OCT manifest rows
p.photography_files  # → DataFrame of CFP/FAF/IR manifest rows
```

### Load a single modality directly

```python
from scripts.loaders.ecg import load_ecg
signal, meta = load_ecg("1001")[0]
# signal: (5500, 12) float32 in mV
# meta: {'Rate': 60, 'QTc': 403, 'participant_position': '0 degrees (supine)', ...}

from scripts.loaders.cgm import load_cgm, compute_cgm_metrics
cgm_df, header = load_cgm("1001")
metrics = compute_cgm_metrics(cgm_df)

from scripts.loaders.wearable import load_wearable
wear = load_wearable("1046")  # → dict of 7 DataFrames
wear["heart_rate"].head()     # → timestamp, value (bpm), unit

from scripts.loaders.environment import load_environment
env_df, env_meta = load_environment("1001")
# env_df: 173,314 rows × 22 columns at 5-sec intervals
# env_meta: {'meta_sensor_location': 'dining room', ...}
```

### Search for clinical concepts

```python
from scripts.utils.concepts import search_concepts
search_concepts("cholesterol", "measurement")
# → {3027114: 'Cholesterol [Mass/volum', 3007070: 'Cholesterol in HDL ...', ...}
```

### Filter participants

```python
from scripts.participants import get_person_ids
# All train-split healthy participants with CGM + wearable + environment
ids = get_person_ids(
    split="train",
    group="healthy",
    modalities=["wearable_blood_glucose", "wearable_activity_monitor", "environment"],
)
```

---

## 4. Module Reference

### 4.1 `config.py`

Path constants for all data directories and files. Key constants:

| Constant | Value | Purpose |
|---|---|---|
| `DATA_ROOT` | `.../aireadi/data/` | Root of the symlinked dataset |
| `RESULTS_DIR` | `.../aireadi/results/` | Output directory for derived files |
| `ECG_SAMPLE_RATE` | 500 | Hz |
| `ECG_NUM_SAMPLES` | 5500 | 11 seconds per recording |
| `ECG_GAIN` | 200 | ADU per mV |
| `ECG_LEAD_NAMES` | `["I","II",...,"V6"]` | Standard 12-lead order |
| `CGM_SAMPLE_INTERVAL_MIN` | 5 | Dexcom G6 sampling interval |
| `CGM_TIR_LOW` / `CGM_TIR_HIGH` | 70 / 180 | mg/dL thresholds for time-in-range |
| `ENV_HEADER_LINES` | 45 | Comment header lines in environmental CSVs |
| `ENV_LIGHT_WAVELENGTHS_NM` | `[415,445,...,910]` | Spectral channel center wavelengths |

---

### 4.2 `participants.py`

Loads `participants.tsv` (2,280 rows × 15 columns) with proper types.

| Function | Returns | Notes |
|---|---|---|
| `load_participants()` | DataFrame indexed by person_id | Cached. Booleans parsed from TRUE/FALSE strings. |
| `get_split("train")` | DataFrame | 1,576 / 352 / 352 for train/val/test |
| `get_group("healthy")` | DataFrame | One of 4 study groups |
| `get_site("UW")` | DataFrame | UW (798), UAB (800), UCSD (682) |
| `participants_with_modality("retinal_flio")` | DataFrame | Participants with a given modality |
| `get_person_ids(split=, group=, site=, modalities=)` | list[str] | Combined filter → list of person_ids |

**Modality availability** (boolean columns in participants.tsv):

| Modality | TRUE count | Coverage |
|---|---|---|
| clinical_data | 2,280 | 100.0% |
| retinal_photography | 2,275 | 99.8% |
| retinal_oct | 2,266 | 99.4% |
| retinal_octa | 2,264 | 99.3% |
| cardiac_ecg | 2,251 | 98.7% |
| wearable_blood_glucose | 2,245 | 98.5% |
| environment | 2,231 | 97.9% |
| wearable_activity_monitor | 2,184 | 95.8% |
| retinal_flio | 1,847 | 81.0% |

---

### 4.3 `loaders/clinical.py`

Loads the 6 OMOP CDM CSV files from `clinical_data/`.

**Raw table loaders** (all cached):

| Function | Source file | Rows | Notes |
|---|---|---|---|
| `load_persons()` | person.csv | 2,280 | Demographics redacted (all concept_ids = 0) |
| `load_visits()` | visit_occurrence.csv | 4,519 | ~2 visits per person |
| `load_measurements()` | measurement.csv | 242,279 | 105 unique concepts. Phantom index column auto-stripped. |
| `load_observations()` | observation.csv | 707,126 | 244 unique concepts. Phantom index column auto-stripped. |
| `load_conditions()` | condition_occurrence.csv | 12,375 | 30 conditions, 2,189 persons |
| `load_procedures()` | procedure_occurrence.csv | 49,879 | 3 concepts (90% monofilament) |

**Per-person query functions:**

| Function | Usage |
|---|---|
| `get_measurements(person_id, concept_ids=None)` | Filter measurements by person and optionally by concept |
| `get_observations(person_id, concept_ids=None)` | Filter observations |
| `get_conditions(person_id)` | All conditions for a person |
| `get_lab_value(person_id, concept_id)` | Single numeric value (first match) |
| `get_condition_flags(person_id)` | Dict of concept_id → True |

**Cohort-level:**

| Function | Usage |
|---|---|
| `measurement_summary(concept_id)` | DataFrame of (person_id, value, date) for one concept across cohort |
| `condition_prevalence()` | Prevalence table with counts and source labels |

---

### 4.4 `loaders/ecg.py`

Loads 12-lead ECG recordings from Philips PageWriter TC30 in WFDB format.

| Function | Returns | Notes |
|---|---|---|
| `load_ecg_manifest()` | DataFrame (2,257 rows) | Includes Rate, PR, QRSD, QT, QTc, P, QRS, T |
| `load_ecg(person_id)` | list[(signal, metadata)] | signal: `np.ndarray[5500, 12]` float32 in mV. Most return 1 item; 6 participants have 2. |
| `load_ecg_signal(person_id)` | `np.ndarray[5500, 12]` | Convenience: first recording's signal only |

**Signal format:**
- Shape: (5500, 12) — 11 seconds at 500 Hz, 12 leads
- Units: millivolts (raw int16 divided by gain of 200)
- Lead order: I, II, III, aVR, aVL, aVF, V1–V6
- All recordings: identical format, no variability

**Metadata dict keys** (from `.hea` header comments):
- `Rate`, `PR`, `QRSD`, `QT`, `QTc`, `P`, `QRS`, `T` — device-computed intervals
- `participant_position` — supine (60.9%), reclined (37.6%), slight recline (1.2%), sitting (0.3%)
- `interpretation_comment_1`, `interpretation_comment_2` — machine ECG interpretation
- `comment_1_key`, `comment_1_val` ... `comment_3_key`, `comment_3_val` — diagnostic findings
- `validation_id`, `validation_date` — data provenance
- `lead_names` — always `["I","II",...,"V6"]`

**Edge cases:**
- 6 participants have 2 recordings: 1213, 1604, 1605, 1782, 4119, 4130
- 7 orphan files exist on disk but are not in the manifest (skipped by the loader)
- PR is null for 1.7% of recordings, P for 2.0%, T for 0.4%

---

### 4.5 `loaders/cgm.py`

Loads Dexcom G6 continuous glucose monitoring data from Open mHealth JSON.

| Function | Returns | Notes |
|---|---|---|
| `load_cgm_manifest()` | DataFrame (2,245 rows) | avg glucose, duration, sensor ID |
| `load_cgm(person_id)` | (DataFrame, header_meta) | DataFrame indexed by UTC timestamp with glucose_mg_dl, transmitter_id, device_id. header_meta includes timezone. |
| `compute_cgm_metrics(df)` | dict | Standard glycemic metrics (see below) |

**CGM DataFrame columns:**
- `glucose_mg_dl` (int) — glucose concentration
- `transmitter_id` (str) — Dexcom transmitter ID
- `device_id` (str) — sensor serial number
- Index: UTC DatetimeIndex at 5-minute intervals

**Header metadata keys:**
- `timezone` — "pst" or "cst" (needed for circadian analysis)
- `schema_name` — "blood-glucose"
- `schema_version` — 3.0
- `modality` — "sensed"
- `patient_id` — "AIREADI-{person_id}"

**Computed glycemic metrics:**

| Metric | Key | Description |
|---|---|---|
| Mean glucose | `mean_glucose` | mg/dL |
| Std glucose | `std_glucose` | mg/dL |
| Coefficient of variation | `cv` | std / mean |
| Time in range (70–180) | `tir` | Fraction of readings in range |
| Time below range (<70) | `tbr` | Fraction below 70 |
| Time above range (>180) | `tar` | Fraction above 180 |
| Glucose Management Indicator | `gmi` | 3.31 + 0.02392 × mean_glucose |
| MAGE | `mage` | Mean amplitude of glycemic excursions (>1 SD) |
| N readings | `n_readings` | Total data points |
| Duration | `duration_days` | Recording span in days |

**Typical values:** 2,856 readings over 11 days. Range 334–2,856 (participants with sensor issues have fewer).

---

### 4.6 `loaders/wearable.py`

Loads 7 Garmin Vivosmart 5 sub-modalities from Open mHealth JSON.

| Function | Returns | Notes |
|---|---|---|
| `load_wearable_manifest()` | DataFrame (2,184 rows) | Summary stats per participant |
| `load_wearable(person_id)` | dict[str, DataFrame] | All 7 sub-modalities |
| `load_wearable_submodality(person_id, name)` | DataFrame | Single sub-modality |

**Sub-modality schemas:**

| Name | Body key | Record type | Value field | Unit | Sentinel filtered |
|---|---|---|---|---|---|
| `heart_rate` | `body.heart_rate` | point | `heart_rate.value` | beats/min | value=0 |
| `oxygen_saturation` | `body.breathing` | point | `oxygen_saturation.value` | % | — |
| `respiratory_rate` | `body.breathing` | point | `respiratory_rate.value` | breaths/min | value<0 |
| `stress` | `body.stress` | point | `stress.value` | stress_level | value<0 |
| `sleep` | `body.sleep` | interval | `sleep_stage_state` | stage | — |
| `physical_activity` | `body.activity` | interval | `base_movement_quantity.value` | steps | — |
| `physical_activity_calorie` | `body.activity` | point | `calories_value.value` | kcal | — |

**DataFrame formats:**
- Point records: DatetimeIndex (UTC), columns: `value`, `unit`
- Interval records: columns: `start_time`, `end_time`, `value`, `unit` [, `activity_name`]
- Sleep stages: `value` is one of `"light"`, `"deep"`, `"rem"`, `"awake"`
- Physical activity `value` is step count (int) or NaN for initialization records

**Typical record counts per participant (over ~20 days):**
- heart_rate: 8,500–15,000
- stress: 8,900–53,500
- respiratory_rate: 1,600–53,500
- sleep: 50–700 (intervals, not individual readings)
- physical_activity: 1,600–21,300 (intervals)

---

### 4.7 `loaders/environment.py`

Loads LeeLab Anura environmental sensor data from CSV with 45-line comment header.

| Function | Returns | Notes |
|---|---|---|
| `load_environment_manifest()` | DataFrame (2,231 rows) | Sensor location, duration, obs count |
| `load_environment(person_id)` | (DataFrame, metadata_dict) | Full sensor data + header metadata |
| `load_environment_light(person_id)` | DataFrame | 10 spectral channels only |
| `load_environment_air_quality(person_id)` | DataFrame | PM, humidity, temp, VOC, NOx only |

**Data columns (22):**

| Column(s) | Type | Range | Unit | Description |
|---|---|---|---|---|
| `ts` | datetime | — | UTC | Timestamp (index) |
| `lch0`–`lch11` | float | 0–1 | relative intensity | 10 spectral channels: 415, 445, 480, 515, 555, 590, 630, 680, clear, 910 nm |
| `pm1`, `pm2.5`, `pm4`, `pm10` | uint16 | 0–65536 | µg/m³ | Particulate matter by size |
| `hum` | float | 0–100 | % | Relative humidity |
| `temp` | float | -10–50 | °C | Ambient temperature (SEN55) |
| `voc` | int | 1–500 | index | VOC index (Sensirion) |
| `nox` | int | 1–500 | index | NOx index (frequent NaN — see quirks) |
| `screen` | bool | 0/1 | — | Screen on/off detection |
| `ff` | int | 0–2000 | Hz | Flicker frequency |
| `inttemp` | float | — | °C | Internal case temperature |

**Metadata dict keys** (from 45-line header):
- `meta_sensor_id`, `meta_participant_id`, `meta_sensor_location`
- `meta_number_of_observations`, `meta_extent_of_observation_in_days`
- `environmental_sensor_firmware_version` (1.2.4)

**Typical values:** ~173,000 rows over 10 days at 5-second intervals.

---

### 4.8 `loaders/retinal.py`

Manifest parsers and lazy DICOM loader for 4 retinal imaging sub-modalities.

**Manifest loaders** (all cached):

| Function | File | Rows | Columns | Notes |
|---|---|---|---|---|
| `load_oct_manifest()` | retinal_oct/manifest.tsv | 56,477 | 15 | Includes reference_filepath to IR images |
| `load_octa_manifest()` | retinal_octa/manifest.tsv | 24,560 | 47 | Cross-references OCT, IR, segmentation, 4 enface layers |
| `load_photography_manifest()` | retinal_photography/manifest.tsv | 93,920 | 11 | CFP, FAF, IR across 6 devices |
| `load_flio_manifest()` | retinal_flio/manifest.tsv | 7,968 | 10 | 4 files per participant (long/short × L/R) |

**Per-person file queries:**

| Function | Filters |
|---|---|
| `get_oct_files(person_id, device=, laterality=)` | OCT manifest rows |
| `get_octa_files(person_id, device=, laterality=)` | OCTA manifest rows |
| `get_photography_files(person_id, imaging_type=, device=, laterality=)` | CFP/FAF/IR rows |
| `get_flio_files(person_id, wavelength=, laterality=)` | FLIO rows |
| `get_octa_with_linked_files(person_id)` | OCTA rows with cross-modal link columns |

**Pixel loading (lazy):**

```python
from scripts.loaders.retinal import load_dicom, load_dicom_metadata

# Load pixel array (caution: FLIO files are 134 MB each)
pixels = load_dicom("/retinal_photography/cfp/optomed_aurora/1001/1001_optomed_....dcm")
# → np.ndarray, shape depends on modality

# Load metadata only (fast, no pixel data)
meta = load_dicom_metadata(filepath)
# → {'rows': 1536, 'columns': 1536, 'number_of_frames': 1, ...}
```

**Utilities:**
- `parse_pixel_spacing("[0.003872, 0.01206]")` → `(0.003872, 0.01206)`

**Per-modality pixel shapes:**

| Modality | Shape | Typical size |
|---|---|---|
| OCT volume | (frames, height, width) | 5.6–51 MB |
| OCTA flow cube | (frames, height, width) | 8–38 MB |
| OCTA enface | (height, width) | 60–240 KB |
| OCTA segmentation | (frames, height, width) | ~4.5 MB |
| CFP (color fundus) | (height, width, 3) RGB | 1.2–3 MB |
| FAF (autofluorescence) | (height, width, 3) RGB | ~2.2 MB |
| IR (infrared) | (height, width) grayscale | 578 KB–2.3 MB |
| FLIO | (1024, 256, 256) | ~134 MB |

---

### 4.9 `utils/concepts.py`

Maps OMOP integer concept_ids to human-readable labels.

| Function | Usage |
|---|---|
| `build_concept_map("measurement")` | → dict[int, str] with 105 entries |
| `build_concept_map("observation")` | → dict[int, str] with 244 entries |
| `build_concept_map("condition")` | → dict[int, str] with 30 entries |
| `get_concept_label(3004410, "measurement")` | → "Hemoglobin A1c/Hemoglobin.total in" |
| `search_concepts("cholesterol", "measurement")` | → {3027114: "Cholesterol [Mass/volum", ...} |

Labels are extracted from `measurement_source_value` fields which encode `"redcap_field_code, Human Label"`. The function strips the REDCap code prefix.

Uses `clinical.py`'s cached DataFrames (no duplicate CSV reads).

---

### 4.10 `utils/temporal.py`

Time alignment for the ~10-day concurrent window of CGM × wearable × environmental data.

| Function | Returns | Notes |
|---|---|---|
| `get_overlap_window(*dataframes)` | (start, end) or None | Intersection of all DatetimeIndex ranges |
| `align_timeseries(dataframes, freq, method, tolerance)` | DataFrame | Reindexes all inputs onto a common grid |
| `compute_overlap_stats(cgm=, wearable_hr=, environment=)` | dict | Per-modality durations + overlap days |

```python
from scripts.utils.temporal import align_timeseries

aligned = align_timeseries({
    "cgm": cgm_df[["glucose_mg_dl"]],
    "hr": hr_df[["value"]].rename(columns={"value": "bpm"}),
    "env": env_df[["temp", "hum"]],
}, freq="5min")
# → DataFrame on common 5-min UTC grid, columns prefixed: cgm_glucose_mg_dl, hr_bpm, env_temp, env_hum
```

**Limitation:** Only numeric columns are aligned. Categorical data (sleep stages, activity names) is silently dropped. For sleep/activity analysis, use the interval-based DataFrames from wearable loaders directly.

---

### 4.11 `participant_index.py`

Builds a unified one-row-per-person Parquet index (2,280 × 39) joining participants.tsv with aggregated summaries from all modality manifests.

| Function | Returns | Notes |
|---|---|---|
| `build_participant_index(save=True)` | DataFrame | Joins all manifests. Saves to `results/features/participant_index.parquet`. |
| `load_participant_index()` | DataFrame | Loads from Parquet (auto-builds if missing). |

**Columns added from manifests:**

| Source | Columns |
|---|---|
| ECG manifest | `ecg_n_recordings`, `ecg_rate`, `ecg_pr`, `ecg_qrsd`, `ecg_qt`, `ecg_qtc`, `ecg_position` |
| CGM manifest | `cgm_n_records`, `cgm_mean_glucose`, `cgm_duration_days` |
| Wearable manifest | `wearable_mean_hr`, `wearable_mean_spo2`, `wearable_mean_stress`, `wearable_mean_sleep_hrs`, `wearable_mean_rr`, `wearable_mean_daily_activity`, `wearable_mean_calories`, `wearable_duration_days` |
| Environment manifest | `env_n_observations`, `env_duration_days`, `env_sensor_location` |
| Retinal manifests | `oct_n_files`, `octa_n_files`, `photo_n_files`, `flio_n_files` |

---

### 4.12 `multimodal.py`

Lazy per-participant accessor that loads all modalities on demand.

```python
from scripts.multimodal import get_participant
p = get_participant("1046")
```

**ParticipantData properties:**

| Property | Type | Loads from |
|---|---|---|
| `person_id`, `clinical_site`, `study_group`, `age`, `study_visit_date`, `recommended_split` | str/int/datetime | participants.tsv |
| `measurements` | DataFrame | clinical.py (lazy) |
| `observations` | DataFrame | clinical.py (lazy) |
| `conditions` | DataFrame | clinical.py (lazy) |
| `ecg_recordings` | list[(ndarray, dict)] | ecg.py (lazy) |
| `ecg_signal` | ndarray or None | First ECG signal |
| `cgm_data` | DataFrame | cgm.py (lazy) |
| `cgm_header` | dict | CGM JSON header (includes timezone) |
| `cgm_metrics` | dict | Computed on access |
| `wearable_data` | dict[str, DataFrame] | wearable.py (lazy) |
| `environment_data` | (DataFrame, dict) | environment.py (lazy) |
| `oct_files`, `octa_files`, `photography_files`, `flio_files` | DataFrame | retinal.py manifests |

**Methods:**

| Method | Returns |
|---|---|
| `aligned_timeseries(freq="5min")` | DataFrame with CGM glucose, HR, env temp/hum/PM2.5 on common grid |
| `overlap_stats()` | dict with per-modality durations and triple-overlap days |

---

### 4.13 `features.py`

Builds the clinical feature matrix (2,280 × 125) by pivoting OMOP long-format tables into one-row-per-person wide format.

| Function | Returns | Notes |
|---|---|---|
| `build_feature_matrix(save=True)` | DataFrame (2280 × 125) | Pivots all measurements + conditions + observations. Saves to `results/features/feature_matrix.parquet`. |
| `load_feature_matrix()` | DataFrame | Loads from Parquet (auto-builds if missing). |

See [Section 5](#5-feature-matrix-schema) for complete column listing.

**How vitals are handled:** SBP, DBP, and heart rate have 2 readings per participant (measured twice per visit). These are **averaged** in the feature matrix. All other labs have 1 reading per person per concept.

**How conditions are handled:** Each of the 30 conditions becomes a boolean column (`True` if present in `condition_occurrence.csv`, `False` otherwise — never NaN).

---

### 4.14 `cohort.py`

Stratified comparison framework for analyzing features across study groups.

| Function | Returns | Notes |
|---|---|---|
| `compare_groups(fm, feature, group_col=, adjust_for=)` | dict | Kruskal-Wallis/ANOVA, pairwise Mann-Whitney U, Cohen's d, effect size |
| `compare_all_features(fm, features=, adjust_for=, fdr_alpha=0.05)` | DataFrame | All features compared with Benjamini-Hochberg FDR correction |
| `site_bias_check(fm, features=)` | DataFrame | Same as above but grouped by `clinical_site` |

**`compare_groups()` return dict:**

| Key | Value |
|---|---|
| `group_stats` | DataFrame with mean, std, median, n per group |
| `test` | "kruskal" or "anova" (auto-selected by normality test) |
| `statistic` | Test statistic |
| `pvalue` | Omnibus p-value |
| `effect_size` | Eta-squared (ANOVA) or epsilon-squared (Kruskal-Wallis) |
| `pairwise` | DataFrame with group1, group2, cohens_d, mean_diff, u_stat, pvalue |

**`compare_all_features()` return DataFrame columns:**
`feature`, `test`, `statistic`, `pvalue`, `pvalue_fdr`, `significant`, `effect_size`, `mean_healthy`, `n_healthy`, `mean_prediab`, `n_prediab`, `mean_oral_med`, `n_oral_med`, `mean_insulin`, `n_insulin`

**Covariate adjustment:** `adjust_for=["age"]` residualizes the feature against the covariate via OLS before testing. Multiple covariates supported.

---

## 5. Feature Matrix Schema

**2,280 rows × 125 columns**, indexed by `person_id` (string).

### Demographics (5 columns)

| Column | Type | Values |
|---|---|---|
| `clinical_site` | str | UW (798), UAB (800), UCSD (682) |
| `study_group` | str | healthy (776), pre_diabetes_lifestyle_controlled (560), oral_medication_...controlled (686), insulin_dependent (258) |
| `age` | int | 40–94 (mean 60.85) |
| `study_visit_date` | datetime | 2023-07-18 to 2025-05-01 |
| `recommended_split` | str | train (1576), val (352), test (352) |

### Labs (38 columns, 97–100% complete)

| Column | Concept ID | Unit | Typical range |
|---|---|---|---|
| `hba1c` | 3004410 | % | 4.5–14 |
| `glucose` | 3004501 | mg/dL | 60–400 |
| `insulin` | 3016244 | stored as ng/L; convert to µIU/mL by dividing by 0.04034 | 1–100 µIU/mL after conversion |
| `c_peptide` | 3010084 | stored as ng/L; values appear consistent with ng/mL scale | 0.5–10 ng/mL-equivalent |
| `total_cholesterol` | 3027114 | mg/dL | 100–350 |
| `hdl` | 3007070 | mg/dL | 20–120 |
| `ldl` | 3028288 | mg/dL | 30–250 |
| `triglycerides` | 3022192 | mg/dL | 30–600 |
| `crp` | 3010156 | mg/L | 0.1–20 |
| `troponin_t` | 40769783 | ng/mL | 0–0.1 |
| `nt_probnp` | 3029187 | pg/mL | 5–3000 |
| `bun` | 3013682 | mg/dL | 5–40 |
| `creatinine` | 3016723 | mg/dL | 0.4–2.5 |
| `bun_cr_ratio` | 4112223 | ratio | 5–30 |
| `sodium` | 3019550 | mEq/L | 133–148 |
| `potassium` | 3023103 | mEq/L | 3.2–5.5 |
| `chloride` | 3014576 | mEq/L | 96–110 |
| `co2` | 3015632 | mEq/L | 18–32 |
| `calcium` | 3006906 | mg/dL | 8–11 |
| `alt` | 3006923 | U/L | 5–100 |
| `ast` | 3013721 | U/L | 5–80 |
| `alk_phos` | 3035995 | U/L | 20–200 |
| `bilirubin_total` | 3024128 | mg/dL | 0.1–3 |
| `albumin` | 3024561 | g/dL | 3–5.5 |
| `globulin` | 3021886 | g/dL | 1.5–4.5 |
| `total_protein` | 3020630 | g/dL | 5.5–9 |
| `ag_ratio` | 4288601 | ratio | 0.8–2.5 |
| `urine_albumin` | 3012516 | mg/L | 0–500 |
| `urine_creatinine` | 3017250 | mg/dL | 10–300 |
| `wbc` | 2005200182 | ×10³/µL | 3–15 |
| `rbc` | 2005200183 | ×10⁶/µL | 3.5–6.5 |
| `hemoglobin` | 3000963 | g/dL | 10–18 |
| `hematocrit` | 3009542 | % | 30–55 |
| `mcv` | 3024731 | fL | 70–105 |
| `mch` | 3035941 | pg | 25–35 |
| `mchc` | 3003338 | g/dL | 30–37 |
| `rdw` | 3002385 | % | 11–18 |
| `platelets` | 3007461 | ×10³/µL | 100–450 |

### Vitals + Anthropometry (9 columns, 99.5%+ complete)

| Column | Notes |
|---|---|
| `sbp`, `dbp` | Averaged from 2 readings per visit (mmHg) |
| `heart_rate` | Averaged from 2 readings (bpm) |
| `height_cm`, `weight_kg`, `bmi` | Standard |
| `waist_cm`, `hip_cm`, `whr` | Waist-to-hip ratio |

### Vision (22 columns, 98–99% complete)

All have separate OD (right eye) and OS (left eye) columns:
- `va_letter_photopic_od/os` — VA letter score under photopic conditions
- `logmar_photopic_od/os` — LogMAR equivalent
- `va_letter_mesopic_od/os` — VA under mesopic (dim) conditions
- `logmar_mesopic_od/os` — LogMAR mesopic
- `log_contrast_plcs_od/os` — Pelli-Robson log contrast sensitivity
- `log_contrast_mlcs_od/os` — Mars letter contrast sensitivity
- `contrast_final_letter_od/os` — Final correct letter in contrast test
- `llva_final_letter_od/os` — Low-luminance VA final correct letter
- `autorefract_sphere_od/os`, `autorefract_cylinder_od/os`, `autorefract_axis_od/os`

### Cognition — MoCA (16 columns, 99.3% complete)

| Column | Description |
|---|---|
| `moca_total` | Montreal Cognitive Assessment total score (0–30) |
| `moca_trails` | Trail-making (visuospatial/executive) |
| `moca_cube` | Cube drawing (visuospatial) |
| `moca_clock` | Clock drawing (visuospatial) |
| `moca_naming` | Naming (language) |
| `moca_memory1`, `moca_memory2` | Memory trials 1 and 2 |
| `moca_digitspan` | Digit span (attention) |
| `moca_lettera` | Letter A tapping (attention) |
| `moca_subtraction` | Serial subtraction (attention) |
| `moca_repetition` | Sentence repetition (language) |
| `moca_fluency` | Verbal fluency (language) |
| `moca_abstraction` | Abstraction |
| `moca_delayed_recall` | Delayed recall (memory) |
| `moca_orientation` | Orientation |
| `moca_combined_mis` | Combined MIS score |

### Conditions (30 boolean columns, 100% complete)

All prefixed with `has_`. Top 10 by prevalence:

| Column | N (of 2,280) | Prevalence |
|---|---|---|
| `has_elevated_a1c` | 1,202 | 52.7% |
| `has_hypertension` | 1,151 | 50.5% |
| `has_dyslipidemia` | 1,145 | 50.2% |
| `has_arthritis` | 941 | 41.3% |
| `has_t2dm` | 899 | 39.4% |
| `has_obesity` | 845 | 37.1% |
| `has_dry_eye` | 741 | 32.5% |
| `has_cataracts` | 688 | 30.2% |
| `has_prediabetes` | 555 | 24.3% |
| `has_urinary_problems` | 517 | 22.7% |

Other conditions: digestive problems, cancer, hearing impairment, other cardiac, chronic pulmonary, osteoporosis, renal problems, circulation problems, glaucoma, neurological, hypotension, MI, AMD, stroke, diabetic retinopathy, MCI, RVO, MS, Parkinson's, dementia.

### Other (5 columns, 99.8%+ complete)

| Column | Source | Type |
|---|---|---|
| `cesd_total` | observation.csv | float (0–30, CES-D-10 depression score) |
| `ever_smoked` | observation.csv | bool |
| `ever_alcohol` | observation.csv | bool |
| `monofilament_right_felt` | measurement.csv | float (neuropathy screen, right foot) |
| `monofilament_left_felt` | measurement.csv | float (neuropathy screen, left foot) |

---

## 6. Data Quirks and Known Issues

### OMOP CSVs: phantom index column

`measurement.csv` and `observation.csv` have a leading empty `""` column (an export artifact from R or pandas). The loaders detect and drop this column automatically. If you read these files directly with `pd.read_csv()`, you must handle it:

```python
df = pd.read_csv(path)
if df.columns[0] in ("", "Unnamed: 0"):
    df = df.drop(columns=[df.columns[0]])
```

### Environmental humidity units

The 45-line CSV header says `hum: float [0.00 to 1.00]` but the actual data contains values like `45.01` (percentages, 0–100). **The data is correct; the header documentation is wrong.** The loader does not transform the values — they are percentages as-is.

### Environmental NOx: frequent NaN

The `nox` column contains "nan" values frequently. This appears to be a sensor initialization issue. The loader converts these to proper `NaN` via `na_values=["nan"]`.

### Wearable JSON schema inconsistencies

The `schema_id` fields are empty strings (`namespace: "", name: "", version: ""`) for `stress`, `physical_activity`, and `physical_activity_calorie` sub-modalities. The `heart_rate`, `oxygen_saturation`, and `respiratory_rate` files properly declare their OMH schema. The loader handles both cases.

### Wearable sentinel values

Different sub-modalities use different sentinel values for invalid/missing readings:
- `heart_rate`: value = 0
- `stress`: value = -1 or -2
- `respiratory_rate`: value = -1.0 or -2.0

All are filtered by the loader. After loading, no sentinel values remain in the DataFrames.

### Physical activity initialization record

Each participant's `physical_activity` JSON has exactly 1 record with empty-string `activity_name` and empty-string `value` (the sensor initialization entry). The loader converts this to `NaN` (not 0).

### CGM timestamp quirk

All CGM records have `start_date_time == end_date_time` in the time interval — they represent instantaneous glucose readings, not time ranges. The loader uses `start_date_time` as the timestamp.

### CGM schema typo

The header field is `acquistion_rate` (missing 'i') — this is preserved in the source schema and is not a loader bug.

### ECG orphan files

7 `.hea/.dat` file pairs exist on disk under `cardiac_ecg/ecg_12lead/philips_tc30/` but are not referenced in the manifest. The loader only reads files listed in the manifest, so these are skipped. Person IDs of orphan files: 1172, 1325, 4052, 4091, 4187, 4205, 7282.

### ECG dual recordings

6 participants have 2 ECG recordings each: 1213, 1604, 1605, 1782, 4119, 4130. `load_ecg()` returns a list containing both. Rate differs by 3–17 bpm between recordings. The participant index uses the first recording's values.

### Redacted demographics

In the public release (v3.0.0), `person.csv` has all demographic concept IDs set to 0:
- `gender_concept_id` = 0
- `race_concept_id` = 0
- `ethnicity_concept_id` = 0
- `birth_datetime` = 1970-01-01 (sentinel)
- `month_of_birth` = 0, `day_of_birth` = 0

Only `year_of_birth` is populated (range 1930–1983). Sex, race, ethnicity, and medications are only available in the controlled-access version.

---

## 7. Missingness Patterns

The feature matrix has structured, non-random missingness:

### Block 1: No blood draw (47 participants, 2.1%)

47 participants are missing **all** 23 blood-panel labs as a block (glucose, lipids, CBC, metabolic, hepatic, CRP, troponin, NT-proBNP). These same 47 people are the core missing group. They retain all imaging, ECG, wearable, CGM, and environmental data.

### Block 2: No CBC tube (7 additional participants)

7 additional participants have metabolic panel results but are missing the entire CBC block (WBC, RBC, Hb, Hct, MCV, MCH, MCHC, RDW, platelets). Different tube/processing pathway.

### Block 3: HbA1c assay failures (21 additional)

69 total participants are missing HbA1c. 47 are from the no-blood-draw block; 21 additional had blood drawn but the HbA1c assay failed or wasn't run.

### Scattered: vision and cognition

- Left eye (OS) measurements have consistently more missingness than right eye (OD): 29 vs 23 for VA, 25 vs 18 for contrast. Consistent with patient fatigue during the ophthalmic exam battery (right eye tested first).
- MoCA subscores: 15 participants (0.7%) didn't complete cognitive testing.
- CES-D: 3 participants (0.1%) didn't complete the depression survey.

### Implications for analysis

- Any analysis using blood labs will lose ~48 participants (2.1%).
- Any analysis using HbA1c specifically will lose ~69 participants (3.0%).
- Imaging + wearable + CGM analyses are minimally affected.
- The missingness is **not associated with study_group** — it appears to be random visit-day logistics, not systematic bias.

---

## 8. Caching Behavior

All loaders use module-level `_cache` dicts for in-memory caching:

| Module | What's cached | Approximate memory |
|---|---|---|
| `participants.py` | participants DataFrame | ~1 MB |
| `clinical.py` | 6 OMOP DataFrames | ~300 MB (observation.csv is largest) |
| `ecg.py` | ECG manifest DataFrame | ~5 MB |
| `cgm.py` | CGM manifest DataFrame | ~1 MB |
| `wearable.py` | Wearable manifest DataFrame | ~2 MB |
| `environment.py` | Environment manifest DataFrame | ~1 MB |
| `retinal.py` | 4 retinal manifest DataFrames | ~200 MB |
| `concepts.py` | Concept mapping dicts | <1 MB |

**Total manifest/table cache:** ~500 MB when fully loaded.

**Not cached:** per-participant raw data (ECG signals, CGM JSONs, wearable JSONs, environmental CSVs, DICOM pixels). These are loaded from disk on each call.

**Parquet caches on disk:**
- `results/features/feature_matrix.parquet` (179 KB) — rebuilt by `build_feature_matrix()`
- `results/features/participant_index.parquet` (179 KB) — rebuilt by `build_participant_index()`

Caches are **not automatically invalidated** when source data changes. Use `force_reload=True` on `load_participants()` or delete the Parquet files and re-run the builders.

---

## 9. Current Limitations

### Implemented Beyond The Base Loaders

The base loader layer is no longer the full project boundary. Several features
that were once listed as future work now exist in separate analysis modules:

- `scripts/aging_features_batch.py`: CGM summaries, wearable circadian metrics,
  sleep architecture, per-day wearable summaries, environment summaries, and
  ECG interval features.
- `scripts/aging_scores.py`: clinical composite scores including KDM,
  allostatic load, frailty, HOMA-IR, TyG, QUICKI, pulse pressure, and UACR.
- `scripts/retinal_age.py` and `scripts/cardiac_age.py`: pretrained embedding
  extraction and age-clock heads when local model weights/artifacts are present.
- `scripts/coupling/`: cross-modal coupling and predictability analyses.
- `scripts/hypothesis/`: hypothesis-driven feature extraction and
  postprocessing scripts.
- `foundation_jepa/`: experimental PyTorch datasets, encoders, negative
  controls, and Slurm launchers for multimodal representation learning.

### Remaining Gaps

These are still real gaps or areas that need stronger validation:

**Derived and signal-processing features:**
- ECG HRV depends on optional signal-processing support and quality checks.
- Environmental light channels still need validated melanopic-lux conversion.
- OCTA vessel segmentation, FAZ measurement, FLIO decay fitting, and DR grading
  are not implemented as validated pipelines.
- Cross-modal analyses exist, but causal interpretation remains exploratory.

**ML and foundation-model pipeline:**
- JEPA stacks are experimental scaffolds, not locked production training
  pipelines.
- Generated sequence caches, checkpoints, logs, and summaries are local
  artifacts and should not be committed.
- Learned embeddings need negative controls, split-preserving evaluation, and
  comparison against classical feature baselines before scientific claims.

**Statistical utilities:**
- Propensity score matching and formal power analysis remain planned utilities.
- Sex-specific formulas remain unsupported unless a validated sex variable is
  available in the local release.

### Design limitations

- **temporal.py** only aligns numeric columns. Categorical data (sleep stages, activity names) is dropped. Use interval-based DataFrames from wearable loaders directly for sleep/activity analysis.
- **No thread safety.** Module-level caches are not protected by locks. Do not use from concurrent threads.
- **No cache eviction.** Memory grows monotonically as more tables are loaded. Call `_cache.clear()` on individual modules if memory is a concern.
- **Feature matrix is static.** Adding new clinical columns requires extending
  `features.py` and rebuilding the Parquet. Many multimodal derived features
  now live in separate artifacts such as `results/features/multimodal_features.parquet`,
  coupling feature tables, or foundation-model caches.
