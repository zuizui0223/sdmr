"""Seed all legacy process-global RNG users before Product-A v2.7.2 execution.

Candidate SDMs in v2.7.2 carry an explicit ``ModelSpec.random_state``. A small
number of candidate-independent nuisance classifiers in the inherited Product-A
v2 machinery still use ``random_state=None`` and therefore scikit-learn's NumPy
global RNG. This successor-only entrypoint freezes that global stream before any
selection code runs, without changing historical APIs or frozen earlier runs.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .v2_7_2_known_truth_confirmation import main as confirmation_main

CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "configs"
    / "product_a_v2_7_2_deterministic_successor_contract.json"
)


def seed_successor_process(contract_path: str | Path = CONTRACT_PATH) -> int:
    payload = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_7_2_deterministic_successor_preoutcome_contract":
        raise ValueError("wrong v2.7.2 successor contract")
    seed = payload["known_truth_confirmation"].get("selection_process_numpy_seed")
    if not isinstance(seed, int):
        raise TypeError("selection_process_numpy_seed must be an integer")
    if payload["implementation_change"].get("successor_selection_process_numpy_seed") != seed:
        raise ValueError("successor process RNG seed is inconsistent across the contract")
    np.random.seed(int(seed))
    return int(seed)


def main(argv=None) -> int:
    seed_successor_process()
    return confirmation_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
