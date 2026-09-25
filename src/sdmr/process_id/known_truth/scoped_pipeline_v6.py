"""Scoped full-system authorization gates for SDMR v6 pipeline v2.

This module preserves legacy SDMR v6/v5 evaluators unchanged and introduces the
explicit world roles that were frozen during gate validation:

- W1/W2/W3/W4/W5/W8: informative controls
- W6 observation_confounded: report-only
- W7 omitted_driver: null control
"""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .integration_v5 import IntegrationDecision
from .prospective_kt import ProspectiveKTDecision, evaluate_prospective_kt


def _authorization_by_world(stage_p_states: pd.DataFrame) -> pd.DataFrame:
    required = {"seed", "world", "full_system_information_adequate"}
    missing = sorted(required - set(stage_p_states.columns))
    if missing:
        raise KeyError(f"stage_p_states missing authorization columns: {missing}")

    rows: list[dict[str, object]] = []
    for (seed, world), group in stage_p_states.groupby(
        ["seed", "world"], sort=True
    ):
        values = set(group["full_system_information_adequate"].astype(bool))
        if len(values) != 1:
            raise ValueError(
                "full-system authorization must be constant within seed/world"
            )
        rows.append(
            {
                "seed": int(seed),
                "world": str(world),
                "authorized": bool(next(iter(values))),
            }
        )
    if not rows:
        raise ValueError("stage_p_states contain no authorization rows")
    return pd.DataFrame(rows)


def _validate_scope(
    *,
    expected_worlds: Sequence[str],
    informative_control_worlds: Sequence[str],
    report_only_world: str,
    null_world: str,
) -> tuple[tuple[str, ...], str, str]:
    expected = tuple(str(x) for x in expected_worlds)
    controls = tuple(str(x) for x in informative_control_worlds)
    report = str(report_only_world)
    null = str(null_world)

    if not controls or len(set(controls)) != len(controls):
        raise ValueError("informative_control_worlds must be non-empty and unique")
    if report == null or report in controls or null in controls:
        raise ValueError("control, report-only, and null world roles must be disjoint")
    role_worlds = set(controls) | {report, null}
    if role_worlds != set(expected):
        raise ValueError(
            "world-role scope must exactly cover expected_worlds; "
            f"roles={sorted(role_worlds)}, expected={sorted(set(expected))}"
        )
    return controls, report, null


def evaluate_scoped_prospective_kt(
    stage_p_states: pd.DataFrame,
    stage_t_states: pd.DataFrame,
    *,
    expected_counts: dict[str, int],
    gate_vector: dict,
    expected_seed_count: int,
    expected_worlds: tuple[str, ...],
    provenance_complete: bool,
    informative_control_worlds: Sequence[str],
    report_only_world: str,
    null_world: str,
) -> ProspectiveKTDecision:
    """Evaluate KT-A–KT-F with explicit full-system authorization world roles."""

    controls, report, null = _validate_scope(
        expected_worlds=expected_worlds,
        informative_control_worlds=informative_control_worlds,
        report_only_world=report_only_world,
        null_world=null_world,
    )

    ke = gate_vector["KT-E"]
    relaxed_gate_vector = {
        **gate_vector,
        "KT-E": {
            "max_sharp_rate_among_odo_unavailable": float(
                ke["max_sharp_rate_among_odo_unavailable"]
            ),
            "max_favorable_positive_rate_among_odo_unavailable": float(
                ke["max_favorable_positive_rate_among_odo_unavailable"]
            ),
            # Legacy evaluator still computes pooled non-W7/W7 rates. Make
            # those checks nonbinding here; explicit scoped checks below are
            # authoritative for v2.
            "min_non_w7_full_system_information_adequacy": 0.0,
            "max_w7_full_system_information_adequacy": 1.0,
        },
    }

    base = evaluate_prospective_kt(
        stage_p_states,
        stage_t_states,
        expected_counts=expected_counts,
        gate_vector=relaxed_gate_vector,
        expected_seed_count=int(expected_seed_count),
        expected_worlds=tuple(expected_worlds),
        provenance_complete=bool(provenance_complete),
    )

    authorization = _authorization_by_world(stage_p_states)
    seed_count = int(expected_seed_count)
    if seed_count <= 0:
        raise ValueError("expected_seed_count must be positive")

    world_counts = (
        authorization.groupby("world", sort=True)
        .agg(
            authorized_count=("authorized", "sum"),
            denominator=("seed", "size"),
        )
        .reset_index()
    )
    if not (world_counts["denominator"].astype(int) == seed_count).all():
        raise ValueError(
            "every scoped authorization world must contain every expected seed"
        )
    counts = {
        str(row["world"]): int(row["authorized_count"])
        for _, row in world_counts.iterrows()
    }

    missing_roles = sorted((set(controls) | {report, null}) - set(counts))
    if missing_roles:
        raise ValueError(f"authorization scope missing worlds: {missing_roles}")

    rates = {world: counts[world] / seed_count for world in counts}
    minimum_control_rate = min(rates[world] for world in controls)
    report_rate = rates[report]
    w7_count = counts[null]
    w7_rate = rates[null]

    max_sharp = float(ke["max_sharp_rate_among_odo_unavailable"])
    max_favorable = float(ke["max_favorable_positive_rate_among_odo_unavailable"])
    min_control = float(
        ke["minimum_each_informative_control_authorization_rate"]
    )
    max_w7_count = int(ke["maximum_w7_authorized_count"])

    scoped_e = bool(
        base.metrics["unavailable_sharp_rate"] <= max_sharp
        and base.metrics["unavailable_favorable_rate"] <= max_favorable
        and minimum_control_rate >= min_control
        and w7_count <= max_w7_count
    )

    gates = dict(base.gates)
    gates["KT-E"] = scoped_e
    metrics = dict(base.metrics)
    metrics.update(
        {
            "minimum_informative_control_authorization_rate": float(
                minimum_control_rate
            ),
            "report_only_world_authorization_rate": float(report_rate),
            "w7_authorized_count": float(w7_count),
            "w7_authorization_rate": float(w7_rate),
        }
    )
    for world in controls:
        metrics[f"authorization_rate__{world}"] = float(rates[world])

    reasons = tuple(name for name, passed in gates.items() if not passed)
    return ProspectiveKTDecision(
        passed=bool(all(gates.values())),
        gates=gates,
        metrics=metrics,
        counts=base.counts,
        reasons=reasons,
    )


