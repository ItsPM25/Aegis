"""Demo-only helpers for injecting fresh fraud rings into the synthetic graph."""

from __future__ import annotations

import random
import zlib
from datetime import datetime, timedelta, timezone
from typing import Literal

import pandas as pd

from .data import Dataset

DemoTopology = Literal["cycle", "chain", "fan_in"]

_DEMO_DISTRICTS = (
    "Jamtara",
    "Deoghar",
    "Alwar",
    "Bharatpur",
    "Nuh",
    "Chennai Central",
    "Mumbai South",
    "Delhi East",
)


def clean_account_names(raw: list[str] | None) -> list[str]:
    """Trim, dedupe (case-insensitive), and cap user-supplied account names.

    Returns [] when nothing usable was given; raises ValueError when 1-2 names
    survive cleaning — a ring needs at least 3 members to be detectable
    (RingConfig.min_ring_size), and silently padding would surprise the demo.
    """
    if not raw:
        return []
    seen: set[str] = set()
    names: list[str] = []
    for item in raw:
        name = str(item).strip()[:24]
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        names.append(name)
    if 0 < len(names) < 3:
        raise ValueError("need at least 3 account names to form a detectable ring")
    return names[:10]


def inject_demo_ring(
    ds: Dataset,
    district: str = "Jamtara",
    topology: DemoTopology = "cycle",
    size: int = 6,
    account_names: list[str] | None = None,
) -> Dataset:
    """Return a copy of *ds* with a fresh illicit ring appended.

    The injected cluster is intentionally high-signal: six new accounts, dense
    transfers, short time gaps, and round-ish values so the graph detector
    catches it on the next pass. Pass *account_names* (3-10 strings) to name
    the ring members yourself — the stage moment where a judge's name shows up
    inside a caught fraud ring.
    """

    district = district if district in _DEMO_DISTRICTS else "Jamtara"
    accounts = ds.accounts.copy(deep=True)
    transactions = ds.transactions.copy(deep=True)

    names = clean_account_names(account_names)
    if names:
        size = len(names)

    next_account = _next_numeric_id(accounts["account_id"], prefix="acc_")
    next_tx = _next_numeric_id(transactions["tx_id"], prefix="tx_")
    next_ring_index = int(accounts["ring_id"].dropna().nunique()) + 1 if "ring_id" in accounts else 1
    ring_id = f"ring_{next_ring_index:02d}"

    existing_ids = set(accounts["account_id"].astype(str))

    def unique_id(base: str) -> str:
        candidate, n = base, 2
        while candidate in existing_ids:
            candidate = f"{base}_{n}"
            n += 1
        existing_ids.add(candidate)
        return candidate

    members: list[str] = []
    for i in range(size):
        if names:
            account_id = unique_id(names[i])
        else:
            account_id = unique_id(f"acc_{next_account:05d}")
            next_account += 1
        members.append(account_id)
        accounts.loc[len(accounts)] = {
            "account_id": account_id,
            "district": district,
            "is_illicit": True,
            "ring_id": ring_id,
        }

    base_ts = datetime.now(timezone.utc).replace(microsecond=0, second=0)
    amount = 420_000.0

    def add_tx(source: str, target: str, value: float, offset_minutes: int) -> None:
        nonlocal next_tx
        transactions.loc[len(transactions)] = {
            "tx_id": f"tx_{next_tx:06d}",
            "source": source,
            "target": target,
            "amount": round(value, 2),
            "timestamp": (base_ts + timedelta(minutes=offset_minutes)).isoformat(),
        }
        next_tx += 1

    if topology == "fan_in":
        collector, *mules = members
        for i, source in enumerate(members[1:], start=1):
            add_tx(source, collector, amount * (0.98 - i * 0.01), i * 7)
        for i, mule in enumerate(mules, start=1):
            add_tx(collector, mule, amount * (0.76 - i * 0.02), 45 + i * 6)
    elif topology == "chain":
        for round_idx in range(3):
            current_amount = amount * (0.99 - round_idx * 0.02)
            start_minute = round_idx * 35
            for i in range(size - 1):
                add_tx(
                    members[i],
                    members[i + 1],
                    current_amount * (0.97**i),
                    start_minute + i * 5,
                )
    else:  # cycle
        for round_idx in range(3):
            current_amount = amount * (1.0 - round_idx * 0.02)
            start_minute = round_idx * 30
            for i in range(size):
                add_tx(
                    members[i],
                    members[(i + 1) % size],
                    current_amount * (0.98**i),
                    start_minute + i * 4,
                )

    return Dataset(
        accounts=accounts.reset_index(drop=True),
        transactions=transactions.reset_index(drop=True),
        name=f"{ds.name}+demo-ring",
    )


