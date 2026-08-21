"""Candidate-independent evidence-balanced spatial folds for Product-A v2.7.1.

The current Product-A partition first creates occurrence-space blocks and later
lets ``GroupKFold`` combine them without considering whether each accessible-area
(M) background has enough rows in every evaluation fold.  This can make an
otherwise valid ecological audit impossible even when thousands of background
rows exist globally.

This successor keeps spatial microblocks atomic but assigns those microblocks to
four common outer fold IDs using only model-pool coordinates and row counts from
presence plus every predeclared M background.  Environmental values, candidate
scores, response magnitudes, process outcomes, and outer sealed rows are not
inputs.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances_argmin_min
from sklearn.model_selection import StratifiedGroupKFold

from .validation import SpatialPartition


@dataclass(frozen=True)
class EvidenceBalancedSpatialPartition:
    presence_folds: np.ndarray
    background_folds: dict[str, np.ndarray]
    presence_microblocks: np.ndarray
    background_microblocks: dict[str, np.ndarray]
    microblock_centers_xyz: np.ndarray
    microblock_to_fold: dict[int, int]
    support_ledger: pd.DataFrame
    attempt_ledger: pd.DataFrame
    selected_attempt: int
    selected_random_state: int
    n_microblocks: int
    outer_folds: int

    def for_M(self, name: str) -> SpatialPartition:
        if name not in self.background_folds:
            raise KeyError(f"unknown M partition: {name}")
        folds = tuple(range(self.outer_folds))
        return SpatialPartition(
            presence_blocks=self.presence_folds.copy(),
            background_blocks=self.background_folds[name].copy(),
            train_blocks=folds,
            test_blocks=(),
            centers_xyz=self.microblock_centers_xyz.copy(),
        )


def _unit_sphere(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    lon_r = np.deg2rad(np.asarray(lon, dtype=float))
    lat_r = np.deg2rad(np.asarray(lat, dtype=float))
    return np.column_stack(
        [
            np.cos(lat_r) * np.cos(lon_r),
            np.cos(lat_r) * np.sin(lon_r),
            np.sin(lat_r),
        ]
    )


def _resource_counts(
    presence_folds: np.ndarray,
    background_folds: Mapping[str, np.ndarray],
    *,
    outer_folds: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_presence = len(presence_folds)
    background_totals = {name: len(values) for name, values in background_folds.items()}
    for fold in range(int(outer_folds)):
        p_eval = int(np.sum(presence_folds == fold))
        row: dict[str, object] = {
            "fold": int(fold),
            "n_evaluation_occurrences": p_eval,
            "n_training_occurrences": int(total_presence - p_eval),
        }
        for name in sorted(background_folds):
            values = background_folds[name]
            eval_n = int(np.sum(values == fold))
            row[f"n_evaluation_background__{name}"] = eval_n
            row[f"n_training_background__{name}"] = int(background_totals[name] - eval_n)
        rows.append(row)
    return pd.DataFrame(rows)


def _support_flags(
    ledger: pd.DataFrame,
    M_names: Sequence[str],
    *,
    minimum_evaluation_occurrences: int,
    minimum_evaluation_background_rows: int,
    minimum_training_background_rows: int,
) -> pd.DataFrame:
    result = ledger.copy()
    result["occurrence_supported"] = (
        pd.to_numeric(result["n_evaluation_occurrences"], errors="coerce")
        >= int(minimum_evaluation_occurrences)
    )
    for name in M_names:
        result[f"evaluation_background_supported__{name}"] = (
            pd.to_numeric(result[f"n_evaluation_background__{name}"], errors="coerce")
            >= int(minimum_evaluation_background_rows)
        )
        result[f"training_background_supported__{name}"] = (
            pd.to_numeric(result[f"n_training_background__{name}"], errors="coerce")
            >= int(minimum_training_background_rows)
        )
    support_cols = ["occurrence_supported"] + [
        column
        for name in M_names
        for column in (
            f"evaluation_background_supported__{name}",
            f"training_background_supported__{name}",
        )
    ]
    result["structural_support_complete"] = result[support_cols].all(axis=1)
    return result


def _imbalance_score(ledger: pd.DataFrame, M_names: Sequence[str]) -> tuple[float, float]:
    resources = ["n_evaluation_occurrences"] + [
        f"n_evaluation_background__{name}" for name in M_names
    ]
    deviations: list[float] = []
    for column in resources:
        values = pd.to_numeric(ledger[column], errors="coerce").to_numpy(float)
        target = float(values.sum() / len(values)) if len(values) else 0.0
        if target <= 0:
            deviations.extend([float("inf")] * len(values))
        else:
            deviations.extend(np.abs(values - target) / target)
    finite = np.asarray(deviations, dtype=float)
    return float(np.nanmax(finite)), float(np.nanmean(finite))


def _canonical_assignment_key(mapping: Mapping[int, int]) -> tuple[int, ...]:
    # Relabel folds by first microblock appearance so label permutations do not
    # create arbitrary ties between otherwise identical assignments.
    remap: dict[int, int] = {}
    next_label = 0
    key: list[int] = []
    for block in sorted(mapping):
        fold = int(mapping[block])
        if fold not in remap:
            remap[fold] = next_label
            next_label += 1
        key.append(remap[fold])
    return tuple(key)


def assign_microblocks_to_evidence_balanced_folds(
    presence_microblocks: Sequence[int] | np.ndarray,
    background_microblocks: Mapping[str, Sequence[int] | np.ndarray],
    *,
    outer_folds: int = 4,
    minimum_evaluation_occurrences: int = 2,
    minimum_evaluation_background_rows: int = 5,
    minimum_training_background_rows: int = 5,
    assignment_attempts: int = 32,
    random_state: int = 0,
) -> tuple[dict[int, int], pd.DataFrame, pd.DataFrame, int, int]:
    """Assign atomic spatial microblocks to fold IDs using row counts only."""

    p_micro = np.asarray(presence_microblocks, dtype=int)
    bg_micro = {
        str(name): np.asarray(values, dtype=int)
        for name, values in background_microblocks.items()
    }
    if int(outer_folds) < 2:
        raise ValueError("outer_folds must be >= 2")
    if int(assignment_attempts) < 1:
        raise ValueError("assignment_attempts must be >= 1")
    blocks = tuple(sorted(set(p_micro.tolist())))
    if len(blocks) < int(outer_folds):
        raise ValueError("not enough spatial microblocks for requested outer folds")
    if any(set(values.tolist()) - set(blocks) for values in bg_micro.values()):
        raise ValueError("background microblock labels must derive from occurrence microblocks")
    M_names = tuple(sorted(bg_micro))
    if not M_names:
        raise ValueError("at least one M background is required")

    # Pseudo-samples expose only resource type and atomic microblock identity to
    # StratifiedGroupKFold.  No environmental values enter the assignment.
    y: list[str] = ["presence"] * len(p_micro)
    groups: list[int] = p_micro.tolist()
    for name in M_names:
        values = bg_micro[name]
        y.extend([f"background::{name}"] * len(values))
        groups.extend(values.tolist())
    y_array = np.asarray(y, dtype=object)
    group_array = np.asarray(groups, dtype=int)
    X_dummy = np.zeros((len(group_array), 1), dtype=float)

    attempts: list[dict[str, object]] = []
    feasible: list[
        tuple[tuple[float, float, tuple[int, ...]], dict[int, int], pd.DataFrame, int, int]
    ] = []
    for attempt in range(int(assignment_attempts)):
        attempt_seed = int(random_state) + int(attempt)
        splitter = StratifiedGroupKFold(
            n_splits=int(outer_folds),
            shuffle=True,
            random_state=attempt_seed,
        )
        mapping: dict[int, int] = {}
        for fold, (_, test_idx) in enumerate(
            splitter.split(X_dummy, y_array, groups=group_array)
        ):
            for block in np.unique(group_array[test_idx]):
                block = int(block)
                old = mapping.get(block)
                if old is not None and old != fold:
                    raise AssertionError("a spatial microblock was assigned to multiple folds")
                mapping[block] = int(fold)
        if set(mapping) != set(blocks):
            raise AssertionError("not every occurrence microblock received a fold")
        p_folds = np.asarray([mapping[int(x)] for x in p_micro], dtype=int)
        bg_folds = {
            name: np.asarray([mapping[int(x)] for x in values], dtype=int)
            for name, values in bg_micro.items()
        }
        ledger = _support_flags(
            _resource_counts(p_folds, bg_folds, outer_folds=int(outer_folds)),
            M_names,
            minimum_evaluation_occurrences=int(minimum_evaluation_occurrences),
            minimum_evaluation_background_rows=int(minimum_evaluation_background_rows),
            minimum_training_background_rows=int(minimum_training_background_rows),
        )
        supported = bool(ledger["structural_support_complete"].all())
        max_imbalance, mean_imbalance = _imbalance_score(ledger, M_names)
        canonical = _canonical_assignment_key(mapping)
        attempts.append(
            {
                "attempt": int(attempt),
                "random_state": attempt_seed,
                "structural_support_complete": supported,
                "n_supported_folds": int(ledger["structural_support_complete"].sum()),
                "max_normalized_imbalance": max_imbalance,
                "mean_normalized_imbalance": mean_imbalance,
                "microblock_to_fold": ",".join(
                    f"{block}:{mapping[block]}" for block in sorted(mapping)
                ),
            }
        )
        if supported:
            feasible.append(
                (
                    (max_imbalance, mean_imbalance, canonical),
                    mapping,
                    ledger,
                    int(attempt),
                    attempt_seed,
                )
            )
    if not feasible:
        attempt_frame = pd.DataFrame(attempts)
        best = attempt_frame.sort_values(
            ["n_supported_folds", "max_normalized_imbalance", "mean_normalized_imbalance", "attempt"],
            ascending=[False, True, True, True],
            kind="mergesort",
        ).iloc[0]
        raise ValueError(
            "no evidence-balanced spatial assignment satisfies the frozen row-count "
            f"support constraints after {assignment_attempts} attempts; "
            f"best_supported_folds={int(best['n_supported_folds'])}/{outer_folds}"
        )
    feasible.sort(key=lambda item: item[0])
    _, mapping, ledger, attempt, attempt_seed = feasible[0]
    return mapping, ledger.reset_index(drop=True), pd.DataFrame(attempts), attempt, attempt_seed


def make_evidence_balanced_spatial_partitions(
    presence_longitude: Sequence[float],
    presence_latitude: Sequence[float],
    backgrounds: Mapping[str, tuple[Sequence[float], Sequence[float]]],
    *,
    n_microblocks: int = 12,
    outer_folds: int = 4,
    minimum_evaluation_occurrences: int = 2,
    minimum_evaluation_background_rows: int = 5,
    minimum_training_background_rows: int = 5,
    assignment_attempts: int = 32,
    random_state: int = 0,
) -> EvidenceBalancedSpatialPartition:
    """Create one occurrence fold assignment shared across all M backgrounds."""

    p_xyz = _unit_sphere(
        np.asarray(presence_longitude, dtype=float),
        np.asarray(presence_latitude, dtype=float),
    )
    if len(p_xyz) < int(outer_folds):
        raise ValueError("not enough model-pool occurrences for outer folds")
    n_micro = min(int(n_microblocks), len(p_xyz))
    if n_micro < int(outer_folds):
        raise ValueError("n_microblocks must allow at least outer_folds atomic groups")
    km = KMeans(n_clusters=n_micro, random_state=int(random_state), n_init=10)
    p_micro = km.fit_predict(p_xyz).astype(int)
    bg_micro: dict[str, np.ndarray] = {}
    for name in sorted(backgrounds):
        lon, lat = backgrounds[name]
        b_xyz = _unit_sphere(np.asarray(lon, dtype=float), np.asarray(lat, dtype=float))
        labels, _ = pairwise_distances_argmin_min(b_xyz, km.cluster_centers_)
        bg_micro[str(name)] = labels.astype(int)

    mapping, ledger, attempts, selected_attempt, selected_seed = (
        assign_microblocks_to_evidence_balanced_folds(
            p_micro,
            bg_micro,
            outer_folds=int(outer_folds),
            minimum_evaluation_occurrences=int(minimum_evaluation_occurrences),
            minimum_evaluation_background_rows=int(minimum_evaluation_background_rows),
            minimum_training_background_rows=int(minimum_training_background_rows),
            assignment_attempts=int(assignment_attempts),
            random_state=int(random_state),
        )
    )
    p_folds = np.asarray([mapping[int(x)] for x in p_micro], dtype=int)
    bg_folds = {
        name: np.asarray([mapping[int(x)] for x in values], dtype=int)
        for name, values in bg_micro.items()
    }
    if set(np.unique(p_folds)) != set(range(int(outer_folds))):
        raise AssertionError("evidence-balanced occurrence folds are incomplete")
    for name, values in bg_folds.items():
        if not set(np.unique(values)).issubset(set(range(int(outer_folds)))):
            raise AssertionError(f"evidence-balanced background folds invalid for {name}")
    return EvidenceBalancedSpatialPartition(
        presence_folds=p_folds,
        background_folds=bg_folds,
        presence_microblocks=p_micro,
        background_microblocks=bg_micro,
        microblock_centers_xyz=km.cluster_centers_.copy(),
        microblock_to_fold=dict(mapping),
        support_ledger=ledger,
        attempt_ledger=attempts,
        selected_attempt=int(selected_attempt),
        selected_random_state=int(selected_seed),
        n_microblocks=int(n_micro),
        outer_folds=int(outer_folds),
    )
