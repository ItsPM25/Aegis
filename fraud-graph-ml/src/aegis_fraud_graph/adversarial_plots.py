"""Arms-race visualization — the two-line plot that IS the deliverable.

Red line:  criminal escape rate over generations (climbing = criminal adapts)
Blue line: detector recall over generations (climbing = cop adapts)
Both climbing = arms race visible.

Output: saved to output/arms_race.png.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_MPL_AVAILABLE = False
try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt
    _MPL_AVAILABLE = True
except ImportError:
    plt = None  # type: ignore[assignment]


def plot_arms_race(
    history: pd.DataFrame,
    output_path: str | Path | None = None,
    title: str = "Criminal vs Cop — Adversarial Arms Race",
) -> Path:
    """Generate the two-line arms-race plot.

    Args:
        history: DataFrame from adversarial.run_arms_race() with columns:
                 [generation, best_escape_rate, detector_recall, retrained]
        output_path: where to save the plot (default: output/arms_race.png)
        title: plot title

    Returns:
        Path to the saved plot.
    """
    if not _MPL_AVAILABLE:
        raise ImportError("Plotting requires matplotlib. Install with: pip install matplotlib")

    from .config import OUTPUT_DIR

    output_path = Path(output_path or (OUTPUT_DIR / "arms_race.png"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax1 = plt.subplots(figsize=(12, 6))

    gens = history["generation"].values

    # ── Criminal escape rate (red) ──
    ax1.plot(
        gens, history["best_escape_rate"].values,
        color="#e74c3c", linewidth=2.5, label="Criminal Escape Rate (best)",
        marker="o", markersize=4, alpha=0.9,
    )
    ax1.plot(
        gens, history["mean_escape_rate"].values,
        color="#e74c3c", linewidth=1.0, linestyle="--",
        label="Criminal Escape Rate (mean)", alpha=0.5,
    )

    # ── Detector recall (blue) ──
    ax1.plot(
        gens, history["detector_recall"].values,
        color="#3498db", linewidth=2.5, label="Detector Recall",
        marker="s", markersize=4, alpha=0.9,
    )

    # ── Retrain markers ──
    retrained = history[history["retrained"] == True]  # noqa: E712
    if not retrained.empty:
        ax1.scatter(
            retrained["generation"].values,
            retrained["detector_recall"].values,
            color="#2ecc71", s=100, zorder=5, marker="^",
            label="Detector Retrained", edgecolors="black", linewidth=1,
        )

    # ── Styling ──
    ax1.set_xlabel("Generation", fontsize=13, fontweight="bold")
    ax1.set_ylabel("Rate", fontsize=13, fontweight="bold")
    ax1.set_title(title, fontsize=15, fontweight="bold", pad=15)
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_xlim(gens[0] - 0.5, gens[-1] + 0.5)
    ax1.legend(loc="lower right", fontsize=10, framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle="--")

    # Add fitness on secondary axis
    ax2 = ax1.twinx()
    ax2.fill_between(
        gens, 0, history["best_fitness"].values,
        alpha=0.1, color="#9b59b6", label="Best Fitness",
    )
    ax2.set_ylabel("Fitness (money × evasion)", fontsize=11, color="#9b59b6")
    ax2.tick_params(axis="y", labelcolor="#9b59b6")
    ax2.set_ylim(0, max(history["best_fitness"].max() * 1.2, 0.1))

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    logger.info("Arms race plot saved to %s", output_path)
    return output_path


def plot_strategy_evolution(
    history: pd.DataFrame,
    output_path: str | Path | None = None,
) -> Path:
    """Plot how the best criminal strategy genes evolve over generations.

    Shows which evasion tactics the criminal discovers over time.
    """
    if not _MPL_AVAILABLE:
        raise ImportError("Plotting requires matplotlib.")

    from .config import OUTPUT_DIR

    output_path = Path(output_path or (OUTPUT_DIR / "strategy_evolution.png"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # If strategy columns aren't in history, skip
    strategy_cols = [
        "delay_mean", "delay_variance", "amount_type",
        "split_count", "hop_depth", "mule_reuse_rate", "threshold_proximity",
    ]
    available = [c for c in strategy_cols if c in history.columns]
    if not available:
        logger.warning("No strategy columns in history; skipping strategy evolution plot.")
        return output_path

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c", "#e67e22"]

    for i, col in enumerate(available):
        ax.plot(
            history["generation"].values,
            history[col].values,
            color=colors[i % len(colors)],
            linewidth=1.5,
            label=col.replace("_", " ").title(),
            alpha=0.8,
        )

    ax.set_xlabel("Generation", fontsize=12)
    ax.set_ylabel("Gene Value [0, 1]", fontsize=12)
    ax.set_title("Criminal Strategy Evolution", fontsize=14, fontweight="bold")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="center right", fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    logger.info("Strategy evolution plot saved to %s", output_path)
    return output_path
