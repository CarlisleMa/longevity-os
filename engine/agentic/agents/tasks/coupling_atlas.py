"""Tier F: Physiological Coupling Atlas.

Goal: Build the first comprehensive map of inter-organ coupling across the
diabetes severity spectrum. Implements brainstorm Directions A-G from
BRAINSTORM_NETWORK_PHYSIOLOGY.md using the multi-agent architecture.

Architecture:
  Phase 1 (data extraction): Modality agents extract aligned time series
  Phase 2 (coupling computation): CausalAgent + new CouplingAgent compute
      pairwise coupling measures across 10 modality pairs
  Phase 3 (atlas assembly): CouplingAgent builds per-person coupling matrices,
      networks, and graph-theoretic biomarkers
  Phase 4 (coupling clock): AgingClockAgent trains coupling-based aging clock
  Phase 5 (phenotyping): PhenotypeAgent discovers coupling-based subtypes
  Phase 6 (causal architecture): CausalAgent runs CCM/PCMCI for causal graphs
  Phase 7 (exposome): EnvironmentAgent + CausalAgent test environment-physiology
      causal pathways
  Phase 8 (tensor modes): PhenotypeAgent runs tensor decomposition
  Phase 9 (validation + critique): CriticAgent reviews all findings

Each phase maps to one or more brainstorm Directions (A-G).
"""

from ..orchestrator import Orchestrator


# ---------------------------------------------------------------------------
# Modality pairs for the coupling atlas (10 undirected pairs)
# ---------------------------------------------------------------------------

MODALITY_PAIRS = [
    ("glucose", "hr"),
    ("glucose", "activity"),
    ("glucose", "sleep"),
    ("glucose", "environment"),
    ("hr", "activity"),
    ("hr", "sleep"),
    ("hr", "environment"),
    ("activity", "sleep"),
    ("activity", "environment"),
    ("sleep", "environment"),
]

# Coupling measures to compute per pair
COUPLING_MEASURES = [
    "cross_correlation",       # time-lagged Pearson r + optimal lag
    "wavelet_coherence",       # coupling at 4 frequency bands (Direction E)
    "transfer_entropy",        # directed information flow in bits/sample
    "cross_predictability",    # R^2 of Ridge predicting one from the other
    "phase_coherence_24h",     # coherence at the circadian frequency
]

# Frequency bands for wavelet coherence (Direction E)
FREQUENCY_BANDS = {
    "ultra_fast": "5-30 min",     # acute glucose-HR response
    "fast": "30 min - 3 h",       # postprandial dynamics
    "circadian": "12-36 h",       # daily rhythms
    "multi_day": "2-10 days",     # slow trends
}


# ---------------------------------------------------------------------------
# Phase 1: Data extraction (parallel, no dependencies)
# Direction A prerequisite
# ---------------------------------------------------------------------------

PHASE_1_EXTRACT = [
    # Step 0
    {
        "agent": "GlucoseAgent",
        "task": (
            "For ALL participants with CGM data (~2,245), compute per-person "
            "time-series features needed for coupling analysis: "
            "1. Raw 5-min glucose time series (for pairwise coupling) "
            "2. Per-person scalar summaries: mean_glucose, cv, tir, mage, gmi "
            "3. Circadian glucose profile via compute_cgm_circadian_metrics() "
            "   for all participants: dawn_phenomenon, nocturnal_mean, nocturnal_cv "
            "4. Multiscale entropy of glucose (using antropy.sample_entropy at "
            "   scales 1,2,4,8,16,32 corresponding to 5min-2.5h; Costa et al. 2014) "
            "Store summaries as workspace.dataframes['coupling_cgm_features']. "
            "Store the list of person_ids with valid CGM as workspace.dataframes['cgm_valid_pids']. "
            "Report: N with valid CGM, mean duration_days, mean n_readings."
        ),
        "depends_on": [],
    },
    # Step 1
    {
        "agent": "WearableAgent",
        "task": (
            "For ALL participants with wearable data (~2,184), compute: "
            "1. compute_circadian_metrics(pid) -> IS, IV, RA, cosinor_amplitude, "
            "   cosinor_acrophase for each person "
            "2. compute_daily_summary(pid) -> per-day: hr_mean_day, hr_mean_night, "
            "   resting_hr, nocturnal_hr_dip, daily_steps, sleep_hours, spo2_mean_night "
            "3. compute_sleep_architecture(pid) -> per-night: tst_min, se, waso_min, "
            "   rem_pct, deep_pct, sleep_midpoint_hr "
            "4. Multiscale entropy of HR (antropy.sample_entropy at scales "
            "   1,2,4,8,16 on the 1-min HR series; Goldberger et al. 2002) "
            "Store circadian metrics as workspace.dataframes['coupling_circadian_features']. "
            "Store daily summaries as workspace.dataframes['coupling_daily_wearable']. "
            "Store sleep architecture as workspace.dataframes['coupling_sleep_features']. "
            "Store the list of person_ids with valid wearable as "
            "workspace.dataframes['wearable_valid_pids']. "
            "Report: N with valid wearable, mean recording days."
        ),
        "depends_on": [],
    },
    # Step 2
    {
        "agent": "EnvironmentAgent",
        "task": (
            "For ALL participants with environment data (~2,231), compute per-person: "
            "1. Daily environmental summaries: mean_pm25, max_pm25, mean_temp, "
            "   temp_range, mean_humidity "
            "2. Circadian light metrics: daily_bright_light_hours (lch2 > threshold), "
            "   evening_light_mean (lch2 after 20:00 local), first_bright_light_hour "
            "3. Screen time: daily_screen_hours (screen column == 1) "
            "Store as workspace.dataframes['coupling_env_features']. "
            "Store valid person_ids as workspace.dataframes['env_valid_pids']. "
            "Report: N with valid environment data, mean recording days."
        ),
        "depends_on": [],
    },
    # Step 3
    {
        "agent": "ClinicalAgent",
        "task": (
            "Load the feature matrix. Extract per-person: person_id, age, "
            "study_group, clinical_site, recommended_split, hba1c, glucose, "
            "insulin, c_peptide, triglycerides, hdl, ldl, crp, bmi, waist_cm, "
            "sbp, dbp, ecg_rate, ecg_qtc, ecg_pr, ecg_qrsd. "
            "Compute HOMA-IR = (insulin * glucose) / 405 and "
            "TyG = ln(triglycerides * glucose) / 2. "
            "Store as workspace.dataframes['coupling_clinical_features']. "
            "Report: N with complete clinical data, group sizes."
        ),
        "depends_on": [],
    },
    # Step 4
    {
        "agent": "CardiacAgent",
        "task": (
            "Extract per-person ECG-derived features: ecg_rate, ecg_qtc, "
            "ecg_pr, ecg_qrsd. If neurokit2 is available, compute RMSSD from "
            "the 11-second ECG strips for participants with recordings. "
            "Store as workspace.dataframes['coupling_cardiac_features']. "
            "Report: N with valid ECG, summary statistics."
        ),
        "depends_on": [],
    },
]