def evaluate_scoped_integration_gate(
    stage_p_states: pd.DataFrame,
    stage_t_states: pd.DataFrame,
    *,
    expected_counts: dict[str, int],
    gate_vector: dict,
    expected_seed_count: int,
    expected_worlds: tuple[str, ...],
    provenance_complete: bool,
    informative_control_worlds: Sequence[str],
    report_only_world: str,
    null_world: str,
) -> IntegrationDecision:
    """Evaluate INT-A–INT-F with W6 report-only authorization scope."""

    mapped = {
        "KT-B": {
            "minimum": float(
                gate_vector["INT-B"]["minimum_positive_recovery"]
            )
        },
        "KT-C": {
            "maximum": float(
                gate_vector["INT-C"]["maximum_false_positive_rate"]
            )
        },
        "KT-D": {
            "max_overresolution_rate_among_odo_unresolved": float(
                gate_vector["INT-D"]["maximum_overresolution_rate"]
            ),
            "max_structural_refusal_violation_rate": float(
                gate_vector["INT-D"][
                    "maximum_structural_refusal_violation_rate"
                ]
            ),
        },
        "KT-E": {
            "max_sharp_rate_among_odo_unavailable": float(
                gate_vector["INT-E"]["maximum_unavailable_sharp_rate"]
            ),
            "max_favorable_positive_rate_among_odo_unavailable": float(
                gate_vector["INT-E"]["maximum_unavailable_favorable_rate"]
            ),
            "minimum_each_informative_control_authorization_rate": float(
                gate_vector["INT-E"][
                    "minimum_each_informative_control_authorization_rate"
                ]
            ),
            "maximum_w7_authorized_count": int(
                gate_vector["INT-E"]["maximum_w7_authorized_count"]
            ),
        },
        "KT-F": {
            "complete_spatial_transfer_evaluation_required": True,
            "max_stage_p_positive_to_spatial_replaceable_contradiction_rate": float(
                gate_vector["INT-F"][
                    "maximum_stage_p_positive_to_spatial_replaceable_contradiction_rate"
                ]
            ),
            "max_spatial_structural_refusal_violation_rate": float(
                gate_vector["INT-F"][
                    "maximum_spatial_structural_refusal_violation_rate"
                ]
            ),
            "spatial_positive_retention_report_only": True,
        },
    }

    base = evaluate_scoped_prospective_kt(
        stage_p_states,
        stage_t_states,
        expected_counts=expected_counts,
        gate_vector=mapped,
        expected_seed_count=int(expected_seed_count),
        expected_worlds=tuple(expected_worlds),
        provenance_complete=bool(provenance_complete),
        informative_control_worlds=tuple(informative_control_worlds),
        report_only_world=str(report_only_world),
        null_world=str(null_world),
    )
    gates = {
        f"INT-{letter}": base.gates[f"KT-{letter}"]
        for letter in ("A", "B", "C", "D", "E", "F")
    }
    reasons = tuple(name for name, passed in gates.items() if not passed)
    return IntegrationDecision(
        passed=bool(all(gates.values())),
        gates=gates,
        metrics=base.metrics,
        counts=base.counts,
        reasons=reasons,
    )
