"""Bridge the validated Product-A strategy into Product-B driver synthesis."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import numpy as np
import pandas as pd

from .drivers import aggregate_process_evidence, validate_candidate_manifest
from .equivalence import correlation_equivalence_groups, drop_group_importance
from .method import benchmark_species_methods
from .validation import make_spatial_partition


@dataclass
class DriverCorpusResult:
    strategy: str
    species: list[str]
    per_species_metrics: pd.DataFrame
    selection_rows: pd.DataFrame
    drop_one_rows: pd.DataFrame
    equivalence_rows: pd.DataFrame
    group_drop_rows: pd.DataFrame
    predictor_summary: pd.DataFrame
    process_summary: pd.DataFrame


def _subset_species(frame: pd.DataFrame, species_name: str, species_col: str) -> pd.DataFrame:
    return frame.loc[frame[species_col].astype(str) == str(species_name)].reset_index(drop=True)


def _partition_species_frames(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    *,
    lon_col: str,
    lat_col: str,
    n_spatial_blocks: int,
    sealed_fraction: float,
    random_state: int,
):
    part = make_spatial_partition(
        occurrences[lon_col].to_numpy(float),
        occurrences[lat_col].to_numpy(float),
        background[lon_col].to_numpy(float),
        background[lat_col].to_numpy(float),
        n_blocks=n_spatial_blocks,
        holdout_fraction=sealed_fraction,
        random_state=random_state,
    )
    p_tr = np.isin(part.presence_blocks, part.train_blocks)
    p_te = np.isin(part.presence_blocks, part.test_blocks)
    b_tr = np.isin(part.background_blocks, part.train_blocks)
    b_te = np.isin(part.background_blocks, part.test_blocks)
    return (
        occurrences.loc[p_tr].reset_index(drop=True),
        occurrences.loc[p_te].reset_index(drop=True),
        background.loc[b_tr].reset_index(drop=True),
        background.loc[b_te].reset_index(drop=True),
    )


def aggregate_predictor_evidence(
    selection_rows: pd.DataFrame,
    drop_one_rows: pd.DataFrame,
    *,
    species_universe: Sequence[str],
) -> pd.DataFrame:
    """Equal-species raster-level evidence table used before process aggregation."""

    species = sorted({str(x) for x in species_universe})
    n_species = len(species)
    if n_species == 0:
        return pd.DataFrame()

    if len(selection_rows):
        sel = selection_rows.copy()
        sel["species"] = sel["species"].astype(str)
        sel_sp = (
            sel.groupby(["species", "predictor"], as_index=False)
            .agg(incremental_gain=("gain", lambda x: x.sum(min_count=1)))
        )
        sel_summary = (
            sel_sp.groupby("predictor", as_index=False)
            .agg(
                species_selected=("species", "nunique"),
                mean_incremental_gain=("incremental_gain", "mean"),
                median_incremental_gain=("incremental_gain", "median"),
                species_with_incremental_gain=("incremental_gain", "count"),
            )
        )
    else:
        sel_summary = pd.DataFrame(
            columns=["predictor", "species_selected", "mean_incremental_gain", "median_incremental_gain", "species_with_incremental_gain"]
        )

    if len(drop_one_rows):
        drop = drop_one_rows.copy()
        drop["species"] = drop["species"].astype(str)
        drop_summary = (
            drop.groupby("predictor", as_index=False)
            .agg(
                species_with_drop_one=("species", "nunique"),
                mean_drop_one_loss=("loss", "mean"),
                median_drop_one_loss=("loss", "median"),
                positive_drop_fraction=("loss", lambda x: float((pd.to_numeric(x, errors="coerce") > 0).mean())),
            )
        )
    else:
        drop_summary = pd.DataFrame(
            columns=["predictor", "species_with_drop_one", "mean_drop_one_loss", "median_drop_one_loss", "positive_drop_fraction"]
        )

    predictors = sorted(set(sel_summary.get("predictor", [])) | set(drop_summary.get("predictor", [])))
    out = pd.DataFrame({"predictor": predictors})
    out = out.merge(sel_summary, on="predictor", how="left").merge(drop_summary, on="predictor", how="left")
    for col in ("species_selected", "species_with_incremental_gain", "species_with_drop_one"):
        out[col] = out[col].fillna(0).astype(int)
    out["n_species"] = n_species
    out["selection_fraction"] = out["species_selected"] / n_species
    out["incremental_gain_coverage_fraction"] = out["species_with_incremental_gain"] / n_species
    out["drop_one_coverage_fraction"] = out["species_with_drop_one"] / n_species
    return out.sort_values(
        ["selection_fraction", "mean_incremental_gain", "mean_drop_one_loss"],
        ascending=[False, False, False],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)


def benchmark_driver_corpus_from_strategy(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    candidate_predictors: Sequence[str],
    manifest: pd.DataFrame,
    *,
    strategy: str,
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
    equivalence_threshold: float = 0.90,
    equivalence_min_periods: int = 20,
    random_state: int = 42,
) -> DriverCorpusResult:
    """Apply one Product-A strategy across species without choosing a new strategy.

    Per-species hyperparameters are still tuned *inside that species' model pool*
    because this is part of the validated procedure. No other strategy's sealed
    result is used to alter the Product-B rule.
    """

    if strategy not in {"all", "vif", "predictive"}:
        raise ValueError("strategy must be one of: all, vif, predictive")
    meta = validate_candidate_manifest(manifest)
    missing_meta = sorted(set(candidate_predictors) - set(meta["predictor"].astype(str)))
    if missing_meta:
        raise ValueError(f"candidate predictors missing from manifest: {missing_meta}")

    species = sorted(set(occurrences[species_col].astype(str)) & set(background[species_col].astype(str)))
    metric_frames = []
    selection_frames = []
    drop_frames = []
    equivalence_frames = []
    group_drop_frames = []

    for i, species_name in enumerate(species):
        seed = random_state + i
        result = benchmark_species_methods(
            occurrences,
            background,
            candidate_predictors,
            species_name=species_name,
            species_col=species_col,
            lon_col=lon_col,
            lat_col=lat_col,
            sealed_fraction=sealed_fraction,
            n_spatial_blocks=n_spatial_blocks,
            inner_folds=inner_folds,
            min_gain=min_gain,
            max_predictors=max_predictors,
            vif_threshold=vif_threshold,
            model_specs=model_specs,
            random_repeats=0,
            compute_drop_one=True,
            random_state=seed,
        )
        if strategy not in result.protocols:
            continue
        protocol = result.protocols[strategy]
        metrics = result.sealed_metrics.loc[result.sealed_metrics["strategy"] == strategy].copy()
        metric_frames.append(metrics)
        drops = result.drop_one.loc[result.drop_one["strategy"] == strategy].copy()
        if len(drops):
            drop_frames.append(drops)

        if strategy == "predictive":
            selection_frames.append(result.predictive_selection.copy())
        else:
            selection_frames.append(
                pd.DataFrame(
                    {
                        "species": str(species_name),
                        "step": range(1, len(protocol.predictors) + 1),
                        "predictor": list(protocol.predictors),
                        "inner_presence_rank": np.nan,
                        "gain": np.nan,
                    }
                )
            )

        p = _subset_species(occurrences, species_name, species_col)
        b = _subset_species(background, species_name, species_col)
        p_model, p_test, b_model, b_test = _partition_species_frames(
            p,
            b,
            lon_col=lon_col,
            lat_col=lat_col,
            n_spatial_blocks=n_spatial_blocks,
            sealed_fraction=sealed_fraction,
            random_state=seed,
        )
        eq = correlation_equivalence_groups(
            pd.concat([p_model[list(protocol.predictors)], b_model[list(protocol.predictors)]], ignore_index=True),
            protocol.predictors,
            threshold=equivalence_threshold,
            min_periods=equivalence_min_periods,
        )
        eq = eq.assign(species=str(species_name), strategy=strategy, model=protocol.model_spec.label)
        equivalence_frames.append(eq)
        group_drop = drop_group_importance(
            p_model,
            b_model,
            p_test,
            b_test,
            protocol.predictors,
            eq[["predictor", "equivalence_group"]],
            model_spec=protocol.model_spec,
        )
        if len(group_drop):
            group_drop_frames.append(
                group_drop.assign(species=str(species_name), strategy=strategy, model=protocol.model_spec.label)
            )

    metrics_all = pd.concat(metric_frames, ignore_index=True) if metric_frames else pd.DataFrame()
    selection_all = pd.concat(selection_frames, ignore_index=True) if selection_frames else pd.DataFrame()
    drop_all = pd.concat(drop_frames, ignore_index=True) if drop_frames else pd.DataFrame()
    eq_all = pd.concat(equivalence_frames, ignore_index=True) if equivalence_frames else pd.DataFrame()
    group_drop_all = pd.concat(group_drop_frames, ignore_index=True) if group_drop_frames else pd.DataFrame()
    predictor_summary = aggregate_predictor_evidence(selection_all, drop_all, species_universe=species)
    process_summary = aggregate_process_evidence(selection_all, drop_all, meta, species_universe=species)
    return DriverCorpusResult(
        strategy=strategy,
        species=species,
        per_species_metrics=metrics_all,
        selection_rows=selection_all,
        drop_one_rows=drop_all,
        equivalence_rows=eq_all,
        group_drop_rows=group_drop_all,
        predictor_summary=predictor_summary,
        process_summary=process_summary,
    )
