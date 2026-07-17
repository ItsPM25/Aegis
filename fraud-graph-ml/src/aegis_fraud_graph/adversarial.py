"""Criminal Trains the Cop — adversarial evolutionary arms race.

A parameterized criminal strategy evolves to evade the XGBoost detector;
every few generations the detector retrains on the evading rings, creating
a visible arms race.

Pipeline:
  1. Synthetic UPI graph generator (reuses synth.py)
  2. Criminal strategy vector: [delay, variance, amount_dist, split_count,
     hop_depth, mule_reuse, threshold_proximity]
  3. Evolutionary loop (DEAP): 50 strategies → inject → detect → fitness →
     select top 10 → mutate → repeat
  4. Retrain cop every k generations on evading patterns
  5. Output: arms_race history (DataFrame) for plotting

Limitation (stated honestly): the criminal can only invent tricks the
simulator can express.
"""

from __future__ import annotations

import logging
import random
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import networkx as nx
import numpy as np
import pandas as pd

from .config import ModelConfig, SynthConfig
from .data import Dataset

logger = logging.getLogger(__name__)

# Soft-import DEAP
_DEAP_AVAILABLE = False
try:
    from deap import algorithms, base, creator, tools
    _DEAP_AVAILABLE = True
except ImportError:
    pass


def _require_deap():
    if not _DEAP_AVAILABLE:
        raise ImportError(
            "Criminal Trains the Cop requires DEAP. "
            "Install with: pip install -e '.[advanced]'"
        )


# ── Criminal strategy ─────────────────────────────────────────────────────


@dataclass
class CriminalStrategy:
    """The criminal's playbook — a float vector in [0, 1] mapped to realistic ranges.

    Each gene controls one axis of laundering behavior:
    - delay_mean:           average minutes between hops (0→5min, 1→2days)
    - delay_variance:       jitter on timing (0=clockwork, 1=very random)
    - amount_type:          0=round amounts, 0.5=structured, 1=organic-looking
    - split_count:          number of splits in fan-out (0→2, 1→8)
    - hop_depth:            chain length (0→2 hops, 1→8 hops)
    - mule_reuse_rate:      fraction of mules reused across runs (0→fresh, 1→all reused)
    - threshold_proximity:  how close amounts sit to reporting thresholds (0→far, 1→right below)
    """
    delay_mean: float = 0.3
    delay_variance: float = 0.2
    amount_type: float = 0.0
    split_count: float = 0.3
    hop_depth: float = 0.4
    mule_reuse_rate: float = 0.1
    threshold_proximity: float = 0.5

    def to_vector(self) -> list[float]:
        return [
            self.delay_mean, self.delay_variance, self.amount_type,
            self.split_count, self.hop_depth, self.mule_reuse_rate,
            self.threshold_proximity,
        ]

    @classmethod
    def from_vector(cls, v: list[float]) -> CriminalStrategy:
        # Clamp to [0, 1]
        v = [max(0.0, min(1.0, x)) for x in v]
        return cls(
            delay_mean=v[0], delay_variance=v[1], amount_type=v[2],
            split_count=v[3], hop_depth=v[4], mule_reuse_rate=v[5],
            threshold_proximity=v[6],
        )

    def _map_delay_minutes(self) -> float:
        """Map [0,1] → [5, 2880] minutes (5min to 2 days)."""
        return 5.0 + self.delay_mean * 2875.0

    def _map_delay_jitter(self) -> float:
        """Map [0,1] → [0, 0.8] coefficient of variation."""
        return self.delay_variance * 0.8

    def _map_splits(self) -> int:
        """Map [0,1] → [2, 8] fan-out splits."""
        return int(2 + self.split_count * 6)

    def _map_hops(self) -> int:
        """Map [0,1] → [2, 8] chain hops."""
        return int(2 + self.hop_depth * 6)

    def _map_amount(self, base: float) -> float:
        """Generate an amount based on amount_type gene."""
        if self.amount_type < 0.33:
            # Round amounts (easy to detect)
            return round(base / 1000) * 1000
        elif self.amount_type < 0.66:
            # Structured: just below reporting thresholds
            thresholds = [10_000, 25_000, 50_000, 100_000]
            closest = min(thresholds, key=lambda t: abs(t - base))
            offset = self.threshold_proximity * 500
            return closest - offset + random.uniform(-100, 100)
        else:
            # Organic-looking: log-normal with realistic noise
            return abs(random.lognormvariate(np.log(base), 0.3))


# ── Ring injection ─────────────────────────────────────────────────────────


