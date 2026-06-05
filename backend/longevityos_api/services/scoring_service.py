"""Scoring: biological-age scorecard, per-system ages, and cross-modal coupling.

Representative mode (default) reads the user's precomputed kb.json. Scoring-live mode would load
frozen aging clocks from model_artifacts/ and compute from normalized streams — see
scoring_service.score_live() for where to wire that (kept lazy so the app runs without sklearn).
"""

from __future__ import annotations

from typing import Optional

from . import store


def dashboard(user_id: str) -> Optional[dict]:
    kb = store.load_kb(user_id)
    if kb is None:
        return None
    return {
        "user_id": user_id,
        "display_name": kb.get("profile", {}).get("display_name", user_id),
        "scorecard": kb.get("scorecard"),
        "systems": kb.get("systems", []),
        "coupling": kb.get("coupling", []),
        "latest_observation": (kb.get("observations") or [None])[-1],
        "top_intervention": (kb.get("interventions") or [None])[0],
    }


def timeline(user_id: str) -> Optional[list[dict]]:
    kb = store.load_kb(user_id)
    if kb is None:
        return None
    return kb.get("timeline", [])


def score_live(user_id: str):  # pragma: no cover - wiring point for Phase 1
    """Real scoring from frozen clocks. Lazy-imports heavy deps on purpose.

    Steps to implement (see docs/BUILD_GUIDE.md Phase 1):
      1. Load normalized/*.parquet for the user.
      2. Build the feature vector with engine.science feature formulas.
      3. joblib.load the frozen clock + scaler/imputer from model_artifacts/.
      4. Predict biological age; place on reference percentile tables; diff vs the user's baseline.
    """
    raise NotImplementedError(
        "Scoring-live not wired yet. Export model_artifacts/ from AI-READI (Phase 1)."
    )
