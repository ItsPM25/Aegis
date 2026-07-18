"""Serial-number layer: flag nonsense serials, then check real-looking ones
against a sighting registry.

Two independent signals, both deterministic:

1. **Format** — Mahatma Gandhi (New) Series serials are `<digit><2 letters>`
   + 6 digits (e.g. `4CB 123456`); RBI avoids I and O in prefixes (they read
   as 1/0). A serial that can't exist is a prop/photocopy tell.
   All-identical or straight-run digit blocks (000000, 123456) are the classic
   movie-money serials, but genuine "fancy number" notes do exist — so they
   mark `suspicious` (blocks a genuine certification) rather than convicting.

2. **Registry** — every genuine note's serial is unique. The same serial
   surfacing on two different scans means a counterfeit printing run (fakes
   copy one real serial onto every note of a plate). The registry stores every
   sighting; a repeat elevates to `duplicate`. The one innocent cause — the
   same physical note rescanned — is exactly why `duplicate` also caps at
   manual review instead of auto-convicting.

Like the triage layer: this can make the system MORE cautious (cap a genuine
verdict at `uncertain`), never certify anything.

Serial capture is manual/UI input for now (the vision-LLM review can read it
from the photo when a key is present); the validation + dedup logic is live
either way.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
REGISTRY_FILE = DATA_DIR / "serial_registry.json"

_FORMAT = re.compile(r"^\d[A-Z]{2}\d{6}$")
_FORBIDDEN_PREFIX_LETTERS = set("IO")

# Precedence when several signals fire at once.
STATUS_ORDER = ["nonsense", "duplicate", "suspicious", "valid"]


def normalize(serial: str) -> str:
    return re.sub(r"[\s-]", "", serial or "").upper()


def validate(serial: str) -> tuple[str, str]:
    """(status, detail) from format alone: valid | suspicious | nonsense."""
    s = normalize(serial)
    if not s:
        return "nonsense", "empty serial"
    if not _FORMAT.match(s):
        return "nonsense", f"'{s}' does not match the RBI pattern digit + 2 letters + 6 digits"
    if _FORBIDDEN_PREFIX_LETTERS & set(s[1:3]):
        return "nonsense", f"prefix '{s[:3]}' uses I/O — never issued by RBI"
    digits = s[3:]
    if len(set(digits)) == 1:
        return "suspicious", f"repeated-digit block {digits} — classic prop serial (genuine fancy numbers exist: manual check)"
    ascending = "0123456789" * 2
    if digits in ascending or digits in ascending[::-1]:
        return "suspicious", f"sequential block {digits} — classic prop serial (genuine fancy numbers exist: manual check)"
    return "valid", f"'{s}' is a well-formed RBI serial"


class SerialRegistry:
    """JSON-file sighting store: serial -> [{event_id, timestamp, district}]."""

    def __init__(self, path: Path = REGISTRY_FILE) -> None:
        self.path = path
        self._lock = Lock()

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def check_and_register(
        self, serial: str, event_id: str, district: str | None = None
    ) -> list[dict]:
        """Record this sighting; return PRIOR sightings of the same serial."""
        s = normalize(serial)
        with self._lock:
            data = self._load()
            prior = list(data.get(s, []))
            data.setdefault(s, []).append(
                {
                    "event_id": event_id,
                    "timestamp": datetime.now(timezone.utc)
                    .isoformat(timespec="seconds")
                    .replace("+00:00", "Z"),
                    "district": district,
                }
            )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, indent=1), encoding="utf-8")
        return prior


def inspect_serial(
    serial: str,
    event_id: str,
    district: str | None = None,
    registry: SerialRegistry | None = None,
) -> dict:
    """Contract-shaped `serial` block. Registry is consulted (and the sighting
    recorded) only for serials that could exist — nonsense ones are pure props."""
    status, detail = validate(serial)
    prior: list[dict] = []
    if status != "nonsense":
        registry = registry or SerialRegistry()
        prior = registry.check_and_register(serial, event_id, district)
        if prior:
            status = "duplicate"
            where = ", ".join(
                f"{p['event_id']}{' in ' + p['district'] if p.get('district') else ''}"
                for p in prior[-3:]
            )
            detail = (
                f"serial already sighted {len(prior)}x ({where}) — genuine serials are "
                "unique; a repeat means a counterfeit printing run, or a rescan of the "
                "same physical note. Manual check required."
            )
    return {
        "value": normalize(serial),
        "status": status,
        "detail": detail,
        "prior_sightings": prior,
    }


def cap_verdict_for_serial(payload: dict) -> None:
    """A note is never CERTIFIED genuine while its serial is nonsense,
    suspicious, or duplicated — mirrors the feature-check rule. Mutates the
    payload; fake/uncertain verdicts are untouched (never acquits)."""
    serial = payload.get("serial")
    if serial and serial["status"] != "valid" and payload["verdict"] == "genuine":
        payload["verdict"] = "uncertain"
        # Confidence that a manual check is warranted, driven by the serial
        # signal itself rather than the model's (overruled) certainty.
        payload["confidence"] = 0.75
