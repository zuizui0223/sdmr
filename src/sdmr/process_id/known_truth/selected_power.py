"""Development-only shallow3 positive-recovery sample-size curve."""
from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Sequence

import pandas as pd

from ..evidence import evaluate_occurrence_processes
from .occurrence_oracle import evaluate_occurrence_oracle_states
from .resampling import resample_world_observations
from .selected_recovery import canonical_odo_state_hash
from .worlds import KNOWN_TRUTH_WORLDS, KnownTruthWorld, simulate_process_world


_POSITIVE = {"contributory", "required"}


@dataclass(frozen=True)
class SelectedPowerResult:
    states: pd.DataFrame
    metrics: pd.DataFrame
    odo_state_hash: str


def summarize_selected_power(rows: pd.DataFrame) -> pd.DataFrame:
    """Summarize positive-denominator recovery by split mode and sample multiplier."""

    required = {
        "split_mode",
        "multiplier",
        "finite_state",
        "delta_mean",
        "delta_sem",
        "full_log_score",
    }
    missing = sorted(required - set(rows.columns))
    if missing:
        raise KeyError(f"selected power rows missing columns: {missing}")

    result = []
    for (split_mode, multiplier), group in rows.groupby(
        ["split_mode", "multiplier"], sort=True
    ):
        positive = group["finite_state"].isin(_POSITIVE)
        unresolved = group["finite_state"].eq("unresolved")
        replaceable = group["finite_state"].eq("replaceable")
        unavailable = group["finite_state"].eq("unavailable")
        result.append(
            {
                "split_mode": str(split_mode),
                "multiplier": int(multiplier),
                "positive_recovery": float(positive.mean()),
                "unresolved_rate": float(unresolved.mean()),
                "replaceable_rate": float(replaceable.mean()),
                "unavailable_rate": float(unavailable.mean()),
                "mean_delta": float(
                    pd.to_numeric(group["delta_mean"], errors="coerce").mean()
                ),
                "mean_delta_sem": float(
                    pd.to_numeric(group["delta_sem"], errors="coerce").mean()
                ),
                "mean_full_log_score": float(
                    pd.to_numeric(group["full_log_score"], errors="coerce").mean()
                ),
                "n_rows": int(len(group)),
            }
        )
    return pd.DataFrame(result)


def _sampling_seed(
    ecological_seed: int,
    world_index: int,
    multiplier: int,
    replicate: int,
) -> int:
    return (
        int(ecological_seed) * 100000
        + (int(world_index) + 1) * 1000
        + int(multiplier) * 100
        + int(replicate)
    )


def _validate_unique(values: Sequence, *, name: str):
    result = tuple(values)
    if not result or len(set(result)) != len(result):
        raise ValueError(f"{name} must be non-empty and unique")
    return result


def run_selected_power_curve(
    seeds: Sequence[int],
    *,
    worlds: Sequence[str] = KNOWN_TRUTH_WORLDS,
    split_modes: Sequence[str] = ("spatial", "random_cell"),
    sample_multipliers: Sequence[int] = (1, 2, 4),
    sampling_replicates: Sequence[int] = (0, 1, 2),
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
) -> SelectedPowerResult:
    """Run the shallow3 finite positive-recovery power curve on burned worlds."""

    seed_tuple = _validate_unique(tuple(int(x) for x in seeds), name="seeds")
    world_tuple = _validate_unique(tuple(str(x) for x in worlds), name="worlds")
    split_tuple = _validate_unique(
        tuple(str(x) for x in split_modes), name="split_modes"
    )
    multiplier_tuple = _validate_unique(
        tuple(int(x) for x in sample_multipliers), name="sample_multipliers"
    )
    replicate_tuple = _validate_unique(
        tuple(int(x) for x in sampling_replicates), name="sampling_replicates"
    )

    unknown_worlds = sorted(set(world_tuple) - set(KNOWN_TRUTH_WORLDS))
    if unknown_worlds:
        raise ValueError(f"unknown worlds: {unknown_worlds}")
    unknown_splits = sorted(set(split_tuple) - {"spatial", "random_cell"})
    if unknown_splits:
        raise ValueError(f"unknown split modes: {unknown_splits}")
    if any(x <= 0 for x in multiplier_tuple):
        raise ValueError("sample_multipliers must be positive")

    worlds_by_key: dict[tuple[str, int], KnownTruthWorld] = {}
    positive_by_key: dict[tuple[str, int], tuple[str, ...]] = {}
    odo_frames: list[pd.DataFrame] = []

    # First freeze/verify the ODO population target before any finite resampling.
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
            positive_by_key[(world_name, ecological_seed)] = tuple(
                odo.loc[odo["state"].isin(_POSITIVE), "process"].astype(str)
            )

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
            positive_processes = positive_by_key[(world_name, ecological_seed)]
            if not positive_processes:
                continue

            world = worlds_by_key[(world_name, ecological_seed)]
            focused_world = replace(world, process_universe=positive_processes)
            odo_target = odo_states.loc[
                odo_states["world"].eq(world_name)
                & odo_states["seed"].eq(ecological_seed)
                & odo_states["process"].isin(positive_processes),
                ["process", "state"],
            ].rename(columns={"state": "odo_state"})

            for multiplier in multiplier_tuple:
                for replicate in replicate_tuple:
                    sampling_seed = _sampling_seed(
                        ecological_seed, world_index, multiplier, replicate
                    )
                    sampled = resample_world_observations(
                        focused_world,
                        n_occurrences=int(n_occurrences) * int(multiplier),
                        n_background=int(n_background) * int(multiplier),
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
                        merged.insert(0, "hgb_profile", str(hgb_profile))
                        merged.insert(0, "replicate", int(replicate))
                        merged.insert(0, "multiplier", int(multiplier))
                        merged.insert(0, "seed", int(ecological_seed))
                        merged.insert(0, "world", world_name)
                        state_frames.append(merged)

    states = (
        pd.concat(state_frames, ignore_index=True)
        if state_frames
        else pd.DataFrame()
    )
    metrics = summarize_selected_power(states) if not states.empty else pd.DataFrame()
    return SelectedPowerResult(
        states=states,
        metrics=metrics,
        odo_state_hash=odo_hash,
    )
