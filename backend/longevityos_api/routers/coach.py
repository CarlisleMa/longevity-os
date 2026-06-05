"""Health coach: a personalized multi-agent consult grounded in your profile."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import coach_service

router = APIRouter(prefix="/api/users", tags=["coach"])
agents_router = APIRouter(prefix="/api/coach", tags=["coach"])


class CoachRequest(BaseModel):
    message: str
    history: Optional[list] = None


@router.post("/{user_id}/coach")
def coach(user_id: str, body: CoachRequest):
    data = coach_service.answer(user_id, body.message, body.history)
    if data is None:
        raise HTTPException(404, f"Unknown user '{user_id}'")
    return data


@agents_router.get("/agents")
def agents():
    """The personalized care team (roster of agents)."""
    return {"agents": coach_service.roster()}
