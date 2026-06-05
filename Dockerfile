# LongevityOS backend (FastAPI). Build from the repo root:
#   docker build -t longevityos-api .
#   docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-... longevityos-api
FROM python:3.11-slim

WORKDIR /app

# Install runtime deps first (better layer caching).
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# App code + the data the backend reads at runtime (demo user + evidence cards).
COPY backend ./backend
COPY engine/knowledge_cards ./engine/knowledge_cards
COPY data/demo_users ./data/demo_users

WORKDIR /app/backend
ENV PORT=8000
EXPOSE 8000

# Shell form so the host-provided $PORT is expanded (Render/Railway/Fly set it).
CMD uvicorn longevityos_api.main:app --host 0.0.0.0 --port ${PORT}
