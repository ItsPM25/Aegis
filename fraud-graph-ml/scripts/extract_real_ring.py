"""Extract one real illicit ring from Elliptic++ for the dashboard's ring viewer.

Finds a small connected cluster of confirmed-illicit Bitcoin wallets (class 1)
in the real AddrAddr edge list and exports its topology as JSON the frontend
can draw. No synthesis — these are real criminals from the real blockchain.

Run (from fraud-graph-ml/):  .venv/Scripts/python scripts/extract_real_ring.py
Writes: ../command-centre/frontend/public/real_ring.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import networkx as nx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis_fraud_graph.config import DATA_DIR  # noqa: E402
from aegis_fraud_graph.rings import _topology_label  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "command-centre" / "frontend" / "public" / "real_ring.json"


def main() -> None:
    root = DATA_DIR / "elliptic"
    classes = pd.read_csv(root / "wallets_classes.csv")
    illicit = set(classes.loc[classes["class"] == 1, "address"])
    print(f"illicit wallets: {len(illicit):,}")

    edges = pd.read_csv(root / "AddrAddr_edgelist.csv")
    ii = edges[edges["input_address"].isin(illicit) & edges["output_address"].isin(illicit)]
    ii = ii[ii["input_address"] != ii["output_address"]]  # self-loops hide topology
    print(f"illicit-to-illicit edges: {len(ii):,}")

    g = nx.DiGraph()
    g.add_edges_from(zip(ii["input_address"], ii["output_address"]))
    und = g.to_undirected()

    # small, dense components read best on screen; prefer one containing a cycle
    best = None
    for comp in nx.connected_components(und):
        if not 5 <= len(comp) <= 10:
            continue
        sub = g.subgraph(comp)
        density = sub.number_of_edges() / len(comp)
        try:
            has_cycle = len(nx.find_cycle(sub)) >= 3
        except nx.NetworkXNoCycle:
            has_cycle = False
        score = density + (2 if has_cycle else 0)
        if best is None or score > best[0]:
            best = (score, comp)
    if best is None:
        raise SystemExit("no suitable 5-10 wallet component found")

    comp = best[1]
    sub = g.subgraph(comp)
    label = _topology_label(nx.DiGraph(sub))
    print(f"picked component: {len(comp)} wallets, {sub.number_of_edges()} edges, label={label}")

    payload = {
        "source": "Elliptic++ — real Bitcoin blockchain, confirmed-illicit wallets",
        "label": label,
        "size": len(comp),
        "nodes": [{"id": n} for n in sorted(comp)],
        "edges": [{"source": u, "target": v} for u, v in sub.edges()],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
