# AI-READI Dataset Reference

> **Living document.** This file captures everything we've learned about the AI-READI dataset structure, modalities, formats, and storage organization. Extend as new findings emerge.

**Dataset version:** 3.0.0 (released 2025-11-17)
**DOI:** [10.60775/fairhub.3](https://doi.org/10.60775/fairhub.3)
**Local symlink:** `/oak/stanford/scg/lab_twc/mazijian/aireadi/data` → `/oak/stanford/scg/lab_twc/Albert/wearable/dataset`
**Size:** ~3.82 TB, 356,343 files
**Participants:** 2,280
**Collection period:** July 19, 2023 – May 1, 2025
**Data standard:** Clinical Dataset Structure (CDS) v0.1.1
**Schema reference:** https://schema.aireadi.org/v0.1.1/

---

## Table of Contents

1. [Study Background](#1-study-background)
2. [Cohort Overview](#2-cohort-overview)
3. [Dataset Root Files](#3-dataset-root-files)
4. [Directory Organization](#4-directory-organization)
5. [Modality 1 — Clinical Data (OMOP CDM)](#5-modality-1--clinical-data-omop-cdm)
6. [Modality 2 — Cardiac ECG (WFDB)](#6-modality-2--cardiac-ecg-wfdb)
7. [Modality 3 — Retinal Structural OCT (DICOM)](#7-modality-3--retinal-structural-oct-dicom)
8. [Modality 4 — Retinal OCTA (DICOM)](#8-modality-4--retinal-octa-dicom)
9. [Modality 5 — Retinal Photography (DICOM)](#9-modality-5--retinal-photography-dicom)
10. [Modality 6 — Retinal FLIO (DICOM)](#10-modality-6--retinal-flio-dicom)
11. [Modality 7 — Wearable Activity Monitor (Open mHealth JSON)](#11-modality-7--wearable-activity-monitor-open-mhealth-json)
12. [Modality 8 — Continuous Glucose Monitoring (Open mHealth JSON)](#12-modality-8--continuous-glucose-monitoring-open-mhealth-json)
13. [Modality 9 — Environmental Sensor (CSV)](#13-modality-9--environmental-sensor-csv)
14. [Temporal Alignment of Continuous Modalities](#14-temporal-alignment-of-continuous-modalities)
15. [Manifest Files Index](#15-manifest-files-index)
16. [Known Limitations](#16-known-limitations)
17. [Published Literature](#17-published-literature)

---

## 1. Study Background

**Full name:** Artificial Intelligence Ready and Exploratory Atlas for Diabetes Insights (AI-READI)

**Funding:** NIH grant 1OT2OD032644 (Bridge2AI Common Fund)

**Goal:** Create a flagship, ethically-sourced, demographically balanced multimodal dataset for Type 2 Diabetes (T2DM) AI/ML research. Primary scientific aim is to understand **salutogenesis** — the pathway from T2DM back to health.

**Principal Investigator:** Aaron Lee, MD (Washington University in St. Louis, ORCID: 0000-0002-7452-1648)

**Clinical Trial ID:** [NCT06002048](https://classic.clinicaltrials.gov/ct2/show/NCT06002048)

**Study Design:** Cross-sectional observational cohort study. ~10% of participants planned for longitudinal follow-up in Year 4.

**IRB:** University of Washington Study #00016228 (approved Dec 20, 2022)

**Clinical Recruitment Sites:**
- University of Washington (UW) — Seattle, WA
- University of California San Diego (UCSD)
- University of Alabama at Birmingham (UAB)

**Inclusion Criteria:**
- Age 40–85 years
- With or without Type 2 Diabetes
- Able to provide informed consent
- English-speaking

**Exclusion Criteria:** Pregnancy, gestational diabetes, Type 1 diabetes, age >85 or <40

---

## 2. Cohort Overview

### Participant Counts

| | |
|---|---|
| **Total** | 2,280 |
| **Age range** | 40–94 years (mean 60.85 ± 11.22) |
| **Clinical sites** | UW (798), UAB (800), UCSD (682) |

### By Diabetes Severity Group

| Group | N | % | Mean age |
|---|---|---|---|
| `healthy` (no DM) | 776 | 34.0% | 60.0 |
| `pre_diabetes_lifestyle_controlled` | 560 | 24.6% | 60.3 |
| `oral_medication_and_or_non_insulin_injectable_medication_controlled` | 686 | 30.1% | 62.1 |
| `insulin_dependent` | 258 | 11.3% | 61.2 |

### Recommended ML Splits

| Split | N | % | Purpose |
|---|---|---|---|
| `train` | 1,576 | 69.1% | Model training |
| `val` | 352 | 15.4% | Hyperparameter tuning |
| `test` | 352 | 15.4% | Final evaluation |

Val/test sets are balanced across sex, race/ethnicity, and diabetes status.

### Data Modality Coverage (per participant)

| Modality | Available | % |
|---|---|---|
| Clinical data | 2,280 | 100.0% |
| Retinal photography | 2,275 | 99.8% |
| Retinal OCT | 2,266 | 99.4% |
| Retinal OCTA | 2,264 | 99.3% |
| Cardiac ECG | 2,251 | 98.7% |
| CGM (blood glucose) | 2,245 | 98.5% |
| Environmental sensor | 2,231 | 97.9% |
| Wearable activity monitor | 2,184 | 95.8% |
| Retinal FLIO | 1,847 | 81.0% |

**Note on FLIO:** Lowest coverage because it's performed last in the clinic visit protocol — patient fatigue reduces compliance.

### Version History

| Version | Release | N | Key additions |
|---|---|---|---|
| v1.0.0 | 2024-05-03 | 204 | Pilot study |
| v2.0.0 | 2024-11-08 | 1,067 | Added Zeiss Cirrus OCT/OCTA |
| v3.0.0 | 2025-11-17 | 2,280 | Added Heidelberg OCTA, Garmin timezone support, field rename `participant_id` → `person_id` |

---

## 3. Dataset Root Files

Location: `/oak/stanford/scg/lab_twc/mazijian/aireadi/data/`

| File | Purpose |
|---|---|
| `README.md` | Human-readable overview of the dataset |
| `CHANGELOG.md` | Version history |
| `LICENSE.txt` | AI-READI Custom License v2.0 |
| `healthsheet.md` | Data quality/ethics sheet (Rostamzadeh et al. template) |
| `dataset_description.json` | Structured metadata: title, creators, DOI, consent |
| `study_description.json` | Study protocol, investigators, protocol version |
| `dataset_structure_description.json` | Detailed structure spec (47.8 KB) — authoritative folder layout |
| `participants.json` | Schema definition for participants.tsv fields |
| `participants.tsv` | Per-participant metadata table (244.9 KB, 2,280 rows) |

### `participants.tsv` Schema

**15 columns (tab-separated):**

```
person_id  clinical_site  study_group  age  study_visit_date  recommended_split  cardiac_ecg  clinical_data  environment  retinal_flio  retinal_oct  retinal_octa  retinal_photography  wearable_activity_monitor  wearable_blood_glucose
```

**Example row:**
```
1001  UW  pre_diabetes_lifestyle_controlled  69  2023-07-27  train  TRUE  TRUE  TRUE  TRUE  TRUE  TRUE  TRUE  FALSE  TRUE
```

- `person_id` — unique integer ID (formerly `participant_id` in v2.0)
- `clinical_site` — one of `UW`, `UCSD`, `UAB`
- `study_group` — one of 4 diabetes severity categories
- `age` — integer at time of visit
- `study_visit_date` — ISO date (YYYY-MM-DD) of the in-person clinical visit
- `recommended_split` — `train`, `val`, or `test`
- 9 boolean modality availability flags

---

## 4. Directory Organization

**Top-level layout under `/oak/stanford/scg/lab_twc/mazijian/aireadi/data/`:**

```
data/
├── README.md
├── CHANGELOG.md
├── LICENSE.txt
├── healthsheet.md
├── dataset_description.json
├── study_description.json
├── dataset_structure_description.json
├── participants.json
├── participants.tsv
│
├── clinical_data/                      # OMOP CDM CSVs + quality JSON
│   ├── person.csv
│   ├── observation.csv
│   ├── measurement.csv
│   ├── condition_occurrence.csv
│   ├── procedure_occurrence.csv
│   ├── visit_occurrence.csv
│   └── dqd_omop.json
│
├── cardiac_ecg/
│   ├── ecg_12lead/
│   │   └── philips_tc30/{person_id}/{person_id}_ecg_{uid}.{hea,dat}
│   └── manifest.tsv
│
├── retinal_oct/
│   ├── structural_oct/
│   │   ├── heidelberg_spectralis/{person_id}/*.dcm
│   │   ├── topcon_maestro2/{person_id}/*.dcm
│   │   ├── topcon_triton/{person_id}/*.dcm
│   │   └── zeiss_cirrus/{person_id}/*.dcm
│   └── manifest.tsv
│
├── retinal_octa/
│   ├── enface/{device}/{person_id}/*.dcm
│   ├── flow_cube/{device}/{person_id}/*.dcm
│   ├── segmentation/{device}/{person_id}/*.dcm
│   └── manifest.tsv
│
├── retinal_photography/
│   ├── cfp/
│   │   ├── icare_eidon/{person_id}/*.dcm
│   │   ├── optomed_aurora/{person_id}/*.dcm
│   │   ├── topcon_maestro2/{person_id}/*.dcm
│   │   └── topcon_triton/{person_id}/*.dcm
│   ├── faf/
│   │   └── icare_eidon/{person_id}/*.dcm
│   ├── ir/
│   │   ├── heidelberg_spectralis/{person_id}/*.dcm
│   │   ├── topcon_maestro2/{person_id}/*.dcm
│   │   ├── topcon_triton/{person_id}/*.dcm
│   │   └── zeiss_cirrus/{person_id}/*.dcm
│   └── manifest.tsv
│
├── retinal_flio/
│   ├── flio/
│   │   └── heidelberg_flio/{person_id}/*.dcm
│   └── manifest.tsv
│
├── wearable_activity_monitor/
│   ├── heart_rate/garmin_vivosmart5/{person_id}/{person_id}_heartrate.json
│   ├── oxygen_saturation/garmin_vivosmart5/{person_id}/{person_id}_oxygensaturation.json
│   ├── physical_activity/garmin_vivosmart5/{person_id}/{person_id}_activity.json
│   ├── physical_activity_calorie/garmin_vivosmart5/{person_id}/{person_id}_calorie.json
│   ├── respiratory_rate/garmin_vivosmart5/{person_id}/{person_id}_respiratoryrate.json
│   ├── sleep/garmin_vivosmart5/{person_id}/{person_id}_sleep.json
│   ├── stress/garmin_vivosmart5/{person_id}/{person_id}_stress.json
│   └── manifest.tsv
│
├── wearable_blood_glucose/
│   ├── continuous_glucose_monitoring/
│   │   └── dexcom_g6/{person_id}/{person_id}_DEX.json
│   └── manifest.tsv
│
└── environment/
    ├── environmental_sensor/
    │   └── leelab_anura/{person_id}/{person_id}_ENV.csv
    └── manifest.tsv
```

**Universal naming convention:** `{datatype}/{modality}/{device}/{person_id}/{data_files}`

---

## 5. Modality 1 — Clinical Data (OMOP CDM)

**Path:** `clinical_data/`
**Format:** CSV files conforming to OMOP Common Data Model
**Coverage:** 100% of participants (2,280)

### Files

| File | Size | Records | Unique persons |
|---|---|---|---|
| `person.csv` | 137 KB | 2,280 | 2,280 |
| `visit_occurrence.csv` | 643 KB | 4,519 | 2,280 |
| `measurement.csv` | 36.6 MB | 242,279 | 2,274 |
| `observation.csv` | 113.3 MB | 707,126 | 2,280 |
| `condition_occurrence.csv` | 1.8 MB | 12,375 | 2,189 |
| `procedure_occurrence.csv` | 7.3 MB | 49,879 | 2,268 |
| `dqd_omop.json` | 2.2 MB | — | — |

### `person.csv`

**18 columns:** `person_id, gender_concept_id, year_of_birth, month_of_birth, day_of_birth, birth_datetime, race_concept_id, ethnicity_concept_id, location_id, provider_id, care_site_id, person_source_value, gender_source_value, gender_source_concept_id, race_source_value, race_source_concept_id, ethnicity_source_value, ethnicity_source_concept_id`

**Sample row:**
```
7117, 0, 1948, 0, 0, 1970-01-01 00:00:00, 0, 0, 0, 0, 0, , , 0, , 0, , 0
```

**Important:** In the public release, `gender_concept_id`, `race_concept_id`, `ethnicity_concept_id` are all set to `0` (redacted). Sex and race/ethnicity are only available in the controlled-access version. Use the `study_group` column in `participants.tsv` as the primary phenotype for modeling.

### `measurement.csv`

**26 columns** (standard OMOP): `measurement_id, person_id, measurement_concept_id, measurement_date, measurement_datetime, measurement_time, measurement_type_concept_id, operator_concept_id, value_as_number, value_as_concept_id, unit_concept_id, range_low, range_high, provider_id, visit_occurrence_id, visit_detail_id, measurement_source_value, measurement_source_concept_id, unit_source_value, unit_source_concept_id, value_source_value, measurement_event_id, meas_event_field_concept_id, qualifier_concept_id, qualifier_source_value`

**105 unique `measurement_concept_id` values.** Categories include:

- **Ophthalmology / vision:** Visual acuity letter scores (photopic & mesopic, OD/OS), LogMAR, contrast sensitivity (MLCS, PLCS, LLVA), autorefraction (sphere/cylinder/axis)
- **Complete blood count:** WBC, RBC, Hb, Hct, MCV, MCH, MCHC, RDW, platelets
- **Metabolic panel:** Glucose, creatinine, BUN, Na, K, Cl, CO2, Ca
- **Hepatic function:** ALT, AST, Alk Phos, total/direct bilirubin, albumin, globulin, total protein
- **Lipid panel:** Total cholesterol, HDL, LDL, triglycerides
- **Renal function:** BUN, creatinine, BUN/Cr ratio
- **Cardiac / inflammatory:** CRP, troponin T, NT-proBNP
- **Endocrine:** Glucose, HbA1c, insulin, C-peptide
- **Urine:** Albumin, creatinine
- **Anthropometry:** Height, weight, BMI, waist/hip circumference, WHR
- **Vitals (measured 2×/visit):** Systolic BP, diastolic BP, heart rate
- **Diabetic neuropathy screening:** Monofilament tests (10 sites each foot)

**Sample row (visual acuity, right eye):**
```
1, 3, 7117, 2005200042, 2023-12-12, 2023-12-12 08:19:00, , 32862, 0, 89.0, 0, 0, , , 0, 2, 0, "viaodplog, VA Letter Score - Photopic VA - OD", 0, , 0, , 0, 0, 45876703, Right eye
```

The `measurement_source_value` contains a REDCap field code followed by a human label.

### `observation.csv`

**22 columns.** **244 unique `observation_concept_id` values.** Contains survey responses, imaging acquisition flags, and medical history entries:

- **Retinal imaging flags** — which scans were acquired (both eyes): OptoMed disc/macula CFP, Eidon UWF (IR/FAF/CFP central/nasal/temporal), Spectralis OCT/OCTA (ONH/posterior pole macula/macula), Cirrus OCT/OCTA (macula cube/disc cube/6x6), Maestro2 3D (wide/macula/OCTA), Triton (3D+radial/macula OCTA), FLIO macula-HS
- **Medical history:** 30 comorbidity flags — cardiac events, diabetes, hypertension, arthritis, cancer, pulmonary, neurological, eye conditions, GI, renal, hearing, etc.
- **CES-D-10 depression survey:** 10 items (ces1–ces10) plus total score
- **Montreal Cognitive Assessment (MoCA):** Clock drawing, 3D cube, delayed recall, digit span, language/fluency, letter A fluency, memory trials, abstraction, orientation, total score
- **Demographics survey:** Enrollment date and IDs
- **Lifestyle:** Smoking history/stage, alcohol use, physical activity

**Sample row:**
```
1, 3, 7117, 2005200289, 2023-12-12, 2023-12-12 00:00:00, 32862, 1, 1.0, 45877994, 45876703, 0, 0, 2, 0, "rtop_odd, OptoMed-Disc centered-CFP", 0, , Right eye, , 0, 0
```

### `condition_occurrence.csv`

**16 columns.** **30 distinct conditions.** Top 10 by prevalence:

| Rank | Condition | Code | N | % of cohort |
|---|---|---|---|---|
| 1 | Elevated A1c | `mh_a1c` | 1,202 | 52.7% |
| 2 | Hypertension | `mhoccur_hbp` | 1,151 | 50.5% |
| 3 | Dyslipidemia | `mhoccur_clsh` | 1,145 | 50.2% |
| 4 | Arthritis/joint pain | `mhoccur_ra` | 941 | 41.3% |
| 5 | Type II diabetes | `mhterm_dm2` | 899 | 39.4% |
| 6 | Obesity | `mhoccur_obs` | 845 | 37.1% |
| 7 | Dry eye disease | `mhoccur_ded` | 741 | 32.5% |
| 8 | Cataracts | `mhoccur_crt` | 688 | 30.2% |
| 9 | Prediabetes | `mhterm_predm` | 555 | 24.3% |
| 10 | Urinary problems | `mhoccur_ua` | 517 | 22.7% |

Other conditions tracked: digestive problems, cancer, hearing impairment, other cardiac, chronic pulmonary, osteoporosis, renal problems, circulation, glaucoma, CNS/neurological, lower back pain, MI, AMD, stroke, diabetic retinopathy, cognitive impairment, RVO, MS, Parkinson's, Alzheimer's.

**Sample row:**
```
3, 7117, 2005200627, 2023-10-11, 2023-10-11 00:00:00, 2023-10-11, 2023-10-11 00:00:00, 45905770, 32893, , 0, 2, 0, "mhoccur_cvdot, Other heart issues (Examples: pace", 0,
```

### `procedure_occurrence.csv`

**16 columns.** Dominated by monofilament neuropathy testing:

- **Right foot:** 22,680 records — 10 sites tested per foot (`mssrf1`–`mssrf10`)
- **Left foot:** 22,670 records (`msslf1`–`msslf10`)
- **Primary procedure concept:** 4047085

**Sample row:**
```
3, 7117, 4047085, 2023-12-12, 2023-12-12 00:00:00, 2023-12-12, 2023-12-12 00:00:00, 32862, 2005200605, 1, 0, 2, 0, "mssrf1, Site 1", 0, right foot - site 1
```

### `visit_occurrence.csv`

**17 columns.** **4,519 visits across 2,280 patients** (~2 per patient).

**Two visit types dominate:**
- `pacmpdat, Date Assessment Performed` — the in-clinic visit day (2,280 visits)
- `lbdattim2, Date & Time Draw Performed` — lab draw (2,239 visits)

**Date range:** 2022-04-16 to 2025-06-06

### `dqd_omop.json`

Data Quality Dashboard output from OMOP CDM validation. Executed 2025-11-08 05:35:03 to 05:39:58. All table-existence checks passed.

---

## 6. Modality 2 — Cardiac ECG (WFDB)

**Path:** `cardiac_ecg/ecg_12lead/`
**Device:** Philips PageWriter TC30
**Format:** WFDB (WaveForm Database) — `.hea` header + `.dat` binary
**Coverage:** 2,251 participants (98.7%)

### Layout

```
cardiac_ecg/
├── ecg_12lead/
│   └── philips_tc30/
│       ├── 1001/
│       │   ├── 1001_ecg_25aafb4b.hea
│       │   └── 1001_ecg_25aafb4b.dat
│       ├── 1002/
│       └── ...
└── manifest.tsv
```

**File naming:** `{person_id}_ecg_{8-hex-uid}.{hea,dat}`

### Recording Specs

| | |
|---|---|
| Leads | 12 (I, II, III, aVR, aVL, aVF, V1–V6) |
| Sampling rate | 500 Hz |
| Duration | 11 seconds (5,500 samples per channel) |
| Bit depth | 16-bit |
| Gain | 200 ADU/mV |
| Filters | High-pass 0.15 Hz, Low-pass 100 Hz, Notch 60 Hz |
| Patient position | Supine (0°) or reclined (30°) |

### `.hea` File Format

```
1001_ecg_25aafb4b 12 500 5500              ← record_name num_signals fs num_samples
1001_ecg_25aafb4b.dat 16 200(0)/mV 16 0 3 31683 0 I       ← signal 1 (lead I)
1001_ecg_25aafb4b.dat 16 200(0)/mV 16 0 -19 54578 0 II    ← signal 2 (lead II)
... (10 more signal lines for III, aVR, aVL, aVF, V1–V6)
# manufacturer: Philips
# device_model: PageWriter TC30
# modality: ECG
# participant_id: 1001
# participant_position: 0 degrees (supine)
# Rate: 60            ← HR (bpm)
# PR: 159             ← PR interval (ms)
# QRSD: 85            ← QRS duration (ms)
# QT: 403             ← QT interval (ms)
# QTc: 403            ← corrected QT (ms)
# P: 72               ← P wave (ms)
# QRS: 48             ← QRS amplitude (ms)
# T: 76               ← T wave (ms)
# report_description: Standard 12 Lead Report
# interpretation_comment_1: Unconfirmed Diagnosis
# interpretation_comment_2: - OTHERWISE NORMAL ECG -
# comment_1_key: Sinus rhythm
# validation_id: 50cff8d7912d47c1926b4bf439b17e7e
# validation_date: 20241014
... (many more metadata comment lines)
```

**Device measurements embedded in header:** Rate, PR, QRSD, QT, QTc, P, QRS, T, plus automated interpretation text and validation IDs.

### `manifest.tsv` (22 columns)

```
person_id, modality, wfdb_hea_filepath, wfdb_dat_filepath,
machine_text, machine_detail_description, device_documentation_type_and_version,
interpretation_criteriaversion, patient_criteriaversion, internalmeasurements_version,
participant_position, Rate, PR, QRSD, QT, QTc, P, QRS, T,
report_description, manufacturer, manufacturers_model_name
```

---

## 7. Modality 3 — Retinal Structural OCT (DICOM)

**Path:** `retinal_oct/structural_oct/`
**Devices:** 4 (Heidelberg Spectralis, Topcon Maestro2, Topcon Triton, Zeiss Cirrus)
**Format:** DICOM
**Coverage:** 2,266 participants (99.4%)
**Files:** ~80,861 DICOM files on disk (manifest lists 56,477 rows — difference includes multi-frame reference images not separately indexed)
**Size:** ~1.32 TB

### Layout

```
retinal_oct/
├── structural_oct/
│   ├── heidelberg_spectralis/{person_id}/*.dcm
│   ├── topcon_maestro2/{person_id}/*.dcm
│   ├── topcon_triton/{person_id}/*.dcm
│   └── zeiss_cirrus/{person_id}/*.dcm
└── manifest.tsv
```

### File Naming Convention

**Pattern:** `{person_id}_{device}_{anatomic_region}_{quality}_{scan_type}_{laterality}_{SOP_UID}.dcm`

**Examples (Heidelberg Spectralis, participant 1001):**
```
1001_spectralis_onh_rc_hr_oct_oct_l_1.3.6.1.4.1.33437.11.4.7587979.98316546453556.22400.4.1.dcm
1001_spectralis_ppol_mac_hr_oct_oct_r_1.3.6.1.4.1.33437.11.4.7587979.66636867678269.22400.4.1.dcm
```

**Decoding the name segments:**
- `onh` = optic nerve head, `ppol_mac` = posterior pole macula
- `rc` = radial circle, `hr` = high-resolution
- `oct` = OCT scan
- `l`/`r` = left/right eye

**Topcon Maestro2 examples:**
```
1001_maestro2_3d_macula_oct_l_2.16.840.1.114517.10.5.1.4.907063120230727165807.1.1.dcm
1001_maestro2_3d_wide_oct_r_2.16.840.1.114517.10.5.1.4.907063120230727165917.1.1.dcm
1001_maestro2_macula_6x6_oct_l_2.16.840.1.114517.10.5.1.4.907063120230727170313.1.1.dcm
```

### Scan Protocols Captured

| Protocol | Count |
|---|---|
| Optic disc (ONH) | 13,836 |
| Macula standard | 13,481 |
| Macula 6×6 mm | 13,320 |
| Optic disc 6×6 mm | 4,427 |
| Wide field | 4,601 |
| Macula 12×12 mm | 4,471 |
| Macula 20×20 mm | 2,341 |

### Image Characteristics

- **File sizes:** 5.8 MB – 25.5 MB per scan
- **Image dimensions:** 496–1024 × 200–768 pixels
- **Frames per volume:** 27–512 B-scans

### `manifest.tsv` (15 columns)

```
person_id, manufacturer, manufacturers_model_name, anatomic_region, imaging, laterality,
height, width, number_of_frames, pixel_spacing, slice_thickness,
sop_instance_uid, filepath, reference_instance_uid, reference_filepath
```

**Key:** `reference_filepath` links each OCT volume to the corresponding IR reflectance image in `retinal_photography/ir/` for spatial context.

**Sample row:**
```
1001, Heidelberg, Spectralis, Macula, OCT, L, 496, 768, 60, [0.003872, 0.01206], 0.128469,
1.3.6.1.4.1.33437.11.4.7587979.86599875670063.22400.4.1,
/retinal_oct/structural_oct/heidelberg_spectralis/1001/1001_spectralis_ppol_mac_hr_oct_oct_l_1.3.6.1.4.1.33437.11.4.7587979.86599875670063.22400.4.1.dcm,
1.3.6.1.4.1.33437.11.4.7587979.86599875670060.22400.4.0.0,
/retinal_photography/ir/heidelberg_spectralis/1001/1001_spectralis_ppol_mac_hr_oct_ir_l_1.3.6.1.4.1.33437.11.4.7587979.86599875670060.22400.4.0.0.dcm
```

---

## 8. Modality 4 — Retinal OCTA (DICOM)

**Path:** `retinal_octa/`
**Devices:** Same 4 as OCT (Heidelberg Spectralis, Topcon Maestro2, Topcon Triton, Zeiss Cirrus)
**Format:** DICOM
**Coverage:** 2,264 participants (99.3%)
**Files:** ~220,876 DICOM files
**Size:** ~1.16 TB

### 3 Sub-modalities

```
retinal_octa/
├── enface/{device}/{person_id}/*.dcm           ← 2D en-face projections
├── flow_cube/{device}/{person_id}/*.dcm        ← 3D volumetric blood flow
├── segmentation/{device}/{person_id}/*.dcm     ← Layer heightmaps
└── manifest.tsv
```

### File Naming

**Enface pattern:** `{person_id}_{device}_{region}_{size}_enface_{laterality}_{UID}.dcm`

**Example (Topcon Maestro2, 6×6 macula):**
```
1001_maestro2_macula_6x6_enface_l_2.16.840.1.114517.10.5.1.4.907063120230727170313.6.3.dcm
1001_maestro2_macula_6x6_enface_l_2.16.840.1.114517.10.5.1.4.907063120230727170313.6.4.dcm
1001_maestro2_macula_6x6_enface_l_2.16.840.1.114517.10.5.1.4.907063120230727170313.6.5.dcm
1001_maestro2_macula_6x6_enface_l_2.16.840.1.114517.10.5.1.4.907063120230727170313.6.80.dcm
```

The trailing `.3`, `.4`, `.5`, `.80` distinguish different vascular layer projections.

**Segmentation pattern:** `{person_id}_{device}_{region}_{size}_octa_segmentation_{laterality}_{UID}.dcm`

### What Each Layer Captures

The 4 en-face projections per scan typically include:
1. **Superficial vascular plexus** (ILM → outer IPL)
2. **Deep capillary plexus** (outer IPL → outer IPL)
3. **Choriocapillaris** (outer RPE → outer RPE)
4. **Avascular complex** (outer IPL → outer RPE)

### Flow Cube Specs
- Dimensions: 320–512 × 360–885 pixels, 320–360 frames
- File sizes: 8–39 MB

### Segmentation Specs
- Heightmaps with 2–10 segmentation surfaces
- Key layer boundaries: ILM, IPL surfaces, RPE
- File size: ~4.6 MB

### `manifest.tsv` — 47 columns

This is the richest manifest file. It cross-references:

- `flow_cube_*` fields for the 3D volume
- `associated_structural_oct_*` link to matching OCT volume
- `associated_retinal_photography_*` link to registered IR image
- `associated_segmentation_*` for layer boundaries
- `associated_enface_1_*` through `associated_enface_4_*` for each vascular layer:
  - `ophthalmic_image_type` (e.g., "Superficial vascular plexus flow")
  - `segmentation_surface_1` / `segmentation_surface_2` (e.g., "Ilm - internal limiting membrane", "Outer surface of ipl")
  - `sop_instance_uid` and `file_path`

**Cross-modal linking** — one row in `retinal_octa/manifest.tsv` references files in `retinal_oct/`, `retinal_photography/`, and `retinal_octa/segmentation/`.

---

## 9. Modality 5 — Retinal Photography (DICOM)

**Path:** `retinal_photography/`
**Format:** DICOM
**Coverage:** 2,275 participants (99.8%)
**Files:** ~121,907 DICOM files
**Size:** ~174 GB

### 3 Sub-types

| Sub-type | Description | Devices | Participants |
|---|---|---|---|
| **`cfp/`** | Color Fundus Photography | Optomed Aurora, iCare Eidon, Topcon Maestro2, Topcon Triton | ~8,797 (device-participant pairs) |
| **`faf/`** | Fundus Autofluorescence | iCare Eidon only | 2,199 |
| **`ir/`** | Infrared Reflectance | Heidelberg Spectralis, Topcon Maestro2, iCare Eidon, Zeiss Cirrus | ~9,044 |

### CFP — File Naming & Examples

**Pattern:** `{person_id}_{device}_{image_type}_cfp_{laterality}_{UID}.dcm`

**Image types:** `mosaic`, `uwf_central` (ultra-wide-field), `uwf_nasal`, `uwf_temporal`

**Example (iCare Eidon, participant 1001):**
```
1001_eidon_mosaic_cfp_l_1.2.826.0.1.3680043.8.641.1.20230809.2044.20521.dcm
1001_eidon_uwf_central_cfp_r_1.2.826.0.1.3680043.8.641.1.20230809.2041.31942.dcm
1001_eidon_uwf_nasal_cfp_l_1.2.826.0.1.3680043.8.641.1.20230809.2054.10612.dcm
1001_eidon_uwf_temporal_cfp_r_1.2.826.0.1.3680043.8.641.1.20230809.2038.72797.dcm
```

**File sizes:** 2–3 MB per image

### IR — File Naming & Examples

**Pattern:** `{person_id}_{device}_{region}_{...}_ir_{laterality}_{UID}.dcm`

Each OCT scan has a paired IR image. The IR image serves as the **en-face reference** overlaid on the OCT volume.

**Image dimensions:** 768×768 to 1536×1536 pixels

### `manifest.tsv` Columns

```
person_id, manufacturer, manufacturers_model_name, laterality, anatomic_region, imaging,
height, width, color_channel_dimension, sop_instance_uid, filepath
```

**Sample row (IR):**
```
1001, Heidelberg, Spectralis, L, Optic Disc, Infrared Reflectance, 1536, 1536, 0,
1.3.6.1.4.1.33437.11.4.7587979.98316546453553.22400.4.0.0,
/retinal_photography/ir/heidelberg_spectralis/1001/1001_spectralis_onh_rc_hr_oct_ir_l_1.3.6.1.4.1.33437.11.4.7587979.98316546453553.22400.4.0.0.dcm
```

---

## 10. Modality 6 — Retinal FLIO (DICOM)

**Path:** `retinal_flio/flio/heidelberg_flio/`
**Device:** Heidelberg FLIO (only one)
**Format:** DICOM
**Coverage:** 1,847 participants (81.0%) — **lowest coverage** due to protocol placement
**Files:** 7,968 DICOM files
**Size:** ~1.07 TB

### Layout

```
retinal_flio/
├── flio/
│   └── heidelberg_flio/
│       └── {person_id}/
│           ├── {person_id}_flio_long_wavelength_l_{UID}.dcm     (134 MB)
│           ├── {person_id}_flio_long_wavelength_r_{UID}.dcm     (134 MB)
│           ├── {person_id}_flio_short_wavelength_l_{UID}.dcm    (134 MB)
│           └── {person_id}_flio_short_wavelength_r_{UID}.dcm    (134 MB)
└── manifest.tsv
```

**Exactly 4 files per participant** — one per (wavelength × eye) combination.

### Image Specs

| | |
|---|---|
| Spatial dimensions | 256 × 256 pixels |
| Temporal frames | **1,024 frames** (temporal FLIM data per pixel) |
| Wavelength channels | 2 (long, short) |
| Laterality | L, R |
| File size | **~134 MB per image** |
| Total per participant | ~536 MB |

**What FLIO captures:** In vivo fluorescence lifetime of endogenous retinal fluorophores (lipofuscin and other autofluorescent compounds). The 1024 temporal frames represent the fluorescence decay curve at each pixel — this is what distinguishes it from simple autofluorescence imaging.

### `manifest.tsv` Columns

```
person_id, manufacturer, manufacturers_model_name, laterality, wavelength,
height, width, number_of_frames, sop_instance_uid, filepath
```

**Sample rows:**
```
1001, Heidelberg, Flio, L, Long wavelength, 256, 256, 1024, ..., /retinal_flio/flio/heidelberg_flio/1001/1001_flio_long_wavelength_l_....dcm
1001, Heidelberg, Flio, R, Long wavelength, 256, 256, 1024, ..., /retinal_flio/flio/heidelberg_flio/1001/1001_flio_long_wavelength_r_....dcm
1001, Heidelberg, Flio, L, Short wavelength, 256, 256, 1024, ..., /retinal_flio/flio/heidelberg_flio/1001/1001_flio_short_wavelength_l_....dcm
1001, Heidelberg, Flio, R, Short wavelength, 256, 256, 1024, ..., /retinal_flio/flio/heidelberg_flio/1001/1001_flio_short_wavelength_r_....dcm
```

---

## 11. Modality 7 — Wearable Activity Monitor (Open mHealth JSON)

**Path:** `wearable_activity_monitor/`
**Device:** Garmin Vivosmart 5 (wrist-worn)
**Format:** Open mHealth JSON schemas
**Coverage:** 2,184 participants (95.8%)
**Duration per participant:** 8–38 days (mean ~20 days)

### 7 Sub-modalities

```
wearable_activity_monitor/
├── heart_rate/garmin_vivosmart5/{person_id}/{person_id}_heartrate.json
├── oxygen_saturation/garmin_vivosmart5/{person_id}/{person_id}_oxygensaturation.json
├── physical_activity/garmin_vivosmart5/{person_id}/{person_id}_activity.json
├── physical_activity_calorie/garmin_vivosmart5/{person_id}/{person_id}_calorie.json
├── respiratory_rate/garmin_vivosmart5/{person_id}/{person_id}_respiratoryrate.json
├── sleep/garmin_vivosmart5/{person_id}/{person_id}_sleep.json
├── stress/garmin_vivosmart5/{person_id}/{person_id}_stress.json
└── manifest.tsv
```

**One JSON file per participant per measurement type.**

### Schemas (Open mHealth)

All JSONs follow the Open mHealth structure:
```json
{
  "header": {
    "uuid": "AIREADI-{person_id}",
    "creation_date_time": "ISO8601",
    "user_id": "AIREADI-{person_id}",
    "schema_id": { "namespace": "omh", "name": "...", "version": 2.0 },
    "timezone": "pst" | "cst"  // added in v3.0.0
  },
  "body": { <measurement-specific array> }
}
```

### Heart Rate (`omh/heart-rate v2.0`)

```json
{
  "body": {
    "heart_rate": [
      {
        "heart_rate": { "value": 87, "unit": "beats/min" },
        "effective_time_frame": { "date_time": "2023-08-30T16:17:45Z" }
      },
      ...
    ]
  }
}
```

**Sampling:** Variable, typically every few minutes during the day.

### Oxygen Saturation (`omh/oxygen-saturation v2.0`)

```json
{
  "body": {
    "breathing": [
      {
        "oxygen_saturation": { "value": 93, "unit": "%" },
        "effective_time_frame": { "date_time": "2023-08-31T07:10:45Z" },
        "measurement_method": "pulse oximetry"
      }
    ]
  }
}
```

### Physical Activity

```json
{
  "body": {
    "activity": [
      {
        "activity_name": "sedentary",
        "base_movement_quantity": { "value": 0, "unit": "steps" },
        "effective_time_frame": {
          "time_interval": {
            "start_date_time": "2023-08-30T16:09:45Z",
            "end_date_time": "2023-08-30T16:11:45Z"
          }
        }
      }
    ]
  }
}
```

### Physical Activity Calorie

Different structure from physical_activity. Uses `calories_value` (not `base_movement_quantity`), point timestamps (not intervals), and `schema_id.namespace: "ieee"`:

```json
{
  "body": {
    "activity": [
      {
        "activity_name": "kcal_burned",
        "calories_value": { "value": 5, "unit": "kcal" },
        "effective_time_frame": { "date_time": "2023-08-31T21:05:45Z" }
      }
    ]
  }
}
```

### Respiratory Rate (`omh/respiratory-rate v2.0`)

```json
{
  "body": {
    "breathing": [
      {
        "respiratory_rate": { "value": 16.5, "unit": "breaths/min" },
        "effective_time_frame": { "date_time": "2023-08-30T16:10:45Z" }
      }
    ]
  }
}
```

### Sleep (`omh/sleep-stages v2.0`)

```json
{
  "body": {
    "sleep": [
      {
        "sleep_stage_state": "deep",
        "effective_time_frame": {
          "time_interval": {
            "start_date_time": "2023-08-31T04:45:45Z",
            "end_date_time": "2023-08-31T04:47:45Z"
          }
        }
      }
    ]
  }
}
```

**Sleep stages:** `awake`, `light`, `deep`, `rem`

### Stress

```json
{
  "body": {
    "stress": [
      {
        "stress": { "value": 15, "unit": "stress level" },
        "effective_time_frame": { "date_time": "2023-08-30T16:11:45Z" }
      }
    ]
  }
}
```

### `manifest.tsv` — 27 columns

```
person_id, wrist_worn_on, dominant_hand,
heartrate_filepath, heartrate_record_count, average_heartrate_bpm,
oxygen_saturation_filepath, oxygen_saturation_record_count, average_oxygen_saturation_pct,
stress_level_filepath, stress_level_record_count, average_stress_level,
sleep_filepath, sleep_record_count, average_sleep_hours,
respiratory_rate_filepath, respiratory_rate_record_count, average_respiratory_rate_bpm,
physical_activity_filepath, physical_activity_num_days, average_daily_activity,
active_calories_filepath, active_calories_record_count, average_active_calories_kcal,
sensor_sampling_duration_days, manufacturer, manufacturer_model_name
```

**Sample row (participant 1023):**
```
1023, Left, Right,
/wearable_activity_monitor/heart_rate/garmin_vivosmart5/1023/1023_heartrate.json, 12780, 79.36,
/wearable_activity_monitor/oxygen_saturation/garmin_vivosmart5/1023/1023_oxygensaturation.json, 2193, 91.71,
/wearable_activity_monitor/stress/garmin_vivosmart5/1023/1023_stress.json, 24659, 15.37,
/wearable_activity_monitor/sleep/garmin_vivosmart5/1023/1023_sleep.json, 328, 0.28,
/wearable_activity_monitor/respiratory_rate/garmin_vivosmart5/1023/1023_respiratoryrate.json, 24642, 7.02,
/wearable_activity_monitor/physical_activity/garmin_vivosmart5/1023/1023_activity.json, 19, 7797.21,
/wearable_activity_monitor/physical_activity_calorie/garmin_vivosmart5/1023/1023_calorie.json, 1573, 294.11,
18, Garmin, Vivosmart 5
```

---

## 12. Modality 8 — Continuous Glucose Monitoring (Open mHealth JSON)

**Path:** `wearable_blood_glucose/continuous_glucose_monitoring/dexcom_g6/`
**Device:** Dexcom G6
**Format:** Open mHealth JSON (`omh/blood-glucose v3.0`)
**Coverage:** 2,245 participants (98.5%)
**Duration:** 9–12 days per participant (~2,800 readings)
**Sampling:** Every 5 minutes (bottleneck defined by sensor 10-day lifespan)

### Layout

```
wearable_blood_glucose/
├── continuous_glucose_monitoring/
│   └── dexcom_g6/
│       ├── 1001/
│       │   └── 1001_DEX.json
│       ├── 1002/
│       │   └── 1002_DEX.json
│       └── ...
└── manifest.tsv
```

**File naming:** `{person_id}_DEX.json`
**Average file size:** ~53,000 lines per file

### JSON Schema

```json
{
  "header": {
    "uuid": "AIREADI-1001",
    "creation_date_time": "2025-10-25T00:09:09Z",
    "patient_id": "AIREADI-1001",
    "schema_id": {
      "namespace": "omh",
      "name": "blood-glucose",
      "version": 3.0
    },
    "modality": "sensed",
    "acquistion_rate": {
      "number_of_times": 1,
      "time_window": { "value": 5, "unit": "min" }
    },
    "external_datasheets": {
      "datasheet_type": "source_device",
      "datasheet_reference": "iri-of-cgm-device"
    },
    "timezone": "pst"
  },
  "body": {
    "cgm": [
      {
        "effective_time_frame": {
          "time_interval": {
            "start_date_time": "2023-07-27T23:51:39Z",
            "end_date_time": "2023-07-27T23:51:39Z"
          }
        },
        "event_type": "EGV",
        "source_device_id": "PG15103578",
        "blood_glucose": { "unit": "mg/dL", "value": 113 },
        "transmitter_time": { "unit": "long integer", "value": 7573 },
        "transmitter_id": "352FG4"
      },
      { "event_type": "EGV", "blood_glucose": {"unit": "mg/dL", "value": 117}, ... },
      ...
    ]
  }
}
```

**Notes:**
- `event_type` is always `EGV` (Estimated Glucose Value)
- `unit` is always `mg/dL`
- The header field `acquistion_rate` (sic — typo preserved in the source schema)

### `manifest.tsv` — 8 columns

```
person_id, glucose_filepath, glucose_level_record_count, average_glucose_level_mg_dl,
glucose_sensor_sampling_duration_days, glucose_sensor_id,
manufacturer, manufacturer_model_name
```

**Sample rows:**
```
1001, /wearable_blood_glucose/continuous_glucose_monitoring/dexcom_g6/1001/1001_DEX.json, 2856, 123.30, 11, PG15103578, Dexcom, G6
1002, /wearable_blood_glucose/continuous_glucose_monitoring/dexcom_g6/1002/1002_DEX.json, 2844, 116.45, 11, PG15103578, Dexcom, G6
1003, /wearable_blood_glucose/continuous_glucose_monitoring/dexcom_g6/1003/1003_DEX.json, 2856, 208.08, 11, PG15103578, Dexcom, G6
```

---

## 13. Modality 9 — Environmental Sensor (CSV)

**Path:** `environment/environmental_sensor/leelab_anura/`
**Device:** LeeLab Anura (custom, HW v1.0.0, FW v1.2.4)
**Format:** CSV with 45-line metadata header comment block
**Coverage:** 2,231 participants (97.9%)
**Duration:** 7.6–13.6 days per participant (~130K–210K rows)
**Sampling:** Every 5 seconds

### Layout

```
environment/
├── environmental_sensor/
│   └── leelab_anura/
│       ├── 1001/
│       │   └── 1001_ENV.csv      (~27.7 MB, 173,314 observations)
│       ├── 1002/
│       └── ...
└── manifest.tsv
```

**File naming:** `{person_id}_ENV.csv`

### CSV Header Format (first 45 lines are `#` comments)

```
# header_lines: 45
# header_version: 1.1
# environmental_sensor_manufacturer: LeeLab
# environmental_sensor_device_model: Anura
# environmental_sensor_hardware_version: 1.0.0
# environmental_sensor_firmware_version: 1.2.4
# time_stamp_source: real time clock RTC programmed to match UTC with error < 120 seconds
# meta_sensor_sampling_interval: 5 seconds
# meta_sensor_id: F491437702FA6836
# meta_participant_id: 1001
# meta_sensor_location: dining room
# meta_number_of_observations: 173314
# meta_extent_of_observation_in_days: 10.0
# number_of_data_columns: 22
# data_column_list: ts,lch0,lch1,lch2,lch3,lch6,lch7,lch8,lch9,lch10,lch11,pm1,pm2.5,pm4,pm10,hum,temp,voc,nox,screen,ff,inttemp
# ts: timestamp UTC YYYY-MM-DD hh:mm:ss, study range 2023 through 2027, units seconds
# lch0: float [0.000 to 1.000] F1 center wavelength 415 nm, units relative intensity
# lch1: float [0.000 to 1.000] F2 center wavelength 445 nm, units relative intensity
... (column descriptions for all 22 columns)
```

### Data Columns (22 total)

| Column | Type | Range | Description |
|---|---|---|---|
| `ts` | timestamp | UTC, YYYY-MM-DD hh:mm:ss | Measurement timestamp |
| `lch0` | float | 0–1 | F1 spectral channel, 415 nm |
| `lch1` | float | 0–1 | F2, 445 nm |
| `lch2` | float | 0–1 | F3, 480 nm |
| `lch3` | float | 0–1 | F4, 515 nm |
| `lch6` | float | 0–1 | F5, 555 nm |
| `lch7` | float | 0–1 | F6, 590 nm |
| `lch8` | float | 0–1 | F7, 630 nm |
| `lch9` | float | 0–1 | F8, 680 nm |
| `lch10` | float | 0–1 | Clear (no filter) |
| `lch11` | float | 0–1 | NIR, 910 nm |
| `pm1` | uint16 | 0–65536 | PM₁.₀ particles (µg/m³) |
| `pm2.5` | uint16 | 0–65536 | PM₂.₅ particles |
| `pm4` | uint16 | 0–65536 | PM₄.₀ particles (estimated) |
| `pm10` | uint16 | 0–65536 | PM₁₀ particles (estimated) |
| `hum` | float | 0–100 | Relative humidity (%) |
| `temp` | float | −10 to 50 | Ambient temperature (°C), SEN55 |
| `voc` | int | 1–500 | VOC Index points |
| `nox` | int | 1–500 | NOx Index points |
| `screen` | bool | 0/1 | Screen on/off state |
| `ff` | int | 0–2000 | Flicker detection (Hz) |
| `inttemp` | float | 0–FF.FF | Internal case temp (°C) |

### Sample Data Rows

```
2023-07-28 03:08:07, 0.0023, 0.0027, 0.0037, 0.0052, 0.0073, 0.0090, 0.0121, 0.0168, 0.0398, 0.0206, 0.0000, 0.0000, 0.0000, 0.0000, 45.0100, 24.8200, 0.0000, nan, 1, 1, 23.7500
2023-07-28 03:08:12, 0.0022, 0.0028, 0.0038, 0.0055, 0.0073, 0.0086, 0.0120, 0.0158, 0.0395, 0.0233, 4.5000, 5.7000, 6.6000, 7.0000, 44.8200, 24.8200, 0.0000, nan, 1, 1, 23.7500
```

### `manifest.tsv` — 9 columns

```
person_id, modality, env_sensor_filepath, sensor_location,
number_of_observations, sensor_sampling_extent_in_days, sensor_id,
manufacturer, manufacturers_model_name
```

**Sample rows:**
```
1001, environmental_sensor, /environment/environmental_sensor/leelab_anura/1001/1001_ENV.csv, dining room, 173314, 10.0, F491437702FA6836, LeeLab, Anura
1002, environmental_sensor, /environment/environmental_sensor/leelab_anura/1002/1002_ENV.csv, living room, 131372, 7.6, C53FA70647A5D557, LeeLab, Anura
1003, environmental_sensor, /environment/environmental_sensor/leelab_anura/1003/1003_ENV.csv, middle of living room, 181779, 10.5, 2266534987D89137, LeeLab, Anura
```

**Sensor placement** is free-text (e.g., "dining room", "middle of their condo on a shelf") — quality varies.

---

## 14. Temporal Alignment of Continuous Modalities

**Finding:** All three continuous modalities (wearable, CGM, environmental) are collected **concurrently**, starting at the clinical visit date.

### Example: Participant 1023 (visit 2023-08-30)

```
Garmin wearable:   Aug 30 ──────────────────────── Sep 16  (17 days)
Dexcom CGM:        Aug 30 ──────────── Sep 09              (9.9 days)
Environmental:     Aug 30 ─────────────── Sep 11            (11.9 days)
                   ├─── 9.8 day triple overlap ──┤
```

### Aggregate (5-participant sample)

| Modality | Typical start | Duration | Driven by |
|---|---|---|---|
| Garmin wearable | Visit day | 17–25 days (mean 20.1) | Battery / participant compliance |
| Dexcom CGM | Visit day | 8.9–9.9 days (mean 9.7) | Sensor 10-day lifespan |
| Environmental sensor | Visit day | 9.8–13.6 days (mean 11.4) | Protocol design |

**Triple overlap:** 8.8–9.8 days (CV ~4%), very consistent across participants

### Within-Day Ordering

- Garmin initialized first on visit day
- CGM starts 1.6–3.3 hours after Garmin
- Environmental sensor starts 2.2–2.6 hours after CGM

### Anchoring Event

The clinical visit day (as recorded in `participants.tsv:study_visit_date`) is **day 1** of continuous recording. That same day includes:
- Lab draws → `clinical_data/measurement.csv`
- 12-lead ECG → `cardiac_ecg/`
- All retinal imaging → `retinal_oct/`, `retinal_octa/`, `retinal_photography/`, `retinal_flio/`

**Practical implication:** For any multimodal analysis combining CGM + activity + environment, you have a reliable **~10-day concurrent window** per participant, anchored to the full set of cross-sectional clinical/imaging measurements from day 1.

---

## 15. Manifest Files Index

Each modality has a top-level `manifest.tsv` file that acts as a lookup index. These are the fastest way to locate and filter data without walking the filesystem.

| Path | Size | Purpose |
|---|---|---|
| `cardiac_ecg/manifest.tsv` | 717 KB | ECG files + derived measurements (Rate, PR, QTc, etc.) |
| `retinal_oct/manifest.tsv` | 27 MB | OCT scan metadata + cross-reference to IR images |
| `retinal_octa/manifest.tsv` | 55 MB | OCTA flow cubes + enface layers + segmentation cross-refs |
| `retinal_photography/manifest.tsv` | 23.5 MB | Fundus, FAF, IR metadata |
| `retinal_flio/manifest.tsv` | 2 MB | FLIO wavelength/laterality index |
| `wearable_activity_monitor/manifest.tsv` | 1.4 MB | Per-participant summary stats for all 7 sub-measures |
| `wearable_blood_glucose/manifest.tsv` | ~100 KB | Per-participant CGM averages & sensor IDs |
| `environment/manifest.tsv` | ~200 KB | Per-participant sensor location & obs count |

**Always start with the manifest** when building a loader for any modality.

---

## 16. Known Limitations

### Data Content Limitations
- **Sex and race/ethnicity are redacted** from the public-release OMOP `person.csv`. The columns exist but contain `0`. Controlled-access version has them.
- **Medications** are also removed from the public version.
- **No free-text notes** — everything is structured/coded.
- **Cross-sectional design** — no per-participant longitudinal baselines (10% follow-up planned for Year 4).

### Recruitment / Sampling Biases
- **Urban hospital recruitment** at 3 academic medical centers — no rural or community populations.
- **Underrepresented groups:** Pacific Islanders, Native Americans.
- **English-speaking only.**
- **Age restricted to 40–85** at enrollment (9 records show age >85 due to timing edge cases).

### Device / Protocol Variability
- **FLIO coverage is only 81%** — performed last in the clinical visit protocol, so patient fatigue reduces compliance.
- **Image quality varies** due to undilated imaging and handheld device operator differences.
- **Some devices (FLIO, Spectralis) are operator-skill-dependent.**
- **Multi-device imaging per participant** — different participants may have different device coverage.

### License Constraints (public v3.0.0)
- Use **restricted to Type 2 Diabetes-related research only**
- Cannot share data with 3rd-party model vendors for weight modification
- Max **5 representative images/figures per publication**
- Cannot attempt to re-identify participants
- Cannot make clinical decisions from the data

### Data Quality Caveats
- `physical_activity_num_days` in wearable manifest is rounded (e.g., 19) while HR duration may span more/fewer days.
- Environmental sensor placement is free-text — quality varies (e.g., "dining room" vs. "middle of their condo on a shelf").
- JSON schema fields sometimes empty (`"namespace": ""`) for sleep/stress/activity — they don't fully conform to a published OMH version.
- Header field `acquistion_rate` (sic) in CGM JSONs — typo preserved.

---

## 17. Published Literature

- **Cross-sectional design and protocol paper:**
  [PMC11800295](https://pmc.ncbi.nlm.nih.gov/articles/PMC11800295/) |
  [PubMed](https://pubmed.ncbi.nlm.nih.gov/39915016/)

- **Nature Metabolism:** "AI-READI: Rethinking Data Collection, Preparation, and Sharing"
  [Nature article](https://www.nature.com/articles/s42255-024-01165-x) |
  [PubMed](https://pubmed.ncbi.nlm.nih.gov/39516364/)

- **IOVS/ARVO:** "Recruitment Strategy and Pilot Data"
  [IOVS article](https://iovs.arvojournals.org/article.aspx?articleid=2793859)

- **Healthsheet template:** Rostamzadeh et al. [arXiv:2202.13028](https://arxiv.org/abs/2202.13028)

### Online Resources

- **Docs:** https://docs.aireadi.org/
- **Website:** https://aireadi.org/
- **GitHub org:** https://github.com/AI-READI
- **Zenodo community:** https://zenodo.org/communities/aireadi
- **Clinical trial:** https://classic.clinicaltrials.gov/ct2/show/NCT06002048
- **Schema spec:** https://schema.aireadi.org/v0.1.1/

---

## Appendix: Quick-Reference Format Summary

| Modality | Format | Path pattern | Per-participant |
|---|---|---|---|
| Clinical | CSV (OMOP) | `clinical_data/*.csv` | Aggregated across all participants |
| ECG | WFDB (.hea+.dat) | `cardiac_ecg/ecg_12lead/philips_tc30/{id}/` | 1 recording (2 files) |
| OCT | DICOM | `retinal_oct/structural_oct/{device}/{id}/` | ~20–40 scans (multi-device, multi-protocol, both eyes) |
| OCTA | DICOM | `retinal_octa/{enface,flow_cube,segmentation}/{device}/{id}/` | ~40–80 files (3 sub-types × layers × eyes) |
| Retinal photo | DICOM | `retinal_photography/{cfp,faf,ir}/{device}/{id}/` | 10–30 images |
| FLIO | DICOM | `retinal_flio/flio/heidelberg_flio/{id}/` | Exactly 4 files (~536 MB total) |
| Wearable | JSON (OMH) | `wearable_activity_monitor/{sub}/garmin_vivosmart5/{id}/` | 7 JSON files |
| CGM | JSON (OMH) | `wearable_blood_glucose/continuous_glucose_monitoring/dexcom_g6/{id}/` | 1 JSON file (~53K lines) |
| Environment | CSV | `environment/environmental_sensor/leelab_anura/{id}/` | 1 CSV file (~130K–210K rows) |
