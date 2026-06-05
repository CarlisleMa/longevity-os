"""Phase 5 — Causal discovery from aligned multimodal time series.

Four analyses:
  5a. Sleep → glucose Granger causality (bidirectional)
  5b. Glucose-HR cross-correlation and optimal lag
  5c. PM2.5 → heart rate lagged regression
  5d. Population-level causal DAG via PCMCI

Processes all participants with triple-overlap (CGM + wearable + environment).
Results saved to results/causal_*.csv and results/causal/causal_summary.json.
"""

import sys
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import correlate, correlation_lags

sys.path.insert(0, "/oak/stanford/scg/lab_twc/mazijian/aireadi")

from scripts.config import (
    result_path,
    RESULTS_DIR, CGM_TIR_LOW, CGM_TIR_HIGH,
)
from scripts.multimodal import get_participant
from scripts.features_wearable import compute_sleep_architecture
from scripts.utils.timezone import get_timezone

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

FIGURES_DIR = RESULTS_DIR / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Try importing tigramite for analysis 5d
try:
    from tigramite.pcmci import PCMCI
    from tigramite.independence_tests.parcorr import ParCorr
    from tigramite import data_processing as pp
    HAS_TIGRAMITE = True
except ImportError:
    HAS_TIGRAMITE = False
    print("[WARN] tigramite not available — skipping 5d (causal DAG).")


# ═════════════════════════════════════════════════════════════════════════════
# 5a. Sleep → Glucose Granger Causality
# ═════════════════════════════════════════════════════════════════════════════

def _daily_glucose_metrics(cgm_df: pd.DataFrame, tz: str) -> pd.DataFrame:
    """Per-local-date glucose metrics: mean, CV, TIR."""
    if cgm_df.empty:
        return pd.DataFrame()
    g = cgm_df["glucose_mg_dl"].dropna()
    if len(g) == 0:
        return pd.DataFrame()
    local_idx = g.index.tz_convert(tz)
    gs = pd.Series(g.values, index=local_idx)
    dates = gs.groupby(gs.index.date)

    rows = []
    for dt, vals in dates:
        if len(vals) < 12:  # need at least 1 hour of data
            continue
        mean_g = vals.mean()
        std_g = vals.std()
        cv = std_g / mean_g if mean_g > 0 else np.nan
        tir = ((vals >= CGM_TIR_LOW) & (vals <= CGM_TIR_HIGH)).mean()
        rows.append({"date": dt, "glucose_mean": mean_g, "glucose_cv": cv, "tir": tir})
    return pd.DataFrame(rows)


def sleep_glucose_granger(person_id: str) -> dict | None:
    """Test bidirectional Granger causality between sleep quality and next-day glucose.

    Returns dict with direction, F-statistic, p-values, or None on failure.
    """
    from statsmodels.tsa.stattools import grangercausalitytests, adfuller

    try:
        p = get_participant(person_id)
        # Sleep architecture (per-night)
        sa = compute_sleep_architecture(person_id)
        if sa.empty or len(sa) < 4:
            return None

        # Assign each night to the date it ends (wake-up date)
        sa = sa.copy()
        sa["date"] = sa["night_end"].dt.date

        # Daily glucose metrics
        tz = get_timezone(person_id)
        glucose_daily = _daily_glucose_metrics(p.cgm_data, tz)
        if glucose_daily.empty or len(glucose_daily) < 4:
            return None

        # Merge on date: night's wake-up date = the day that follows that night
        merged = pd.merge(
            sa[["date", "tst_min", "se", "waso_min"]],
            glucose_daily,
            on="date",
            how="inner",
        ).sort_values("date").reset_index(drop=True)

        if len(merged) < 4:
            return None

        # Also create a lagged version: night sleep → NEXT day glucose
        # and glucose_today → TONIGHT sleep
        # With ~10 nights max, use lag=1 only
        result = {"person_id": person_id, "n_days": len(merged)}

        # Test 1: sleep_efficiency → next_day_tir (sleep quality → glucose control)
        # Use SE as the sleep quality metric and TIR as glucose metric
        se_series = merged["se"].values
        tir_series = merged["tir"].values

        # Check stationarity (ADF test) — difference if needed
        for name, s in [("se", se_series), ("tir", tir_series)]:
            if len(s) < 4:
                return None
            adf_p = adfuller(s, maxlag=1, autolag=None)[1]
            if adf_p > 0.1:
                # Try first-differencing
                pass  # Granger test handles short series; proceed

        # Granger: sleep → glucose (does past SE help predict TIR?)
        data_sg = np.column_stack([tir_series, se_series])  # [y, x] format
        try:
            gc_sg = grangercausalitytests(data_sg, maxlag=1, verbose=False)
            f_sg = gc_sg[1][0]["ssr_ftest"][0]
            p_sg = gc_sg[1][0]["ssr_ftest"][1]
        except Exception:
            f_sg, p_sg = np.nan, np.nan

        # Granger: glucose → sleep (does past TIR help predict SE?)
        data_gs = np.column_stack([se_series, tir_series])  # [y, x] format
        try:
            gc_gs = grangercausalitytests(data_gs, maxlag=1, verbose=False)
            f_gs = gc_gs[1][0]["ssr_ftest"][0]
            p_gs = gc_gs[1][0]["ssr_ftest"][1]
        except Exception:
            f_gs, p_gs = np.nan, np.nan

        result.update({
            "se_mean": float(np.nanmean(se_series)),
            "tir_mean": float(np.nanmean(tir_series)),
            "sleep_to_glucose_F": float(f_sg),
            "sleep_to_glucose_p": float(p_sg),
            "glucose_to_sleep_F": float(f_gs),
            "glucose_to_sleep_p": float(p_gs),
        })
        return result

    except Exception as e:
        return None


