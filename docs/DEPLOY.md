# Deploy LongevityOS

Two pieces deploy separately:

- **Frontend** (Next.js, `frontend/`) → **Vercel** (easiest).
- **Backend** (FastAPI, `backend/`) → **Render / Railway / Fly.io** (any Python/Docker host).

The demo user works with no database and no secrets. The **live multi-agent coach**
turns on automatically when `ANTHROPIC_API_KEY` is set on the backend.

---

## 1. Backend (FastAPI)

### Environment variables

| Var | Required | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | for live coach | Enables live Claude agents. Without it the coach runs grounded/offline. |
| `COACH_MODEL` | no | Model for the coach. Default `claude-opus-4-8`; `claude-sonnet-4-6` is faster/cheaper for debates. |
| `CORS_ORIGINS` | **yes (prod)** | Comma-separated allowed origins, e.g. `https://your-frontend.vercel.app`. **Set this to your deployed frontend URL or the browser will block API calls.** |
| `CORS_ORIGIN_REGEX` | no | Regex to allow a family of origins, e.g. `https://.*\.vercel\.app` for Vercel preview deploys. |
| `PORT` | host-set | The host injects this; the start command reads it. |

### Option A — Render (Docker, one blueprint)

A `Dockerfile` and `render.yaml` are in the repo root.

1. Render → **New → Blueprint** → pick this repo (it reads `render.yaml`).
2. After it provisions, open the service → **Environment** and set:
   - `ANTHROPIC_API_KEY` = your key (secret)
   - `CORS_ORIGINS` = your Vercel URL (add it after step 2 of the frontend, then redeploy)
3. Health check is `/health`. Your API base will be `https://longevityos-api.onrender.com` (or similar).

### Option B — Railway / Fly.io / Heroku-style (Procfile)

A root `Procfile` runs the app from `backend/`:

```
web: uvicorn longevityos_api.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}
```

- **Railway:** New project → deploy this repo → set the env vars above. Build = `pip install -r backend/requirements.txt`.
- **Fly.io:** `fly launch` (it'll use the Dockerfile) → `fly secrets set ANTHROPIC_API_KEY=... CORS_ORIGINS=https://...`.

### Option C — plain Docker / a VM

```bash
docker build -t longevityos-api .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e COACH_MODEL=claude-sonnet-4-6 \
  -e CORS_ORIGINS=https://your-frontend.vercel.app \
  longevityos-api
```

> The image only includes the backend + the demo user + the evidence cards
> (`engine/knowledge_cards/`) — it stays small. Scoring-live extras
> (`backend/requirements-scoring.txt`) are **not** installed; they aren't needed to
> run the app or the coach.

---

## 2. Frontend (Next.js → Vercel)

1. Vercel → **Add New → Project** → import this repo.
2. **Root Directory: `frontend`** (important — the app isn't at the repo root).
3. Framework preset: **Next.js** (auto-detected). Build/Output are default.
4. **Environment Variable:**
   - `NEXT_PUBLIC_API_BASE` = your backend URL (e.g. `https://longevityos-api.onrender.com`)
   - This is read at **build time**, so set it before the first deploy (or redeploy after changing it).
5. Deploy. Then go back and set the backend's `CORS_ORIGINS` to this Vercel URL and redeploy the backend.

---

## 3. Wire-up checklist

- [ ] Backend deployed; `GET /<backend>/health` returns `{"status":"ok"}`.
- [ ] `NEXT_PUBLIC_API_BASE` on Vercel points at the backend URL.
- [ ] `CORS_ORIGINS` on the backend includes the Vercel URL (and any custom domain).
- [ ] (Live coach) `ANTHROPIC_API_KEY` set on the backend → Coach shows **Live · Claude**, `GET /<backend>/api/meta` shows `"agent_live": true`.
- [ ] Open the site → `/dashboard` renders the demo user; `/coach` → Debate streams.

## Notes

- **No persistent storage needed** for the demo (the demo user ships in the repo;
  per-user uploads under `data/users/` are gitignored runtime state).
- **Secrets:** never commit `ANTHROPIC_API_KEY`. Set it in the host's env/secret store.
- **Cost:** the coach debate is ~6–8 sequential model calls. Use `COACH_MODEL=claude-sonnet-4-6`
  to keep it fast and inexpensive.
