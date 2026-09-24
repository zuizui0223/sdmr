"""Prospective known-truth gate evaluation for SDMR v3.

This module evaluates already-produced Stage-P and Stage-T evidence.  It never
generates prospective seeds or tunes thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd


_POSITIVE = {"contributory", "required"}
_SHARP = {"replaceable", "contributory", "required"}
_STATES = _SHARP | {"unresolved", "unavailable"}
_KEY = ["seed", "world", "process"]


@dataclass(frozen=True)
class ProspectiveKTDecision:
    passed: bool
    gates: dict[str, bool]
    metrics: dict[str, float]
    counts: dict[str, int]
    reasons: tuple[str, ...]


def _rate(mask, denominator_mask) -> float:
    den = int(denominator_mask.sum())
    if den <= 0:
        return float("nan")
    return float((mask & denominator_mask).sum() / den)


def _validate_states(frame: pd.DataFrame, *, name: str, require_full_gate: bool) -> pd.DataFrame:
    required = {
        "seed",
        "world",
        "process",
        "odo_state",
        "finite_state",
        "structural_refusal_expected",
    }
    if require_full_gate:
        required.add("full_system_information_adequate")
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"{name} missing columns: {missing}")

    data = frame.copy(deep=True)
    if data[_KEY].isna().any().any():
        raise ValueError(f"{name} keys must not contain missing values")
    if data.duplicated(_KEY).any():
        raise ValueError(f"{name} contains duplicate seed/world/process cells")

    for column in ("odo_state", "finite_state"):
        unknown = sorted(set(data[column].astype(str)) - _STATES)
        if unknown:
            raise ValueError(f"{name} contains unknown {column} values: {unknown}")

    refusal = data["structural_refusal_expected"]
    if refusal.isna().any() or not all(isinstance(v, bool) for v in refusal.tolist()):
        raise ValueError(f"{name} structural_refusal_expected must be boolean")

    if require_full_gate:
        adequate = data["full_system_information_adequate"]
        if adequate.isna().any() or not all(isinstance(v, bool) for v in adequate.tolist()):
            raise ValueError(
                f"{name} full_system_information_adequate must be boolean"
            )

    return data


def _validate_denominator(
    stage_p: pd.DataFrame,
    *,
    expected_counts: dict[str, int],
    expected_seed_count: int,
    expected_worlds: tuple[str, ...],
) -> dict[str, int]:
    seeds = sorted(set(int(v) for v in stage_p["seed"]))
    if len(seeds) != int(expected_seed_count):
        raise ValueError(
            f"expected {expected_seed_count} seeds, observed {len(seeds)}"
        )

    expected_world_set = set(str(v) for v in expected_worlds)
    observed_world_set = set(stage_p["world"].astype(str))
    if observed_world_set != expected_world_set:
        raise ValueError(
            "expected world set does not match observed world set: "
            f"expected={sorted(expected_world_set)}, observed={sorted(observed_world_set)}"
        )

    # Every seed must contain every declared world.
    by_seed = stage_p.groupby("seed", sort=False)["world"].agg(
        lambda s: set(s.astype(str))
    )
    if not all(worlds == expected_world_set for worlds in by_seed):
        raise ValueError("every prospective seed must contain every declared world")

    counts = {
        "positive": int(stage_p["odo_state"].isin(_POSITIVE).sum()),
        "replaceable": int(stage_p["odo_state"].eq("replaceable").sum()),
        "unresolved": int(stage_p["odo_state"].eq("unresolved").sum()),
        "unavailable": int(stage_p["odo_state"].eq("unavailable").sum()),
        "structural_refusal": int(
            stage_p["structural_refusal_expected"].astype(bool).sum()
        ),
    }

    wanted = {
        key: int(expected_counts[key])
        for key in (
            "positive",
            "replaceable",
            "unresolved",
            "unavailable",
            "structural_refusal",
        )
    }
    if counts != wanted:
        raise ValueError(
            f"expected ODO denominator {wanted}, observed {counts}"
        )
    return counts


def _full_system_rates(stage_p: pd.DataFrame) -> tuple[float, float]:
    rows = []
    for (seed, world), group in stage_p.groupby(["seed", "world"], sort=False):
        values = set(group["full_system_information_adequate"].astype(bool))
        if len(values) != 1:
            raise ValueError(
                "full-system adequacy must be constant within each seed/world"
            )
        rows.append(
            {
                "seed": int(seed),
                "world": str(world),
                "adequate": bool(next(iter(values))),
            }
        )
    gate = pd.DataFrame(rows)
    w7 = gate["world"].eq("omitted_driver")
    non_w7 = ~w7
    if not w7.any() or not non_w7.any():
        raise ValueError("full-system gate evaluation requires W7 and non-W7 worlds")
    return float(gate.loc[non_w7, "adequate"].mean()), float(
        gate.loc[w7, "adequate"].mean()
    )


def evaluate_prospective_kt(
    stage_p_states: pd.DataFrame,
    stage_t_states: pd.DataFrame,
    *,
    expected_counts: dict[str, int],
    gate_vector: dict,
    expected_seed_count: int,
    expected_worlds: tuple[str, ...],
    provenance_complete: bool,
) -> ProspectiveKTDecision:
    """Evaluate the frozen prospective KT-A through KT-F conjunction."""

    stage_p = _validate_states(
        stage_p_states, name="stage_p_states", require_full_gate=True
    )
    stage_t = _validate_states(
        stage_t_states, name="stage_t_states", require_full_gate=False
    )

    counts = _validate_denominator(
        stage_p,
        expected_counts=expected_counts,
        expected_seed_count=int(expected_seed_count),
        expected_worlds=tuple(expected_worlds),
    )

    # Stage-T must address exactly the same prospective cells.
    p_keys = stage_p.loc[:, _KEY].sort_values(_KEY).reset_index(drop=True)
    t_keys = stage_t.loc[:, _KEY].sort_values(_KEY).reset_index(drop=True)
    if not p_keys.equals(t_keys):
        raise ValueError("Stage-P and Stage-T prospective cells do not align")

    p_positive_target = stage_p["odo_state"].isin(_POSITIVE)
    p_replaceable_target = stage_p["odo_state"].eq("replaceable")
    p_unresolved_target = stage_p["odo_state"].eq("unresolved")
    p_unavailable_target = stage_p["odo_state"].eq("unavailable")
    p_finite_positive = stage_p["finite_state"].isin(_POSITIVE)
    p_finite_sharp = stage_p["finite_state"].isin(_SHARP)
    p_refusal = stage_p["structural_refusal_expected"].astype(bool)

    positive_recovery = _rate(p_finite_positive, p_positive_target)
    false_positive_rate = _rate(p_finite_positive, p_replaceable_target)
    overresolution_rate = _rate(p_finite_sharp, p_unresolved_target)
    structural_refusal_violation = _rate(p_finite_sharp, p_refusal)
    unavailable_sharp_rate = _rate(p_finite_sharp, p_unavailable_target)
    unavailable_favorable_rate = _rate(p_finite_positive, p_unavailable_target)

    non_w7_adequacy, w7_adequacy = _full_system_rates(stage_p)

    aligned = stage_p.loc[
        :, _KEY + ["finite_state", "structural_refusal_expected"]
    ].rename(
        columns={
            "finite_state": "stage_p_state",
            "structural_refusal_expected": "stage_p_refusal",
        }
    ).merge(
        stage_t.loc[
            :, _KEY + ["finite_state", "structural_refusal_expected"]
        ].rename(
            columns={
                "finite_state": "stage_t_state",
                "structural_refusal_expected": "stage_t_refusal",
            }
        ),
        on=_KEY,
        how="inner",
        validate="one_to_one",
    )

    stage_p_positive = aligned["stage_p_state"].isin(_POSITIVE)
    if int(stage_p_positive.sum()) == 0:
        spatial_contradiction_rate = float("nan")
    else:
        spatial_contradiction_rate = float(
            aligned.loc[stage_p_positive, "stage_t_state"].eq("replaceable").mean()
        )

    spatial_refusal = aligned["stage_t_refusal"].astype(bool)
    spatial_sharp = aligned["stage_t_state"].isin(_SHARP)
    spatial_refusal_violation = _rate(spatial_sharp, spatial_refusal)
    stage_t_complete = bool(len(aligned) == len(stage_p) == len(stage_t))

    metrics = {
        "positive_recovery": positive_recovery,
        "false_positive_rate": false_positive_rate,
        "overresolution_rate": overresolution_rate,
        "structural_refusal_violation_rate": structural_refusal_violation,
        "unavailable_sharp_rate": unavailable_sharp_rate,
        "unavailable_favorable_rate": unavailable_favorable_rate,
        "non_w7_full_system_information_adequacy": non_w7_adequacy,
        "w7_full_system_information_adequacy": w7_adequacy,
        "stage_t_complete": float(stage_t_complete),
        "stage_p_positive_to_spatial_replaceable_contradiction_rate": (
            spatial_contradiction_rate
        ),
        "spatial_structural_refusal_violation_rate": spatial_refusal_violation,
    }

    kb = gate_vector["KT-B"]
    kc = gate_vector["KT-C"]
    kd = gate_vector["KT-D"]
    ke = gate_vector["KT-E"]
    kf = gate_vector["KT-F"]

    gates = {
        "KT-A": bool(provenance_complete),
        "KT-B": bool(
            math.isfinite(positive_recovery)
            and positive_recovery >= float(kb["minimum"])
        ),
        "KT-C": bool(
            math.isfinite(false_positive_rate)
            and false_positive_rate <= float(kc["maximum"])
        ),
        "KT-D": bool(
            math.isfinite(overresolution_rate)
            and overresolution_rate
            <= float(kd["max_overresolution_rate_among_odo_unresolved"])
            and math.isfinite(structural_refusal_violation)
            and structural_refusal_violation
            <= float(kd["max_structural_refusal_violation_rate"])
        ),
        "KT-E": bool(
            math.isfinite(unavailable_sharp_rate)
            and unavailable_sharp_rate
            <= float(ke["max_sharp_rate_among_odo_unavailable"])
            and math.isfinite(unavailable_favorable_rate)
            and unavailable_favorable_rate
            <= float(ke["max_favorable_positive_rate_among_odo_unavailable"])
            and non_w7_adequacy
            >= float(ke["min_non_w7_full_system_information_adequacy"])
            and w7_adequacy
            <= float(ke["max_w7_full_system_information_adequacy"])
        ),
        "KT-F": bool(
            (not bool(kf["complete_spatial_transfer_evaluation_required"]) or stage_t_complete)
            and math.isfinite(spatial_contradiction_rate)
            and spatial_contradiction_rate
            <= float(
                kf[
                    "max_stage_p_positive_to_spatial_replaceable_contradiction_rate"
                ]
            )
            and math.isfinite(spatial_refusal_violation)
            and spatial_refusal_violation
            <= float(kf["max_spatial_structural_refusal_violation_rate"])
        ),
    }

    reasons = tuple(name for name, passed in gates.items() if not passed)
    return ProspectiveKTDecision(
        passed=bool(all(gates.values())),
        gates=gates,
        metrics=metrics,
        counts=counts,
        reasons=reasons,
    )
