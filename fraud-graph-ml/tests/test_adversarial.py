"""Tests for Criminal Trains the Cop — adversarial arms race."""

from __future__ import annotations

import pytest
import numpy as np
import pandas as pd

from aegis_fraud_graph.data import load_synthetic
from aegis_fraud_graph.config import SynthConfig


@pytest.fixture(scope="module")
def small_dataset():
    cfg = SynthConfig(n_legit_accounts=200, n_rings=3, ring_size_min=3,
                      ring_size_max=5, n_background_tx=500, seed=99)
    return load_synthetic(cfg, cache=False)


class TestCriminalStrategy:
    def test_vector_roundtrip(self):
        from aegis_fraud_graph.adversarial import CriminalStrategy
        s = CriminalStrategy(delay_mean=0.5, split_count=0.7)
        v = s.to_vector()
        assert len(v) == 7
        s2 = CriminalStrategy.from_vector(v)
        assert abs(s2.delay_mean - 0.5) < 1e-6
        assert abs(s2.split_count - 0.7) < 1e-6

    def test_clamping(self):
        from aegis_fraud_graph.adversarial import CriminalStrategy
        s = CriminalStrategy.from_vector([-0.5, 1.5, 0.3, 0.4, 0.5, 0.6, 0.7])
        assert s.delay_mean == 0.0
        assert s.delay_variance == 1.0

    def test_strategy_maps(self):
        from aegis_fraud_graph.adversarial import CriminalStrategy
        s = CriminalStrategy(delay_mean=0.0, split_count=0.0, hop_depth=0.0)
        assert s._map_delay_minutes() == 5.0
        assert s._map_splits() == 2
        assert s._map_hops() == 2

        s2 = CriminalStrategy(delay_mean=1.0, split_count=1.0, hop_depth=1.0)
        assert s2._map_delay_minutes() == 2880.0
        assert s2._map_splits() == 8
        assert s2._map_hops() == 8


class TestInjection:
    def test_inject_ring_adds_accounts(self, small_dataset):
        from aegis_fraud_graph.adversarial import CriminalStrategy, inject_adversarial_ring
        strategy = CriminalStrategy()
        ds_aug, members, money = inject_adversarial_ring(small_dataset, strategy, seed=42)
        assert len(ds_aug.accounts) > len(small_dataset.accounts)
        assert len(members) > 0
        assert money > 0

    def test_inject_ring_adds_transactions(self, small_dataset):
        from aegis_fraud_graph.adversarial import CriminalStrategy, inject_adversarial_ring
        strategy = CriminalStrategy()
        ds_aug, _, _ = inject_adversarial_ring(small_dataset, strategy, seed=42)
        assert len(ds_aug.transactions) > len(small_dataset.transactions)

    def test_members_marked_illicit(self, small_dataset):
        from aegis_fraud_graph.adversarial import CriminalStrategy, inject_adversarial_ring
        strategy = CriminalStrategy()
        ds_aug, members, _ = inject_adversarial_ring(small_dataset, strategy, seed=42)
        for m in members:
            row = ds_aug.accounts[ds_aug.accounts["account_id"] == m]
            assert row["is_illicit"].iloc[0] == True  # noqa


class TestFitnessEvaluation:
    def test_evaluate_returns_valid(self, small_dataset):
        from aegis_fraud_graph.adversarial import CriminalStrategy, evaluate_strategy

        strategy = CriminalStrategy()

        def dummy_detector(ds, suspects):
            # Detect half
            return suspects[:len(suspects)//2]

        fitness, money, detection = evaluate_strategy(
            strategy, small_dataset, dummy_detector, seed=42,
        )
        assert fitness >= 0
        assert money > 0
        assert 0.0 <= detection <= 1.0


class TestEvolutionaryLoop:
    @pytest.mark.skipif(
        not pytest.importorskip("deap", reason="DEAP not installed"),
        reason="DEAP required",
    )
    def test_arms_race_runs(self, small_dataset):
        """Smoke test: 3 generations, tiny population."""
        from aegis_fraud_graph.adversarial import run_arms_race

        history = run_arms_race(
            n_generations=3,
            population_size=6,
            top_k=2,
            retrain_every=2,
            source="synthetic",
            seed=42,
        )
        assert len(history) == 3
        assert "best_fitness" in history.columns
        assert "detector_recall" in history.columns
        assert "best_escape_rate" in history.columns


class TestPlots:
    @pytest.mark.skipif(
        not pytest.importorskip("matplotlib", reason="matplotlib not installed"),
        reason="matplotlib required",
    )
    def test_plot_generates_file(self, tmp_path):
        from aegis_fraud_graph.adversarial_plots import plot_arms_race

        history = pd.DataFrame({
            "generation": [0, 1, 2],
            "best_fitness": [0.1, 0.3, 0.5],
            "mean_fitness": [0.05, 0.15, 0.3],
            "best_escape_rate": [0.2, 0.4, 0.6],
            "mean_escape_rate": [0.1, 0.2, 0.4],
            "detector_recall": [0.8, 0.7, 0.85],
            "retrained": [False, False, True],
        })

        out = plot_arms_race(history, output_path=tmp_path / "test_plot.png")
        assert out.exists()
        assert out.stat().st_size > 1000  # non-trivial image
