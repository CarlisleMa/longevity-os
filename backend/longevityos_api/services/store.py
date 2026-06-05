"""Per-user knowledge-base store.

Resolves a user id to a directory (runtime users first, then bundled demo users) and loads its
consolidated `kb.json`. The directory layout mirrors docs/ARCHITECTURE.md; for the prototype the
demo user ships a single consolidated kb.json so the whole app runs with no external data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..config import DEMO_USERS, USERS, load_json


def user_dir(user_id: str) -> Optional[Path]:
    for base in (USERS, DEMO_USERS):
        d = base / user_id
        if d.is_dir():
            return d
    return None


def load_kb(user_id: str) -> Optional[dict]:
    d = user_dir(user_id)
    if d is None:
        return None
    return load_json(d / "kb.json")


def list_users() -> list[dict]:
    out: list[dict] = []
    for base, is_demo in ((USERS, False), (DEMO_USERS, True)):
        if not base.exists():
            continue
        for d in sorted(base.iterdir()):
            if not d.is_dir():
                continue
            profile = load_json(d / "profile.json", {}) or {}
            out.append(
                {
                    "user_id": d.name,
                    "display_name": profile.get("display_name", d.name),
                    "is_demo": is_demo,
                    "created_at": profile.get("created_at"),
                }
            )
    return out
