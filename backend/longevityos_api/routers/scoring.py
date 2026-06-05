"""Dashboard + timeline (scoring outputs)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import DashboardResponse, TimelineEvent
from ..services import scoring_service

router = APIRouter(prefix="/api/users", tags=["scoring"])


@router.get("/{user_id}/dashboard", response_model=DashboardResponse)
def dashboard(user_id: str):
    data = scoring_service.dashboard(user_id)
    if data is None:
        raise HTTPException(404, f"Unknown user '{user_id}'")
    return data


@router.get("/{user_id}/timeline", response_model=list[TimelineEvent])
def timeline(user_id: str):
    data = scoring_service.timeline(user_id)
    if data is None:
        raise HTTPException(404, f"Unknown user '{user_id}'")
    return data
