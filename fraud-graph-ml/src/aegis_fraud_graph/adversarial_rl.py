"""Adversarial RL upgrade — PPO agent learns to launder money.

Optional upgrade over the evolutionary loop.  The criminal is a PPO policy
that takes graph-level state and outputs the next transaction action.

Env:
  - State:  current graph snapshot features (account-level aggregates)
  - Action: (target_account_idx, amount_bucket, delay_bucket)
  - Reward: money_moved × (1 - detection_probability)

Stack: stable-baselines3, gymnasium.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_RL_AVAILABLE = False
try:
    import gymnasium as gym
    from gymnasium import spaces
    from stable_baselines3 import PPO
    _RL_AVAILABLE = True
except ImportError:
    gym = None  # type: ignore[assignment]
    spaces = None  # type: ignore[assignment]
    PPO = None  # type: ignore[assignment]


def _require_rl():
    if not _RL_AVAILABLE:
        raise ImportError(
            "RL upgrade requires stable-baselines3 and gymnasium. "
            "Install with: pip install -e '.[rl]'"
        )


class FraudEnv(gym.Env if _RL_AVAILABLE else object):
    """Gymnasium environment for the criminal RL agent.

    The agent builds a laundering subgraph one transaction at a time.
    After `max_steps` transactions, the detector runs and scores the result.

    Observation: [n_accounts_used, total_moved, avg_delay, n_hops, detection_est]
    Action: Discrete — (target_idx × amount_bucket × delay_bucket)
    Reward: Per-step: small reward for moving money; terminal: big bonus for evasion.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        base_ds=None,
        max_steps: int = 20,
        n_target_choices: int = 5,
        n_amount_buckets: int = 4,
        n_delay_buckets: int = 3,
    ):
        _require_rl()
        super().__init__()

        self.base_ds = base_ds
        self.max_steps = max_steps
        self.n_targets = n_target_choices
        self.n_amounts = n_amount_buckets
        self.n_delays = n_delay_buckets

        # Action: single discrete index encoding (target, amount, delay)
        self.n_actions = n_target_choices * n_amount_buckets * n_delay_buckets
        self.action_space = spaces.Discrete(self.n_actions)

        # Observation: 5 features
        self.observation_space = spaces.Box(
            low=0.0, high=np.inf, shape=(5,), dtype=np.float32,
        )

        self._reset_state()

    def _reset_state(self):
        self.step_count = 0
        self.accounts_used = set()
        self.total_moved = 0.0
        self.delays: list[float] = []
        self.transactions: list[dict] = []

    def _decode_action(self, action: int) -> tuple[int, int, int]:
        """Decode flat action index into (target_idx, amount_bucket, delay_bucket)."""
        delay = action % self.n_delays
        remainder = action // self.n_delays
        amount = remainder % self.n_amounts
        target = remainder // self.n_amounts
        return target, amount, delay

    def _get_obs(self) -> np.ndarray:
        return np.array([
            len(self.accounts_used),
            self.total_moved / 1_000_000,  # normalize
            np.mean(self.delays) if self.delays else 0.0,
            self.step_count,
            0.0,  # detection estimate (updated at terminal)
        ], dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed) if hasattr(super(), 'reset') else None
        self._reset_state()
        return self._get_obs(), {}

    def step(self, action):
        target_idx, amount_bucket, delay_bucket = self._decode_action(action)

        # Map buckets to values
        amount_map = [10_000, 50_000, 200_000, 500_000]
        delay_map = [5.0, 60.0, 1440.0]  # minutes

        amount = amount_map[min(amount_bucket, len(amount_map) - 1)]
        delay = delay_map[min(delay_bucket, len(delay_map) - 1)]

        self.accounts_used.add(target_idx)
        self.total_moved += amount
        self.delays.append(delay)
        self.transactions.append({
            "target": target_idx,
            "amount": amount,
            "delay": delay,
        })
        self.step_count += 1

        # Per-step reward: small incentive to move money
        reward = amount / 1_000_000

        terminated = self.step_count >= self.max_steps
        truncated = False

        if terminated:
            # Terminal reward: bonus for evasion
            # Heuristic detection estimate based on how "suspicious" the pattern is
            suspicion = 0.0
            if self.total_moved > 1_000_000:
                suspicion += 0.2
            if len(self.delays) > 0 and np.mean(self.delays) < 30:
                suspicion += 0.3  # fast = suspicious
            if len(self.accounts_used) < 3:
                suspicion += 0.2  # few accounts = suspicious
            detection_prob = min(suspicion, 1.0)
            evasion_bonus = (self.total_moved / 1_000_000) * (1.0 - detection_prob)
            reward += evasion_bonus

        return self._get_obs(), reward, terminated, truncated, {}


def train_rl_criminal(
    base_ds=None,
    total_timesteps: int = 10_000,
    seed: int = 42,
) -> dict:
    """Train a PPO criminal agent and return performance summary.

    Returns dict with {mean_reward, total_moved, n_episodes}.
    """
    _require_rl()

    env = FraudEnv(base_ds=base_ds)
    model = PPO(
        "MlpPolicy",
        env,
        verbose=0,
        seed=seed,
        n_steps=128,
        batch_size=64,
        learning_rate=3e-4,
    )
    model.learn(total_timesteps=total_timesteps)

    # Evaluate
    rewards = []
    for _ in range(20):
        obs, _ = env.reset()
        total_reward = 0.0
        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(action)
            total_reward += reward
            done = terminated or truncated
        rewards.append(total_reward)

    result = {
        "mean_reward": float(np.mean(rewards)),
        "std_reward": float(np.std(rewards)),
        "total_moved": env.total_moved,
        "n_eval_episodes": 20,
    }

    logger.info("RL Criminal: mean_reward=%.4f, std=%.4f", result["mean_reward"], result["std_reward"])
    return result