# ---------------------------------------------------------------------------
# Phase 2: Pairwise coupling computation (Direction A core)
# Depends on Phase 1 completing. Uses CausalAgent for each modality pair.
# ---------------------------------------------------------------------------

PHASE_2_COUPLING = [
    # Step 5
    {
        "agent": "CausalAgent",
        "task": (
            "PAIRWISE COUPLING COMPUTATION — Glucose-HR pair.\n"
            "For all participants who have BOTH CGM and wearable HR data "
            "(intersect cgm_valid_pids and wearable_valid_pids), load "
            "aligned_timeseries(freq='5min') via get_participant(pid).\n\n"
            "Compute per-person (N-of-1) coupling measures:\n"
            "1. TIME-LAGGED CROSS-CORRELATION: scipy.signal.correlate on "
            "   z-scored glucose vs HR. Record peak_r and optimal_lag_min.\n"
            "2. TRANSFER ENTROPY (both directions): glucose->HR and HR->glucose.\n"
            "   Use tigramite if available, else pyinform. Record TE in bits/sample.\n"
            "3. CROSS-PREDICTABILITY: Ridge regression predicting HR from "
            "   lagged glucose features (lags 0,1,2,3 = 0-15min). Record R^2.\n"
            "   Then reverse: predict glucose from lagged HR. Record R^2.\n"
            "4. PHASE COHERENCE at 24h: scipy.signal.coherence at f=1/288 "
            "   (288 5-min bins per day). Record coherence magnitude.\n\n"
            "Start with a pilot of 50 participants (balanced across study_group) "
            "to validate, then scale to all.\n"
            "Store per-person results as workspace.dataframes['coupling_glucose_hr'] "
            "with columns: person_id, xcorr_r, xcorr_lag_min, te_glucose_to_hr, "
            "te_hr_to_glucose, xpred_hr_from_glucose_r2, xpred_glucose_from_hr_r2, "
            "phase_coherence_24h.\n"
            "Report: N computed, median coupling values, fraction with significant "
            "coupling (xcorr_r > 0.2)."
        ),
        "depends_on": [0, 1],
    },
    # Step 6
    {
        "agent": "CausalAgent",
        "task": (
            "PAIRWISE COUPLING — Glucose-Activity pair.\n"
            "For participants with both CGM and wearable data, use "
            "aligned_timeseries() and extract glucose + steps/calories.\n"
            "Compute the same 4 coupling measures as glucose-HR: "
            "cross-correlation, transfer entropy (both directions), "
            "cross-predictability (both directions), phase coherence at 24h.\n"
            "Also compute the ACTIVITY-GLUCOSE RESPONSE TIME: the lag (in minutes) "
            "at which activity most strongly predicts glucose reduction "
            "(Fabris et al. Sci Rep 2022 found shared variance even during sleep).\n"
            "Store as workspace.dataframes['coupling_glucose_activity'].\n"
            "Report: N, median coupling values."
        ),
        "depends_on": [0, 1],
    },
    # Step 7
    {
        "agent": "CausalAgent",
        "task": (
            "PAIRWISE COUPLING — Glucose-Sleep pair.\n"
            "For participants with both CGM and wearable sleep data, compute:\n"
            "1. NIGHTLY coupling: per-night sleep_efficiency vs next-day mean glucose, "
            "   next-day TIR, next-day CV. Use compute_sleep_architecture() + daily CGM.\n"
            "2. OVERNIGHT coupling: mean nocturnal glucose (00:00-06:00) vs "
            "   sleep efficiency of that same night.\n"
            "3. BIDIRECTIONAL Granger: does sleep_efficiency Granger-cause next-day "
            "   glucose? Does glucose variability Granger-cause next-night sleep? "
            "   maxlag=2 days.\n"
            "Store as workspace.dataframes['coupling_glucose_sleep'].\n"
            "Report: N, median coupling values, fraction showing significant "
            "sleep->glucose vs glucose->sleep direction."
        ),
        "depends_on": [0, 1],
    },
    # Step 8
    {
        "agent": "CausalAgent",
        "task": (
            "PAIRWISE COUPLING — Glucose-Environment pair.\n"
            "For participants with both CGM and environment data, use "
            "aligned_timeseries(). Compute:\n"
            "1. Cross-correlation: glucose vs PM2.5, glucose vs temperature.\n"
            "2. Transfer entropy: PM2.5->glucose and glucose->PM2.5 (control).\n"
            "3. Cross-predictability: predict glucose from env features.\n"
            "4. Evening light -> next-morning glucose: does evening blue light "
            "   (lch2 after 20:00) predict elevated fasting glucose next AM? "
            "   (Scheer et al. PNAS 2009 showed 3 days of misalignment -> prediabetes)\n"
            "Store as workspace.dataframes['coupling_glucose_env'].\n"
            "Report: N, key findings."
        ),
        "depends_on": [0, 2],
    },
    # Step 9
    {
        "agent": "CausalAgent",
        "task": (
            "PAIRWISE COUPLING — HR-Activity, HR-Sleep, HR-Environment pairs.\n"
            "Batch computation of the remaining HR-involving pairs.\n"
            "For each pair, compute: cross-correlation, transfer entropy (both "
            "directions), cross-predictability (both directions), phase coherence.\n"
            "Store as:\n"
            "  workspace.dataframes['coupling_hr_activity']\n"
            "  workspace.dataframes['coupling_hr_sleep']\n"
            "  workspace.dataframes['coupling_hr_env']\n"
            "Report: N per pair, median coupling values."
        ),
        "depends_on": [1, 2],
    },
    # Step 10
    {
        "agent": "CausalAgent",
        "task": (
            "PAIRWISE COUPLING — Activity-Sleep, Activity-Environment, "
            "Sleep-Environment pairs.\n"
            "Batch computation of remaining pairs. Same measures: cross-correlation, "
            "transfer entropy, cross-predictability, phase coherence.\n"
            "Store as:\n"
            "  workspace.dataframes['coupling_activity_sleep']\n"
            "  workspace.dataframes['coupling_activity_env']\n"
            "  workspace.dataframes['coupling_sleep_env']\n"
            "Report: N per pair, median coupling values."
        ),
        "depends_on": [1, 2],
    },
]


