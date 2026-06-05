# Data Infrastructure Plan

> Detailed mapping of data structures and the loaders/utilities needed to work with AI-READI v3.0.0.
>
> **Status (2026-04-16):** Layers 1–3 implemented. Derived features include:
> - Clinical feature matrix (`features.py`, 2280 × 125)
> - Cohort comparison framework (`cohort.py`)
> - Full CGM metrics: 5-level TIR, GRI, LBGI/HBGI, GMI, MAGE, AGP percentile
>   curves, dawn phenomenon, data completeness (`loaders/cgm.py`)
> - Wearable per-night sleep architecture (TST/SE/WASO/SOL/REM%/Deep%/N_awakenings/
>   sleep midpoint), per-day summaries (HR day/night, resting HR, nocturnal dip,
>   SpO2, T90, stress, RR, daily steps, sleep hours), and circadian metrics
>   (IS/IV/M10/L5/RA + cosinor A/φ/M) in `features_wearable.py`
> - Timezone lookup via `utils/timezone.py` (UW/UCSD → PST, UAB → CST)
> - Temporal alignment in `utils/temporal.py`
>
> Layer 4 (ML pipeline) not yet started. ECG HRV features (R-peak detection,
> SDNN/RMSSD/HF power) also deferred. See `docs/reference/LOADING.md` for the current
> API reference.

## Per-Modality Data Structures & Loader Requirements

---

### 1. participants.tsv (Join Key)

**Format:** TSV, 2,280 rows × 15 columns, zero nulls

| Column | Type | Notes |
|---|---|---|
| person_id | string | Primary key across all modalities |
| clinical_site | string | {UW, UCSD, UAB} |
| study_group | string | 4 diabetes severity levels |
| age | int | 40–94 |
| study_visit_date | date | YYYY-MM-DD, range 2023-07-18 to 2025-05-01 |
| recommended_split | string | {train, val, test} — 1576/352/352 |
| 9 boolean columns | bool | TRUE/FALSE per modality availability |

**Loader:** `pd.read_csv(path, sep='\t')` with dtype mapping. Convert booleans from string TRUE/FALSE.

---

### 2. Clinical Data (OMOP CDM)

**Format:** 6 CSV files, comma-delimited, RFC 4180 quoting

| File | Rows | Columns | Key Quirks |
|---|---|---|---|
| person.csv | 2,280 | 18 | All demographic concept_ids = 0 (redacted). birth_datetime = 1970-01-01 sentinel |
| visit_occurrence.csv | 4,519 | 17 | ~2 visits/person. discharged_to, preceding_visit are null |
| measurement.csv | 242,279 | 26 | **Leading `""` index column to skip.** 105 unique concepts. value_as_number 0.01% null. range_low/high ~53% null |
| observation.csv | 707,126 | 22 | **Leading `""` index column.** 244 unique concepts. value_as_string is polymorphic (numeric/date/text). unit_source_value 100% null |
| condition_occurrence.csv | 12,375 | 16 | 30 conditions, 2,189 persons (96%). condition_source_value has embedded commas in quotes |
| procedure_occurrence.csv | 49,879 | 16 | Only 3 unique procedure concepts. 90% = concept 4047085 (monofilament) |

**Loader needs:**
- Skip leading empty column in measurement.csv and observation.csv
- Parse concept IDs → human-readable labels (need concept mapping dict)
- Handle RFC 4180 quoting with embedded commas/newlines in source_value fields
- Parse measurement_source_value format: `"redcap_field, Human Label"` → split on first `, `
- Filter convenience functions: `get_measurements(person_id, concept_ids=None)`, `get_conditions(person_id)`

**Concept mapping priority:** Build a dict of the 105 measurement concepts and 244 observation concepts → human-readable names from the `measurement_source_value` / `observation_source_value` fields.

---

### 3. Cardiac ECG (WFDB)

**Format:** WFDB (.hea header + .dat binary), one recording per participant (6 have 2)