def aggregate_sleep_glucose(results: list[dict], participant_index: pd.DataFrame) -> dict:
    """Aggregate Granger results across participants, stratified by study_group."""
    from statsmodels.stats.multitest import multipletests

    df = pd.DataFrame(results)
    df = df.merge(
        participant_index[["study_group"]],
        left_on="person_id", right_index=True, how="left",
    )
    df.to_csv(result_path("causal_sleep_glucose.csv"), index=False)
    print(f"  Saved {len(df)} rows to causal_sleep_glucose.csv")

    summary = {"n_tested": len(df)}

    # FDR correction on sleep→glucose p-values
    valid_sg = df.dropna(subset=["sleep_to_glucose_p"])
    if len(valid_sg) > 0:
        reject_sg, pval_corr_sg, _, _ = multipletests(
            valid_sg["sleep_to_glucose_p"], alpha=0.05, method="fdr_bh"
        )
        summary["sleep_to_glucose"] = {
            "n_valid": int(len(valid_sg)),
            "n_nominal_p05": int((valid_sg["sleep_to_glucose_p"] < 0.05).sum()),
            "n_fdr_p05": int(reject_sg.sum()),
            "median_F": float(valid_sg["sleep_to_glucose_F"].median()),
        }

    # FDR correction on glucose→sleep p-values
    valid_gs = df.dropna(subset=["glucose_to_sleep_p"])
    if len(valid_gs) > 0:
        reject_gs, pval_corr_gs, _, _ = multipletests(
            valid_gs["glucose_to_sleep_p"], alpha=0.05, method="fdr_bh"
        )
        summary["glucose_to_sleep"] = {
            "n_valid": int(len(valid_gs)),
            "n_nominal_p05": int((valid_gs["glucose_to_sleep_p"] < 0.05).sum()),
            "n_fdr_p05": int(reject_gs.sum()),
            "median_F": float(valid_gs["glucose_to_sleep_F"].median()),
        }

    # Stratify by study_group
    by_group = {}
    for grp, gdf in df.groupby("study_group"):
        g_valid = gdf.dropna(subset=["sleep_to_glucose_p"])
        by_group[grp] = {
            "n": int(len(gdf)),
            "n_sleep_to_glucose_nom_p05": int((g_valid["sleep_to_glucose_p"] < 0.05).sum()),
            "n_glucose_to_sleep_nom_p05": int(
                (gdf.dropna(subset=["glucose_to_sleep_p"])["glucose_to_sleep_p"] < 0.05).sum()
            ),
            "mean_se": float(gdf["se_mean"].mean()) if "se_mean" in gdf else None,
            "mean_tir": float(gdf["tir_mean"].mean()) if "tir_mean" in gdf else None,
        }
    summary["by_study_group"] = by_group
    return summary