# ---------------------------------------------------------------------------
# Phase 3: Atlas assembly — per-person coupling matrices & networks
# Direction A: "The Physiological Coupling Atlas of Diabetes"
# Direction B: "Cross-Modal Predictability as a Disease Biomarker"
# ---------------------------------------------------------------------------

PHASE_3_ATLAS = [
    # Step 11
    {
        "agent": "CausalAgent",
        "task": (
            "COUPLING MATRIX ASSEMBLY.\n"
            "Merge all 10 pairwise coupling DataFrames (coupling_glucose_hr, "
            "coupling_glucose_activity, ..., coupling_sleep_env) into a single "
            "per-person coupling feature matrix.\n\n"
            "For each person, construct:\n"
            "1. A COUPLING VECTOR of length 50 (10 pairs x 5 measures: xcorr_r, "
            "   te_fwd, te_rev, xpred_r2, phase_coherence_24h).\n"
            "2. A COUPLING MATRIX (5x5 symmetric, nodes=modalities, edges=mean "
            "   coupling strength across measures for that pair).\n"
            "3. Scalar summary biomarkers:\n"
            "   - total_coupling_strength = mean of all 50 coupling features\n"
            "   - coupling_asymmetry = mean |TE_fwd - TE_rev| across pairs\n"
            "   - predictability_score = mean R^2 across all cross-predictions "
            "     (Direction B core metric)\n\n"
            "Store the full coupling feature matrix as "
            "workspace.dataframes['coupling_matrix_full'] (N x 50+).\n"
            "Store per-person scalar biomarkers as "
            "workspace.dataframes['coupling_biomarkers'].\n"
            "Report: N with complete coupling data, summary of biomarkers."
        ),
        "depends_on": [5, 6, 7, 8, 9, 10],
    },
    # Step 12
    {
        "agent": "CausalAgent",
        "task": (
            "COUPLING VS DIABETES SEVERITY (Direction A core analysis).\n"
            "Using workspace.dataframes['coupling_biomarkers'] merged with "
            "coupling_clinical_features (for study_group, age, clinical_site):\n\n"
            "1. For EACH of the 50 coupling features, test group differences "
            "   across the 4 diabetes groups (Kruskal-Wallis, age-adjusted). "
            "   Apply Benjamini-Hochberg FDR correction. Report effect sizes.\n"
            "2. Test monotonic trend: Jonckheere-Terpstra test for ordered "
            "   decrease healthy > pre-diabetes > oral_med > insulin.\n"
            "3. For total_coupling_strength and predictability_score: "
            "   violin plots by study_group, Mann-Whitney pairwise comparisons.\n"
            "4. Identify WHICH EDGES BREAK FIRST in pre-diabetes: "
            "   compare healthy vs pre-diabetes only, rank edges by effect size. "
            "   (This reveals the earliest decoupling signals.)\n"
            "5. Site bias check: repeat #1 within each clinical site.\n\n"
            "Store as workspace.dataframes['coupling_group_comparisons'].\n"
            "Report: top 10 most discriminative coupling features, "
            "total_coupling_strength effect size, earliest-breaking edges."
        ),
        "depends_on": [11],
    },
    # Step 13
    {
        "agent": "CausalAgent",
        "task": (
            "GRAPH-THEORETIC BIOMARKERS (Direction A network analysis).\n"
            "For each person, treat the 5x5 coupling matrix as a weighted graph. "
            "Compute using networkx:\n"
            "1. graph_density (fraction of strong edges, threshold > median)\n"
            "2. global_efficiency (inverse path length)\n"
            "3. modularity (is the network fragmented?)\n"
            "4. node_strength per modality (which organ is the coupling hub?)\n"
            "5. betweenness_centrality per modality\n\n"
            "Store as workspace.dataframes['coupling_graph_metrics'].\n"
            "Compare graph metrics across diabetes groups. "
            "Test: does global_efficiency predict diabetes severity better "
            "than individual coupling edges? (logistic regression AUROC)\n"
            "Report: graph metric group differences, hub identification."
        ),
        "depends_on": [11],
    },
]


