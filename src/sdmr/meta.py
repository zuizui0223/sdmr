"""Across-species validation of the Product-A tuning procedure."""

from __future__ import annotations
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .method import benchmark_species_methods


@dataclass
class MethodTaxonValidationResult:
    discovery_species: list[str]
    validation_species: list[str]
    winning_strategy: str
    discovery_metrics: pd.DataFrame
    discovery_summary: pd.DataFrame
    validation_metrics: pd.DataFrame
    validation_summary: pd.DataFrame


def summarize_method_performance(sealed_metrics: pd.DataFrame) -> pd.DataFrame:
    """Equal-species comparison of all/VIF/predictive strategies."""
    required = {"species", "strategy", "presence_rank", "n_predictors"}
    missing = required - set(sealed_metrics.columns)
    if missing:
        raise KeyError(f"sealed_metrics missing columns: {sorted(missing)}")
    data = sealed_metrics.copy()
    best = data.groupby("species")["presence_rank"].transform("max")
    data["win"] = (data["presence_rank"] >= best - 1e-12).astype(float)
    return (
        data.groupby("strategy", as_index=False)
        .agg(
            n_species=("species", "nunique"),
            mean_presence_rank=("presence_rank", "mean"),
            median_presence_rank=("presence_rank", "median"),
            win_fraction=("win", "mean"),
            mean_predictors=("n_predictors", "mean"),
        )
        .sort_values(["mean_presence_rank", "win_fraction"], ascending=[False, False], kind="mergesort")
        .reset_index(drop=True)
    )


def benchmark_method_corpus(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    candidate_predictors: Sequence[str],
    *,
    species_col: str = "species",
    random_state: int = 42,
    **kwargs,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    species = sorted(set(occurrences[species_col].astype(str)) & set(background[species_col].astype(str)))
    frames = []
    for i, species_name in enumerate(species):
        result = benchmark_species_methods(
            occurrences, background, candidate_predictors,
            species_name=species_name, species_col=species_col,
            random_state=random_state + i, **kwargs,
        )
        frames.append(result.sealed_metrics)
    metrics = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return metrics, summarize_method_performance(metrics) if len(metrics) else pd.DataFrame()


def benchmark_method_taxon_split(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    candidate_predictors: Sequence[str],
    *,
    species_col: str = "species",
    taxon_validation_fraction: float = 0.20,
    random_state: int = 42,
    **kwargs,
) -> MethodTaxonValidationResult:
    """Choose the method on discovery taxa and test it on unseen plant taxa."""
    if not 0 < taxon_validation_fraction < 1:
        raise ValueError("taxon_validation_fraction must be between 0 and 1.")
    species = sorted(set(occurrences[species_col].astype(str)) & set(background[species_col].astype(str)))
    if len(species) < 4:
        raise ValueError("At least four species are required for method-level taxon validation.")
    rng = np.random.default_rng(random_state)
    shuffled = np.array(species, dtype=object)
    rng.shuffle(shuffled)
    n_validation = max(1, int(round(len(shuffled) * taxon_validation_fraction)))
    n_validation = min(n_validation, len(shuffled) - 2)
    validation_species = sorted(str(x) for x in shuffled[:n_validation])
    discovery_species = sorted(str(x) for x in shuffled[n_validation:])

    def run(group: list[str], offset: int) -> pd.DataFrame:
        frames = []
        for i, species_name in enumerate(group):
            result = benchmark_species_methods(
                occurrences, background, candidate_predictors,
                species_name=species_name, species_col=species_col,
                random_state=random_state + offset + i, **kwargs,
            )
            frames.append(result.sealed_metrics)
        return pd.concat(frames, ignore_index=True)

    discovery_metrics = run(discovery_species, 1_000)
    discovery_summary = summarize_method_performance(discovery_metrics)
    winning_strategy = str(discovery_summary.iloc[0]["strategy"])
    validation_metrics = run(validation_species, 100_000)
    validation_summary = summarize_method_performance(validation_metrics)
    validation_metrics = validation_metrics.assign(
        selected_by_discovery=lambda x: x["strategy"].astype(str) == winning_strategy
    )
    return MethodTaxonValidationResult(
        discovery_species, validation_species, winning_strategy,
        discovery_metrics, discovery_summary, validation_metrics, validation_summary,
    )


def benchmark_holdout_sensitivity(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    candidate_predictors: Sequence[str],
    *,
    species_name: str = "species",
    fractions: Iterable[float] = (0.10, 0.20, 0.30),
    seeds: Iterable[int] = (11, 22, 33),
    **kwargs,
) -> pd.DataFrame:
    """Check that method rankings are not an artifact of one test fraction."""
    frames = []
    for fraction in fractions:
        for seed in seeds:
            result = benchmark_species_methods(
                occurrences, background, candidate_predictors,
                species_name=species_name, sealed_fraction=float(fraction),
                random_state=int(seed), compute_drop_one=False,
                random_repeats=0, **kwargs,
            )
            frames.append(result.sealed_metrics.assign(sealed_fraction=float(fraction), split_seed=int(seed)))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
