"""FastAPI service the command centre calls.

Endpoints:
    GET  /health             liveness probe
    GET  /fraud-graph        latest detection result (contract JSON); runs the
                             pipeline on first call if no cached output exists
    POST /detect             force a fresh detection run
    POST /demo/inject-ring   stage demo: add a fresh 6-account ring + re-detect
    POST /demo/score-custom  fraud console: score human-designed transactions
    POST /demo/reset         drop injected rings, back to the base dataset
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import OUTPUT_DIR
from .data import load
from .demo import build_custom_dataset, inject_demo_ring
from .pipeline import run_detection

_OUTPUT_FILE = OUTPUT_DIR / "fraud_graph.json"
_STATE_LOCK = Lock()
_CURRENT_DATASET = load("synthetic")
_CURRENT_OUTPUT = None


def _load_output() -> dict | None:
    if _OUTPUT_FILE.exists():
        return json.loads(_OUTPUT_FILE.read_text(encoding="utf-8"))
    return None


def _current_output() -> dict:
    global _CURRENT_OUTPUT
    with _STATE_LOCK:
        if _CURRENT_OUTPUT is not None:
            return json.loads(_CURRENT_OUTPUT.model_dump_json())
        cached = _load_output()
        if cached is not None:
            return cached

    output = run_detection(ds=_CURRENT_DATASET)
    with _STATE_LOCK:
        _CURRENT_OUTPUT = output
    return json.loads(output.model_dump_json())


def _set_current_output(payload) -> None:
    global _CURRENT_OUTPUT
    with _STATE_LOCK:
        _CURRENT_OUTPUT = payload


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Warm at startup: a cold first GET /fraud-graph used to run the whole
    # detect pipeline inside the request and blow the command centre's 30 s
    # timeout on stage. Always recompute from the clean base dataset so a
    # restart also wipes any rings injected during a previous rehearsal
    # (the output file on disk may still contain them).
    _set_current_output(run_detection(ds=_CURRENT_DATASET))
    yield


app = FastAPI(
    title="Aegis Fraud Graph",
    description="Fraud-ring detection over transaction networks (graph features + XGBoost).",
    version=__version__,
    lifespan=lifespan,
)

# The dashboard runs on another port during development; allow it.
app.add_middleware(
    CORSMiddleware,
    # Local-origin browsers only (command centre + demo UIs).
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "module": "fraud-graph", "version": __version__}


@app.get("/fraud-graph")
def fraud_graph() -> dict:
    """Latest contract-compliant fraud_graph payload."""
    return _current_output()


@app.post("/detect")
def detect() -> dict:
    """Re-run detection and return the fresh payload."""
    global _CURRENT_OUTPUT
    out = run_detection(ds=_CURRENT_DATASET)
    _set_current_output(out)
    return json.loads(out.model_dump_json())


@app.post("/demo/inject-ring")
def demo_inject_ring(body: dict | None = None) -> dict:
    """Inject a fresh ring and rerun detection immediately.

    Body (all optional): district, topology (cycle|chain|fan_in), and
    accounts — 3-10 custom member names for the name-the-criminals moment.
    """
    global _CURRENT_DATASET, _CURRENT_OUTPUT

    payload = body or {}
    district = str(payload.get("district") or "Jamtara")
    topology = payload.get("topology") or "cycle"
    if topology not in {"cycle", "chain", "fan_in"}:
        topology = "cycle"
    raw_names = payload.get("accounts")
    if raw_names is not None and not isinstance(raw_names, list):
        raise HTTPException(422, "'accounts' must be a list of names")

    with _STATE_LOCK:
        current_dataset = _CURRENT_DATASET

    try:
        injected = inject_demo_ring(
            current_dataset, district=district, topology=topology, account_names=raw_names
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    output = run_detection(ds=injected)

    with _STATE_LOCK:
        _CURRENT_DATASET = injected
        _CURRENT_OUTPUT = output

    return json.loads(output.model_dump_json())


@app.post("/demo/score-custom")
def demo_score_custom(body: dict | None = None) -> dict:
    """Fraud console: score transactions a human designed by hand.

    Body: transactions [{source, target, amount}] (1-40), district?, speed?
    ("minutes" fast / "days" slow), commit? (default true — a caught ring is
    kept on the live map; uncaught activity never pollutes state).
    """
    global _CURRENT_DATASET, _CURRENT_OUTPUT

    from .config import RingConfig
    from .export import build_output
    from .graph import compute_features
    from .model import load_model, score_all
    from .rings import detect_rings

    payload = body or {}
    txs = payload.get("transactions")
    if not isinstance(txs, list) or not 1 <= len(txs) <= 40:
        raise HTTPException(422, "provide 1-40 transactions")
    district = str(payload.get("district") or "Jamtara")
    speed = payload.get("speed") if payload.get("speed") in {"minutes", "days"} else "minutes"
    commit = bool(payload.get("commit", True))

    with _STATE_LOCK:
        base = _CURRENT_DATASET

    try:
        eval_ds, user_accounts = build_custom_dataset(base, txs, district=district, speed=speed)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    features = compute_features(eval_ds)
    clf = load_model()
    scores = score_all(clf, features)
    rings, accounts_df = detect_rings(eval_ds, scores, RingConfig())

    user_set = set(user_accounts)
    hit = next((r for r in rings if len(user_set & set(r.account_ids)) >= 3), None)

    committed = False
    if hit is not None and commit:
        output = build_output(eval_ds, rings, accounts_df, features)
        (OUTPUT_DIR / "fraud_graph.json").write_text(
            output.model_dump_json(indent=2), encoding="utf-8"
        )
        with _STATE_LOCK:
            _CURRENT_DATASET = eval_ds
            _CURRENT_OUTPUT = output
        committed = True

    return {
        "accounts": [
            {
                "account_id": a,
                "illicit_probability": round(float(scores.get(a, 0.0)), 4),
                "in_ring": hit is not None and a in set(hit.account_ids),
            }
            for a in user_accounts
        ],
        "ring": (
            {
                "ring_id": hit.ring_id,
                "label": hit.label,
                "size": hit.size,
                "risk_score": round(hit.risk_score, 4),
                "district": hit.district,
                "total_amount": hit.total_amount,
                "account_ids": hit.account_ids,
            }
            if hit
            else None
        ),
        "committed": committed,
        "rings_total": len(rings),
    }


@app.post("/demo/reset")
def demo_reset() -> dict:
    """Drop all injected rings: reload the base dataset and rerun detection."""
    global _CURRENT_DATASET, _CURRENT_OUTPUT

    base = load("synthetic")
    output = run_detection(ds=base)

    with _STATE_LOCK:
        _CURRENT_DATASET = base
        _CURRENT_OUTPUT = output

    return json.loads(output.model_dump_json())
