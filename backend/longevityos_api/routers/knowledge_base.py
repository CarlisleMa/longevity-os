"""User knowledge base + the research knowledge cards (evidence priors)."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, HTTPException

from ..schemas import KnowledgeCard
from ..services import knowledge_service, store

router = APIRouter(prefix="/api", tags=["knowledge"])


@router.get("/users/{user_id}/knowledge-base")
def user_knowledge_base(user_id: str):
    kb = store.load_kb(user_id)
    if kb is None:
        raise HTTPException(404, f"Unknown user '{user_id}'")
    grouped: dict[str, list] = defaultdict(list)
    for item in kb.get("knowledge_base", []):
        grouped[item.get("modality", "other")].append(item)
    return {"user_id": user_id, "groups": grouped}


@router.get("/knowledge-cards", response_model=list[KnowledgeCard])
def knowledge_cards():
    return knowledge_service.all_cards()


@router.get("/knowledge-cards/{card_id}", response_model=KnowledgeCard)
def knowledge_card(card_id: str):
    card = knowledge_service.get_card(card_id)
    if card is None:
        raise HTTPException(404, f"Unknown card '{card_id}'")
    return card
