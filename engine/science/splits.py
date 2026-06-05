"""Create and load alternate participant split assignments.

The AI-READI release provides `recommended_split` in `participants.tsv`.
This module preserves that split and adds deterministic project-local split
columns for sensitivity analyses.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, kruskal, ks_2samp

from .config import result_path
from .participants import load_participants


DEFAULT_BALANCED_SPLIT = "balanced_split_v1"
SPLIT_LABELS = ("train", "val", "test")
DEFAULT_FRACTIONS = {"train": 0.70, "val": 0.15, "test": 0.15}
AGE_BINS = [39, 49, 59, 69, 120]
AGE_LABELS = ["40s", "50s", "60s", "70plus"]


@dataclass(frozen=True)
class SplitConfig:
    column: str = DEFAULT_BALANCED_SPLIT
    seed: int = 20260430
    fractions: dict[str, float] | None = None


def age_bins(age: pd.Series) -> pd.Series:
    """Return coarse age bins used for split stratification and auditing."""
    return pd.cut(age.astype(float), bins=AGE_BINS, labels=AGE_LABELS)


def _allocate_counts(n: int, fractions: dict[str, float], rng: np.random.Generator) -> dict[str, int]:
    """Allocate n rows to train/val/test by largest fractional remainder."""
    if n <= 0:
        return {label: 0 for label in SPLIT_LABELS}

    raw = {label: n * fractions[label] for label in SPLIT_LABELS}
    counts = {label: int(np.floor(raw[label])) for label in SPLIT_LABELS}
    remainder = n - sum(counts.values())
    order = sorted(
        SPLIT_LABELS,
        key=lambda label: (-(raw[label] - counts[label]), rng.random()),
    )
    for label in order[:remainder]:
        counts[label] += 1
    return counts


def make_balanced_split(config: SplitConfig = SplitConfig()) -> pd.DataFrame:
    """Create a deterministic split balanced by site, study group, and age bin.

    The balancing stratum is `(clinical_site, study_group, age_bin)`. The
    provided `recommended_split` remains in the output for comparison.
    """
    fractions = config.fractions or DEFAULT_FRACTIONS
    total = sum(fractions.values())
    if not np.isclose(total, 1.0):
        raise ValueError(f"split fractions must sum to 1.0, got {total}")
    if set(fractions) != set(SPLIT_LABELS):
        raise ValueError(f"split fractions must have labels {SPLIT_LABELS}")

    participants = load_participants().copy()
    participants["age_bin"] = age_bins(participants["age"])
    rng = np.random.default_rng(config.seed)
    assignments: dict[str, str] = {}

    strata = ["clinical_site", "study_group", "age_bin"]
    for _, group in participants.groupby(strata, observed=True, sort=True):
        ids = group.index.to_numpy(dtype=str)
        ids = rng.permutation(ids)
        counts = _allocate_counts(len(ids), fractions, rng)
        start = 0
        for split_label in SPLIT_LABELS:
            stop = start + counts[split_label]
            for person_id in ids[start:stop]:
                assignments[str(person_id)] = split_label
            start = stop

    out = participants[["clinical_site", "study_group", "age", "recommended_split"]].copy()
    out[config.column] = pd.Series(assignments, name=config.column)
    out["age_bin"] = participants["age_bin"].astype(str)
    out.index.name = "person_id"
    return out


def load_split_assignments() -> pd.DataFrame:
    """Load saved split assignments, or return an empty frame if absent."""
    path = result_path("split_assignments.parquet")
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    if "person_id" in df.columns:
        df["person_id"] = df["person_id"].astype(str)
        df = df.set_index("person_id")
    df.index = df.index.astype(str)
    return df


def attach_split_columns(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Attach saved alternate split columns to a person-indexed dataframe."""
    out = df.copy()
    out.index = out.index.astype(str)
    needed = [col for col in (columns or []) if col not in out.columns]
    if columns is None:
        needed = []
    if not needed and columns is not None:
        return out

    splits = load_split_assignments()
    if splits.empty:
        if needed:
            raise FileNotFoundError(
                f"Missing split assignment artifact: {result_path('split_assignments.parquet')}. "
                "Run `python -m scripts.splits` first."
            )
        return out

    split_cols = [
        col for col in splits.columns
        if col.endswith("_split") or "_split_" in col or col == "recommended_split"
    ]
    if columns is not None:
        missing = [col for col in columns if col not in out.columns and col not in splits.columns]
        if missing:
            raise KeyError(f"Split column(s) not found in dataframe or split assignments: {missing}")
        split_cols = [col for col in columns if col not in out.columns]

    if split_cols:
        out = out.join(splits[split_cols], how="left")
    return out


