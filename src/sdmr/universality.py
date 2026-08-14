"""Cross-taxon validation of universal environmental-process cores."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import numpy as np
import pandas as pd

from .drivers import validate_candidate_manifest
from .synthesis import benchmark_driver_corpus_from_strategy


@dataclass
class ProcessCoreSplitResult:
    discovery_species: list[str]
    validation_species: list[str]
    core_processes: list[str]
    discovery_process_summary: pd.DataFrame
    validation_full_metrics: pd.DataFrame
    validation_core_metrics: pd.DataFrame
    validation_comparison: pd.DataFrame
    random_core_metrics: pd.DataFrame


@dataclass
class RepeatedProcessCoreResult:
    splits: pd.DataFrame
    process_stability: pd.DataFrame
    validation_comparison: pd.DataFrame


def choose_common_processes(
    process_summary: pd.DataFrame,
    *,
    min_selection_fraction: float = 0.25,
    top_k: int | None = 6,
) -> list[str]:
    """Freeze candidate universal processes using discovery taxa only."""

    if not 0 <= min_selection_fraction <= 1:
        raise ValueError("min_selection_fraction must be in [0, 1]")
    required = {"process", "selection_fraction"}
    missing = required - set(process_summary.columns)
    if missing:
        raise KeyError(f"process_summary missing columns: {sorted(missing)}")
    ranked = process_summary.copy()
    for column in ("mean_max_drop_one_loss", "mean_incremental_gain"):
        if column not in ranked:
            ranked[column] = np.nan
    ranked = ranked.sort_values(
        ["selection_fraction", "mean_max_drop_one_loss", "mean_incremental_gain"],
        ascending=[False, False, False],
        na_position="last",
        kind="mergesort",
    )
    chosen = ranked.loc[ranked["selection_fraction"] >= min_selection_fraction, "process"].astype(str).tolist()
    if not chosen and len(ranked):
        chosen = ranked["process"].astype(str).tolist()
    return chosen if top_k is None else chosen[: int(top_k)]


def _subset_taxa(frame: pd.DataFrame, species: Sequence[str], species_col: str) -> pd.DataFrame:
    keep = {str(x) for x in species}
    return frame.loc[frame[species_col].astype(str).isin(keep)].reset_index(drop=True)


def _core_manifest(manifest: pd.DataFrame, processes: Sequence[str]) -> pd.DataFrame:
    wanted = {str(x) for x in processes}
    out = validate_candidate_manifest(manifest)
    out = out.loc[out["process"].astype(str).isin(wanted)].reset_index(drop=True)
    if not len(out):
        raise ValueError("No candidate predictors belong to the selected process core")
    return out


def _compare_validation(full: pd.DataFrame, core: pd.DataFrame) -> pd.DataFrame:
    columns = ["species", "presence_rank", "boyce", "n_predictors"]
    left = full[columns].rename(
        columns={
            "presence_rank": "full_presence_rank",
            "boyce": "full_boyce",
            "n_predictors": "full_n_predictors",
        }
    )
    right = core[columns].rename(
        columns={
            "presence_rank": "core_presence_rank",
            "boyce": "core_boyce",
            "n_predictors": "core_n_predictors",
        }
    )
    out = left.merge(right, on="species", how="inner", validate="one_to_one")
    out["core_minus_full_presence_rank"] = out["core_presence_rank"] - out["full_presence_rank"]
    out["core_retained_fraction_above_random"] = (
        (out["core_presence_rank"] - 0.5) / (out["full_presence_rank"] - 0.5).replace(0, np.nan)
    )
    return out


def benchmark_process_core_taxon_split(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    candidate_predictors: Sequence[str],
    manifest: pd.DataFrame,
    *,
    strategy: str,
    species_col: str = "species",
    taxon_validation_fraction: float = 0.20,
    min_process_selection_fraction: float = 0.25,
    process_top_k: int | None = 6,
    random_process_repeats: int = 0,
    random_state: int = 42,
    **driver_kwargs,
) -> ProcessCoreSplitResult:
    """Discover a process core in some plants and test it on unseen plants."""

    if not 0 < taxon_validation_fraction < 1:
        raise ValueError("taxon_validation_fraction must be between 0 and 1")
    meta = validate_candidate_manifest(manifest)
    species = sorted(set(occurrences[species_col].astype(str)) & set(background[species_col].astype(str)))
    if len(species) < 4:
        raise ValueError("At least four species are required for process-core taxon validation")
    rng = np.random.default_rng(random_state)
    shuffled = np.array(species, dtype=object)
    rng.shuffle(shuffled)
    n_validation = max(1, int(round(len(shuffled) * taxon_validation_fraction)))
    n_validation = min(n_validation, len(shuffled) - 2)
    validation_species = sorted(str(x) for x in shuffled[:n_validation])
    discovery_species = sorted(str(x) for x in shuffled[n_validation:])

    discovery = benchmark_driver_corpus_from_strategy(
        _subset_taxa(occurrences, discovery_species, species_col),
        _subset_taxa(background, discovery_species, species_col),
        candidate_predictors,
        meta,
        strategy=strategy,
        species_col=species_col,
        random_state=random_state + 1_000,
        **driver_kwargs,
    )
    core_processes = choose_common_processes(
        discovery.process_summary,
        min_selection_fraction=min_process_selection_fraction,
        top_k=process_top_k,
    )
    core_meta = _core_manifest(meta, core_processes)
    core_predictors = core_meta["predictor"].astype(str).tolist()

    validation_occ = _subset_taxa(occurrences, validation_species, species_col)
    validation_bg = _subset_taxa(background, validation_species, species_col)
    validation_seed = random_state + 100_000
    full = benchmark_driver_corpus_from_strategy(
        validation_occ,
        validation_bg,
        candidate_predictors,
        meta,
        strategy=strategy,
        species_col=species_col,
        random_state=validation_seed,
        **driver_kwargs,
    )
    core = benchmark_driver_corpus_from_strategy(
        validation_occ,
        validation_bg,
        core_predictors,
        core_meta,
        strategy=strategy,
        species_col=species_col,
        random_state=validation_seed,
        **driver_kwargs,
    )
    comparison = _compare_validation(full.per_species_metrics, core.per_species_metrics)

    random_frames = []
    all_processes = meta["process"].drop_duplicates().astype(str).to_numpy(object)
    n_core = min(len(core_processes), len(all_processes))
    for repeat in range(int(random_process_repeats)):
        sampled = sorted(str(x) for x in rng.choice(all_processes, size=n_core, replace=False))
        random_meta = _core_manifest(meta, sampled)
        random_predictors = random_meta["predictor"].astype(str).tolist()
        random_result = benchmark_driver_corpus_from_strategy(
            validation_occ,
            validation_bg,
            random_predictors,
            random_meta,
            strategy=strategy,
            species_col=species_col,
            random_state=validation_seed,
            **driver_kwargs,
        )
        if len(random_result.per_species_metrics):
            random_frames.append(
                random_result.per_species_metrics.assign(
                    repeat=repeat,
                    processes=",".join(sampled),
                    n_processes=n_core,
                )
            )

    return ProcessCoreSplitResult(
        discovery_species=discovery_species,
        validation_species=validation_species,
        core_processes=core_processes,
        discovery_process_summary=discovery.process_summary,
        validation_full_metrics=full.per_species_metrics,
        validation_core_metrics=core.per_species_metrics,
        validation_comparison=comparison,
        random_core_metrics=pd.concat(random_frames, ignore_index=True) if random_frames else pd.DataFrame(),
    )


def benchmark_repeated_process_core_splits(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    candidate_predictors: Sequence[str],
    manifest: pd.DataFrame,
    *,
    strategy: str,
    seeds: Iterable[int] = (11, 22, 33, 44, 55),
    **kwargs,
) -> RepeatedProcessCoreResult:
    """Repeat taxon-level discovery/validation and report process-core stability."""

    seed_list = [int(seed) for seed in seeds]
    split_rows = []
    comparison_frames = []
    for split_id, seed in enumerate(seed_list):
        result = benchmark_process_core_taxon_split(
            occurrences,
            background,
            candidate_predictors,
            manifest,
            strategy=strategy,
            random_state=int(seed),
            **kwargs,
        )
        for process in result.core_processes:
            split_rows.append(
                {
                    "split_id": split_id,
                    "seed": int(seed),
                    "process": process,
                    "selected_core": True,
                    "n_discovery_species": len(result.discovery_species),
                    "n_validation_species": len(result.validation_species),
                }
            )
        comparison_frames.append(
            result.validation_comparison.assign(split_id=split_id, seed=int(seed))
        )

    splits = pd.DataFrame(split_rows)
    total_splits = len(seed_list)
    if len(splits):
        stability = (
            splits.groupby("process", as_index=False)
            .agg(splits_selected=("split_id", "nunique"))
        )
        stability["n_splits"] = total_splits
        stability["core_stability"] = stability["splits_selected"] / total_splits
        stability = stability.sort_values("core_stability", ascending=False, kind="mergesort").reset_index(drop=True)
    else:
        stability = pd.DataFrame(columns=["process", "splits_selected", "n_splits", "core_stability"])
    return RepeatedProcessCoreResult(
        splits=splits,
        process_stability=stability,
        validation_comparison=pd.concat(comparison_frames, ignore_index=True) if comparison_frames else pd.DataFrame(),
    )
