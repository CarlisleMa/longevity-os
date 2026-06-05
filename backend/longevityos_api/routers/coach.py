"""Health coach: ask questions grounded in your profile + today's activities."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import coach_service

router = APIRouter(prefix="/api/users", tags=["coach"])


class CoachRequest(BaseModel):
    message: str
    history: Optional[list] = None


@router.post("/{user_id}/coach")
def coach(user_id: str, body: CoachRequest):
    data = coach_service.answer(user_id, body.message, body.history)
    if data is None:
        raise HTTPException(404, f"Unknown user '{user_id}'")
    return data
