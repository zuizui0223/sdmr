"""Conservative process-information decision prototype for forest known truth.

This is a DEVELOPMENT-ONLY policy over declared diagnostics. It does NOT
identify causal competition, prove ignorability or authorize field promotion.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite

from .structural_known_truth_v1 import ForestScore


@dataclass(frozen=True)
class StructureProcessGate:
    """Development thresholds tuned only on burned development seeds."""

    min_regions: int = 8
    full_vs_null_margin: float = 0.05
    carrier_closure_margin: float = 0.03
    temporal_margin: float = 0.03
    alpha: float = 0.05

    def __post_init__(self) -> None:
        if self.min_regions < 6:
            raise ValueError("at least six independent blocks are required")
        for field in ("full_vs_null_margin", "carrier_closure_margin", "temporal_margin"):
            x = getattr(self, field)
            if not isfinite(x) or x <= 0:
                raise ValueError("strictly positive, finite evidence margin required")
        if not isfinite(self.alpha) or not 0 < self.alpha < 1:
            raise ValueError("alpha must be between zero and one")


@dataclass(frozen=True)
class ProcessInformationStatus:
    state: str
    reason: str
    evidence_class: str
    causal_process_identified: bool = False
    empirical_promotion_authorized: bool = False


def assess_forest_development(
    score: ForestScore, gate: StructureProcessGate = StructureProcessGate()
) -> ProcessInformationStatus:
    """Classify only known-truth development metrics, not real organisms.

    Require external source and selection/attrition audit *before* using
    either spatial or temporal evidence for a sharper conditional statement.
    If a real dataset is available, it needs a separate source-audited adapter,
    not casting real results into ForestScore.
    """
    if score.inference_ceiling != "development_known_truth_only":
        raise ValueError("no field/empirical inference by this development gate")

    def out(state: str, reason: str) -> ProcessInformationStatus:
        return ProcessInformationStatus(
            state=state, reason=reason,
            evidence_class="synthetic_development",
        )

    if score.n_regions < gate.min_regions:
        return out("unavailable", "independent_block_support")
    if not score.observation_selection_known:
        return out("unresolved", "observation_or_survivor_selection_unverified")
    if score.full_vs_null_gain <= gate.full_vs_null_margin:
        return out("unavailable", "declared_full_system_not_demonstrably_informative")
    if score.closure_gain <= gate.carrier_closure_margin:
        return out("unresolved", "complete_carrier_knockout_not_informative")
    if (score.temporal_closure_gain <= gate.temporal_margin or
            score.temporal_closure_p > gate.alpha):
        return out("unresolved", "within_site_change_information_not_supported")
    return out(
        "contributory_information_candidate",
        "full_system_and_all_carrier_closure_and_within_site_transfer",
    )


def observation_audit_ablation(
    score: ForestScore, gate: StructureProcessGate = StructureProcessGate()
) -> tuple[ProcessInformationStatus, ProcessInformationStatus]:
    """Demonstrate sensitivity to wrongly waiving the observation audit.

    The override is deliberately unavailable in assess_forest_development's
    ordinary signature and cannot be used for a real-data promotion.
    """
    correctly_guarded = assess_forest_development(score, gate)
    incorrectly_waived = assess_forest_development(
        replace(score, observation_selection_known=True), gate
    )
    return correctly_guarded, incorrectly_waived
