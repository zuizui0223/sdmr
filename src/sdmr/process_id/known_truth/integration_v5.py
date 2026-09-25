"""SDMR v5 full-pipeline integration helpers."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .prospective_kt import evaluate_prospective_kt


@dataclass(frozen=True)
class IntegrationDecision:
    passed: bool
    gates: dict[str, bool]
    metrics: dict[str, float]
    counts: dict[str, int]
    reasons: tuple[str, ...]


def apply_permutation_authorization(
    states: pd.DataFrame,
    *,
    authorized: bool,
    observed_mean_score: float,
    mean_gain_over_null: float,
    p_value: float,
) -> pd.DataFrame:
    """Attach the v5 full-system gate and fail closed before process interpretation."""

    required={"process","state","reason"}
    missing=sorted(required-set(states.columns))
    if missing:
        raise KeyError(f"process state table missing columns: {missing}")
    if states.empty:
        raise ValueError("process state table must be non-empty")

    out=states.copy(deep=True)
    out["full_system_information_adequate"]=bool(authorized)
    out["full_system_observed_mean_score"]=float(observed_mean_score)
    out["full_system_mean_gain_over_null"]=float(mean_gain_over_null)
    out["full_system_permutation_p"]=float(p_value)

    if not bool(authorized):
        out["state"]="unavailable"
        out["reason"]="full_system_not_informative"
    return out


def evaluate_integration_gate(
    stage_p_states: pd.DataFrame,
    stage_t_states: pd.DataFrame,
    *,
    expected_counts: dict[str,int],
    gate_vector: dict,
    expected_seed_count: int,
    expected_worlds: tuple[str,...],
    provenance_complete: bool,
) -> IntegrationDecision:
    """Evaluate frozen INT-A through INT-F as a strict conjunction."""

    mapped={
        "KT-B":{
            "minimum":float(
                gate_vector["INT-B"]["minimum_positive_recovery"]
            )
        },
        "KT-C":{
            "maximum":float(
                gate_vector["INT-C"]["maximum_false_positive_rate"]
            )
        },
        "KT-D":{
            "max_overresolution_rate_among_odo_unresolved":float(
                gate_vector["INT-D"]["maximum_overresolution_rate"]
            ),
            "max_structural_refusal_violation_rate":float(
                gate_vector["INT-D"][
                    "maximum_structural_refusal_violation_rate"
                ]
            ),
        },
        "KT-E":{
            "max_sharp_rate_among_odo_unavailable":float(
                gate_vector["INT-E"]["maximum_unavailable_sharp_rate"]
            ),
            "max_favorable_positive_rate_among_odo_unavailable":float(
                gate_vector["INT-E"]["maximum_unavailable_favorable_rate"]
            ),
            "min_non_w7_full_system_information_adequacy":float(
                gate_vector["INT-E"]["minimum_non_w7_authorization_rate"]
            ),
            "max_w7_full_system_information_adequacy":float(
                gate_vector["INT-E"]["maximum_w7_authorized_count"]
            ) / float(expected_seed_count),
        },
        "KT-F":{
            "complete_spatial_transfer_evaluation_required":True,
            "max_stage_p_positive_to_spatial_replaceable_contradiction_rate":float(
                gate_vector["INT-F"][
                    "maximum_stage_p_positive_to_spatial_replaceable_contradiction_rate"
                ]
            ),
            "max_spatial_structural_refusal_violation_rate":float(
                gate_vector["INT-F"][
                    "maximum_spatial_structural_refusal_violation_rate"
                ]
            ),
            "spatial_positive_retention_report_only":True,
        },
    }

    base=evaluate_prospective_kt(
        stage_p_states,
        stage_t_states,
        expected_counts=expected_counts,
        gate_vector=mapped,
        expected_seed_count=int(expected_seed_count),
        expected_worlds=tuple(expected_worlds),
        provenance_complete=bool(provenance_complete),
    )
    gates={
        f"INT-{letter}":base.gates[f"KT-{letter}"]
        for letter in ("A","B","C","D","E","F")
    }
    reasons=tuple(name for name,passed in gates.items() if not passed)
    return IntegrationDecision(
        passed=bool(all(gates.values())),
        gates=gates,
        metrics=base.metrics,
        counts=base.counts,
        reasons=reasons,
    )
