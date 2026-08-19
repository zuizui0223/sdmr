"""Leakage-safe selection across predeclared M/background data specifications."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib

import numpy as np
import pandas as pd

from .meta import benchmark_method_corpus, summarize_method_performance
from .method import freeze_candidate_methods
from .model import evaluate_predictor_set
from .validation import make_spatial_partition


@dataclass
class DataSpecificationBenchmarkResult:
    occurrence_sha256: str
    discovery_species: list[str]
    validation_species: list[str]
    winning_specification: str
    winning_strategy: str
    discovery_metrics: pd.DataFrame
    discovery_summary: pd.DataFrame
    validation_metrics: pd.DataFrame
    validation_summary: pd.DataFrame
    paired_validation_deltas: pd.DataFrame


def occurrence_table_fingerprint(
    occurrences: pd.DataFrame,
    *,
    species_col: str = "species",
) -> str:
    """Fingerprint the occurrence evidence used as the common prediction target."""
    required = {species_col, "longitude", "latitude"}
    missing = required - set(occurrences.columns)
    if missing:
        raise KeyError(f"occurrences missing columns: {sorted(missing)}")
    columns = [species_col, "longitude", "latitude"]
    if "gbifID" in occurrences:
        columns.insert(0, "gbifID")
    stable = occurrences[columns].copy()
    for column in stable.columns:
        stable[column] = stable[column].astype("string").fillna("")
    stable = stable.sort_values(columns, kind="mergesort").reset_index(drop=True)
    payload = stable.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _subset_taxa(frame: pd.DataFrame, species: Sequence[str], species_col: str) -> pd.DataFrame:
    keep = {str(x) for x in species}
    return frame.loc[frame[species_col].astype(str).isin(keep)].reset_index(drop=True)


def _common_species(
    specifications: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    species_col: str,
) -> list[str]:
    common: set[str] | None = None
    for occurrences, background in specifications.values():
        available = set(occurrences[species_col].astype(str)) & set(background[species_col].astype(str))
        common = available if common is None else common & available
    return sorted(common or set())


def validate_matched_occurrence_specifications(
    specifications: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    *,
    species_col: str = "species",
) -> str:
    """Require identical occurrence evidence before directly ranking background specs.

    M/background choices can then be compared on the same sealed occurrence
    target. If occurrence-quality filtering changes the occurrence table, direct
    ranking is rejected because it would mix method quality with test-set ease.
    """
    if len(specifications) < 2:
        raise ValueError("At least two data specifications are required")
    fingerprints = {
        name: occurrence_table_fingerprint(occurrences, species_col=species_col)
        for name, (occurrences, _) in specifications.items()
    }
    unique = set(fingerprints.values())
    if len(unique) != 1:
        details = ", ".join(f"{name}={value[:12]}" for name, value in sorted(fingerprints.items()))
        raise ValueError(
            "Direct data-specification ranking requires identical occurrence evidence across specifications. "
            "Treat occurrence-quality alternatives as sensitivity analyses rather than selecting the easiest test set. "
            f"Fingerprints: {details}"
        )
    return next(iter(unique))


def _evaluate_fixed_strategies_corpus(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    candidate_predictors: Sequence[str],
    species: Sequence[str],
    *,
    strategies: Sequence[str] = ("all", "vif", "predictive"),
    species_col: str = "species",
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    sealed_fraction: float = 0.20,
    n_spatial_blocks: int = 8,
    inner_folds: int = 4,
    min_gain: float = 0.005,
    max_predictors: int | None = 8,
    vif_threshold: float = 5.0,
    model_specs=None,
    random_state: int = 42,
) -> pd.DataFrame:
    """Evaluate only predeclared strategies on validation taxa, without reselection."""
    rows: list[dict[str, object]] = []
    for i, species_name in enumerate(species):
        p = _subset_taxa(occurrences, [species_name], species_col)
        b = _subset_taxa(background, [species_name], species_col)
        if len(p) < 12 or len(b) < 8:
            continue
        seed = random_state + i
        part = make_spatial_partition(
            p[lon_col].to_numpy(float),
            p[lat_col].to_numpy(float),
            b[lon_col].to_numpy(float),
            b[lat_col].to_numpy(float),
            n_blocks=n_spatial_blocks,
            holdout_fraction=sealed_fraction,
            random_state=seed,
        )
        p_tr = np.isin(part.presence_blocks, part.train_blocks)
        p_te = np.isin(part.presence_blocks, part.test_blocks)
        b_tr = np.isin(part.background_blocks, part.train_blocks)
        b_te = np.isin(part.background_blocks, part.test_blocks)
        p_model, p_test = p.loc[p_tr].reset_index(drop=True), p.loc[p_te].reset_index(drop=True)
        b_model, b_test = b.loc[b_tr].reset_index(drop=True), b.loc[b_te].reset_index(drop=True)
        protocols, _ = freeze_candidate_methods(
            p_model,
            b_model,
            part.presence_blocks[p_tr],
            part.background_blocks[b_tr],
            candidate_predictors,
            model_specs=model_specs,
            inner_folds=inner_folds,
            min_gain=min_gain,
            max_predictors=max_predictors,
            vif_threshold=vif_threshold,
        )
        for strategy in strategies:
            protocol = protocols.get(str(strategy))
            if protocol is None:
                continue
            metrics = evaluate_predictor_set(
                p_model,
                b_model,
                p_test,
                b_test,
                protocol.predictors,
                model_spec=protocol.model_spec,
            )
            rows.append(
                {
                    "species": str(species_name),
                    "strategy": str(strategy),
                    "model": protocol.model_spec.label,
                    "inner_presence_rank": protocol.inner_score,
                    "n_predictors": len(protocol.predictors),
                    "predictors": ",".join(protocol.predictors),
                    **metrics,
                }
            )
    return pd.DataFrame(rows)


def _paired_deltas(validation: pd.DataFrame, winning_spec: str, winning_strategy: str) -> pd.DataFrame:
    data = validation.loc[validation["data_specification"].astype(str) == winning_spec].copy()
    if not len(data):
        return pd.DataFrame()
    pivot = data.pivot(index="species", columns="strategy", values="presence_rank")
    if winning_strategy not in pivot:
        return pd.DataFrame()
    rows = []
    for comparator in sorted(c for c in pivot.columns if c != winning_strategy):
        paired = pivot[[winning_strategy, comparator]].dropna()
        for species, values in paired.iterrows():
            rows.append(
                {
                    "species": str(species),
                    "winning_specification": winning_spec,
                    "winning_strategy": winning_strategy,
                    "comparator": str(comparator),
                    "delta_presence_rank": float(values[winning_strategy] - values[comparator]),
                }
            )
    return pd.DataFrame(rows)


def benchmark_matched_data_specifications(
    specifications: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    candidate_predictors: Sequence[str],
    *,
    species_col: str = "species",
    taxon_validation_fraction: float = 0.20,
    random_state: int = 42,
    **method_kwargs,
) -> DataSpecificationBenchmarkResult:
    """Choose M/background specification + strategy on discovery taxa only.

    All candidate specifications must contain the *same occurrence evidence*.
    Only background/M construction may differ. The taxon split is fixed once.
    Validation evaluates all predeclared strategy/specification combinations for
    reporting, but the selected pair is frozen from discovery results and is not
    changed after validation scores are visible.
    """
    occurrence_sha = validate_matched_occurrence_specifications(specifications, species_col=species_col)
    if not 0 < taxon_validation_fraction < 1:
        raise ValueError("taxon_validation_fraction must be between 0 and 1")
    species = _common_species(specifications, species_col)
    if len(species) < 4:
        raise ValueError("At least four species shared by all specifications are required")
    rng = np.random.default_rng(random_state)
    shuffled = np.array(species, dtype=object)
    rng.shuffle(shuffled)
    n_validation = max(1, int(round(len(shuffled) * taxon_validation_fraction)))
    n_validation = min(n_validation, len(shuffled) - 2)
    validation_species = sorted(str(x) for x in shuffled[:n_validation])
    discovery_species = sorted(str(x) for x in shuffled[n_validation:])

    discovery_metrics_frames = []
    discovery_summary_frames = []
    for spec_name, (occurrences, background) in specifications.items():
        occ = _subset_taxa(occurrences, discovery_species, species_col)
        bg = _subset_taxa(background, discovery_species, species_col)
        metrics, summary = benchmark_method_corpus(
            occ,
            bg,
            candidate_predictors,
            species_col=species_col,
            random_state=random_state + 1_000,
            **method_kwargs,
        )
        discovery_metrics_frames.append(metrics.assign(data_specification=str(spec_name)))
        discovery_summary_frames.append(summary.assign(data_specification=str(spec_name)))
    discovery_metrics = pd.concat(discovery_metrics_frames, ignore_index=True)
    discovery_summary = pd.concat(discovery_summary_frames, ignore_index=True)
    ranked = discovery_summary.sort_values(
        ["mean_presence_rank", "win_fraction", "mean_predictors", "data_specification", "strategy"],
        ascending=[False, False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    winner = ranked.iloc[0]
    winning_spec = str(winner["data_specification"])
    winning_strategy = str(winner["strategy"])

    validation_frames = []
    fixed_kwargs = dict(method_kwargs)
    fixed_kwargs.pop("random_repeats", None)
    fixed_kwargs.pop("compute_drop_one", None)
    for spec_name, (occurrences, background) in specifications.items():
        metrics = _evaluate_fixed_strategies_corpus(
            occurrences,
            background,
            candidate_predictors,
            validation_species,
            species_col=species_col,
            random_state=random_state + 100_000,
            **fixed_kwargs,
        )
        if len(metrics):
            validation_frames.append(metrics.assign(data_specification=str(spec_name)))
    validation_metrics = pd.concat(validation_frames, ignore_index=True) if validation_frames else pd.DataFrame()
    if len(validation_metrics):
        validation_summary_frames = []
        for spec_name, group in validation_metrics.groupby("data_specification", sort=True):
            summary = summarize_method_performance(group).assign(data_specification=str(spec_name))
            validation_summary_frames.append(summary)
        validation_summary = pd.concat(validation_summary_frames, ignore_index=True)
        validation_summary["selected_by_discovery"] = (
            (validation_summary["data_specification"].astype(str) == winning_spec)
            & (validation_summary["strategy"].astype(str) == winning_strategy)
        )
        validation_metrics["selected_by_discovery"] = (
            (validation_metrics["data_specification"].astype(str) == winning_spec)
            & (validation_metrics["strategy"].astype(str) == winning_strategy)
        )
    else:
        validation_summary = pd.DataFrame()
    paired = _paired_deltas(validation_metrics, winning_spec, winning_strategy)
    return DataSpecificationBenchmarkResult(
        occurrence_sha256=occurrence_sha,
        discovery_species=discovery_species,
        validation_species=validation_species,
        winning_specification=winning_spec,
        winning_strategy=winning_strategy,
        discovery_metrics=discovery_metrics,
        discovery_summary=ranked,
        validation_metrics=validation_metrics,
        validation_summary=validation_summary,
        paired_validation_deltas=paired,
    )
