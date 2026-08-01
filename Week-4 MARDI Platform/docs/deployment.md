# Deployment Guide — Section 35

**Status: deployment configuration is ready and locally verified; actual
hosting requires connecting your own account on the chosen platform (an
API key, a GitHub repo, and a Render/Railway account — none of which this
environment has access to). This is stated plainly rather than claiming a
live URL that doesn't exist.**

## What's provided

| File | Purpose |
|---|---|
| `render.yaml` (repo root) | One-click Render Blueprint — provisions both the backend (Docker web service) and frontend (static site) |
| `backend/Dockerfile` | Serves the FastAPI app via `uvicorn` on `$PORT` by default (verified locally with `PORT=8123`, confirmed `/api/health` responds correctly) |
| `backend/Procfile` | Alternative for Railway/Heroku-style platforms that use Procfiles instead of a Blueprint |
| `frontend/src/api/client.js` | Now resolves its API base from `VITE_API_BASE` at build time, so the same code works both in local dev (via Vite's proxy) and as a statically-hosted production build pointed at a separately-deployed backend |

## Deploying on Render (recommended path)

1. Push this repo to GitHub (public or private, either works with Render).
2. In the Render dashboard: **New +** → **Blueprint** → select the repo. Render reads `render.yaml` automatically.
3. When prompted for `GEMINI_API_KEY` (marked `sync: false` in `render.yaml` so it is never stored in the repo), paste your key. Render stores it as an encrypted environment variable, never in git.
4. Render provisions both services. Note the backend's assigned URL (e.g. `https://mardi-backend-xxxx.onrender.com`).
5. Edit `render.yaml`'s `VITE_API_BASE` value to that exact URL, commit, and push — Render redeploys the frontend automatically with the correct backend target baked in at build time.
6. Visit the frontend service's URL. That's the deployed app.

## Deploying on Railway (alternative)

1. `railway init` in `backend/`, or connect the GitHub repo in the Railway dashboard.
2. Railway auto-detects `backend/Procfile` (or the Dockerfile — either works).
3. Set `GEMINI_API_KEY`, `LLM_PROVIDER=gemini`, `LLM_MODE=auto` as Railway environment variables (never committed to the repo).
4. Deploy `frontend/` as a separate Railway static site (or any static host — Netlify/Vercel/Cloudflare Pages all work identically, since the frontend is a plain Vite build with no server-side requirements), setting `VITE_API_BASE` to the backend's Railway URL at build time.

## How each deployment requirement is met

- **Protect API keys:** Every platform above stores `GEMINI_API_KEY` as an encrypted environment variable, injected at runtime — never committed to the repo (`.env` is a local-only file; `.env.example` is the only version-controlled template, and contains no real key). Verified automatically by `verify_requirements.py`'s "no hard-coded API keys" check.
- **Handle errors gracefully:** Already built into the running system, not added for deployment — `app/api.py`'s `_run_graph` wraps the entire workflow execution in try/except and surfaces `session.error` + `session.status="error"` to the frontend rather than crashing the process; `llm_client.py`'s hard timeout (Section on the earlier hang bug) prevents an indefinite hang from a stalled network call.
- **Provide sample requests:** Already built into the running system — `frontend/src/components/RequestForm.jsx`'s example chips are the four example requests from Part 1 of the assignment brief.
- **Display workflow progress:** Already built into the running system — the entire React dashboard (Task Plan, Agent Pipeline status, Evidence count, Execution Log) polls the backend live; this is Requirement 16's dashboard, unchanged for deployment.
- **Be accessible during evaluation:** Both services above use free tiers suitable for grading-period access; see limitations below for the specific behavior to expect on a free tier.

## Documented limitations of the deployed environment

> These are also included in the consolidated
> [`docs/known_limitations.md`](known_limitations.md) (Deployment &
> Infrastructure section) alongside every other known limitation in the
> project.

Being upfront about what does **not** carry over perfectly from local
development to a hosted free-tier deployment:

1. **In-memory run state is lost on redeploy or free-tier sleep.**
   `RunSession` objects live in a Python dict in `app/api.py`'s process
   memory (see the comment in that file). Render/Railway free-tier
   services spin down after a period of inactivity and lose all in-memory
   state on the next cold start — run history will not survive that. A
   production deployment needing persistent run history would need to
   swap the in-memory `SESSIONS` dict for a real database, which was
   intentionally out of scope here (see `app/tools/evidence.py`'s
   docstring, which flags the same in-memory-vs-database trade-off for
   the evidence store).
2. **Free-tier cold starts add latency.** The first request after a period
   of inactivity may take 30-60+ seconds while the platform spins the
   container back up — this is a platform characteristic, not an
   application bug.
3. **No authentication.** As flagged in `docs/security_review.md` (R7,
   R10, R11), there is currently no login/auth layer, no per-user rate
   limiting, and no protection against a script bypassing the frontend to
   call the checkpoint-resolution endpoint directly. This is acceptable
   for an evaluation/demo deployment behind an unlisted URL, but is
   explicitly flagged as unsuitable for a public production launch without
   adding auth first.
4. **Live-mode LLM calls cost real money once deployed publicly.** Anyone
   with the deployed URL can trigger `POST /api/runs`, which makes real
   Gemini/Anthropic API calls if `LLM_MODE` resolves to `live`. Combined
   with limitation #3 (no rate limiting), this means an unlisted-but-public
   URL should not be shared widely without first adding the cost controls
   flagged in the security review.
