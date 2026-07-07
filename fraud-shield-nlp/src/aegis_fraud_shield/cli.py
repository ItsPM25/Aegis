"""Fraud Shield command line.

    python -m aegis_fraud_shield.cli train
        Download data (first run), train, save model + held-out report.

    python -m aegis_fraud_shield.cli analyze "<text>" [--source sms] [--out out.json]
        Analyse one message with the saved model; print contract JSON.

    python -m aegis_fraud_shield.cli demo
        Run the bundled demo scripts through the model (quick sanity check).
"""

from __future__ import annotations

import argparse
import json
import sys

from .analyze import analyze, validate_payload
from .config import ModelConfig
from .model import MODEL_FILE, REPORT_FILE, ScamClassifier, save_report, train

DEMO_SCRIPTS = [
    ("call_transcript",
     "This is Inspector Sharma from CBI. An FIR has been registered against your Aadhaar for "
     "money laundering. Stay on this video call and do not disconnect. Transfer the "
     "verification amount in USDT immediately or a warrant will be issued."),
    ("sms",
     "Dear customer your SBI account KYC has expired. Account will be blocked within 24 hours. "
     "Update immediately at bit.ly/kyc-upd8 to avoid suspension."),
    ("sms",
     "482913 is your OTP for HDFC net banking login. Valid for 10 minutes. Do not share this "
     "OTP with anyone."),
    ("whatsapp",
     "Hey, are we still meeting for lunch tomorrow at 1pm? Let me know if you want to move it."),
]


def cmd_train(_: argparse.Namespace) -> int:
    from .data import load_training_frame

    print("Loading data (downloads UCI SMS Spam Collection on first run)...")
    frame = load_training_frame()
    print(f"Training on {len(frame)} messages ({int(frame['label'].sum())} scam/spam)...")
    model, report = train(frame, ModelConfig())
    model.save()
    save_report(report)
    print(f"Model  -> {MODEL_FILE}")
    print(f"Report -> {REPORT_FILE}")
    print(json.dumps(report.to_dict(), indent=2))
    return 0


def _load_model() -> ScamClassifier:
    if not MODEL_FILE.exists():
        sys.exit("No trained model found. Run: python -m aegis_fraud_shield.cli train")
    return ScamClassifier.load()


def cmd_analyze(args: argparse.Namespace) -> int:
    model = _load_model()
    payload = analyze(args.text, model, source=args.source)
    validate_payload(payload)
    output = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Wrote {args.out}")
    print(output)
    return 0


def cmd_demo(_: argparse.Namespace) -> int:
    model = _load_model()
    for source, text in DEMO_SCRIPTS:
        payload = analyze(text, model, source=source)
        validate_payload(payload)
        print(f"[{payload['verdict']:>10}] risk={payload['risk_score']:.2f} "
              f"type={payload['scam_type']:<14} {text[:60]}...")
        print(f"             {payload['explanation']}\n")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="fraud-shield", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("train", help="train and save the classifier").set_defaults(fn=cmd_train)

    p_analyze = sub.add_parser("analyze", help="analyse one message")
    p_analyze.add_argument("text")
    p_analyze.add_argument("--source", default="manual_demo",
                           choices=["sms", "call_transcript", "whatsapp", "email", "manual_demo"])
    p_analyze.add_argument("--out", default=None, help="also write the JSON to this file")
    p_analyze.set_defaults(fn=cmd_analyze)

    sub.add_parser("demo", help="run bundled demo scripts").set_defaults(fn=cmd_demo)

    args = parser.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