# ---------------------------------------------------------------------------
# Phase 4: Coupling-based aging clock (Direction C)
# ---------------------------------------------------------------------------

PHASE_4_COUPLING_CLOCK = [
    # Step 14
    {
        "agent": "AgingClockAgent",
        "task": (
            "COUPLING-BASED AGING CLOCK (Direction C).\n"
            "Using workspace.dataframes['coupling_matrix_full'] (50 coupling features) "
            "plus the following complexity features from Phase 1:\n"
            "  - Multiscale entropy of glucose (from coupling_cgm_features)\n"
            "  - Multiscale entropy of HR (from coupling_circadian_features)\n"
            "  - Circadian phase coherence metrics\n\n"
            "Build a coupling-based aging clock:\n"
            "1. Feature set: all 50 coupling features + MSE features + "
            "   total_coupling_strength + predictability_score\n"
            "2. Model: RidgeCV (alpha grid: 0.01, 0.1, 1, 10, 100)\n"
            "3. Train on recommended_split='train', evaluate on 'test'\n"
            "4. Report: MAE, R^2, and top 10 features by |coefficient|\n"
            "5. Compute coupling_AgeAccel = predicted_age - chronological_age\n"
            "6. COMPARE TO STATIC CLOCKS: compute AUROC for binary classification "
            "   healthy vs insulin-dependent using:\n"
            "   a) coupling_AgeAccel alone\n"
            "   b) static unified AgeAccel (from workspace if available, else recompute)\n"
            "   c) coupling_AgeAccel + static AgeAccel combined\n"
            "   The brainstorm predicts coupling AUROC > 0.70 vs static's 0.47.\n\n"
            "Store as workspace.dataframes['coupling_age_accel'].\n"
            "Report: all metrics, comparison to static clocks."
        ),
        "depends_on": [11],
    },
    # Step 15
    {
        "agent": "AgingClockAgent",
        "task": (
            "COUPLING PREDICTS STRUCTURAL DAMAGE (Direction A, Fig 6).\n"
            "Test whether coupling features predict retinal and cardiac damage "
            "independent of HbA1c and age:\n"
            "1. Partial correlation: total_coupling_strength vs logMAR (visual "
            "   acuity), adjusting for age, HbA1c, study_group.\n"
            "2. Partial correlation: glucose_hr coupling specifically vs ecg_qtc "
            "   (cardiac electrical remodeling), adjusting for age.\n"
            "3. If retinal AgeAccel or cardiac AgeAccel exist in workspace, "
            "   test: weak coupling -> faster retinal/cardiac aging?\n"
            "4. Mediation: does coupling mediate the diabetes -> organ damage "
            "   pathway? study_group -> coupling -> logMAR. "
            "   (Baron & Kenny or pingouin.mediation_analysis)\n\n"
            "Store as workspace.dataframes['coupling_damage_associations'].\n"
            "Report: partial correlations, mediation test results."
        ),
        "depends_on": [14],
    },
]


# ---------------------------------------------------------------------------
# Phase 5: Coupling-based phenotyping (Directions A, B)
# ---------------------------------------------------------------------------

