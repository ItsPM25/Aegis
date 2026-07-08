# 🚀 Aegis — Deployment Guide

Aegis is **6 services** that talk over HTTP. This guide covers two paths:

1. **Local (recommended for the demo)** — one script, zero cost, no cloud flakiness on stage.
2. **Cloud (Render + Vercel)** — a shareable public link.

| Service | Port | Runtime | Notes |
|---|---|---|---|
| Fraud Shield | 8001 | Python | light |
| Counterfeit Vision | 8002 | Python + **torch** | heavy (~2 GB installed) |
| Fraud Graph | 8003 | Python | light |
| Command backend | 8000 | Python | imports fusion + geospatial |
| Gateway | 4000 | Node / Express | public entry point |
| Dashboard | 3000 | Next.js | browser UI |

---

## Option 1 — Local (recommended)

**Judges watch a live demo — running locally is the norm and avoids cloud cold-starts /
timeouts on stage.** See [`demo-script.md`](demo-script.md) for the run-of-show.

### First time (fresh checkout)
```powershell
./setup.ps1        # creates venvs, installs deps, trains models, npm install
```
Takes a while the first time (torch is ~2 GB). Requires Python 3.11+, Node 18+, and
[`uv`](https://astral.sh/uv) on PATH.

### Every run
```powershell
./run-all.ps1              # launches all 6 services in separate windows
# ... demo ...
./run-all.ps1 -Stop        # stops everything
```
Then open **http://localhost:3000**. The two citizen demo UIs are at
`:8001/` (scam chat) and `:8002/` (camera scanner).

### Optional — live Gen AI narrator
Drop a key in `command-centre/fusion/.env` (a deterministic template narrator runs without one):
```
GROQ_API_KEY=gsk_...      # free & fast — get one at console.groq.com
```

---

## Option 2 — Cloud (Render + Vercel, free tier)

A public URL. **Honest caveats up front:**
- Free tiers **cold-start** (services sleep after ~15 min idle → first request is slow). Hit
  each service once before demoing.
- **Counterfeit Vision (torch ~2 GB) is the hard part** — it often exceeds free-tier build/RAM
  limits. Options: use a paid Render instance for that one service, deploy CPU-only torch
  (`torch --index-url https://download.pytorch.org/whl/cpu`), or run it locally while the rest
  is cloud-hosted.
- Model weights are gitignored, so each service must **train on deploy** (add to the build
  command) or you must commit the weights to a release / bucket.

### Architecture on the cloud
```
Vercel:  Dashboard (Next.js)  ──▶  Render: Gateway ──▶ Render: Backend ──▶ Render: 3 ML services
```

### A. Dashboard → Vercel
1. Import the repo in Vercel; set **Root Directory** to `command-centre/frontend`.
2. Env var: `NEXT_PUBLIC_API_BASE = https://<your-gateway>.onrender.com`
3. Deploy. Vercel auto-detects Next.js.

### B. Gateway → Render (Node web service)
- Root: `command-centre/gateway` · Build: `npm install` · Start: `npm start`
- Env: `COMMAND_API = https://<your-backend>.onrender.com`,
  `ALLOWED_ORIGINS = https://<your-dashboard>.vercel.app`
- Render sets `PORT` automatically (the gateway already reads `process.env.PORT`).

### C. Backend → Render (Python web service)
- Root: `command-centre/backend`
- Build: `pip install -e . -e ../fusion -e ../geospatial`
- Start: `uvicorn aegis_command.api:app --app-dir src --host 0.0.0.0 --port $PORT`
- Env: `GROQ_API_KEY=...` (for live fusion), and the three module URLs (see note below).

### D. The 3 ML services → Render (Python web services)
Each: Build installs the package **and trains the model**, Start serves on `$PORT`. Example for
Fraud Shield:
- Build: `pip install -e ".[dev]" && python -m aegis_fraud_shield.cli train`
- Start: `uvicorn aegis_fraud_shield.api:app --app-dir src --host 0.0.0.0 --port $PORT`

Fraud Graph and Counterfeit Vision follow the same shape (`fraud-graph serve` reads `$PORT` via
`--port`; counterfeit needs `generate && train` in the build).

> **Wiring:** the backend currently hard-codes module URLs (`127.0.0.1:8001-8003` in
> `api.py:MODULES`). For cloud, make those env-configurable
> (`FRAUD_SHIELD_URL`, `COUNTERFEIT_URL`, `FRAUD_GRAPH_URL`) — a small change, not yet done.
> Same for the counterfeit `COUNTERFEIT_PUBLIC_URL` so note images resolve.

### Deploy order
ML services → backend → gateway → dashboard (each needs the previous one's URL).

---

## Option 3 — Docker Compose (one VM, all 6 services)

Cleaner than juggling 6 Render services, handles torch fine, ~$5–10/mo on a small VPS (or free
on your own machine). **Not yet scaffolded** — would need a `Dockerfile` per service + a
`docker-compose.yml` on a shared network. Ask if you want this built; it's the best path for a
portfolio-grade always-on deploy.

---

## Pre-demo checklist (local)
- [ ] `./run-all.ps1` — all 6 windows up, no errors
- [ ] http://localhost:3000 loads, header health pills green
- [ ] `command-centre/fusion/.env` has a working `GROQ_API_KEY` (or accept template narrator)
- [ ] Ran each wow-moment once to warm caches (see [`demo-script.md`](demo-script.md))
- [ ] Real ₹500 note + a fake handy for the camera
