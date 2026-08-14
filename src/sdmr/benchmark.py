"""Core within-species and cross-taxon benchmark workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from .aggregate import aggregate_predictor_selection, choose_common_predictors
from .model import evaluate_predictor_set
from .selection import forward_select_predictors
from .validation import make_spatial_partition


@dataclass
class SpeciesBenchmarkResult:
    species: str
    selected_predictors: list[str]
    selection_trace: pd.DataFrame
    candidate_trace: pd.DataFrame
    outer_metrics: pd.DataFrame
    train_blocks: tuple[int, ...]
    test_blocks: tuple[int, ...]


@dataclass
class TaxonSplitBenchmarkResult:
    discovery_species: list[str]
    validation_species: list[str]
    common_predictors: list[str]
    predictor_aggregate: pd.DataFrame
    discovery_selection: pd.DataFrame
    discovery_outer: pd.DataFrame
    validation_outer: pd.DataFrame


def _subset_species(frame: pd.DataFrame, species: str, species_col: str) -> pd.DataFrame:
    return frame.loc[frame[species_col].astype(str) == str(species)].reset_index(drop=True)


def _partition_frames(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    *,
    lon_col: str,
    lat_col: str,
    n_blocks: int,
    holdout_fraction: float,
    random_state: int,
):
    part = make_spatial_partition(
        presence[lon_col].to_numpy(float),
        presence[lat_col].to_numpy(float),
        background[lon_col].to_numpy(float),
        background[lat_col].to_numpy(float),
        n_blocks=n_blocks,
        holdout_fraction=holdout_fraction,
        random_state=random_state,
    )
    p_train_mask = np.isin(part.presence_blocks, part.train_blocks)
    p_test_mask = np.isin(part.presence_blocks, part.test_blocks)
    b_train_mask = np.isin(part.background_blocks, part.train_blocks)
    b_test_mask = np.isin(part.background_blocks, part.test_blocks)
    return part, p_train_mask, p_test_mask, b_train_mask, b_test_mask


def benchmark_species(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    candidate_predictors: Sequence[str],
    *,
    species: str = "species",
    species_col: str = "species",
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    holdout_fraction: float = 0.5,
    n_spatial_blocks: int = 8,
    inner_folds: int = 4,
    min_gain: float = 0.005,
    max_predictors: int | None = 8,
    random_state: int = 42,
) -> SpeciesBenchmarkResult:
    """Discover predictors in training blocks, then score untouched outer blocks."""

    if species_col in occurrences.columns:
        p = _subset_species(occurrences, species, species_col)
    else:
        p = occurrences.reset_index(drop=True)
    if species_col in background.columns:
        b = _subset_species(background, species, species_col)
    else:
        b = background.reset_index(drop=True)
    if len(p) < 8:
        raise ValueError(f"{species}: too few occurrences ({len(p)}) for nested spatial holdout.")
    if len(b) < 8:
        raise ValueError(f"{species}: too few background rows ({len(b)}).")

    part, p_tr, p_te, b_tr, b_te = _partition_frames(
        p,
        b,
        lon_col=lon_col,
        lat_col=lat_col,
        n_blocks=n_spatial_blocks,
        holdout_fraction=holdout_fraction,
        random_state=random_state,
    )
    p_train = p.loc[p_tr].reset_index(drop=True)
    p_test = p.loc[p_te].reset_index(drop=True)
    b_train = b.loc[b_tr].reset_index(drop=True)
    b_test = b.loc[b_te].reset_index(drop=True)
    p_groups_train = part.presence_blocks[p_tr]
    b_groups_train = part.background_blocks[b_tr]

    selected, steps, candidate_trace = forward_select_predictors(
        p_train,
        b_train,
        p_groups_train,
        b_groups_train,
        candidate_predictors,
        inner_folds=inner_folds,
        min_gain=min_gain,
        max_predictors=max_predictors,
    )

    rows: list[dict[str, object]] = []
    for label, predictors in (
        ("selected", selected),
        ("all_candidates", list(candidate_predictors)),
    ):
        metrics = evaluate_predictor_set(p_train, b_train, p_test, b_test, predictors)
        rows.append(
            {
                "species": str(species),
                "model": label,
                "n_predictors": len(predictors),
                "predictors": ",".join(predictors),
                **metrics,
            }
        )

    selection_trace = pd.DataFrame(
        [
            {
                "species": str(species),
                "step": s.step,
                "predictor": s.predictor,
                "inner_presence_rank": s.score,
                "gain": s.gain,
            }
            for s in steps
        ]
    )
    if len(candidate_trace):
        candidate_trace = candidate_trace.assign(species=str(species))

    return SpeciesBenchmarkResult(
        species=str(species),
        selected_predictors=selected,
        selection_trace=selection_trace,
        candidate_trace=candidate_trace,
        outer_metrics=pd.DataFrame(rows),
        train_blocks=part.train_blocks,
        test_blocks=part.test_blocks,
    )


def _evaluate_fixed_set_for_species(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    species: str,
    predictors: Sequence[str],
    all_predictors: Sequence[str],
    *,
    species_col: str,
    lon_col: str,
    lat_col: str,
    holdout_fraction: float,
    n_spatial_blocks: int,
    random_state: int,
) -> list[dict[str, object]]:
    p = _subset_species(occurrences, species, species_col)
    b = _subset_species(background, species, species_col)
    part, p_tr, p_te, b_tr, b_te = _partition_frames(
        p,
        b,
        lon_col=lon_col,
        lat_col=lat_col,
        n_blocks=n_spatial_blocks,
        holdout_fraction=holdout_fraction,
        random_state=random_state,
    )
    p_train, p_test = p.loc[p_tr], p.loc[p_te]
    b_train, b_test = b.loc[b_tr], b.loc[b_te]
    rows: list[dict[str, object]] = []
    for model_name, pred in (("common", list(predictors)), ("all_candidates", list(all_predictors))):
        metrics = evaluate_predictor_set(p_train, b_train, p_test, b_test, pred)
        rows.append(
            {
                "species": species,
                "model": model_name,
                "n_predictors": len(pred),
                "predictors": ",".join(pred),
                **metrics,
            }
        )
    return rows


def benchmark_taxon_split(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    candidate_predictors: Sequence[str],
    *,
    species_col: str = "species",
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    taxon_holdout_fraction: float = 0.5,
    spatial_holdout_fraction: float = 0.5,
    n_spatial_blocks: int = 8,
    inner_folds: int = 4,
    min_gain: float = 0.005,
    max_predictors: int | None = 8,
    common_min_fraction: float = 0.25,
    common_top_k: int | None = 8,
    random_state: int = 42,
) -> TaxonSplitBenchmarkResult:
    """Discover a common raster set in some taxa and test it on unseen taxa.

    This creates two independent generalization barriers:
      1. within each species, whole spatial blocks are held out;
      2. the common predictor set is learned only from discovery species and is
         evaluated on validation species never used to choose that set.
    """

    species = sorted(set(occurrences[species_col].astype(str)) & set(background[species_col].astype(str)))
    if len(species) < 4:
        raise ValueError("At least four species with occurrence and background data are required.")
    if not 0 < taxon_holdout_fraction < 1:
        raise ValueError("taxon_holdout_fraction must be between 0 and 1.")

    rng = np.random.default_rng(random_state)
    shuffled = np.array(species, dtype=object)
    rng.shuffle(shuffled)
    n_validation = max(1, int(round(len(shuffled) * taxon_holdout_fraction)))
    n_validation = min(n_validation, len(shuffled) - 1)
    validation_species = sorted(str(x) for x in shuffled[:n_validation])
    discovery_species = sorted(str(x) for x in shuffled[n_validation:])

    discovery_selection_frames: list[pd.DataFrame] = []
    discovery_outer_frames: list[pd.DataFrame] = []
    for i, sp in enumerate(discovery_species):
        result = benchmark_species(
            occurrences,
            background,
            candidate_predictors,
            species=sp,
            species_col=species_col,
            lon_col=lon_col,
            lat_col=lat_col,
            holdout_fraction=spatial_holdout_fraction,
            n_spatial_blocks=n_spatial_blocks,
            inner_folds=inner_folds,
            min_gain=min_gain,
            max_predictors=max_predictors,
            random_state=random_state + i,
        )
        discovery_selection_frames.append(result.selection_trace)
        discovery_outer_frames.append(result.outer_metrics)

    discovery_selection = pd.concat(discovery_selection_frames, ignore_index=True)
    discovery_outer = pd.concat(discovery_outer_frames, ignore_index=True)
    aggregate = aggregate_predictor_selection(discovery_selection)
    common = choose_common_predictors(
        aggregate,
        min_fraction=common_min_fraction,
        top_k=common_top_k,
    )
    if not common:
        raise ValueError("Discovery taxa did not yield a common predictor set.")

    validation_rows: list[dict[str, object]] = []
    for i, sp in enumerate(validation_species):
        validation_rows.extend(
            _evaluate_fixed_set_for_species(
                occurrences,
                background,
                sp,
                common,
                candidate_predictors,
                species_col=species_col,
                lon_col=lon_col,
                lat_col=lat_col,
                holdout_fraction=spatial_holdout_fraction,
                n_spatial_blocks=n_spatial_blocks,
                random_state=random_state + 10_000 + i,
            )
        )

    return TaxonSplitBenchmarkResult(
        discovery_species=discovery_species,
        validation_species=validation_species,
        common_predictors=common,
        predictor_aggregate=aggregate,
        discovery_selection=discovery_selection,
        discovery_outer=discovery_outer,
        validation_outer=pd.DataFrame(validation_rows),
    )
