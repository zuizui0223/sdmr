"""Selected nonlinear finite-recovery retest against frozen ODO v2 states."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from collections.abc import Sequence

import pandas as pd

from ..evidence import evaluate_occurrence_processes
from .occurrence_oracle import evaluate_occurrence_oracle_states
from .worlds import KNOWN_TRUTH_WORLDS, simulate_process_world


_POSITIVE = {"contributory", "required"}
_SHARP = {"replaceable", "contributory", "required"}


@dataclass(frozen=True)
class SelectedRecoveryResult:
    states: pd.DataFrame
    metrics: pd.DataFrame
    odo_state_hash: str


def canonical_odo_state_hash(states: pd.DataFrame) -> str:
    """Hash the canonical world/seed/process/state ODO target table."""

    required = {"world", "seed", "process", "state"}
    missing = sorted(required - set(states.columns))
    if missing:
        raise KeyError(f"ODO state table missing columns: {missing}")
    data = states.loc[:, ["world", "seed", "process", "state"]].copy()
    if data.duplicated(["world", "seed", "process"]).any():
        raise ValueError("ODO state table contains duplicate world/seed/process cells")
    data = data.sort_values(
        ["world", "seed", "process"], kind="mergesort"
    ).reset_index(drop=True)
    payload = data.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ratio(num: int, den: int) -> float:
    return float(num / den) if den > 0 else float("nan")


def summarize_selected_recovery(rows: pd.DataFrame) -> pd.DataFrame:
    """Summarize recovery and safety separately for each learner × split mode."""

    required = {
        "learner",
        "split_mode",
        "odo_state",
        "finite_state",
        "full_log_score",
        "delta_mean",
        "delta_sem",
    }
    missing = sorted(required - set(rows.columns))
    if missing:
        raise KeyError(f"selected recovery rows missing columns: {missing}")

    result = []
    for (learner, split_mode), group in rows.groupby(
        ["learner", "split_mode"], sort=True
    ):
        positive = group["odo_state"].isin(_POSITIVE)
        replaceable = group["odo_state"].eq("replaceable")
        unresolved = group["odo_state"].eq("unresolved")
        finite_positive = group["finite_state"].isin(_POSITIVE)
        finite_sharp = group["finite_state"].isin(_SHARP)
        unavailable = group["finite_state"].eq("unavailable")
        finite_unresolved = group["finite_state"].eq("unresolved")
        result.append(
            {
                "learner": str(learner),
                "split_mode": str(split_mode),
                "positive_recovery": _ratio(
                    int((positive & finite_positive).sum()), int(positive.sum())
                ),
                "positive_unavailable_rate": _ratio(
                    int((positive & unavailable).sum()), int(positive.sum())
                ),
                "positive_unresolved_rate": _ratio(
                    int((positive & finite_unresolved).sum()), int(positive.sum())
                ),
                "false_positive_rate": _ratio(
                    int((replaceable & finite_positive).sum()),
                    int(replaceable.sum()),
                ),
                "overresolution_rate": _ratio(
                    int((unresolved & finite_sharp).sum()), int(unresolved.sum())
                ),
                "mean_positive_delta": float(
                    pd.to_numeric(group.loc[positive, "delta_mean"], errors="coerce").mean()
                ),
                "mean_positive_delta_sem": float(
                    pd.to_numeric(group.loc[positive, "delta_sem"], errors="coerce").mean()
                ),
                "mean_positive_full_log_score": float(
                    pd.to_numeric(
                        group.loc[positive, "full_log_score"], errors="coerce"
                    ).mean()
                ),
                "n_positive": int(positive.sum()),
                "n_replaceable": int(replaceable.sum()),
                "n_unresolved": int(unresolved.sum()),
            }
        )
    return pd.DataFrame(result)


def run_selected_recovery_retest(
    seeds: Sequence[int],
    *,
    worlds: Sequence[str] = KNOWN_TRUTH_WORLDS,
    learners: Sequence[str] = ("linear", "quadratic", "hgb"),
    split_modes: Sequence[str] = ("spatial", "random_cell"),
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
) -> SelectedRecoveryResult:
    """Run the selected nonlinear recovery retest on burned development worlds."""

    seed_tuple = tuple(int(x) for x in seeds)
    world_tuple = tuple(str(x) for x in worlds)
    learner_tuple = tuple(str(x) for x in learners)
    split_tuple = tuple(str(x) for x in split_modes)

    if not seed_tuple or len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("seeds must be non-empty and unique")
    if not world_tuple or len(set(world_tuple)) != len(world_tuple):
        raise ValueError("worlds must be non-empty and unique")
    unknown_worlds = sorted(set(world_tuple) - set(KNOWN_TRUTH_WORLDS))
    if unknown_worlds:
        raise ValueError(f"unknown worlds: {unknown_worlds}")
    if not learner_tuple or len(set(learner_tuple)) != len(learner_tuple):
        raise ValueError("learners must be non-empty and unique")
    unknown_learners = sorted(set(learner_tuple) - {"linear", "quadratic", "hgb"})
    if unknown_learners:
        raise ValueError(f"unknown learners: {unknown_learners}")
    if not split_tuple or len(set(split_tuple)) != len(split_tuple):
        raise ValueError("split_modes must be non-empty and unique")
    unknown_splits = sorted(set(split_tuple) - {"spatial", "random_cell"})
    if unknown_splits:
        raise ValueError(f"unknown split modes: {unknown_splits}")

    state_frames: list[pd.DataFrame] = []
    odo_frames: list[pd.DataFrame] = []

    for world_name in world_tuple:
        for ecological_seed in seed_tuple:
            world = simulate_process_world(
                world_name,
                seed=ecological_seed,
                n_cells=int(n_cells),
                n_occurrences=int(n_occurrences),
                n_background=int(n_background),
            )
            odo = evaluate_occurrence_oracle_states(
                world,
                n_splits=int(n_splits),
                margin=float(odo_margin),
                sem_multiplier=float(odo_sem_multiplier),
                adequacy_floor=float(odo_adequacy_floor),
                approximation_tolerance=float(odo_approximation_tolerance),
                split_mode="random",
            ).states
            odo_key = odo.loc[:, ["process", "state"]].copy()
            odo_key.insert(0, "seed", int(ecological_seed))
            odo_key.insert(0, "world", world_name)
            odo_frames.append(odo_key)

            odo_target = odo.loc[:, ["process", "state"]].rename(
                columns={"state": "odo_state"}
            )
            for split_mode in split_tuple:
                for learner in learner_tuple:
                    finite = evaluate_occurrence_processes(
                        world,
                        n_splits=int(n_splits),
                        margin=float(finite_margin),
                        adequacy_floor=float(finite_adequacy_floor),
                        sem_multiplier=float(finite_sem_multiplier),
                        C=float(logistic_C),
                        learner=learner,
                        split_mode=split_mode,
                        hgb_profile=hgb_profile if learner == "hgb" else "current",
                    ).states
                    merged = odo_target.merge(
                        finite,
                        on="process",
                        how="left",
                        validate="one_to_one",
                    ).rename(columns={"state": "finite_state"})
                    merged.insert(0, "learner", learner)
                    merged.insert(0, "seed", int(ecological_seed))
                    merged.insert(0, "world", world_name)
                    state_frames.append(merged)

    odo_states = pd.concat(odo_frames, ignore_index=True)
    odo_hash = canonical_odo_state_hash(odo_states)
    if expected_odo_state_hash is not None and odo_hash != str(expected_odo_state_hash):
        raise ValueError(
            "ODO state hash drift: "
            f"expected {expected_odo_state_hash}, observed {odo_hash}"
        )

    states = pd.concat(state_frames, ignore_index=True)
    metrics = summarize_selected_recovery(states)
    return SelectedRecoveryResult(
        states=states,
        metrics=metrics,
        odo_state_hash=odo_hash,
    )