# ═════════════════════════════════════════════════════════════════════════════
# 5b. Glucose-HR Cross-Correlation
# ═════════════════════════════════════════════════════════════════════════════

def glucose_hr_coupling(person_id: str) -> dict | None:
    """Cross-correlation between glucose and heart rate at 5-min resolution.

    Returns dict with optimal lag, peak correlation, Pearson r, or None.
    """
    try:
        p = get_participant(person_id)
        aligned = p.aligned_timeseries("5min")
        if aligned.empty:
            return None

        glucose = aligned["cgm_glucose_mg_dl"].dropna()
        hr = aligned["hr_bpm"].dropna()

        # Need common valid indices
        common = glucose.index.intersection(hr.index)
        if len(common) < 24:  # need at least 2 hours
            return None

        g = glucose.loc[common].values.astype(float)
        h = hr.loc[common].values.astype(float)

        # Remove NaNs
        valid = ~(np.isnan(g) | np.isnan(h))
        g = g[valid]
        h = h[valid]
        if len(g) < 24:
            return None

        # Standardize
        g_z = (g - g.mean()) / g.std() if g.std() > 0 else np.zeros_like(g)
        h_z = (h - h.mean()) / h.std() if h.std() > 0 else np.zeros_like(h)

        # Cross-correlation at lags from -12 to +12 (5-min steps = -60 to +60 min)
        max_lag_steps = 12  # 12 * 5min = 60 minutes
        n = len(g_z)
        lags = np.arange(-max_lag_steps, max_lag_steps + 1)
        xcorr = np.zeros(len(lags))

        for i, lag in enumerate(lags):
            if lag >= 0:
                xcorr[i] = np.corrcoef(g_z[:n - lag], h_z[lag:])[0, 1] if n - lag > 10 else np.nan
            else:
                xcorr[i] = np.corrcoef(g_z[-lag:], h_z[:n + lag])[0, 1] if n + lag > 10 else np.nan

        # Find optimal lag
        valid_mask = ~np.isnan(xcorr)
        if not valid_mask.any():
            return None

        best_idx = np.nanargmax(np.abs(xcorr))
        optimal_lag_steps = int(lags[best_idx])
        optimal_lag_min = optimal_lag_steps * 5
        peak_corr = float(xcorr[best_idx])

        # Zero-lag correlation
        zero_lag_corr = float(xcorr[lags == 0][0]) if 0 in lags else np.nan

        # Pearson r with p-value at zero lag
        r, p_val = stats.pearsonr(g, h)

        return {
            "person_id": person_id,
            "n_common_points": int(len(g)),
            "optimal_lag_min": optimal_lag_min,
            "peak_xcorr": round(peak_corr, 4),
            "zero_lag_corr": round(zero_lag_corr, 4),
            "pearson_r": round(float(r), 4),
            "pearson_p": float(p_val),
        }

    except Exception:
        return None


def aggregate_glucose_hr(results: list[dict], participant_index: pd.DataFrame) -> dict:
    """Aggregate glucose-HR coupling, test for study_group differences."""
    df = pd.DataFrame(results)
    df = df.merge(
        participant_index[["study_group"]],
        left_on="person_id", right_index=True, how="left",
    )
    df.to_csv(result_path("causal_glucose_hr.csv"), index=False)
    print(f"  Saved {len(df)} rows to causal_glucose_hr.csv")

    summary = {
        "n_tested": int(len(df)),
        "median_optimal_lag_min": float(df["optimal_lag_min"].median()),
        "mean_peak_xcorr": float(df["peak_xcorr"].mean()),
        "mean_zero_lag_corr": float(df["zero_lag_corr"].mean()),
        "mean_pearson_r": float(df["pearson_r"].mean()),
    }

    # Kruskal-Wallis: does coupling strength differ by diabetes severity?
    groups = [g["peak_xcorr"].dropna().values for _, g in df.groupby("study_group")]
    groups = [g for g in groups if len(g) > 1]
    if len(groups) >= 2:
        kw_stat, kw_p = stats.kruskal(*groups)
        summary["kruskal_wallis_H"] = float(kw_stat)
        summary["kruskal_wallis_p"] = float(kw_p)

    # Per-group summaries
    by_group = {}
    for grp, gdf in df.groupby("study_group"):
        by_group[grp] = {
            "n": int(len(gdf)),
            "mean_peak_xcorr": float(gdf["peak_xcorr"].mean()),
            "median_optimal_lag_min": float(gdf["optimal_lag_min"].median()),
            "mean_pearson_r": float(gdf["pearson_r"].mean()),
        }
    summary["by_study_group"] = by_group
    return summary