def inject_adversarial_ring(
    ds: Dataset,
    strategy: CriminalStrategy,
    ring_id: str = "adv_ring",
    seed: int = None,
) -> tuple[Dataset, list[str], float]:
    """Inject a laundering subgraph (fan-out → mule chain → fan-in) into ds.

    Returns (modified Dataset, list of ring member account_ids, total money moved).
    """
    rng = random.Random(seed)
    accounts = ds.accounts.copy(deep=True)
    transactions = ds.transactions.copy(deep=True)

    existing = set(accounts["account_id"].astype(str))
    n_splits = strategy._map_splits()
    n_hops = strategy._map_hops()
    delay_mean = strategy._map_delay_minutes()
    delay_jitter = strategy._map_delay_jitter()

    # Total members: 1 source + n_splits chains of n_hops + 1 collector
    total_members = 1 + n_splits * n_hops + 1
    base_ts = datetime.now(timezone.utc).replace(microsecond=0)
    base_amount = rng.uniform(200_000, 800_000)

    # Generate member accounts
    members: list[str] = []
    next_id = len(accounts)
    for i in range(total_members):
        aid = f"adv_{next_id + i:05d}"
        while aid in existing:
            next_id += 1
            aid = f"adv_{next_id + i:05d}"
        existing.add(aid)
        members.append(aid)
        accounts.loc[len(accounts)] = {
            "account_id": aid,
            "district": rng.choice(["Jamtara", "Deoghar", "Alwar"]),
            "is_illicit": True,
            "ring_id": ring_id,
        }

    source = members[0]
    collector = members[-1]
    chains: list[list[str]] = []
    idx = 1
    for s in range(n_splits):
        chain = []
        for h in range(n_hops):
            chain.append(members[idx])
            idx += 1
        chains.append(chain)

    tx_rows = []
    next_tx = len(transactions)
    total_moved = 0.0

    def add_tx(src: str, dst: str, amount: float, ts: datetime):
        nonlocal next_tx, total_moved
        tx_rows.append({
            "tx_id": f"adv_tx_{next_tx:06d}",
            "source": src,
            "target": dst,
            "amount": round(amount, 2),
            "timestamp": ts.isoformat(),
        })
        next_tx += 1
        total_moved += amount

    # Phase 1: Fan-out — source distributes to chain heads
    split_amount = base_amount / n_splits
    for i, chain in enumerate(chains):
        delay = delay_mean * (1 + rng.gauss(0, delay_jitter))
        ts = base_ts + timedelta(minutes=max(1, delay) * (i + 1))
        amt = strategy._map_amount(split_amount)
        add_tx(source, chain[0], amt, ts)

    # Phase 2: Mule chains — each chain passes money down
    for chain in chains:
        current_amount = split_amount
        for j in range(len(chain) - 1):
            current_amount *= rng.uniform(0.94, 0.99)  # mule takes cut
            delay = delay_mean * (1 + rng.gauss(0, delay_jitter))
            ts = base_ts + timedelta(minutes=max(1, delay) * (j + 2 + len(chains)))
            amt = strategy._map_amount(current_amount)
            add_tx(chain[j], chain[j + 1], amt, ts)

    # Phase 3: Fan-in — chain tails collect into the final account
    for chain in chains:
        tail = chain[-1]
        delay = delay_mean * (1 + rng.gauss(0, delay_jitter))
        ts = base_ts + timedelta(minutes=max(1, delay) * (n_hops + len(chains) + 2))
        current_amount = split_amount * (0.96 ** n_hops)
        amt = strategy._map_amount(current_amount)
        add_tx(tail, collector, amt, ts)

    # Camouflage: each member also does some small organic traffic
    legit_ids = accounts[accounts["is_illicit"] == False]["account_id"].tolist()  # noqa: E712
    if legit_ids:
        reuse_count = int(strategy.mule_reuse_rate * len(members))
        for m in members[:max(1, reuse_count)]:
            for _ in range(rng.randint(1, 3)):
                peer = rng.choice(legit_ids)
                amt = rng.lognormvariate(6.5, 0.9)
                ts = base_ts + timedelta(days=rng.uniform(-3, 3))
                if rng.random() < 0.5:
                    add_tx(m, peer, amt, ts)
                else:
                    add_tx(peer, m, amt, ts)

    if tx_rows:
        new_tx = pd.DataFrame(tx_rows)
        transactions = pd.concat([transactions, new_tx], ignore_index=True)

    return (
        Dataset(
            accounts=accounts.reset_index(drop=True),
            transactions=transactions.reset_index(drop=True),
            name=f"{ds.name}+adversarial",
        ),
        members,
        total_moved,
    )


