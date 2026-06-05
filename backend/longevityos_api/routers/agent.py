"""Agent observations over a user's current state."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import Observation
from ..services import agent_service

router = APIRouter(prefix="/api/users", tags=["agent"])


@router.get("/{user_id}/agent/observations", response_model=list[Observation])
def observations(user_id: str):
    data = agent_service.observations(user_id)
    if data is None:
        raise HTTPException(404, f"Unknown user '{user_id}'")
    return data


@router.post("/{user_id}/agent/observe", response_model=Observation)
def observe(user_id: str):
    obs = agent_service.generate_observation(user_id)
    if obs is None:
        raise HTTPException(404, f"Unknown user '{user_id}'")
    return obs