PHASE_5_PHENOTYPES = [
    # Step 16
    {
        "agent": "PhenotypeAgent",
        "task": (
            "COUPLING-BASED SUBTYPES (Direction A + B).\n"
            "Using workspace.dataframes['coupling_matrix_full'] (50 features) "
            "merged with coupling_clinical_features:\n\n"
            "1. Standardize coupling features (StandardScaler).\n"
            "2. Dimensionality reduction: UMAP (n_components=2) for visualization.\n"
            "3. Clustering: HDBSCAN (if available, else KMeans k=3,4,5,6). "
            "   Report silhouette scores for each k.\n"
            "4. CHARACTERIZE each cluster:\n"
            "   a) Which coupling edges are strongest/weakest?\n"
            "   b) Which modality is the 'hub' for each cluster?\n"
            "   c) Mean HbA1c, HOMA-IR, age per cluster\n"
            "   d) Study_group distribution (chi-squared test)\n"
            "5. IDENTIFY KEY PHENOTYPES:\n"
            "   a) 'Compensated diabetes': high HbA1c but preserved coupling "
            "      (Direction B, Hypothesis 4)\n"
            "   b) 'Decompensated diabetes': high HbA1c AND broken coupling\n"
            "   c) 'At-risk normals': normal HbA1c but already decoupled "
            "      (potential early detection target)\n"
            "   d) 'Resilient': diabetic by study_group but coupling intact\n"
            "6. Do coupling-based subtypes cut across the 4 clinical groups? "
            "   (If yes, this shows coupling captures information beyond HbA1c.)\n\n"
            "Store cluster labels as workspace.dataframes['coupling_phenotypes'].\n"
            "Store UMAP coordinates as workspace.dataframes['coupling_umap'].\n"
            "Report: cluster characterization, key phenotype counts."
        ),
        "depends_on": [11],
    },
]


# ---------------------------------------------------------------------------
# Phase 6: Causal architecture via CCM and PCMCI (Direction D)
# ---------------------------------------------------------------------------

PHASE_6_CAUSAL = [
    # Step 17
    {
        "agent": "CausalAgent",
        "task": (
            "CONVERGENT CROSS MAPPING (Direction D).\n"
            "For a subsample of 200 participants (50 per study_group), apply CCM "
            "(Sugihara et al. Science 2012) to test nonlinear causal coupling.\n\n"
            "For each person, for the glucose-HR pair:\n"
            "1. Embed glucose and HR in delay-coordinate space (Takens embedding, "
            "   tau=1, E=3-5 chosen by simplex projection).\n"
            "2. CCM in both directions: glucose xmap HR, HR xmap glucose.\n"
            "3. Convergence test: does CCM skill increase with library length? "
            "   Use library lengths L = 50, 100, 200, 500, N.\n"
            "4. Record: ccm_glucose_to_hr (skill at max L), "
            "   ccm_hr_to_glucose, convergence_p_value.\n\n"
            "Use pyEDM if available, else implement basic CCM with sklearn KNN.\n"
            "Compare CCM asymmetry (glucose->HR vs HR->glucose) across groups.\n"
            "PREDICTION: healthy = strong glucose->HR (autonomic response), "
            "insulin-dependent = weakened + symmetrized (autonomic neuropathy).\n\n"
            "Store as workspace.dataframes['coupling_ccm_glucose_hr'].\n"
            "Report: per-group median CCM skill, directional asymmetry."
        ),
        "depends_on": [0, 1],
    },
    # Step 18
    {
        "agent": "CausalAgent",
        "task": (
            "PCMCI CAUSAL GRAPHS (Direction D extension).\n"
            "For 100 participants (25 per study_group), run PCMCI (tigramite) "
            "on the full 5-variable aligned time series: "
            "[glucose, HR, activity, PM2.5, temperature].\n\n"
            "Settings:\n"
            "  - tau_max = 12 (1 hour at 5-min resolution)\n"
            "  - ParCorr independence test (linear; robust baseline per "
            "    CausalRivers ICLR 2025 finding that linear Granger is most reliable)\n"
            "  - alpha_level = 0.05\n\n"
            "For each person, extract the causal graph:\n"
            "  - directed edges with lag and partial correlation strength\n"
            "  - contemporaneous edges (PCMCI+)\n\n"
            "Aggregate across participants:\n"
            "  - Edge frequency: how often does each directed edge appear?\n"
            "  - Compare edge frequency and strength across diabetes groups.\n"
            "  - Identify 'causal hubs': which variable has the most outgoing edges?\n\n"
            "Store as workspace.dataframes['coupling_pcmci_graphs'].\n"
            "Report: most common causal edges, group differences in graph topology."
        ),
        "depends_on": [0, 1, 2],
    },
]


# ---------------------------------------------------------------------------
# Phase 7: Exposome-physiology coupling (Direction F)
# ---------------------------------------------------------------------------