def build_custom_dataset(
    ds: Dataset,
    transactions: list[dict],
    district: str = "Jamtara",
    speed: str = "minutes",
) -> tuple[Dataset, list[str]]:
    """Append user-authored accounts + transactions to a copy of *ds*.

    This powers the fraud console: the human designs the money movement
    entirely (who pays whom, how much, fast or slow) and the engine scores
    whatever they built — nothing about the pattern is machine-generated.
    Returns (dataset, resolved user account ids).
    """
    district = district if district in _DEMO_DISTRICTS else "Jamtara"
    accounts = ds.accounts.copy(deep=True)
    txdf = ds.transactions.copy(deep=True)
    existing = set(accounts["account_id"].astype(str))

    parsed: list[tuple[str, str, float]] = []
    for i, t in enumerate(transactions):
        try:
            src = str(t["source"]).strip()[:24]
            dst = str(t["target"]).strip()[:24]
            amt = float(t["amount"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"transaction {i + 1} needs source, target and a numeric amount")
        if not src or not dst or src.lower() == dst.lower():
            raise ValueError(f"transaction {i + 1}: source and target must differ")
        if not amt > 0:
            raise ValueError(f"transaction {i + 1}: amount must be positive")
        parsed.append((src, dst, amt))

    name_map: dict[str, str] = {}
    # Ordinary accounts to serve as background counterparties (not in any ring).
    ring_col = accounts["ring_id"] if "ring_id" in accounts else pd.Series(dtype=object)
    peers = accounts.loc[ring_col.isna(), "account_id"].astype(str).tolist() or list(existing)

    next_tx = _next_numeric_id(txdf["tx_id"], prefix="tx_")
    base_ts = datetime.now(timezone.utc).replace(microsecond=0, second=0)

    def add_background(candidate: str) -> None:
        """A brand-new account whose ONLY activity is the user's 2-3 transfers
        looks like a mule to a model trained on accounts with full lives (the
        blank-slate false positive — verified live: 3 innocent payments scored
        0.999). So every console account gets a small organic history — slow,
        small, non-round transactions with random ordinary peers. Deterministic
        per name, and identical whether the user then builds fraud or rent
        payments, so it cannot manufacture fraud signal."""
        nonlocal next_tx
        rng = random.Random(zlib.crc32(candidate.encode("utf-8")))
        # 3-4 txs: enough life to kill the blank-slate false positive, little
        # enough that a designed laundering pattern still dominates the account
        for _ in range(rng.randint(3, 4)):
            peer = rng.choice(peers)
            amount = round(rng.lognormvariate(6.8, 0.8), 2)  # median ~900, organic
            ts = base_ts - timedelta(days=rng.uniform(1, 25), hours=rng.uniform(0, 20))
            src, dst = (candidate, peer) if rng.random() < 0.5 else (peer, candidate)
            txdf.loc[len(txdf)] = {
                "tx_id": f"tx_{next_tx:06d}",
                "source": src,
                "target": dst,
                "amount": amount,
                "timestamp": ts.isoformat(),
            }
            next_tx += 1

    def resolve(name: str) -> str:
        if name not in name_map:
            candidate, n = name, 2
            while candidate in existing:
                candidate = f"{name}_{n}"
                n += 1
            existing.add(candidate)
            name_map[name] = candidate
            accounts.loc[len(accounts)] = {
                "account_id": candidate,
                "district": district,
                "is_illicit": False,  # ground-truth label unknown; scoring ignores it
                "ring_id": None,
            }
            add_background(candidate)
        return name_map[name]
    # tempo is the one lever the user picks explicitly: laundering moves in
    # minutes, normal life moves in days — the engine must see the difference
    gap = timedelta(minutes=6) if speed == "minutes" else timedelta(days=1, hours=9)
    for i, (src, dst, amt) in enumerate(parsed):
        txdf.loc[len(txdf)] = {
            "tx_id": f"tx_{next_tx:06d}",
            "source": resolve(src),
            "target": resolve(dst),
            "amount": round(amt, 2),
            "timestamp": (base_ts + gap * i).isoformat(),
        }
        next_tx += 1

    return (
        Dataset(
            accounts=accounts.reset_index(drop=True),
            transactions=txdf.reset_index(drop=True),
            name=f"{ds.name}+custom",
        ),
        list(name_map.values()),
    )


def _next_numeric_id(values: pd.Series, prefix: str) -> int:
    extracted = values.astype(str).str.extract(rf"^{prefix}(\d+)$")[0].dropna()
    if extracted.empty:
        return 0
    return int(extracted.astype(int).max()) + 1