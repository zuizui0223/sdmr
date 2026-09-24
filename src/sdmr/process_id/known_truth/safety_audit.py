"""Development-only 8x safety audit for the selected shallow3 SDMR route."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import pandas as pd

from ..evidence import evaluate_occurrence_processes
from .occurrence_oracle import evaluate_occurrence_oracle_states
from .resampling import resample_world_observations
from .selected_power import _sampling_seed
from .selected_recovery import canonical_odo_state_hash
from .worlds import KNOWN_TRUTH_WORLDS, simulate_process_world


_POSITIVE = {"contributory", "required"}
_SHARP = {"replaceable", "contributory", "required"}


@dataclass(frozen=True)
class SafetyAuditResult:
    states: pd.DataFrame
    metrics: pd.DataFrame
    odo_state_hash: str


def structural_refusal_expected(world: str, process: str) -> bool:
    """Return whether the declared architecture requires an unresolved state."""

    world = str(world)
    process = str(process)
    if world == "observation_confounded" and process == "thermal":
        return True
    if world == "shared_carrier" and process in {"thermal", "water"}:
        return True
    return False


def _ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator > 0 else float("nan")


def summarize_safety(rows: pd.DataFrame) -> pd.DataFrame:
    """Summarize recovery, specificity and abstention by split mode."""

    required = {
        "split_mode",
        "odo_state",
        "finite_state",
        "structural_refusal_expected",
    }
    missing = sorted(required - set(rows.columns))
    if missing:
        raise KeyError(f"safety rows missing columns: {missing}")

    result = []
    for split_mode, group in rows.groupby("split_mode", sort=True):
        odo_positive = group["odo_state"].isin(_POSITIVE)
        odo_replaceable = group["odo_state"].eq("replaceable")
        odo_unresolved = group["odo_state"].eq("unresolved")
        odo_unavailable = group["odo_state"].eq("unavailable")

        finite_positive = group["finite_state"].isin(_POSITIVE)
        finite_sharp = group["finite_state"].isin(_SHARP)
        finite_unavailable = group["finite_state"].eq("unavailable")
        finite_unresolved = group["finite_state"].eq("unresolved")

        refusal = group["structural_refusal_expected"].astype(bool)
        refusal_sharp = refusal & finite_sharp

        result.append(
            {
                "split_mode": str(split_mode),
                "positive_recovery": _ratio(
                    int((odo_positive & finite_positive).sum()),
                    int(odo_positive.sum()),
                ),
                "false_positive_rate": _ratio(
                    int((odo_replaceable & finite_positive).sum()),
                    int(odo_replaceable.sum()),
                ),
                "overresolution_rate": _ratio(
                    int((odo_unresolved & finite_sharp).sum()),
                    int(odo_unresolved.sum()),
                ),
                "unavailable_favorable_rate": _ratio(
                    int((odo_unavailable & finite_positive).sum()),
                    int(odo_unavailable.sum()),
                ),
                "unavailable_sharp_rate": _ratio(
                    int((odo_unavailable & finite_sharp).sum()),
                    int(odo_unavailable.sum()),
                ),
                "structural_refusal_violation_rate": _ratio(
                    int(refusal_sharp.sum()),
                    int(refusal.sum()),
                ),
                "structural_refusal_unresolved_rate": _ratio(
                    int((refusal & finite_unresolved).sum()),
                    int(refusal.sum()),
                ),
                "positive_unavailable_rate": _ratio(
                    int((odo_positive & finite_unavailable).sum()),
                    int(odo_positive.sum()),
                ),
                "replaceable_unavailable_rate": _ratio(
                    int((odo_replaceable & finite_unavailable).sum()),
                    int(odo_replaceable.sum()),
                ),
                "unresolved_unavailable_rate": _ratio(
                    int((odo_unresolved & finite_unavailable).sum()),
                    int(odo_unresolved.sum()),
                ),
                "n_positive": int(odo_positive.sum()),
                "n_replaceable": int(odo_replaceable.sum()),
                "n_unresolved": int(odo_unresolved.sum()),
                "n_unavailable": int(odo_unavailable.sum()),
                "n_structural_refusal": int(refusal.sum()),
            }
        )
    return pd.DataFrame(result)


def _validate_unique(values: Sequence, *, name: str):
    result = tuple(values)
    if not result or len(set(result)) != len(result):
        raise ValueError(f"{name} must be non-empty and unique")
    return result


def run_8x_safety_audit(
    seeds: Sequence[int],
    *,
    worlds: Sequence[str] = KNOWN_TRUTH_WORLDS,
    split_modes: Sequence[str] = ("spatial", "random_cell"),
    sampling_replicates: Sequence[int] = (0, 1, 2),
    multiplier: int = 8,
    n_cells: int = 1600,
    n_occurrences: int = 180,
    n_background: int = 600,
    n_splits: int = 3,
    hgb_profile: str = "shallow3",
    odo_margin: float = 0.01,
    odo_sem_multiplier: float = 1.0,
    odo_adequacy_floor: float = -0.75,
    odo_approximation_tolerance: float = 0.01,
    finite_margin: float = 0.01,
    finite_sem_multiplier: float = 1.0,
    finite_adequacy_floor: float = -0.75,
    logistic_C: float = 1.0,
    expected_odo_state_hash: str | None = None,
) -> SafetyAuditResult:
    """Run the full-state 8x safety audit on burned development worlds."""

    seed_tuple = _validate_unique(tuple(int(x) for x in seeds), name="seeds")
    world_tuple = _validate_unique(tuple(str(x) for x in worlds), name="worlds")
    split_tuple = _validate_unique(
        tuple(str(x) for x in split_modes), name="split_modes"
    )
    replicate_tuple = _validate_unique(
        tuple(int(x) for x in sampling_replicates), name="sampling_replicates"
    )
    multiplier = int(multiplier)

    unknown_worlds = sorted(set(world_tuple) - set(KNOWN_TRUTH_WORLDS))
    if unknown_worlds:
        raise ValueError(f"unknown worlds: {unknown_worlds}")
    unknown_splits = sorted(set(split_tuple) - {"spatial", "random_cell"})
    if unknown_splits:
        raise ValueError(f"unknown split modes: {unknown_splits}")
    if multiplier <= 0:
        raise ValueError("multiplier must be positive")
    if str(hgb_profile) != "shallow3":
        raise ValueError("8x safety audit requires frozen shallow3 profile")

    worlds_by_key = {}
    odo_frames: list[pd.DataFrame] = []

    # Reconstruct and verify the frozen population target before resampling.
    for world_name in world_tuple:
        for ecological_seed in seed_tuple:
            world = simulate_process_world(
                world_name,
                seed=ecological_seed,
                n_cells=int(n_cells),
                n_occurrences=int(n_occurrences),
                n_background=int(n_background),
            )
            worlds_by_key[(world_name, ecological_seed)] = world
            odo = evaluate_occurrence_oracle_states(
                world,
                n_splits=int(n_splits),
                margin=float(odo_margin),
                sem_multiplier=float(odo_sem_multiplier),
                adequacy_floor=float(odo_adequacy_floor),
                approximation_tolerance=float(odo_approximation_tolerance),
                split_mode="random",
            ).states
            keyed = odo.loc[:, ["process", "state"]].copy()
            keyed.insert(0, "seed", int(ecological_seed))
            keyed.insert(0, "world", world_name)
            odo_frames.append(keyed)

    odo_states = pd.concat(odo_frames, ignore_index=True)
    odo_hash = canonical_odo_state_hash(odo_states)
    if expected_odo_state_hash is not None and odo_hash != str(expected_odo_state_hash):
        raise ValueError(
            "ODO state hash drift: "
            f"expected {expected_odo_state_hash}, observed {odo_hash}"
        )

    state_frames: list[pd.DataFrame] = []
    for world_index, world_name in enumerate(world_tuple):
        for ecological_seed in seed_tuple:
            world = worlds_by_key[(world_name, ecological_seed)]
            odo_target = odo_states.loc[
                odo_states["world"].eq(world_name)
                & odo_states["seed"].eq(ecological_seed),
                ["process", "state"],
            ].rename(columns={"state": "odo_state"})

            for replicate in replicate_tuple:
                sampling_seed = _sampling_seed(
                    ecological_seed, world_index, multiplier, replicate
                )
                sampled = resample_world_observations(
                    world,
                    n_occurrences=int(n_occurrences) * multiplier,
                    n_background=int(n_background) * multiplier,
                    sampling_seed=sampling_seed,
                )
                for split_mode in split_tuple:
                    finite = evaluate_occurrence_processes(
                        sampled,
                        n_splits=int(n_splits),
                        margin=float(finite_margin),
                        adequacy_floor=float(finite_adequacy_floor),
                        sem_multiplier=float(finite_sem_multiplier),
                        C=float(logistic_C),
                        learner="hgb",
                        split_mode=split_mode,
                        hgb_profile=str(hgb_profile),
                    ).states
                    merged = odo_target.merge(
                        finite,
                        on="process",
                        how="left",
                        validate="one_to_one",
                    ).rename(columns={"state": "finite_state"})
                    merged.insert(
                        0,
                        "structural_refusal_expected",
                        [
                            structural_refusal_expected(world_name, process)
                            for process in merged["process"].astype(str)
                        ],
                    )
                    if "hgb_profile" not in merged.columns:
                        raise ValueError("finite safety states missing hgb_profile")
                    if set(merged["hgb_profile"].astype(str)) != {str(hgb_profile)}:
                        raise ValueError("finite safety HGB profile drift")
                    merged.insert(0, "replicate", int(replicate))
                    merged.insert(0, "multiplier", multiplier)
                    merged.insert(0, "seed", int(ecological_seed))
                    merged.insert(0, "world", world_name)
                    state_frames.append(merged)

    states = pd.concat(state_frames, ignore_index=True)
    metrics = summarize_safety(states)
    return SafetyAuditResult(
        states=states,
        metrics=metrics,
        odo_state_hash=odo_hash,
    )
