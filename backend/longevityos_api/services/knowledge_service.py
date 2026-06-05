"""Knowledge cards: the research evidence priors the agent and UI cite.

This is REAL data — distilled from validated AI-READI findings in
engine/knowledge_cards/knowledge_cards.json.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from ..config import KNOWLEDGE_CARDS_PATH, load_json


@lru_cache(maxsize=1)
def all_cards() -> list[dict]:
    return load_json(KNOWLEDGE_CARDS_PATH, []) or []


def get_card(card_id: str) -> Optional[dict]:
    for c in all_cards():
        if c.get("id") == card_id:
            return c
    return None


def cards_for_metric(metric: str) -> list[dict]:
    return [c for c in all_cards() if metric in c.get("metrics", [])]
