"""Fixed synthetic benchmark comparators for structural process inference.

All endpoints are information candidates, never causal claims. The comparison
is DEVELOPMENT ONLY until independently frozen seeds are opened.
"""
from __future__ import annotations

from dataclasses import dataclass

from .structural_known_truth_v1 import ForestScore
from .structural_process_gate_v1 import StructureProcessGate, assess_forest_development


COMPARATORS = (
    "spatial_single_predictor",
    "space_and_time_single_predictor",
    "all_carriers_without_observation_audit",
    "all_carriers_with_observation_audit",
)
TRUTH_POSITIVES = frozenset(
    {"direct_structure", "shared_carrier", "temporal_transfer"}
)


def synthetic_truth_positive(world: str) -> bool:
    """Oracle for *within-site structural beta*, used for scoring only."""
    from .structural_known_truth_v1 import WORLDS
    if world not in WORLDS:
        raise ValueError("unregistered known-truth world")
    return world in TRUTH_POSITIVES


def comparator_candidate(
    score: ForestScore, comparator: str,
    gate: StructureProcessGate = StructureProcessGate(),
) -> bool:
    if comparator not in COMPARATORS:
        raise ValueError("unknown frozen comparator")
    if score.inference_ceiling != "development_known_truth_only":
        raise ValueError("not authorized on empirical scores")
    if score.n_regions < gate.min_regions:
        return False
    if score.full_vs_null_gain <= gate.full_vs_null_margin:
        return False
    if comparator == "all_carriers_with_observation_audit":
        return assess_forest_development(score, gate).state == "contributory_information_candidate"

    if comparator in ("all_carriers_without_observation_audit",):
        return (
            score.closure_gain > gate.carrier_closure_margin
            and score.temporal_closure_gain > gate.temporal_margin
            and score.temporal_closure_p <= gate.alpha
        )
    if score.spatial_gain <= gate.carrier_closure_margin or score.spatial_p > gate.alpha:
        return False
    if comparator == "spatial_single_predictor":
        return True
    return (
        score.temporal_gain > gate.temporal_margin
        and score.temporal_p <= gate.alpha
    )


@dataclass(frozen=True)
class BenchmarkCounts:
    comparator: str
    n_cases: int
    true_positive_targets: int
    true_positive_calls: int
    null_targets: int
    false_positive_calls: int


def aggregate_comparators(
    scores: list[ForestScore],
    gate: StructureProcessGate = StructureProcessGate(),
) -> tuple[BenchmarkCounts, ...]:
    if not scores:
        raise ValueError("no scored synthetic cases")
    identities = [(s.world, s.seed) for s in scores]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate world x seed cases")
    tp_targets = sum(synthetic_truth_positive(s.world) for s in scores)
    return tuple(
        BenchmarkCounts(
            comparator=name,
            n_cases=len(scores),
            true_positive_targets=tp_targets,
            true_positive_calls=sum(
                synthetic_truth_positive(s.world) and comparator_candidate(s, name, gate)
                for s in scores
            ),
            null_targets=len(scores) - tp_targets,
            false_positive_calls=sum(
                not synthetic_truth_positive(s.world) and comparator_candidate(s, name, gate)
                for s in scores
            ),
        )
        for name in COMPARATORS
    )