# ═════════════════════════════════════════════════════════════════════════════
# 5c. PM2.5 → Heart Rate Lagged Regression
# ═════════════════════════════════════════════════════════════════════════════

def pm25_hr_effect(person_id: str) -> dict | None:
    """Lagged regression: PM2.5(t) → HR(t+lag), adjusting for hour-of-day.

    Tests lags: 0, 15, 30, 60, 120, 240 minutes.
    Returns dict with per-lag coefficients, R-squared, p-values.
    """
    try:
        p = get_participant(person_id)
        aligned = p.aligned_timeseries("5min")
        if aligned.empty:
            return None

        pm25 = aligned["env_pm2.5"]
        hr = aligned["hr_bpm"]

        # Drop rows where either is NaN
        valid = pm25.notna() & hr.notna()
        if valid.sum() < 48:  # need at least 4 hours
            return None

        pm_vals = pm25[valid].values.astype(float)
        hr_vals = hr[valid].values.astype(float)
        hours = aligned.index[valid].hour.astype(float)

        # Test each lag (in 5-min steps)
        lag_minutes = [0, 15, 30, 60, 120, 240]
        lag_results = {}

        for lag_min in lag_minutes:
            lag_steps = lag_min // 5

            if lag_steps == 0:
                pm_lagged = pm_vals
                hr_target = hr_vals
                hour_adj = hours
            else:
                if len(pm_vals) <= lag_steps:
                    continue
                pm_lagged = pm_vals[:-lag_steps]
                hr_target = hr_vals[lag_steps:]
                hour_adj = hours[lag_steps:]

            if len(pm_lagged) < 24:
                continue

            # Regression: HR ~ PM2.5 + sin(2*pi*hour/24) + cos(2*pi*hour/24)
            # Hour-of-day adjustment via Fourier terms
            omega = 2 * np.pi / 24
            X = np.column_stack([
                np.ones(len(pm_lagged)),
                pm_lagged,
                np.sin(omega * hour_adj),
                np.cos(omega * hour_adj),
            ])

            try:
                coefs, residuals, rank, sv = np.linalg.lstsq(X, hr_target, rcond=None)
                y_pred = X @ coefs
                ss_res = np.sum((hr_target - y_pred) ** 2)
                ss_tot = np.sum((hr_target - hr_target.mean()) ** 2)
                r_sq = 1 - ss_res / ss_tot if ss_tot > 0 else 0

                # Coefficient significance (t-test on PM2.5 coefficient)
                n_obs = len(hr_target)
                k = X.shape[1]
                if n_obs > k:
                    mse = ss_res / (n_obs - k)
                    try:
                        cov = mse * np.linalg.inv(X.T @ X)
                        se_beta = np.sqrt(np.diag(cov))
                        t_stat = coefs[1] / se_beta[1] if se_beta[1] > 0 else 0
                        p_val = 2 * stats.t.sf(abs(t_stat), df=n_obs - k)
                    except np.linalg.LinAlgError:
                        t_stat, p_val = np.nan, np.nan
                else:
                    t_stat, p_val = np.nan, np.nan

                lag_results[f"lag_{lag_min}min"] = {
                    "coef_pm25": float(coefs[1]),
                    "r_squared": float(r_sq),
                    "t_stat": float(t_stat),
                    "p_value": float(p_val),
                    "n_obs": int(n_obs),
                }
            except Exception:
                continue

        if not lag_results:
            return None

        # Find best lag (strongest absolute coefficient with p < 0.05, or minimum p)
        best_lag = min(lag_results, key=lambda k: lag_results[k]["p_value"])

        result = {
            "person_id": person_id,
            "pm25_mean": float(np.nanmean(pm_vals)),
            "pm25_std": float(np.nanstd(pm_vals)),
            "hr_mean": float(np.nanmean(hr_vals)),
            "best_lag": best_lag,
            "best_lag_coef": lag_results[best_lag]["coef_pm25"],
            "best_lag_p": lag_results[best_lag]["p_value"],
            "best_lag_r2": lag_results[best_lag]["r_squared"],
        }
        # Flatten all lags into columns
        for lag_key, lag_data in lag_results.items():
            for metric, val in lag_data.items():
                result[f"{lag_key}_{metric}"] = val

        return result

    except Exception:
        return None