# ── Fitness evaluation ─────────────────────────────────────────────────────


def evaluate_strategy(
    strategy: CriminalStrategy,
    base_ds: Dataset,
    detector_fn,
    ring_id: str = "adv_ring",
    seed: int = None,
) -> tuple[float, float, float]:
    """Inject a ring with this strategy, run the detector, return fitness.

    Returns (fitness, money_moved, detection_rate).
    Fitness = money_moved × (1 - detection_rate)
    """
    injected_ds, members, money_moved = inject_adversarial_ring(
        base_ds, strategy, ring_id=ring_id, seed=seed,
    )

    # Run detector
    detected_members = detector_fn(injected_ds, members)

    # Detection rate: fraction of adversarial members found by the detector
    member_set = set(members)
    detected_set = set(detected_members)
    detection_rate = len(detected_set & member_set) / max(len(member_set), 1)

    # Fitness: criminal wants to move money AND evade
    fitness = (money_moved / 1_000_000) * (1.0 - detection_rate)

    return fitness, money_moved, detection_rate


# ── Default detector (XGBoost) ─────────────────────────────────────────────


def _default_detector(ds: Dataset, suspect_members: list[str]) -> list[str]:
    """Run the existing XGBoost pipeline and return detected members."""
    from .graph import compute_features
    from .model import load_model, score_all
    from .rings import detect_rings

    features = compute_features(ds)
    try:
        clf = load_model()
    except Exception:
        from .model import train as train_model
        labels = ds.accounts.set_index("account_id")["is_illicit"]
        clf, _ = train_model(features, labels)

    scores = score_all(clf, features)
    rings, accounts = detect_rings(ds, scores)

    # All accounts placed in any ring
    detected = set()
    for r in rings:
        detected.update(r.account_ids)

    return list(detected & set(suspect_members))


def _retrain_detector(
    base_ds: Dataset,
    evading_datasets: list[tuple[Dataset, list[str]]],
) -> None:
    """Retrain the XGBoost model on the base data PLUS the evading rings.

    The evading rings are labeled as illicit and merged into training.
    """
    from .graph import compute_features
    from .model import save_model, train as train_model

    # Merge all evading rings into the base dataset
    merged_accs = base_ds.accounts.copy()
    merged_tx = base_ds.transactions.copy()

    for ds_aug, members in evading_datasets:
        # Add new accounts (illicit=True for ring members)
        new_accs = ds_aug.accounts[ds_aug.accounts["account_id"].isin(members)]
        merged_accs = pd.concat([merged_accs, new_accs], ignore_index=True).drop_duplicates(
            subset=["account_id"], keep="last"
        )
        # Add new transactions
        existing_tx = set(merged_tx["tx_id"])
        new_tx = ds_aug.transactions[~ds_aug.transactions["tx_id"].isin(existing_tx)]
        merged_tx = pd.concat([merged_tx, new_tx], ignore_index=True)

    merged_ds = Dataset(
        accounts=merged_accs.reset_index(drop=True),
        transactions=merged_tx.reset_index(drop=True),
        name="retrained",
    )

    features = compute_features(merged_ds)
    labels = merged_ds.accounts.set_index("account_id")["is_illicit"]
    clf, report = train_model(features, labels, ModelConfig())
    save_model(clf, report)

    logger.info(
        "Retrained detector: AUC=%.4f, AP=%.4f, threshold=%.4f",
        report.roc_auc, report.avg_precision, report.chosen_threshold,
    )


# ── Evolutionary loop ──────────────────────────────────────────────────────


@dataclass
class GenerationLog:
    """One row of the arms-race history."""
    generation: int
    best_fitness: float
    mean_fitness: float
    best_escape_rate: float
    mean_escape_rate: float
    detector_recall: float
    retrained: bool