**Fixed parameters (no variation):**
- 12 leads: I, II, III, aVR, aVL, aVF, V1–V6
- 500 Hz, 5,500 samples (11 seconds)
- int16 little-endian, gain = 200 ADU/mV
- .dat always 132,000 bytes (12 × 5500 × 2)

**Variable parameters:**
- participant_position: {supine 60.9%, reclined 37.6%, slight recline 1.2%, sitting 0.3%}
- Cardiac measurements: Rate, PR (1.7% null), QRSD, QT, QTc, P (2.0% null), QRS, T (0.4% null)
- Interpretation comments: 1–3 diagnostic finding pairs
- interpretation_criteriaversion: {0B: 70%, 0C: 30%}

**Data on disk:**
- 2,264 .hea/.dat pairs across 2,251 participant dirs
- 7 extra files NOT in manifest (investigate or skip)
- Manifest has 2,257 rows (6 participants have 2 recordings)

**Loader needs:**
- Option A: `wfdb.rdrecord(record_path)` → wfdb Record object (recommended, handles all parsing)
- Option B: Direct binary read: `np.fromfile(dat_path, dtype='<i2').reshape(5500, 12)` then divide by 200.0 for mV
- Parse .hea comment lines for metadata: `Rate`, `PR`, `QTc`, `participant_position`, `interpretation_comment_*`
- Return: `(signal: np.ndarray[5500, 12], metadata: dict)` per recording
- Handle 6 participants with 2 recordings (return list)
- Skip 7 orphan files not in manifest

---

### 4. Wearable Activity Monitor (Garmin OMH JSON)

**Format:** 7 JSON files per participant, each with different schema

| Sub-modality | Body key | Record type | Value field | Unit | Sentinel |
|---|---|---|---|---|---|
| heart_rate | `body.heart_rate` | point (date_time) | `heart_rate.value` | beats/min | 0 |
| oxygen_saturation | `body.breathing` | point (date_time) | `oxygen_saturation.value` | % | — |
| respiratory_rate | `body.breathing` | point (date_time) | `respiratory_rate.value` | breaths/min | -1.0, -2.0 |
| stress | `body.stress` | point (date_time) | `stress.value` | stress level | -1 |
| sleep | `body.sleep` | interval (start/end) | `sleep_stage_state` | — | — |
| physical_activity | `body.activity` | interval (start/end) | `base_movement_quantity.value` | steps | empty string |
| physical_activity_calorie | `body.activity` | point (date_time) | `calories_value.value` | kcal | — |

**Common header fields:** uuid, creation_date_time, user_id, schema_id (sometimes empty), timezone (pst or cst)

**Loader needs:**
- Unified loader that normalizes all 7 sub-modalities into pandas DataFrames with columns: `(timestamp, value, unit)`
- For interval-based records (sleep, activity): expand to `(start_time, end_time, value/state, unit)`
- Filter sentinel values: drop records where value ∈ {-1, -2.0, 0 (for HR only), empty string}
- Parse timezone from header and convert UTC timestamps to local time if needed
- Return per-participant: `dict[str, pd.DataFrame]` keyed by sub-modality name

---

### 5. Continuous Glucose Monitoring (Dexcom OMH JSON)

**Format:** 1 JSON per participant, OMH blood-glucose v3.0

**Structure:**
```
header.timezone: "pst" or "cst"
header.acquistion_rate: {number_of_times: 1, time_window: {value: 5, unit: "min"}}
body.cgm[]: array of {
  effective_time_frame.time_interval.start_date_time (ISO 8601 UTC)
  event_type: "EGV"
  blood_glucose: {unit: "mg/dL", value: int}
  source_device_id: string
  transmitter_time: {unit: "long integer", value: int}
  transmitter_id: string
}
```

**Stats:** 2,245 participants. Typical 2,856 records (11 days). Range 334–2,856.

