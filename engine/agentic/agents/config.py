"""Agent system configuration."""

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path("/oak/stanford/scg/lab_twc/mazijian/aireadi")
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
RESULTS_DIR = PROJECT_ROOT / "results"
MEMORY_DIR = RESULTS_DIR / "agent_memory"

# ── Load .env if present ───────────────────────────────────────────────────
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# ── Model settings ─────────────────────────────────────────────────────────
MODEL = os.environ.get("AGENT_MODEL", "claude-sonnet-4-20250514")
MODEL_ORCHESTRATOR = os.environ.get("AGENT_MODEL_ORCH", "claude-sonnet-4-20250514")
MODEL_CRITIC = os.environ.get("AGENT_MODEL_CRITIC", "claude-sonnet-4-20250514")

MAX_TOKENS = 4096
MAX_TURNS = 15
MAX_CODE_RUNTIME_SEC = 120
TEMPERATURE = 0.0

# ── API key ────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Output truncation ──────────────────────────────────────────────────────
MAX_OUTPUT_CHARS = 30_000