def run_arms_race(
    n_generations: int = 30,
    population_size: int = 50,
    top_k: int = 10,
    retrain_every: int = 5,
    source: str = "synthetic",
    seed: int = 42,
) -> pd.DataFrame:
    """Full evolutionary arms race.

    Returns a DataFrame with columns:
    [generation, best_fitness, mean_fitness, best_escape_rate,
     mean_escape_rate, detector_recall, retrained]
    """
    _require_deap()
    from .data import load

    rng = random.Random(seed)
    np.random.seed(seed)

    base_ds = load(source)
    n_genes = 7

    # DEAP setup — create types only if they don't already exist
    if not hasattr(creator, "AdversarialFitness"):
        creator.create("AdversarialFitness", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "CriminalIndividual"):
        creator.create("CriminalIndividual", list, fitness=creator.AdversarialFitness)

    toolbox = base.Toolbox()
    toolbox.register("attr_float", rng.random)
    toolbox.register(
        "individual",
        tools.initRepeat,
        creator.CriminalIndividual,
        toolbox.attr_float,
        n=n_genes,
    )
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    def eval_individual(ind):
        strategy = CriminalStrategy.from_vector(ind)
        fitness, money, detection = evaluate_strategy(
            strategy, base_ds, _default_detector,
            seed=int(sum(ind) * 1000) % 2**31,
        )
        return (fitness,)

    toolbox.register("evaluate", eval_individual)
    toolbox.register("mate", tools.cxUniform, indpb=0.5)
    toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.15, indpb=0.3)
    toolbox.register("select", tools.selBest, k=top_k)

    # Initialize population
    population = toolbox.population(n=population_size)

    history: list[GenerationLog] = []
    evading_datasets: list[tuple[Dataset, list[str]]] = []

    logger.info("=== Arms Race: %d generations, pop=%d ===", n_generations, population_size)

    for gen in range(n_generations):
        # Evaluate all individuals
        fitnesses = list(map(toolbox.evaluate, population))
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit

        fits = [f[0] for f in fitnesses]

        # Track escape rates
        escape_rates = []
        for ind in population:
            strategy = CriminalStrategy.from_vector(ind)
            _, _, detection = evaluate_strategy(
                strategy, base_ds, _default_detector,
                seed=int(sum(ind) * 1000) % 2**31,
            )
            escape_rates.append(1.0 - detection)

        # Detector recall on the best evader this generation
        best_idx = int(np.argmax(fits))
        best_strategy = CriminalStrategy.from_vector(population[best_idx])
        _, _, best_detection = evaluate_strategy(
            best_strategy, base_ds, _default_detector,
            seed=int(sum(population[best_idx]) * 1000) % 2**31,
        )

        retrained = False
        if (gen + 1) % retrain_every == 0 and gen > 0:
            # Collect evading rings (fitness > 0 means partial evasion)
            for ind in population:
                if ind.fitness.values[0] > 0:
                    strategy = CriminalStrategy.from_vector(ind)
                    ds_aug, members, _ = inject_adversarial_ring(
                        base_ds, strategy,
                        ring_id=f"evader_g{gen}",
                        seed=int(sum(ind) * 1000) % 2**31,
                    )
                    evading_datasets.append((ds_aug, members))

            if evading_datasets:
                _retrain_detector(base_ds, evading_datasets[-top_k:])
                retrained = True
                evading_datasets = []  # reset after retraining

        log = GenerationLog(
            generation=gen,
            best_fitness=float(max(fits)),
            mean_fitness=float(np.mean(fits)),
            best_escape_rate=float(max(escape_rates)) if escape_rates else 0.0,
            mean_escape_rate=float(np.mean(escape_rates)) if escape_rates else 0.0,
            detector_recall=float(best_detection),
            retrained=retrained,
        )
        history.append(log)

        logger.info(
            "Gen %02d: best_fit=%.4f mean_fit=%.4f escape=%.2f det_recall=%.2f %s",
            gen, log.best_fitness, log.mean_fitness,
            log.best_escape_rate, log.detector_recall,
            "[RETRAINED]" if retrained else "",
        )

        # Selection + reproduction
        elite = toolbox.select(population)
        offspring = [toolbox.clone(ind) for ind in elite]

        # Fill back to population_size via crossover + mutation
        while len(offspring) < population_size:
            p1, p2 = rng.sample(elite, 2)
            c1, c2 = toolbox.clone(p1), toolbox.clone(p2)
            toolbox.mate(c1, c2)
            toolbox.mutate(c1)
            toolbox.mutate(c2)
            # Clamp genes to [0, 1]
            for c in (c1, c2):
                for i in range(len(c)):
                    c[i] = max(0.0, min(1.0, c[i]))
                del c.fitness.values
            offspring.extend([c1, c2])

        population = offspring[:population_size]

    df = pd.DataFrame([
        {
            "generation": h.generation,
            "best_fitness": h.best_fitness,
            "mean_fitness": h.mean_fitness,
            "best_escape_rate": h.best_escape_rate,
            "mean_escape_rate": h.mean_escape_rate,
            "detector_recall": h.detector_recall,
            "retrained": h.retrained,
        }
        for h in history
    ])

    logger.info("=== Arms Race Complete ===")
    logger.info("Final best escape rate: %.4f", history[-1].best_escape_rate)
    logger.info("Final detector recall: %.4f", history[-1].detector_recall)

    return df