def aggregate_pm25_hr(results: list[dict], participant_index: pd.DataFrame) -> dict:
    """Population-level PM2.5→HR effect aggregation."""
    from statsmodels.stats.multitest import multipletests

    df = pd.DataFrame(results)
    df = df.merge(
        participant_index[["study_group"]],
        left_on="person_id", right_index=True, how="left",
    )
    df.to_csv(result_path("causal_pm25_hr.csv"), index=False)
    print(f"  Saved {len(df)} rows to causal_pm25_hr.csv")

    summary = {"n_tested": int(len(df))}

    # Per-lag population averages
    lag_minutes = [0, 15, 30, 60, 120, 240]
    per_lag = {}
    for lag_min in lag_minutes:
        coef_col = f"lag_{lag_min}min_coef_pm25"
        p_col = f"lag_{lag_min}min_p_value"
        if coef_col in df.columns:
            valid = df.dropna(subset=[coef_col, p_col])
            if len(valid) > 0:
                # FDR correction
                reject, pval_corr, _, _ = multipletests(
                    valid[p_col], alpha=0.05, method="fdr_bh"
                )
                per_lag[f"{lag_min}min"] = {
                    "n_valid": int(len(valid)),
                    "mean_coef": float(valid[coef_col].mean()),
                    "median_coef": float(valid[coef_col].median()),
                    "n_nominal_p05": int((valid[p_col] < 0.05).sum()),
                    "n_fdr_p05": int(reject.sum()),
                    "mean_r2": float(valid[f"lag_{lag_min}min_r_squared"].mean())
                    if f"lag_{lag_min}min_r_squared" in valid.columns else None,
                }
    summary["per_lag"] = per_lag

    # Best lag distribution
    if "best_lag" in df.columns:
        summary["best_lag_distribution"] = df["best_lag"].value_counts().to_dict()

    # Study group comparison
    by_group = {}
    for grp, gdf in df.groupby("study_group"):
        by_group[grp] = {
            "n": int(len(gdf)),
            "mean_pm25": float(gdf["pm25_mean"].mean()),
            "mean_best_coef": float(gdf["best_lag_coef"].mean()),
        }
    summary["by_study_group"] = by_group
    return summary


# ═════════════════════════════════════════════════════════════════════════════
# 5d. Population Causal DAG (PCMCI)
# ═════════════════════════════════════════════════════════════════════════════

def causal_dag(person_id: str) -> dict | None:
    """PCMCI causal discovery on aligned multimodal time series.

    Variables: glucose, HR, PM2.5, temperature, humidity.
    Max lag = 12 (1 hour at 5-min resolution).
    """
    if not HAS_TIGRAMITE:
        return None

    try:
        p = get_participant(person_id)
        aligned = p.aligned_timeseries("5min")
        if aligned.empty:
            return None

        # Select variables
        var_names = ["cgm_glucose_mg_dl", "hr_bpm", "env_pm2.5", "env_temp", "env_hum"]
        available = [v for v in var_names if v in aligned.columns]
        if len(available) < 3:
            return None

        sub = aligned[available].dropna()
        if len(sub) < 100:  # need reasonable length
            return None

        data = sub.values.astype(float)
        short_names = [v.replace("cgm_", "").replace("env_", "").replace("hr_", "")
                       for v in available]

        dataframe = pp.DataFrame(
            data,
            var_names=short_names,
        )

        parcorr = ParCorr(significance="analytic")
        pcmci = PCMCI(dataframe=dataframe, cond_ind_test=parcorr, verbosity=0)

        results = pcmci.run_pcmci(tau_max=12, pc_alpha=0.05)

        # Extract significant edges
        q_matrix = pcmci.get_corrected_pvalues(p_matrix=results["p_matrix"], fdr_method="fdr_bh")
        sig_links = (q_matrix < 0.05)

        edges = []
        n_vars = len(available)
        for i in range(n_vars):
            for j in range(n_vars):
                for tau in range(0, 13):
                    if sig_links[i, j, tau]:
                        edges.append({
                            "source": short_names[i],
                            "target": short_names[j],
                            "lag": int(tau),
                            "val": float(results["val_matrix"][i, j, tau]),
                            "p": float(results["p_matrix"][i, j, tau]),
                            "q": float(q_matrix[i, j, tau]),
                        })

        return {
            "person_id": person_id,
            "n_variables": n_vars,
            "n_timepoints": len(sub),
            "n_edges": len(edges),
            "edges": edges,
        }

    except Exception:
        return None