PHASE_7_EXPOSOME = [
    # Step 19
    {
        "agent": "CausalAgent",
        "task": (
            "ENVIRONMENT-PHYSIOLOGY CAUSAL PATHWAYS (Direction F).\n"
            "Test the causal chain: PM2.5 -> HR/HRV -> glucose dysregulation.\n\n"
            "For 200 participants with all 3 modalities (CGM + HR + environment):\n"
            "1. LAGGED CAUSAL ANALYSIS (PCMCI or Granger):\n"
            "   a) PM2.5 at time t -> HR at t+30min, t+1h, t+2h\n"
            "   b) PM2.5 at time t -> glucose at t+1h, t+2h, t+4h\n"
            "   c) HR at time t -> glucose at t+15min, t+30min, t+1h\n"
            "   Adjust for time-of-day (all three have diurnal patterns).\n\n"
            "2. MEDIATION ANALYSIS:\n"
            "   Test: is the PM2.5->glucose effect mediated by HR?\n"
            "   Model: PM2.5 -> HR -> glucose (HR as mediator)\n"
            "   Use Baron & Kenny steps or pingouin.mediation_analysis.\n"
            "   Report: indirect effect, direct effect, proportion mediated.\n\n"
            "3. EVENING LIGHT -> CIRCADIAN -> GLUCOSE:\n"
            "   Does evening blue light (lch2 after 20:00) predict:\n"
            "   a) later sleep onset (sleep_midpoint_hr from WearableAgent)?\n"
            "   b) worse next-day glucose (higher mean, lower TIR)?\n"
            "   c) Is sleep onset a mediator? (light -> late sleep -> bad glucose)\n\n"
            "4. COUPLING MODERATION BY DISEASE:\n"
            "   Does diabetes severity moderate the environment-physiology coupling?\n"
            "   Interaction test: PM2.5 * study_group -> glucose.\n"
            "   PREDICTION: healthy = better buffered (weaker PM2.5->glucose), "
            "   insulin-dependent = worse buffered (stronger PM2.5->glucose).\n\n"
            "Store as workspace.dataframes['coupling_exposome_causal'].\n"
            "Report: mediation results, evening light effects, moderation by disease."
        ),
        "depends_on": [0, 1, 2],
    },
]


# ---------------------------------------------------------------------------
# Phase 8: Tensor decomposition (Direction G)
# ---------------------------------------------------------------------------

PHASE_8_TENSOR = [
    # Step 20
    {
        "agent": "PhenotypeAgent",
        "task": (
            "TENSOR DECOMPOSITION FOR LATENT PHYSIOLOGICAL MODES (Direction G).\n"
            "Construct a 3D tensor: participants x time_bins x modalities.\n\n"
            "SETUP:\n"
            "  - Participants: all with >= 3 modalities available\n"
            "  - Time bins: aggregate the 10-day window into 6-hour blocks "
            "    (4 per day x 10 days = 40 bins)\n"
            "  - Modalities (6): mean_glucose, mean_HR, activity_level (steps), "
            "    sleep_state (0/1), PM2.5, light_intensity (lch2)\n"
            "  - Standardize each modality slice independently.\n\n"
            "DECOMPOSITION:\n"
            "  Apply non-negative CP decomposition (tensorly library) with "
            "  K = 3, 4, 5, 6 components. Select K by reconstruction error "
            "  and core consistency diagnostic.\n\n"
            "For each component, extract and interpret:\n"
            "  1. PARTICIPANT LOADINGS: which participants express this pattern?\n"
            "     Compare loadings across study_groups (Kruskal-Wallis).\n"
            "  2. TEMPORAL PROFILE: when does this pattern occur?\n"
            "     Plot temporal loading across the 40 time bins. Is it circadian?\n"
            "  3. MODALITY PROFILE: which signals participate?\n"
            "     Which modalities have high loadings?\n\n"
            "EXPECTED COMPONENTS (from brainstorm):\n"
            "  - 'Coordinated circadian': 24h rhythm across all modalities, "
            "    high in healthy participants.\n"
            "  - 'Nocturnal metabolic stress': elevated night glucose + HR + "
            "    poor sleep, high in insulin-dependent.\n"
            "  - 'Environmental sensitivity': PM2.5-correlated HR and glucose.\n"
            "  - 'Activity-glucose responders': strong activity->glucose coupling.\n\n"
            "Store as workspace.dataframes['tensor_components'] (participant loadings) "
            "and workspace.dataframes['tensor_profiles'] (temporal + modality profiles).\n"
            "Report: K selected, component interpretations, group associations."
        ),
        "depends_on": [0, 1, 2],
    },
]


# ---------------------------------------------------------------------------
# Phase 9: Multi-scale wavelet coupling spectrograms (Direction E)
# ---------------------------------------------------------------------------

PHASE_9_MULTISCALE = [
    # Step 21
    {
        "agent": "CausalAgent",
        "task": (
            "MULTI-SCALE COUPLING SPECTROGRAMS (Direction E).\n"
            "For 200 participants (50 per group), compute wavelet coherence "
            "between glucose and HR decomposed into 4 frequency bands:\n"
            "  - Ultra-fast (5-30 min): acute glucose-HR response\n"
            "  - Fast (30 min - 3h): postprandial dynamics\n"
            "  - Circadian (12-36h): daily rhythm alignment\n"
            "  - Multi-day (2-10 days): slow trends\n\n"
            "Use pycwt or ssqueezepy for continuous wavelet transform.\n"
            "Morlet wavelet, frequency range 1/(10 days) to 1/(5 min).\n\n"
            "Per-person output: mean wavelet coherence in each band.\n"
            "Per-group analysis:\n"
            "1. Compare coherence per band across the 4 diabetes groups.\n"
            "2. TEST BRAINSTORM HYPOTHESES:\n"
            "   a) Pre-diabetes: preserved circadian but broken ultra-fast? "
            "      (acute glucose-HR response impaired while daily rhythms intact)\n"
            "   b) Oral medication: circadian partially restored but ultra-fast "
            "      still broken?\n"
            "   c) Insulin-dependent: breakdown at ALL scales?\n"
            "3. Which scale breaks first? Rank frequency bands by effect size "
            "   for healthy vs pre-diabetes comparison.\n\n"
            "Also compute wavelet coherence for glucose-activity and HR-activity "
            "pairs at the same 4 bands.\n\n"
            "Store as workspace.dataframes['coupling_wavelet_spectrograms'].\n"
            "Report: per-band coherence by group, hypothesis test results."
        ),
        "depends_on": [0, 1],
    },
]


