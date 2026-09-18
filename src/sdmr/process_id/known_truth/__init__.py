"""Known-truth worlds and gates for SDMR v3 process identification."""

from .benchmark import compare_oracle_and_occurrence
from .oracle import evaluate_oracle_states
from .promotion import KnownTruthGateDecision, evaluate_known_truth_gate
from .worlds import KNOWN_TRUTH_WORLDS, KnownTruthWorld, simulate_process_world

__all__ = [
    "KNOWN_TRUTH_WORLDS",
    "KnownTruthGateDecision",
    "KnownTruthWorld",
    "compare_oracle_and_occurrence",
    "evaluate_known_truth_gate",
    "evaluate_oracle_states",
    "simulate_process_world",
]
