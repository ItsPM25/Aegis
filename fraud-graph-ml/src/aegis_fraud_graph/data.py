"""Dataset loaders.

Every loader returns the same shape (`Dataset`), so the rest of the pipeline
doesn't care where data came from. Swap synthetic -> Elliptic++ by changing one
CLI flag, not the code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import DATA_DIR, SynthConfig
from .synth import generate, save


@dataclass
class Dataset:
    """Normalized dataset the pipeline consumes.

    accounts:     account_id, district (nullable), is_illicit (nullable for unlabeled), ring_id (nullable)
    transactions: tx_id, source, target, amount, timestamp
    """

    accounts: pd.DataFrame
    transactions: pd.DataFrame
    name: str = "unnamed"


def load_synthetic(cfg: SynthConfig | None = None, cache: bool = True) -> Dataset:
    """Generate (or load cached) synthetic data with ground-truth rings."""
    cache_dir = DATA_DIR / "synthetic"
    if cache and (cache_dir / "accounts.csv").exists():
        return Dataset(
            accounts=pd.read_csv(cache_dir / "accounts.csv"),
            transactions=pd.read_csv(cache_dir / "transactions.csv"),
            name="synthetic(cached)",
        )
    result = generate(cfg)
    if cache:
        save(result, cache_dir)
    return Dataset(accounts=result.accounts, transactions=result.transactions, name="synthetic")


def load_elliptic(root: Path | None = None) -> Dataset:
    """Load the Elliptic / Elliptic++ dataset if present under data/elliptic/.

    Expected files (from the Elliptic++ release):
      - txs_features.csv / txs_classes.csv  (transactions-as-nodes variant), or
      - AddrAddr_edgelist.csv + wallets features (actor variant).

    We map the *actor/wallet* variant onto our account model when available;
    otherwise raise with instructions. Download requires Google Drive / Kaggle
    access — see PROJECT_PLAN.md postponed items.
    """
    root = root or (DATA_DIR / "elliptic")
    edge_file = root / "AddrAddr_edgelist.csv"
    cls_file = root / "wallets_classes.csv"
    if not edge_file.exists():
        raise FileNotFoundError(
            f"Elliptic++ files not found under {root}. "
            "Download AddrAddr_edgelist.csv and wallets_classes.csv from the "
            "Elliptic++ release (github.com/git-disl/EllipticPlusPlus) into that folder."
        )
    edges = pd.read_csv(edge_file)
    edges = edges.rename(columns={"input_address": "source", "output_address": "target"})
    edges["tx_id"] = [f"tx_{i:07d}" for i in range(len(edges))]
    # Elliptic++ edge list has no amounts/timestamps at the address level; fill neutrals.
    if "amount" not in edges:
        edges["amount"] = 1.0
    if "timestamp" not in edges:
        edges["timestamp"] = pd.NaT

    classes = pd.read_csv(cls_file).rename(columns={"address": "account_id", "class": "cls"})
    # Elliptic labels: 1 = illicit, 2 = licit, 3/unknown = unlabeled.
    classes["is_illicit"] = classes["cls"].map({1: True, 2: False}).astype("boolean")
    accounts = classes[["account_id", "is_illicit"]].copy()
    accounts["district"] = None
    accounts["ring_id"] = None

    return Dataset(
        accounts=accounts,
        transactions=edges[["tx_id", "source", "target", "amount", "timestamp"]],
        name="elliptic++",
    )


LOADERS = {
    "synthetic": load_synthetic,
    "elliptic": load_elliptic,
}


def load(source: str = "synthetic") -> Dataset:
    if source not in LOADERS:
        raise ValueError(f"Unknown source '{source}'. Options: {sorted(LOADERS)}")
    return LOADERS[source]()