**Loader needs:**
- Parse JSON → `pd.DataFrame` with columns: `(timestamp, glucose_mg_dl, transmitter_id, device_id)`
- Extract timezone from header for local-time conversion
- Compute derived metrics: mean glucose, CV, TIR (time in range 70–180), MAGE, GRI
- Return: `pd.DataFrame` with DatetimeIndex

---

### 6. Environmental Sensor (CSV with header)

**Format:** CSV with 45-line `#` comment header, then 22 data columns

**Columns (22):**
- `ts`: UTC timestamp (YYYY-MM-DD hh:mm:ss)
- `lch0`–`lch11`: 10 spectral channels (415–910 nm), float 0–1 relative intensity
- `pm1`, `pm2.5`, `pm4`, `pm10`: particulate matter µg/m³
- `hum`: relative humidity (DOCUMENTED as 0–1 but ACTUAL data is 0–100 %)
- `temp`: ambient °C
- `voc`: VOC index (1–500)
- `nox`: NOx index (1–500, **frequent NaN**)
- `screen`: boolean 0/1
- `ff`: flicker Hz
- `inttemp`: internal temp °C

**Loader needs:**
- `pd.read_csv(path, comment='#', parse_dates=['ts'])` — skips 45 header lines automatically
- Handle NaN in nox column
- Extract metadata from header comments: sensor_id, sensor_location, participant_id, observation_count, extent_days
- Return: `(data: pd.DataFrame, metadata: dict)`
- NOTE: Do NOT divide humidity by 100 despite what the header says — actual values are already percentages

---

### 7. Retinal Imaging (DICOM)

**4 sub-modalities, all DICOM format:**

| Modality | Path | Devices | Manifest cols | Records | Per-file size |
|---|---|---|---|---|---|
| Structural OCT | retinal_oct/structural_oct/ | 4 | 15 | 56,477 | 5.6–51 MB |
| OCTA | retinal_octa/{enface,flow_cube,segmentation}/ | 4 | 47 | 24,560 | 60 KB–38 MB |
| Photography | retinal_photography/{cfp,faf,ir}/ | 6 | 11 | 93,920 | 578 KB–3 MB |
| FLIO | retinal_flio/flio/heidelberg_flio/ | 1 | 10 | 7,968 | ~134 MB |

**Manifest quirks:**
- OCTA manifest (47 cols) cross-references files across OCT, photography, and segmentation via SOP UIDs and file paths
- OCT manifest has `pixel_spacing` stored as string `[0.003872, 0.01206]` — needs `ast.literal_eval` or regex parsing
- OCT manifest has `reference_filepath` linking to IR images in retinal_photography/ir/
- `slice_thickness` is sometimes `"Not reported"` (string, not numeric)

**Photography sub-types:**
- CFP: color_channel_dimension=3 (RGB), 1776–3688 × 2368–3680 px
- FAF: color_channel_dimension=3 (RGB), 3288 × 3680 px (iCare Eidon only)
- IR: color_channel_dimension=0 (grayscale), 480–1536 × 512–1536 px

**FLIO specifics:**
- 4 files per participant: (long_wavelength, short_wavelength) × (L, R)
- 256 × 256 × 1024 frames per file
- ~134 MB per file, ~536 MB per participant
- 1,847 participants (81% coverage)

**Loader needs:**
- Manifest-first approach: parse manifest.tsv to get file paths + metadata, then load DICOM on demand
- `pydicom.dcmread(path)` for individual files → pixel_array
- For OCT volumes: return `np.ndarray[frames, height, width]`
- For OCTA: return enface projections as 2D arrays, flow_cube as 3D, segmentation as heightmaps
- For photography (CFP/FAF): return `np.ndarray[height, width, 3]` (RGB)
- For photography (IR): return `np.ndarray[height, width]` (grayscale)
- For FLIO: return `np.ndarray[256, 256, 1024]` — **lazy loading essential** (134 MB per file)
- Cross-modal linking: use OCTA manifest SOP UIDs to find associated OCT + IR + segmentation files
- Parse pixel_spacing from string list format

