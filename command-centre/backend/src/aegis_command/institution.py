"""Financial-institution surface — the B2B integration the challenge names.

The challenge statement names three stakeholders: law enforcement, **financial
institutions**, and citizens. The citizen and law-enforcement surfaces already
exist (the dashboard, case files, alerts). This module adds the institution one:
the same Counterfeit Vision and Fraud Graph models, re-framed as machine-to-
machine calls a bank teller terminal / counting machine or an AML screening
system would make — behind an API key, with terse pass/fail responses and no
citizen UI chrome.

Auth is a static header check (`X-API-Key`) — enough to demonstrate a gated B2B
surface. Set `AEGIS_INSTITUTION_API_KEY` to override the demo key.
"""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Header, HTTPException

router = APIRouter(prefix="/institution", tags=["institution"])

COUNTERFEIT_VISION = "http://127.0.0.1:8002"
DEMO_API_KEY = os.environ.get("AEGIS_INSTITUTION_API_KEY", "aegis-demo-institution-key")


def _require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Gate the B2B surface. A real deployment would use per-partner keys +
    mTLS; a static header is enough to show the surface is not public."""
    if x_api_key != DEMO_API_KEY:
        raise HTTPException(401, "missing or invalid X-API-Key")


def _band(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


@router.post("/verify-note")
async def verify_note(body: dict, x_api_key: str | None = Header(default=None)) -> dict:
    """Teller / counting-machine note check. Same Counterfeit Vision model as the
    citizen path, but a terse pass/fail response suitable for a POS or bank
    counter — no dashboard ingest, no map, no UI chrome.

    Body: { "image_b64": "<base64 note image>" }
    """
    _require_api_key(x_api_key)
    if not body.get("image_b64"):
        raise HTTPException(422, "body must contain 'image_b64'")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{COUNTERFEIT_VISION}/analyze_b64", json={"image_b64": body["image_b64"]})
            r.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"counterfeit-vision service unreachable: {exc}") from exc

    scan = r.json()
    verdict = scan.get("verdict", "uncertain")
    confidence = scan.get("confidence", 0.0)
    return {
        "pass": verdict == "genuine",
        "verdict": verdict,
        "denomination": scan.get("denomination", "unknown"),
        "confidence": confidence,
        "missing_features": scan.get("missing_features", []),
        "recommendation": {
            "genuine": "Accept note.",
            "fake": "Reject and retain note; log serial; report to currency chest.",
            "uncertain": "Refer for manual inspection under UV.",
        }.get(verdict, "Refer for manual inspection."),
        "engine": "counterfeit-vision",
        "channel": "institution.teller",
        "disclaimer": (
            "Automated screening decision-support for bank/POS use — not a legal "
            "determination of forgery. Retain and escalate per RBI currency-chest "
            "procedure."
        ),
    }


@router.post("/screen-account")
def screen_account(body: dict, x_api_key: str | None = Header(default=None)) -> dict:
    """AML account screening. Returns the Fraud Graph risk for one account,
    framed as a pre-onboarding / pre-transaction check a bank's AML system runs.

    Body: { "account_id": "<id>" }
    """
    _require_api_key(x_api_key)
    from .store import store

    account_id = (body or {}).get("account_id", "").strip()
    if not account_id:
        raise HTTPException(422, "body must include an 'account_id'")

    _, _, fraud_graph = store.snapshot()
    graph = fraud_graph or {}
    accounts = {a["account_id"]: a for a in graph.get("accounts", [])}
    rings = {r["ring_id"]: r for r in graph.get("rings", [])}

    hit = accounts.get(account_id)
    if hit is None:
        # Not in the flagged graph — an honest "clear" (no adverse signal), not a
        # guarantee of legitimacy.
        return {
            "account_id": account_id,
            "known": False,
            "risk_score": 0.0,
            "risk_band": "low",
            "in_ring": None,
            "decision": "clear",
            "recommendation": "No adverse signal in the fraud graph. Proceed with standard KYC.",
            "engine": "fraud-graph",
            "channel": "institution.aml",
            "disclaimer": (
                "Absence from the flagged graph is not proof of legitimacy — it "
                "only means no fraud-network link is currently known."
            ),
        }

    score = float(hit.get("illicit_probability", 0.0))
    ring_id = hit.get("ring_id")
    ring = rings.get(ring_id) if ring_id else None
    band = _band(score)
    decision = "block" if band == "high" else ("review" if band == "medium" else "monitor")
    recommendation = {
        "block": "High illicit probability — hold transactions and file an STR (Suspicious Transaction Report).",
        "review": "Elevated risk — apply Enhanced Due Diligence before further transactions.",
        "monitor": "Low but non-zero linkage — flag for periodic monitoring.",
    }[decision]

    return {
        "account_id": account_id,
        "known": True,
        "risk_score": score,
        "risk_band": band,
        "in_ring": ring_id,
        "ring": {
            "ring_id": ring_id,
            "risk_score": ring.get("risk_score"),
            "size": ring.get("size"),
            "label": ring.get("label"),
            "district": ring.get("district"),
        }
        if ring
        else None,
        "features": hit.get("features"),
        "decision": decision,
        "recommendation": recommendation,
        "engine": "fraud-graph",
        "channel": "institution.aml",
        "disclaimer": (
            "Risk score is a model output for AML triage, not a determination of "
            "guilt. Combine with the bank's own KYC and transaction monitoring "
            "before acting."
        ),
    }


@router.get("/health")
def institution_health(x_api_key: str | None = Header(default=None)) -> dict:
    """Cheap authenticated ping so a partner can verify their key + connectivity."""
    _require_api_key(x_api_key)
    return {"status": "ok", "surface": "institution", "endpoints": ["/institution/verify-note", "/institution/screen-account"]}