def require_split_column(df: pd.DataFrame, split_column: str) -> pd.DataFrame:
    """Return dataframe with split_column attached, raising a clear error if absent."""
    out = attach_split_columns(df, [split_column])
    if split_column not in out.columns:
        raise KeyError(f"Split column not found: {split_column}")
    missing = out[split_column].isna()
    if missing.any():
        raise ValueError(f"{split_column} is missing for {int(missing.sum())} participants")
    return out


def balance_report(df: pd.DataFrame, split_column: str) -> tuple[pd.DataFrame, dict]:
    """Build tabular and JSON-friendly balance diagnostics."""
    audit = df.copy()
    audit["age_bin"] = age_bins(audit["age"]).astype(str)
    rows = []
    for variable in ["clinical_site", "study_group", "age_bin"]:
        overall = audit[variable].value_counts(normalize=True)
        for split_label, sub in audit.groupby(split_column, sort=True):
            split_dist = sub[variable].value_counts(normalize=True)
            for level in sorted(audit[variable].dropna().unique()):
                rows.append({
                    "split_column": split_column,
                    "variable": variable,
                    "level": level,
                    "split": split_label,
                    "n": int((sub[variable] == level).sum()),
                    "split_pct": round(float(100 * split_dist.get(level, 0.0)), 3),
                    "overall_pct": round(float(100 * overall.get(level, 0.0)), 3),
                    "delta_pct": round(float(100 * (split_dist.get(level, 0.0) - overall.get(level, 0.0))), 3),
                })

    report = pd.DataFrame(rows)
    summary = {
        "split_column": split_column,
        "counts": {k: int(v) for k, v in audit[split_column].value_counts().sort_index().items()},
        "max_abs_delta_pct": {
            var: float(report.loc[report["variable"].eq(var), "delta_pct"].abs().max())
            for var in ["clinical_site", "study_group", "age_bin"]
        },
    }

    for variable in ["clinical_site", "study_group", "age_bin"]:
        table = pd.crosstab(audit[split_column], audit[variable])
        summary[f"chi2_p_{variable}"] = float(chi2_contingency(table)[1])
    groups = [sub["age"].to_numpy(dtype=float) for _, sub in audit.groupby(split_column, sort=True)]
    summary["kruskal_p_age"] = float(kruskal(*groups)[1])
    train_age = audit.loc[audit[split_column].eq("train"), "age"]
    test_age = audit.loc[audit[split_column].eq("test"), "age"]
    summary["ks_p_train_test_age"] = float(ks_2samp(train_age, test_age).pvalue)
    return report, summary


def save_balanced_split(config: SplitConfig = SplitConfig()) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Create and save split assignments plus balance diagnostics."""
    assignments = make_balanced_split(config)
    existing = load_split_assignments()
    if not existing.empty:
        keep = [col for col in existing.columns if col not in assignments.columns]
        assignments = assignments.join(existing[keep], how="left")

    assignments.to_parquet(result_path("split_assignments.parquet"))
    report, summary = balance_report(assignments, config.column)
    report.to_csv(result_path("split_balance_report.csv"), index=False)
    with result_path("split_balance_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    return assignments, report, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Create balanced alternate train/val/test splits")
    parser.add_argument("--split-column", default=DEFAULT_BALANCED_SPLIT)
    parser.add_argument("--seed", type=int, default=20260430)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--test-frac", type=float, default=0.15)
    args = parser.parse_args()

    config = SplitConfig(
        column=args.split_column,
        seed=args.seed,
        fractions={"train": args.train_frac, "val": args.val_frac, "test": args.test_frac},
    )
    assignments, _report, summary = save_balanced_split(config)
    print(f"Saved split assignments: {result_path('split_assignments.parquet')}")
    print(f"Saved split balance report: {result_path('split_balance_report.csv')}")
    print(f"Saved split balance summary: {result_path('split_balance_summary.json')}")
    print(assignments[config.column].value_counts().sort_index().to_string())
    print(json.dumps(summary["max_abs_delta_pct"], indent=2))


if __name__ == "__main__":
    main()