---

## Infrastructure Components to Build

### Layer 1: Core Data Access (build first)

```
scripts/
├── __init__.py
├── config.py              # DATA_ROOT, paths, constants
├── participants.py        # load_participants() → DataFrame
├── loaders/
│   ├── __init__.py
│   ├── clinical.py        # OMOP CSV loaders + concept mapping
│   ├── ecg.py             # WFDB loader → (signal, metadata)
│   ├── wearable.py        # 7 Garmin JSON sub-modalities → DataFrames
│   ├── cgm.py             # Dexcom JSON → DataFrame + derived metrics
│   ├── environment.py     # CSV with header → (DataFrame, metadata)
│   └── retinal.py         # DICOM manifest parser + lazy pixel loader
└── utils/
    ├── __init__.py
    ├── temporal.py         # Time alignment across modalities
    └── concepts.py         # OMOP concept_id → human label mapping
```

### Layer 2: Unified Participant View (build second)

```
scripts/
├── participant_index.py   # Join participants.tsv + all manifests → one-row-per-person Parquet
└── multimodal.py          # get_participant(person_id) → all modalities for one person
```

**participant_index.py** output: a single Parquet file with columns:
- All 15 columns from participants.tsv
- Per-modality file paths (from manifests)
- Per-modality summary stats (from manifests): avg HR, avg glucose, ECG Rate/QTc, etc.
- Temporal alignment: first/last timestamp per continuous modality, overlap window length

### Layer 3: Analysis Utilities (build third)

```
scripts/
├── cgm_metrics.py         # TIR, CV, MAGE, GRI, AGP from CGM DataFrame
├── ecg_features.py        # HRV, interval features from ECG signal
├── temporal_alignment.py  # Align CGM × wearable × environment on common time grid
└── cohort.py              # Filtering, stratification, train/val/test split helpers
```

### Layer 4: EDA Notebook (build alongside)

```
notebooks/
└── 01_eda.ipynb           # Cohort overview, missingness, distributions, cross-modal alignment demo
```

---

## Build Order

| Phase | Component | Depends on | Output |
|---|---|---|---|
| 1a | config.py | — | Path constants |
| 1b | participants.py | config | participants DataFrame |
| 1c | concepts.py | clinical CSVs | concept_id → label dict |
| 2a | clinical.py | config, concepts | OMOP query functions |
| 2b | ecg.py | config | ECG loader |
| 2c | cgm.py | config | CGM loader + metrics |
| 2d | wearable.py | config | Garmin loader |
| 2e | environment.py | config | Environmental loader |
| 2f | retinal.py | config | Manifest parser + lazy DICOM loader |
| 3 | participant_index.py | all loaders | Unified Parquet index |
| 4 | multimodal.py | all loaders, index | get_participant() API |
| 5 | temporal_alignment.py | cgm, wearable, environment | Aligned time-series matrix |
| 6 | 01_eda.ipynb | all above | Cohort overview + validation |

---

## Key Design Decisions

1. **Manifest-first, not filesystem-walk.** Always parse manifest.tsv to discover files; never walk directories. Manifests are the authoritative index.

2. **Lazy loading for imaging.** Never load all DICOM pixels into memory. Parse manifests eagerly, load pixel_array on demand via `get_image(filepath)`.

3. **Parquet for derived tables.** All joined/computed tables stored as Parquet in results/ for fast reload.

4. **Sentinel value filtering at load time.** Each loader strips its modality's sentinel values (HR=0, stress=-1, RR=-2, nox=NaN) and documents what was removed.

5. **UTC timestamps everywhere.** Store all timestamps as UTC. Timezone info from headers (pst/cst) stored as metadata but not applied to timestamps — alignment is simpler in UTC.

6. **person_id as string, not int.** Some operations are safer with string keys. Cast consistently at load time.