# ---------------------------------------------------------------------------
# Phase 10: Validation and critique
# ---------------------------------------------------------------------------

PHASE_10_VALIDATE = [
    # Step 22
    {
        "agent": "HypothesisAgent",
        "task": (
            "Review ALL coupling atlas findings in the workspace. "
            "Propose mechanistic hypotheses that EXPLAIN the observed patterns.\n\n"
            "Specifically address:\n"
            "1. If glucose-HR coupling breaks first in pre-diabetes, what mechanism? "
            "   (autonomic neuropathy? insulin resistance affecting vagal tone?)\n"
            "2. If coupling-based aging clock outperforms static clocks, why? "
            "   (dynamics capture what static summaries miss?)\n"
            "3. If 'compensated' and 'decompensated' phenotypes exist, what "
            "   maintains compensation? (fitness? sleep quality? genetics?)\n"
            "4. If environment-glucose coupling is moderated by disease, "
            "   what's the buffering mechanism? (parasympathetic reserve?)\n\n"
            "Propose 3-5 testable hypotheses with specific next analyses."
        ),
        "depends_on": [12, 14, 16, 19],
    },
    # Step 23
    {
        "agent": "LiteratureAgent",
        "task": (
            "Contextualize the coupling atlas findings against the literature.\n"
            "Specifically compare to:\n"
            "1. Bashan et al. Nature Comms 2012 (network physiology baselines)\n"
            "2. Oh et al. Nature 2023 (proteomic organ clocks — our coupling "
            "   approach is complementary, not competing)\n"
            "3. Marras et al. Nature 2026 (wearable -> HOMA-IR, AUROC=0.80 — "
            "   how does our coupling AUROC compare?)\n"
            "4. Reyes-Lagos et al. Front Physiol 2025 (RQA in T2DM — do our "
            "   findings align with their rigidity/decoupling observation?)\n"
            "5. Vallat et al. Cell Reports Med 2023 (sleep-glucose coupling "
            "   predicts fasting glucose)\n\n"
            "Identify what is NOVEL in our findings vs prior work."
        ),
        "depends_on": [12, 14],
    },
    # Step 24
    {
        "agent": "CriticAgent",
        "task": (
            "COMPREHENSIVE REVIEW of the coupling atlas pipeline.\n"
            "Review ALL coupling findings accumulated in the workspace. "
            "Pay special attention to:\n"
            "1. MULTIPLE COMPARISONS: 50 coupling features x 4 groups = 200 tests. "
            "   Was FDR correction applied everywhere?\n"
            "2. TEMPORAL RESOLUTION: is 5-min resolution sufficient for ultra-fast "
            "   coupling (acute glucose-HR at ~2-3 min peak)?\n"
            "3. GARMIN LIMITATIONS: sleep staging is consumer-grade. How much "
            "   does this affect sleep-dependent coupling measures?\n"
            "4. MEDICATION CONFOUND: medications are redacted. Beta-blockers "
            "   directly affect HR; insulin directly affects glucose. Could "
            "   medication effects masquerade as 'coupling change'?\n"
            "5. SAMPLE SIZE for CCM/PCMCI: are 200 participants sufficient "
            "   for robust causal discovery?\n"
            "6. SITE BIAS: were all results checked across 3 sites?\n"
            "7. AGE ADJUSTMENT: insulin-dependent participants are older — "
            "   was age adjusted in all group comparisons?\n"
            "8. CLINICAL PLAUSIBILITY: do the coupling directions and effect "
            "   sizes make biological sense?"
        ),
        "depends_on": [12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
    },
]


# ---------------------------------------------------------------------------
# Full pipeline: all phases concatenated
# ---------------------------------------------------------------------------

COUPLING_ATLAS_PIPELINE = (
    PHASE_1_EXTRACT       # Steps 0-4:   Data extraction (parallel)
    + PHASE_2_COUPLING    # Steps 5-10:  Pairwise coupling (partially parallel)
    + PHASE_3_ATLAS       # Steps 11-13: Atlas assembly + group comparisons
    + PHASE_4_COUPLING_CLOCK  # Steps 14-15: Coupling aging clock
    + PHASE_5_PHENOTYPES  # Step 16:     Coupling-based subtypes
    + PHASE_6_CAUSAL      # Steps 17-18: CCM + PCMCI causal graphs
    + PHASE_7_EXPOSOME    # Step 19:     Environment-physiology pathways
    + PHASE_8_TENSOR      # Step 20:     Tensor decomposition
    + PHASE_9_MULTISCALE  # Step 21:     Wavelet coupling spectrograms
    + PHASE_10_VALIDATE   # Steps 22-24: Hypotheses + literature + critic
)


# ---------------------------------------------------------------------------
# Direction-to-phase mapping for selective execution
# ---------------------------------------------------------------------------

DIRECTION_PHASES = {
    "A": {
        "name": "Physiological Coupling Atlas",
        "steps": list(range(0, 5)) + list(range(5, 14)),  # Phase 1 + 2 + 3
        "description": "Build per-person coupling matrices, compare across diabetes groups",
    },
    "B": {
        "name": "Cross-Modal Predictability Biomarker",
        "steps": list(range(0, 5)) + list(range(5, 14)) + [16],  # A + phenotyping
        "description": "Predictability scores + compensated/decompensated phenotypes",
    },
    "C": {
        "name": "Coupling-Based Aging Clock",
        "steps": list(range(0, 5)) + list(range(5, 14)) + [14, 15],  # A + clock
        "description": "Aging clock from coupling features, compare to static clocks",
    },
    "D": {
        "name": "Nonlinear Causal Architecture",
        "steps": list(range(0, 5)) + [17, 18],  # Phase 1 + CCM/PCMCI
        "description": "CCM and PCMCI causal graphs across diabetes groups",
    },
    "E": {
        "name": "Multi-Scale Coupling Spectrograms",
        "steps": list(range(0, 5)) + [21],  # Phase 1 + wavelet
        "description": "Wavelet coherence decomposed by frequency band",
    },
    "F": {
        "name": "Exposome-Metabolism Axis",
        "steps": list(range(0, 5)) + [19],  # Phase 1 + exposome
        "description": "Environment -> HR -> glucose causal pathways",
    },
    "G": {
        "name": "Tensor Decomposition Modes",
        "steps": list(range(0, 5)) + [20],  # Phase 1 + tensor
        "description": "Latent physiological modes from tensor factorization",
    },
}


def run_coupling_atlas(
    orchestrator: Orchestrator,
    directions: list[str] | None = None,
    pilot_mode: bool = False,
) -> dict[str, str]:
    """Execute the coupling atlas pipeline.

    Args:
        orchestrator: The orchestrator with registered agents.
        directions: List of direction letters to run (e.g. ["A", "C"]).
            Default: all directions (full pipeline).
        pilot_mode: If True, run only Phase 1 + first coupling pair (glucose-HR)
            for quick validation before scaling.

    Returns:
        dict mapping step index to result string.
    """
    if pilot_mode:
        # Quick validation: extract data + compute glucose-HR coupling only
        pilot_step_ids = [0, 1, 3, 5]  # CGM, wearable, clinical, glucose-HR
        target_steps = set(pilot_step_ids)
        pipeline = [
            spec for i, spec in enumerate(COUPLING_ATLAS_PIPELINE)
            if i in target_steps
        ]
    elif directions:
        # Collect all steps needed for requested directions
        target_steps = set()
        for d in directions:
            if d.upper() in DIRECTION_PHASES:
                target_steps.update(DIRECTION_PHASES[d.upper()]["steps"])
        # Always include validation if we have enough steps
        if len(target_steps) > 10:
            target_steps.update([22, 23, 24])
        pipeline = [
            (i, spec) for i, spec in enumerate(COUPLING_ATLAS_PIPELINE)
            if i in target_steps
        ]
    else:
        # Full pipeline
        pipeline = list(enumerate(COUPLING_ATLAS_PIPELINE))

    # Execute with dependency tracking
    results = {}
    completed = set()

    if pilot_mode or directions:
        # When running subset, re-index for dependency tracking
        steps_to_run = pilot_mode and list(range(len(pipeline))) or pipeline
        for item in (pipeline if not pilot_mode else enumerate(pipeline)):
            if pilot_mode:
                local_i, spec = item
                global_i = pilot_step_ids[local_i] if local_i < len(pilot_step_ids) else local_i
            else:
                global_i, spec = item

            # Check dependencies (only against steps we plan to run)
            deps = spec.get("depends_on", [])
            deps_met = all(d in completed for d in deps if d in (
                target_steps if not pilot_mode else {0, 1, 3, 5}
            ))

            if not deps_met:
                results[global_i] = (
                    f"[SKIP] {spec['agent']}: unmet dependency"
                )
                continue

            result = orchestrator.dispatch(spec)
            results[global_i] = f"[{spec['agent']}] {result.answer[:500]}"
            completed.add(global_i)
    else:
        for i, spec in pipeline:
            deps = spec.get("depends_on", [])
            if not all(d in completed for d in deps):
                results[i] = f"[SKIP] {spec['agent']}: unmet dependency"
                continue

            result = orchestrator.dispatch(spec)
            results[i] = f"[{spec['agent']}] {result.answer[:500]}"
            completed.add(i)

    return results


def get_pipeline_summary() -> str:
    """Return a human-readable summary of the coupling atlas pipeline."""
    lines = ["Coupling Atlas Pipeline Summary", "=" * 40]
    for i, spec in enumerate(COUPLING_ATLAS_PIPELINE):
        deps = spec.get("depends_on", [])
        dep_str = f" (depends on: {deps})" if deps else " (independent)"
        lines.append(f"  Step {i:2d}: [{spec['agent']:20s}]{dep_str}")
        # First 80 chars of task
        task_preview = spec["task"].split("\n")[0][:80]
        lines.append(f"          {task_preview}")

    lines.append("")
    lines.append("Direction Mapping:")
    for letter, info in DIRECTION_PHASES.items():
        lines.append(f"  {letter}: {info['name']} — steps {info['steps']}")

    return "\n".join(lines)
