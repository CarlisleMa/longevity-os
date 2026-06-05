"""The 24-hour day view: activities + synthesized glucose/HR signal."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..services import day_service

router = APIRouter(prefix="/api/users", tags=["day"])


@router.get("/{user_id}/day")
def day(user_id: str):
    data = day_service.day(user_id)
    if data is None:
        raise HTTPException(404, f"No day data for user '{user_id}'")
    return data
