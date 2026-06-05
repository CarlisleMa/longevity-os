"""User listing and creation."""

from __future__ import annotations

import json
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import USERS
from ..schemas import UserSummary
from ..services import store

router = APIRouter(prefix="/api/users", tags=["users"])


class CreateUser(BaseModel):
    display_name: str


@router.get("", response_model=list[UserSummary])
def list_users():
    return store.list_users()


@router.post("", response_model=UserSummary, status_code=201)
def create_user(body: CreateUser):
    slug = re.sub(r"[^a-z0-9]+", "_", body.display_name.strip().lower()).strip("_") or "user"
    user_dir = USERS / slug
    if user_dir.exists():
        raise HTTPException(409, f"User '{slug}' already exists")
    user_dir.mkdir(parents=True, exist_ok=True)
    profile = {"user_id": slug, "display_name": body.display_name}
    with open(user_dir / "profile.json", "w") as fh:
        json.dump(profile, fh, indent=2)
    # Seed an empty knowledge base so downstream endpoints resolve.
    with open(user_dir / "kb.json", "w") as fh:
        json.dump({"profile": profile}, fh, indent=2)
    return {"user_id": slug, "display_name": body.display_name, "is_demo": False}
