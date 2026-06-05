"""Intervention recommendations (gated) + accept/dismiss."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import Intervention
from ..services import intervention_service

router = APIRouter(prefix="/api/users", tags=["interventions"])


@router.get("/{user_id}/interventions", response_model=list[Intervention])
def interventions(user_id: str):
    data = intervention_service.recommend(user_id)
    if data is None:
        raise HTTPException(404, f"Unknown user '{user_id}'")
    return data


@router.post("/{user_id}/interventions/{intervention_id}/accept", response_model=Intervention)
def accept(user_id: str, intervention_id: str):
    item = intervention_service.set_status(user_id, intervention_id, "accepted")
    if item is None:
        raise HTTPException(404, "Unknown user or intervention")
    return item


@router.post("/{user_id}/interventions/{intervention_id}/dismiss", response_model=Intervention)
def dismiss(user_id: str, intervention_id: str):
    item = intervention_service.set_status(user_id, intervention_id, "dismissed")
    if item is None:
        raise HTTPException(404, "Unknown user or intervention")
    return item
