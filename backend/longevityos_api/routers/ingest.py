"""Ingestion endpoint.

Representative mode acknowledges uploads and returns a synthetic ingest event so the frontend
flow works end-to-end. Real parsing (Apple Health / Garmin / labs / FHIR / omics → normalized
schema) is docs/BUILD_GUIDE.md Phase 4; wire it in services and write to data/users/<id>/.
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..services import store

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/{user_id}")
async def ingest(user_id: str, files: list[UploadFile] = File(default=[])):
    if store.user_dir(user_id) is None:
        raise HTTPException(404, f"Unknown user '{user_id}'")
    received = [{"filename": f.filename, "content_type": f.content_type} for f in files]
    # Representative: we don't persist or parse raw uploads in the prototype.
    return {
        "user_id": user_id,
        "received": received,
        "status": "accepted",
        "mode": "representative",
        "note": "Parsing to the normalized schema is Phase 4. See docs/BUILD_GUIDE.md.",
    }
