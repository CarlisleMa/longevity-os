"""Health coach: a personalized multi-agent consult + streaming team debate."""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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


@router.post("/{user_id}/coach/debate")
async def coach_debate(user_id: str, body: CoachRequest):
    """Stream a multi-agent team debate as Server-Sent Events."""
    gen = coach_service.debate(user_id, body.message)
    if gen is None:
        raise HTTPException(404, f"Unknown user '{user_id}'")

    async def sse():
        async for event in gen:
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@agents_router.get("/agents")
def agents():
    """The personalized care team (roster of agents)."""
    return {"agents": coach_service.roster()}