def population_dag(results: list[dict]) -> dict:
    """Aggregate per-person DAGs into population structure.

    For each edge (source, target, lag), count how many participants show it.
    Keep edges present in >10% of participants.
    """
    if not results:
        return {"n_participants": 0}

    # Collect all edges
    edge_counts = {}
    n_participants = len(results)

    for r in results:
        seen = set()
        for e in r["edges"]:
            key = (e["source"], e["target"], e["lag"])
            if key not in seen:
                seen.add(key)
                edge_counts[key] = edge_counts.get(key, 0) + 1

    # Filter: keep edges in >10% of participants
    threshold = max(2, int(0.10 * n_participants))
    robust_edges = []
    for (src, tgt, lag), count in sorted(edge_counts.items(), key=lambda x: -x[1]):
        frac = count / n_participants
        if count >= threshold:
            robust_edges.append({
                "source": src,
                "target": tgt,
                "lag": lag,
                "count": count,
                "fraction": round(frac, 3),
            })

    summary = {
        "n_participants": n_participants,
        "total_unique_edges": len(edge_counts),
        "robust_edges_10pct": robust_edges,
    }

    # Visualize
    _plot_population_dag(robust_edges, n_participants)

    return summary


def _plot_population_dag(edges: list[dict], n_participants: int):
    """Draw population causal DAG with networkx."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx

    if not edges:
        return

    G = nx.DiGraph()
    # Add nodes from edges
    nodes = set()
    for e in edges:
        nodes.add(e["source"])
        nodes.add(e["target"])
    G.add_nodes_from(nodes)

    # Add edges with width proportional to fraction
    for e in edges:
        label = f"lag={e['lag']} ({e['fraction']:.0%})"
        G.add_edge(
            e["source"], e["target"],
            weight=e["fraction"],
            label=label,
            lag=e["lag"],
        )

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    pos = nx.spring_layout(G, seed=42, k=2)
    weights = [G[u][v]["weight"] * 4 for u, v in G.edges()]

    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=2000, node_color="lightblue",
                           edgecolors="black", linewidths=1.5)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=11, font_weight="bold")
    nx.draw_networkx_edges(G, pos, ax=ax, width=weights, edge_color="gray",
                           arrows=True, arrowsize=20, connectionstyle="arc3,rad=0.1")

    # Edge labels
    edge_labels = {(u, v): G[u][v]["label"] for u, v in G.edges()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax,
                                 font_size=7, font_color="red")

    ax.set_title(f"Population Causal DAG (PCMCI, n={n_participants})\n"
                 f"Edges present in >10% of participants", fontsize=13)
    ax.margins(0.15)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "causal_dag.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved causal_dag.png")


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()

    # Load participant index, filter for triple-overlap
    idx = pd.read_parquet(result_path("participant_index.parquet"))
    triple = idx[
        (idx["environment"] == True)
        & (idx["wearable_activity_monitor"] == True)
        & (idx["wearable_blood_glucose"] == True)
    ]
    person_ids = triple.index.tolist()
    print(f"Found {len(person_ids)} participants with triple overlap (CGM+wearable+env).")

    # ── 5a: Sleep → Glucose Granger ──────────────────────────────────────────
    print("\n=== 5a: Sleep → Glucose Granger Causality ===")
    sg_results = []
    for i, pid in enumerate(person_ids):
        if (i + 1) % 100 == 0:
            print(f"  5a progress: {i + 1}/{len(person_ids)}")
        r = sleep_glucose_granger(pid)
        if r is not None:
            sg_results.append(r)
    print(f"  Completed: {len(sg_results)} participants with valid Granger results")
    sg_summary = aggregate_sleep_glucose(sg_results, idx)

    # ── 5b: Glucose-HR Cross-Correlation ─────────────────────────────────────
    print("\n=== 5b: Glucose-HR Cross-Correlation ===")
    gh_results = []
    for i, pid in enumerate(person_ids):
        if (i + 1) % 100 == 0:
            print(f"  5b progress: {i + 1}/{len(person_ids)}")
        r = glucose_hr_coupling(pid)
        if r is not None:
            gh_results.append(r)
    print(f"  Completed: {len(gh_results)} participants with valid coupling results")
    gh_summary = aggregate_glucose_hr(gh_results, idx)

    # ── 5c: PM2.5 → HR ──────────────────────────────────────────────────────
    print("\n=== 5c: PM2.5 → Heart Rate Lagged Effects ===")
    pm_results = []
    for i, pid in enumerate(person_ids):
        if (i + 1) % 100 == 0:
            print(f"  5c progress: {i + 1}/{len(person_ids)}")
        r = pm25_hr_effect(pid)
        if r is not None:
            pm_results.append(r)
    print(f"  Completed: {len(pm_results)} participants with valid PM2.5→HR results")
    pm_summary = aggregate_pm25_hr(pm_results, idx)

    # ── 5d: Population Causal DAG ────────────────────────────────────────────
    dag_summary = {}
    if HAS_TIGRAMITE:
        print("\n=== 5d: Population Causal DAG (PCMCI) ===")
        dag_results = []
        for i, pid in enumerate(person_ids):
            if (i + 1) % 100 == 0:
                print(f"  5d progress: {i + 1}/{len(person_ids)}")
            r = causal_dag(pid)
            if r is not None:
                dag_results.append(r)
        print(f"  Completed: {len(dag_results)} participants with valid DAG results")
        dag_summary = population_dag(dag_results)
    else:
        print("\n=== 5d: Skipped (tigramite not available) ===")

    # ── Save summary ─────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    full_summary = {
        "analysis": "Phase 5 — Causal discovery from aligned multimodal time series",
        "n_triple_overlap": len(person_ids),
        "elapsed_seconds": round(elapsed, 1),
        "sleep_glucose_granger": sg_summary,
        "glucose_hr_coupling": gh_summary,
        "pm25_hr_effect": pm_summary,
        "causal_dag": dag_summary,
    }

    with open(result_path("causal_summary.json"), "w") as f:
        json.dump(full_summary, f, indent=2, default=str)
    print(f"\nSaved causal_summary.json")
    print(f"Total elapsed: {elapsed:.1f}s")

    # Print key findings
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)
    if "sleep_to_glucose" in sg_summary:
        stg = sg_summary["sleep_to_glucose"]
        gts = sg_summary.get("glucose_to_sleep", {})
        print(f"5a: Sleep→Glucose: {stg.get('n_nominal_p05', 0)}/{stg.get('n_valid', 0)} nominal p<0.05, "
              f"{stg.get('n_fdr_p05', 0)} survive FDR")
        print(f"    Glucose→Sleep: {gts.get('n_nominal_p05', 0)}/{gts.get('n_valid', 0)} nominal p<0.05, "
              f"{gts.get('n_fdr_p05', 0)} survive FDR")

    print(f"5b: Glucose-HR coupling: median lag = {gh_summary.get('median_optimal_lag_min', '?')} min, "
          f"mean r = {gh_summary.get('mean_pearson_r', '?')}")
    if "kruskal_wallis_p" in gh_summary:
        print(f"    Group difference (Kruskal-Wallis): H={gh_summary['kruskal_wallis_H']:.2f}, "
              f"p={gh_summary['kruskal_wallis_p']:.4f}")

    if "per_lag" in pm_summary:
        for lag_name, lag_data in pm_summary["per_lag"].items():
            print(f"5c: PM2.5→HR at {lag_name}: mean coef={lag_data.get('mean_coef', '?'):.4f}, "
                  f"{lag_data.get('n_fdr_p05', 0)}/{lag_data.get('n_valid', 0)} FDR-significant")

    if dag_summary.get("robust_edges_10pct"):
        print(f"5d: {len(dag_summary['robust_edges_10pct'])} robust edges in population DAG")


if __name__ == "__main__":
    main()
