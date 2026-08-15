"""Select Product-A method components robustly across predeclared M/background specs.

Accessible-area/background specifications are ecological sensitivity assumptions,
not candidates to be made to "win" by the easiest evaluation background.  This
module compares environmental-universe × selection-strategy combinations only
*within the same species and M/background specification*, converts those scores
to within-case ranks, and aggregates the ranks across all predeclared specs.
Validation taxa then evaluate the frozen universe/strategy in every M spec.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .method import benchmark_species_methods
from .protocol import (
    ProductAProtocolValidationResult,
    _common_species,
    _normalize_universes,
    validate_matched_protocol_specifications,
)
from .universe import CandidateUniverse

SENSITIVITY_SET_NAME = "all_predeclared_M_sensitivity_specs"


def summarize_discovery_robust_across_specs(
    metrics: pd.DataFrame,
    universes: Mapping[str, CandidateUniverse],
) -> pd.DataFrame:
    """Rank methods within species×M cases, then aggregate those ranks equally."""
    required = {"species", "data_specification", "universe", "strategy", "presence_rank", "n_predictors"}
    missing = required - set(metrics.columns)
    if missing:
        raise KeyError(f"robust Product-A discovery metrics missing columns: {sorted(missing)}")
    data = metrics.copy()
    case_cols = ["data_specification", "species"]
    data["case_rank"] = data.groupby(case_cols)["presence_rank"].rank(method="min", ascending=False)
    n_methods = data.groupby(case_cols)["presence_rank"].transform("size").astype(float)
    data["case_rank_score"] = np.where(
        n_methods <= 1,
        1.0,
        1.0 - (data["case_rank"] - 1.0) / (n_methods - 1.0),
    )
    best = data.groupby(case_cols)["presence_rank"].transform("max")
    data["case_win"] = (data["presence_rank"] >= best - 1e-12).astype(float)

    # Also ask whether the same method is the best mean method inside each M
    # specification.  This is descriptive robustness, not a separate M winner.
    per_spec = (
        data.groupby(["data_specification", "universe", "strategy"], as_index=False)
        .agg(spec_mean_presence_rank=("presence_rank", "mean"))
    )
    spec_best = per_spec.groupby("data_specification")["spec_mean_presence_rank"].transform("max")
    per_spec["spec_win"] = (per_spec["spec_mean_presence_rank"] >= spec_best - 1e-12).astype(float)
    spec_consistency = (
        per_spec.groupby(["universe", "strategy"], as_index=False)
        .agg(spec_win_fraction=("spec_win", "mean"), n_specs=("data_specification", "nunique"))
    )

    summary = (
        data.groupby(["universe", "strategy"], as_index=False)
        .agg(
            n_species=("species", "nunique"),
            n_cases=("presence_rank", "size"),
            mean_case_rank_score=("case_rank_score", "mean"),
            median_case_rank_score=("case_rank_score", "median"),
            case_win_fraction=("case_win", "mean"),
            mean_predictors=("n_predictors", "mean"),
        )
        .merge(spec_consistency, on=["universe", "strategy"], how="left")
    )
    summary["n_candidates"] = summary["universe"].map(lambda x: len(universes[str(x)].predictors))
    summary["universe_sha256"] = summary["universe"].map(lambda x: universes[str(x)].fingerprint)
    summary["data_specification"] = SENSITIVITY_SET_NAME
    return summary.sort_values(
        [
            "mean_case_rank_score",
            "case_win_fraction",
            "spec_win_fraction",
            "mean_predictors",
            "n_candidates",
            "universe",
            "strategy",
        ],
        ascending=[False, False, False, True, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def paired_validation_deltas_across_specs(metrics: pd.DataFrame, winning_strategy: str) -> pd.DataFrame:
    """Pair strategy comparisons within the exact same validation taxon and M spec."""
    if not len(metrics):
        return pd.DataFrame()
    pivot = metrics.pivot(
        index=["data_specification", "species"],
        columns="strategy",
        values="presence_rank",
    )
    if winning_strategy not in pivot:
        return pd.DataFrame()
    rows = []
    for comparator in sorted(c for c in pivot.columns if str(c) != str(winning_strategy)):
        paired = pivot[[winning_strategy, comparator]].dropna()
        for (data_specification, species), values in paired.iterrows():
            rows.append(
                {
                    "data_specification": str(data_specification),
                    "species": str(species),
                    "winning_strategy": str(winning_strategy),
                    "comparator": str(comparator),
                    "delta_presence_rank": float(values[winning_strategy] - values[comparator]),
                }
            )
    return pd.DataFrame(rows)


def benchmark_product_a_method_across_sensitivity_specs(
    specifications: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    universes: Mapping[str, Sequence[str] | CandidateUniverse],
    *,
    species_col: str = "species",
    taxon_validation_fraction: float = 0.20,
    random_state: int = 42,
    **method_kwargs,
) -> ProductAProtocolValidationResult:
    """Choose universe×strategy without directly ranking alternative M backgrounds."""
    occurrence_sha, feature_sha, normalized = validate_matched_protocol_specifications(
        specifications,
        universes,
        species_col=species_col,
    )
    if not 0 < taxon_validation_fraction < 1:
        raise ValueError("taxon_validation_fraction must be between 0 and 1")
    species = _common_species(specifications, species_col)
    if len(species) < 4:
        raise ValueError("At least four species shared by all sensitivity specifications are required")

    rng = np.random.default_rng(random_state)
    shuffled = np.array(species, dtype=object)
    rng.shuffle(shuffled)
    n_validation = max(1, int(round(len(shuffled) * taxon_validation_fraction)))
    n_validation = min(n_validation, len(shuffled) - 2)
    validation_species = sorted(str(x) for x in shuffled[:n_validation])
    discovery_species = sorted(str(x) for x in shuffled[n_validation:])

    discovery_frames: list[pd.DataFrame] = []
    for spec_name, (occurrences, background) in specifications.items():
        for universe_name, universe in normalized.items():
            for i, species_name in enumerate(discovery_species):
                result = benchmark_species_methods(
                    occurrences,
                    background,
                    universe.predictors,
                    species_name=species_name,
                    species_col=species_col,
                    random_state=random_state + 1_000 + i,
                    **method_kwargs,
                )
                discovery_frames.append(
                    result.sealed_metrics.assign(
                        data_specification=str(spec_name),
                        universe=str(universe_name),
                        universe_sha256=universe.fingerprint,
                        n_candidates=len(universe.predictors),
                    )
                )
    discovery_metrics = pd.concat(discovery_frames, ignore_index=True)
    discovery_summary = summarize_discovery_robust_across_specs(discovery_metrics, normalized)
    winner = discovery_summary.iloc[0]
    winning_universe = str(winner["universe"])
    winning_strategy = str(winner["strategy"])
    universe = normalized[winning_universe]

    validation_frames: list[pd.DataFrame] = []
    for spec_name, (occurrences, background) in specifications.items():
        for i, species_name in enumerate(validation_species):
            result = benchmark_species_methods(
                occurrences,
                background,
                universe.predictors,
                species_name=species_name,
                species_col=species_col,
                random_state=random_state + 100_000 + i,
                **method_kwargs,
            )
            frame = result.sealed_metrics.assign(
                data_specification=str(spec_name),
                universe=winning_universe,
                universe_sha256=universe.fingerprint,
                n_candidates=len(universe.predictors),
            )
            frame["selected_by_discovery"] = frame["strategy"].astype(str) == winning_strategy
            validation_frames.append(frame)
    validation_metrics = pd.concat(validation_frames, ignore_index=True) if validation_frames else pd.DataFrame()

    if len(validation_metrics):
        validation_summary = (
            validation_metrics.groupby("strategy", as_index=False)
            .agg(
                n_species=("species", "nunique"),
                n_specs=("data_specification", "nunique"),
                n_cases=("presence_rank", "size"),
                mean_presence_rank=("presence_rank", "mean"),
                median_presence_rank=("presence_rank", "median"),
                mean_predictors=("n_predictors", "mean"),
            )
        )
        validation_summary["selected_by_discovery"] = (
            validation_summary["strategy"].astype(str) == winning_strategy
        )
        validation_summary = validation_summary.sort_values(
            ["selected_by_discovery", "mean_presence_rank", "mean_predictors", "strategy"],
            ascending=[False, False, True, True],
            kind="mergesort",
        ).reset_index(drop=True)
    else:
        validation_summary = pd.DataFrame()

    paired = paired_validation_deltas_across_specs(validation_metrics, winning_strategy)
    return ProductAProtocolValidationResult(
        occurrence_sha256=occurrence_sha,
        occurrence_feature_sha256=feature_sha,
        discovery_species=discovery_species,
        validation_species=validation_species,
        winning_data_specification=SENSITIVITY_SET_NAME,
        winning_universe=winning_universe,
        winning_strategy=winning_strategy,
        winning_predictors=list(universe.predictors),
        winning_universe_sha256=universe.fingerprint,
        discovery_metrics=discovery_metrics,
        discovery_summary=discovery_summary,
        validation_metrics=validation_metrics,
        validation_summary=validation_summary,
        paired_validation_deltas=paired,
    )
