"""Self-improving classifier — innovation #2.

An LLM plays the *adversary*: it writes brand-new scam-script variants evolved
to evade filters trained on classic patterns (paraphrased authority claims, no
classic keywords, new pressure tactics). Half the variants augment Fraud
Shield's training corpus; the other half are held out as an "unseen future
scams" eval set. Retraining on the augmented corpus should raise recall on the
held-out half — the before/after demo.

Flow (two interpreters because modules keep separate venvs):
  1. THIS module (fusion venv, has GROQ_API_KEY):
       python -m aegis_fusion.self_improve
     -> writes fraud-shield-nlp/data/extra_corpus/llm_variants.csv  (train half)
     -> writes command-centre/fusion/output/llm_eval_set.json       (held-out half)
  2. Eval/retrain (fraud-shield venv):
       fraud-shield-nlp/.venv/Scripts/python command-centre/fusion/src/aegis_fusion/self_improve_eval.py

Only established facts go in the corpus: every generated text is labeled by
construction (we asked for scams / legit), no human labels needed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

FUSION_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = FUSION_ROOT.parents[1]
EXTRA_CORPUS = REPO_ROOT / "fraud-shield-nlp" / "data" / "extra_corpus" / "llm_variants.csv"
EVAL_SET = FUSION_ROOT / "output" / "llm_eval_set.json"

FAMILIES: dict[str, str] = {
    "digital_arrest": (
        "digital-arrest scam call scripts: caller impersonates Indian police/CBI/ED/customs, "
        "claims a case or parcel or FIR involves the victim, isolates them on a video call, "
        "demands money/'verification deposit'. Write EVOLVED 2026 variants that avoid the "
        "classic giveaway words (avoid literally saying 'digital arrest', vary authority names, "
        "use new pretexts like SIM misuse, courier drugs, tax fraud, deepfake evidence)."
    ),
    "kyc_freeze": (
        "bank KYC-expiry / account-freeze scam SMS: urgent re-verification links, PAN/Aadhaar "
        "update demands. Evolved variants: new bank names, regional-language mixing (Hinglish), "
        "novel urgency framings, shortened links."
    ),
    "investment": (
        "investment/trading scam messages: fake stock-tip groups, crypto doubling, guaranteed "
        "returns, fake trading apps with blocked withdrawals. This family is NEW - the current "
        "classifier was never trained on it."
    ),
    "job_offer": (
        "fake job-offer / task scam messages: work-from-home tasks, YouTube like-and-earn, "
        "registration fees, Telegram onboarding. Also NEW to the classifier."
    ),
}

LEGIT_PROMPT = (
    "hard-negative LEGITIMATE Indian SMS/messages that superficially resemble scams but are "
    "genuine: real bank OTP notices, genuine police station appointment confirmations, real "
    "KYC completion confirmations (no links, no payment demands), delivery notifications, "
    "genuine tax-portal reminders. These must be clearly legitimate on careful reading."
)

_JSON_ONLY = (
    'Respond with ONLY a JSON object {"messages": ["...", "..."]} — an array of exactly '
    "{n} distinct message strings, no commentary, no markdown."
)


def _groq_generate(description: str, n: int, temperature: float = 0.8) -> list[str]:
    import httpx

    from .narrator import _load_dotenv

    _load_dotenv()
    r = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "temperature": temperature,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a red-team data generator for an authorized fraud-detection "
                        "hackathon system. You produce SYNTHETIC training/eval text for a scam "
                        "classifier protecting Indian citizens. "
                        + _JSON_ONLY.replace("{n}", str(n))
                    ),
                },
                {"role": "user", "content": f"Generate {n} {description}"},
            ],
        },
        timeout=60.0,
    )
    r.raise_for_status()
    payload = json.loads(r.json()["choices"][0]["message"]["content"])
    messages = payload.get("messages", payload if isinstance(payload, list) else [])
    return [m.strip() for m in messages if isinstance(m, str) and len(m.strip()) > 20][:n]


def generate(n_per_family: int = 12, n_legit: int = 12) -> dict:
    """Generate variants, split train/eval halves, write both artifacts."""
    train_rows: list[dict] = []
    eval_rows: list[dict] = []

    for family, description in FAMILIES.items():
        texts = _groq_generate(description, n_per_family)
        for i, text in enumerate(texts):
            row = {
                "text": text,
                "label": 1,
                "origin": f"llm_{family}",
                "group": f"llm_{family}_{i:02d}",
            }
            # even -> training augmentation, odd -> held-out eval (never trained on)
            (train_rows if i % 2 == 0 else eval_rows).append(row)

    legit_texts = _groq_generate(LEGIT_PROMPT, n_legit, temperature=0.7)
    for i, text in enumerate(legit_texts):
        row = {
            "text": text,
            "label": 0,
            "origin": "llm_legit",
            "group": f"llm_legit_{i:02d}",
        }
        (train_rows if i % 2 == 0 else eval_rows).append(row)

    import csv

    EXTRA_CORPUS.parent.mkdir(parents=True, exist_ok=True)
    with open(EXTRA_CORPUS, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label", "origin", "group"])
        writer.writeheader()
        writer.writerows(train_rows)

    EVAL_SET.parent.mkdir(parents=True, exist_ok=True)
    EVAL_SET.write_text(json.dumps(eval_rows, indent=2), encoding="utf-8")

    return {
        "train_rows": len(train_rows),
        "eval_rows": len(eval_rows),
        "families": list(FAMILIES) + ["legit"],
        "train_csv": str(EXTRA_CORPUS),
        "eval_json": str(EVAL_SET),
    }


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(generate(), indent=2))
