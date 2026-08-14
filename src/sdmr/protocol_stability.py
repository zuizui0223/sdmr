"""Repeated promotion-gate validation for the complete Product-A protocol."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from .protocol import benchmark_product_a_protocol_grid
from .universe import CandidateUniverse


@dataclass
class RepeatedProductAProtocolResult:
    runs: pd.DataFrame
    choice_stability: pd.DataFrame
    component_stability: pd.DataFrame
    selected_validation_metrics: pd.DataFrame
    paired_validation_deltas: pd.DataFrame
    validation_delta_summary: pd.DataFrame


def _component_stability(runs: pd.DataFrame, total_runs: int) -> pd.DataFrame:
    rows = []
    for column, label in (
        ("winning_data_specification", "data_specification"),
        ("winning_universe", "universe"),
        ("winning_strategy", "strategy"),
    ):
        counts = runs.groupby(column, as_index=False).size().rename(columns={column: "value", "size": "runs_selected"})
        counts["component"] = label
        counts["n_runs"] = int(total_runs)
        counts["selection_fraction"] = counts["runs_selected"] / float(total_runs)
        rows.append(counts[["component", "value", "runs_selected", "n_runs", "selection_fraction"]])
    return pd.concat(rows, ignore_index=True).sort_values(
        ["component", "selection_fraction", "value"],
        ascending=[True, False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _delta_summary(deltas: pd.DataFrame) -> pd.DataFrame:
    if not len(deltas):
        return pd.DataFrame(
            columns=[
                "comparator",
                "n_pairs",
                "n_runs",
                "mean_delta_presence_rank",
                "median_delta_presence_rank",
                "positive_fraction",
            ]
        )
    return (
        deltas.groupby("comparator", as_index=False)
        .agg(
            n_pairs=("delta_presence_rank", "size"),
            n_runs=("run_id", "nunique"),
            mean_delta_presence_rank=("delta_presence_rank", "mean"),
            median_delta_presence_rank=("delta_presence_rank", "median"),
            positive_fraction=("delta_presence_rank", lambda x: float((x > 0).mean())),
        )
        .sort_values("mean_delta_presence_rank", ascending=False, kind="mergesort")
        .reset_index(drop=True)
    )


def benchmark_repeated_product_a_protocols(
    specifications: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    universes: Mapping[str, Sequence[str] | CandidateUniverse],
    *,
    seeds: Iterable[int] = (11, 22, 33, 44, 55),
    sealed_fractions: Iterable[float] = (0.15, 0.20, 0.30),
    taxon_validation_fraction: float = 0.20,
    **method_kwargs,
) -> RepeatedProductAProtocolResult:
    """Repeat full protocol selection across taxon/spatial partitions and holdout sizes.

    No promotion threshold is hard-coded. The returned stability and paired
    unseen-taxon deltas are evidence for deciding whether one complete protocol
    is sufficiently reproducible to freeze for Product B.
    """
    seed_list = [int(x) for x in seeds]
    fraction_list = [float(x) for x in sealed_fractions]
    if not seed_list:
        raise ValueError("At least one seed is required")
    if not fraction_list or any(not 0 < x < 1 for x in fraction_list):
        raise ValueError("sealed_fractions must contain values between 0 and 1")
    if "sealed_fraction" in method_kwargs:
        raise ValueError("Pass sealed holdout sizes through sealed_fractions, not method_kwargs")

    run_rows = []
    selected_frames = []
    delta_frames = []
    expected_occurrence_sha = None
    expected_feature_sha = None
    run_id = 0
    for sealed_fraction in fraction_list:
        for seed in seed_list:
            result = benchmark_product_a_protocol_grid(
                specifications,
                universes,
                taxon_validation_fraction=taxon_validation_fraction,
                sealed_fraction=sealed_fraction,
                random_state=seed,
                **method_kwargs,
            )
            if expected_occurrence_sha is None:
                expected_occurrence_sha = result.occurrence_sha256
                expected_feature_sha = result.occurrence_feature_sha256
            elif (
                result.occurrence_sha256 != expected_occurrence_sha
                or result.occurrence_feature_sha256 != expected_feature_sha
            ):
                raise RuntimeError("Occurrence/feature fingerprints changed across repeated protocol runs")

            run_rows.append(
                {
                    "run_id": run_id,
                    "seed": seed,
                    "sealed_fraction": sealed_fraction,
                    "taxon_validation_fraction": taxon_validation_fraction,
                    "winning_data_specification": result.winning_data_specification,
                    "winning_universe": result.winning_universe,
                    "winning_strategy": result.winning_strategy,
                    "winning_universe_sha256": result.winning_universe_sha256,
                    "n_winning_predictors": len(result.winning_predictors),
                    "winning_predictors": ",".join(result.winning_predictors),
                    "occurrence_sha256": result.occurrence_sha256,
                    "occurrence_feature_sha256": result.occurrence_feature_sha256,
                    "n_discovery_species": len(result.discovery_species),
                    "n_validation_species": len(result.validation_species),
                }
            )
            if len(result.validation_metrics):
                selected = result.validation_metrics.loc[
                    result.validation_metrics["selected_by_discovery"].astype(bool)
                ].copy()
                selected_frames.append(
                    selected.assign(
                        run_id=run_id,
                        seed=seed,
                        sealed_fraction=sealed_fraction,
                        winning_data_specification=result.winning_data_specification,
                        winning_universe=result.winning_universe,
                        winning_strategy=result.winning_strategy,
                    )
                )
            if len(result.paired_validation_deltas):
                delta_frames.append(
                    result.paired_validation_deltas.assign(
                        run_id=run_id,
                        seed=seed,
                        sealed_fraction=sealed_fraction,
                        winning_data_specification=result.winning_data_specification,
                        winning_universe=result.winning_universe,
                    )
                )
            run_id += 1

    runs = pd.DataFrame(run_rows)
    total_runs = len(runs)
    choice_stability = (
        runs.groupby(
            ["winning_data_specification", "winning_universe", "winning_strategy"],
            as_index=False,
        )
        .agg(
            runs_selected=("run_id", "nunique"),
            mean_n_predictors=("n_winning_predictors", "mean"),
        )
    )
    choice_stability["n_runs"] = total_runs
    choice_stability["selection_fraction"] = choice_stability["runs_selected"] / float(total_runs)
    choice_stability = choice_stability.sort_values(
        ["selection_fraction", "mean_n_predictors", "winning_data_specification", "winning_universe", "winning_strategy"],
        ascending=[False, True, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    selected_metrics = pd.concat(selected_frames, ignore_index=True) if selected_frames else pd.DataFrame()
    deltas = pd.concat(delta_frames, ignore_index=True) if delta_frames else pd.DataFrame()
    return RepeatedProductAProtocolResult(
        runs=runs,
        choice_stability=choice_stability,
        component_stability=_component_stability(runs, total_runs),
        selected_validation_metrics=selected_metrics,
        paired_validation_deltas=deltas,
        validation_delta_summary=_delta_summary(deltas),
    )
