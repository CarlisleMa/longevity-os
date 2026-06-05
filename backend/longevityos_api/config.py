"""Paths and run-mode detection for the LongevityOS backend.

Three run modes (see docs/ARCHITECTURE.md):
  - representative (default): serve the synthetic demo user; canned-but-realistic agent output.
  - scoring-live:  model_artifacts present -> real aging-clock scoring on user data.
  - agent-live:    ANTHROPIC_API_KEY set   -> real agent reasoning + intervention generation.

The app always runs; missing capability degrades gracefully and is reported via /api/meta.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# longevityos_api/ -> backend/ -> LongevityOS/
ROOT = Path(__file__).resolve().parents[2]

ENGINE = ROOT / "engine"
KNOWLEDGE_CARDS_PATH = ENGINE / "knowledge_cards" / "knowledge_cards.json"
HYPOTHESES_DIR = ENGINE / "hypothesis" / "hypotheses"

DATA = ROOT / "data"
DEMO_USERS = DATA / "demo_users"
USERS = DATA / "users"  # runtime, gitignored

MODEL_ARTIFACTS = ROOT / "model_artifacts"
WEIGHTS_DIR = MODEL_ARTIFACTS / "weights"

DEMO_USER_ID = "demo_alex"

# CORS origins for the local frontend.
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def agent_live() -> bool:
    """True when a real Anthropic key is available for the agent layer."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def scoring_live() -> bool:
    """True when exported model artifacts are present for real scoring."""
    return MODEL_ARTIFACTS.exists() and any(MODEL_ARTIFACTS.glob("*.joblib"))


def run_modes() -> dict:
    return {
        "representative": True,
        "scoring_live": scoring_live(),
        "agent_live": agent_live(),
    }


def load_json(path: Path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default
