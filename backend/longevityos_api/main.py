"""LongevityOS backend — FastAPI application.

Run:  uvicorn longevityos_api.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import CORS_ORIGINS, USERS, run_modes
from .routers import agent, ingest, interventions, knowledge_base, scoring, users
from .schemas import MetaResponse
from .services import knowledge_service

app = FastAPI(
    title="LongevityOS API",
    version=__version__,
    description="Personal longevity OS — upload data, grow a private knowledge base, "
    "get evidence-grounded interventions. Wellness/informational, not medical advice.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (users, ingest, scoring, knowledge_base, agent, interventions):
    app.include_router(r.router)


@app.on_event("startup")
def _ensure_dirs():
    USERS.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta", response_model=MetaResponse, tags=["meta"])
def meta():
    return {
        "version": __version__,
        "run_modes": run_modes(),
        "knowledge_cards": len(knowledge_service.all_cards()),
        "note": "LongevityOS API",
    }


@app.get("/", tags=["meta"])
def root():
    return {
        "name": "LongevityOS API",
        "version": __version__,
        "docs": "/docs",
        "meta": "/api/meta",
    }
