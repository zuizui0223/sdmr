"""Freeze a complete Product-A protocol: data specification × candidate universe × strategy.

The promoted methodological object is not just a predictor-selection strategy.
It also includes the background/accessible-area specification and the candidate
environmental universe. All three are chosen on discovery taxa only and then
frozen before validation taxa are inspected.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib

import numpy as np
import pandas as pd

from .method import benchmark_species_methods
from .specification import occurrence_table_fingerprint, validate_matched_occurrence_specifications
from .universe import CandidateUniverse


@dataclass
class ProductAProtocolValidationResult:
    occurrence_sha256: str
    occurrence_feature_sha256: str
    discovery_species: list[str]
    validation_species: list[str]
    winning_data_specification: str
    winning_universe: str
    winning_strategy: str
    winning_predictors: list[str]
    winning_universe_sha256: str
    discovery_metrics: pd.DataFrame
    discovery_summary: pd.DataFrame
    validation_metrics: pd.DataFrame
    validation_summary: pd.DataFrame
    paired_validation_deltas: pd.DataFrame


def _normalize_universes(
    universes: Mapping[str, Sequence[str] | CandidateUniverse],
) -> dict[str, CandidateUniverse]:
    out: dict[str, CandidateUniverse] = {}
    for name, value in universes.items():
        if isinstance(value, CandidateUniverse):
            predictors = tuple(value.predictors)
        else:
            predictors = tuple(dict.fromkeys(str(x) for x in value))
        if not predictors:
            raise ValueError(f"candidate universe {name!r} is empty")
        out[str(name)] = CandidateUniverse(str(name), predictors)
    if not out:
        raise ValueError("At least one candidate universe is required")
    return out


def _identity_columns(frame: pd.DataFrame, species_col: str) -> list[str]:
    columns = [species_col, "longitude", "latitude"]
    if "gbifID" in frame:
        columns.insert(0, "gbifID")
    return columns


def occurrence_feature_fingerprint(
    occurrences: pd.DataFrame,
    predictors: Sequence[str],
    *,
    species_col: str = "species",
) -> str:
    """Fingerprint occurrence identities, coordinates, and candidate feature values."""
    predictors = list(dict.fromkeys(str(x) for x in predictors))
    required = set(_identity_columns(occurrences, species_col)) | set(predictors)
    missing = required - set(occurrences.columns)
    if missing:
        raise KeyError(f"occurrences missing columns required for feature fingerprint: {sorted(missing)}")
    identity = _identity_columns(occurrences, species_col)
    stable = occurrences[identity + predictors].copy()
    for column in identity:
        stable[column] = stable[column].astype("string").fillna("")
    for column in predictors:
        values = pd.to_numeric(stable[column], errors="coerce").astype(float)
        # Stable text representation avoids platform-dependent CSV formatting of NaN.
        stable[column] = values.map(lambda x: "NA" if not np.isfinite(x) else format(float(x), ".17g"))
    stable = stable.sort_values(identity + predictors, kind="mergesort").reset_index(drop=True)
    payload = stable.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_matched_protocol_specifications(
    specifications: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    universes: Mapping[str, Sequence[str] | CandidateUniverse],
    *,
    species_col: str = "species",
) -> tuple[str, str, dict[str, CandidateUniverse]]:
    """Require identical occurrence evidence and environmental feature values across specs."""
    occurrence_sha = validate_matched_occurrence_specifications(specifications, species_col=species_col)
    normalized = _normalize_universes(universes)
    union_predictors = list(
        dict.fromkeys(p for universe in normalized.values() for p in universe.predictors)
    )
    feature_hashes = {
        name: occurrence_feature_fingerprint(occurrences, union_predictors, species_col=species_col)
        for name, (occurrences, _) in specifications.items()
    }
    if len(set(feature_hashes.values())) != 1:
        details = ", ".join(f"{name}={value[:12]}" for name, value in sorted(feature_hashes.items()))
        raise ValueError(
            "Direct Product-A protocol ranking requires identical occurrence environmental features across "
            "data specifications. Different raster versions/extractions belong to a separate sensitivity layer. "
            f"Feature fingerprints: {details}"
        )
    return occurrence_sha, next(iter(feature_hashes.values())), normalized


def _common_species(
    specifications: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    species_col: str,
) -> list[str]:
    shared: set[str] | None = None
    for occurrences, background in specifications.values():
        available = set(occurrences[species_col].astype(str)) & set(background[species_col].astype(str))
        shared = available if shared is None else shared & available
    return sorted(shared or set())


def _subset_species(frame: pd.DataFrame, species_name: str, species_col: str) -> pd.DataFrame:
    return frame.loc[frame[species_col].astype(str) == str(species_name)].reset_index(drop=True)


def _summarize_discovery(
    metrics: pd.DataFrame,
    universes: Mapping[str, CandidateUniverse],
) -> pd.DataFrame:
    required = {"species", "data_specification", "universe", "strategy", "presence_rank", "n_predictors"}
    missing = required - set(metrics.columns)
    if missing:
        raise KeyError(f"protocol discovery metrics missing columns: {sorted(missing)}")
    data = metrics.copy()
    best = data.groupby("species")["presence_rank"].transform("max")
    data["global_win"] = (data["presence_rank"] >= best - 1e-12).astype(float)
    summary = (
        data.groupby(["data_specification", "universe", "strategy"], as_index=False)
        .agg(
            n_species=("species", "nunique"),
            mean_presence_rank=("presence_rank", "mean"),
            median_presence_rank=("presence_rank", "median"),
            global_win_fraction=("global_win", "mean"),
            mean_predictors=("n_predictors", "mean"),
        )
    )
    summary["n_candidates"] = summary["universe"].map(lambda x: len(universes[str(x)].predictors))
    summary["universe_sha256"] = summary["universe"].map(lambda x: universes[str(x)].fingerprint)
    return summary.sort_values(
        [
            "mean_presence_rank",
            "global_win_fraction",
            "mean_predictors",
            "n_candidates",
            "data_specification",
            "universe",
            "strategy",
        ],
        ascending=[False, False, True, True, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _summarize_validation(metrics: pd.DataFrame, winning_strategy: str) -> pd.DataFrame:
    if not len(metrics):
        return pd.DataFrame()
    data = metrics.copy()
    best = data.groupby("species")["presence_rank"].transform("max")
    data["within_frozen_protocol_win"] = (data["presence_rank"] >= best - 1e-12).astype(float)
    summary = (
        data.groupby("strategy", as_index=False)
        .agg(
            n_species=("species", "nunique"),
            mean_presence_rank=("presence_rank", "mean"),
            median_presence_rank=("presence_rank", "median"),
            win_fraction=("within_frozen_protocol_win", "mean"),
            mean_predictors=("n_predictors", "mean"),
        )
    )
    summary["selected_by_discovery"] = summary["strategy"].astype(str) == str(winning_strategy)
    return summary.sort_values(
        ["selected_by_discovery", "mean_presence_rank", "mean_predictors", "strategy"],
        ascending=[False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _paired_validation_deltas(metrics: pd.DataFrame, winning_strategy: str) -> pd.DataFrame:
    if not len(metrics):
        return pd.DataFrame()
    pivot = metrics.pivot(index="species", columns="strategy", values="presence_rank")
    if winning_strategy not in pivot:
        return pd.DataFrame()
    rows = []
    for comparator in sorted(c for c in pivot.columns if str(c) != str(winning_strategy)):
        paired = pivot[[winning_strategy, comparator]].dropna()
        for species, values in paired.iterrows():
            rows.append(
                {
                    "species": str(species),
                    "winning_strategy": str(winning_strategy),
                    "comparator": str(comparator),
                    "delta_presence_rank": float(values[winning_strategy] - values[comparator]),
                }
            )
    return pd.DataFrame(rows)


def benchmark_product_a_protocol_grid(
    specifications: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    universes: Mapping[str, Sequence[str] | CandidateUniverse],
    *,
    species_col: str = "species",
    taxon_validation_fraction: float = 0.20,
    random_state: int = 42,
    **method_kwargs,
) -> ProductAProtocolValidationResult:
    """Choose data spec × candidate universe × strategy on discovery taxa only.

    Validation is deliberately narrower than discovery: after the winning data
    specification and environmental universe are frozen, only the predeclared
    strategy baselines are evaluated within that frozen data/universe context.
    The winning strategy is marked but not reselected from validation results.
    """
    occurrence_sha, feature_sha, normalized = validate_matched_protocol_specifications(
        specifications,
        universes,
        species_col=species_col,
    )
    if not 0 < taxon_validation_fraction < 1:
        raise ValueError("taxon_validation_fraction must be between 0 and 1")
    species = _common_species(specifications, species_col)
    if len(species) < 4:
        raise ValueError("At least four species shared by all data specifications are required")

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
    discovery_summary = _summarize_discovery(discovery_metrics, normalized)
    winner = discovery_summary.iloc[0]
    winning_spec = str(winner["data_specification"])
    winning_universe = str(winner["universe"])
    winning_strategy = str(winner["strategy"])
    universe = normalized[winning_universe]

    occurrences, background = specifications[winning_spec]
    validation_frames: list[pd.DataFrame] = []
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
            data_specification=winning_spec,
            universe=winning_universe,
            universe_sha256=universe.fingerprint,
            n_candidates=len(universe.predictors),
        )
        frame["selected_by_discovery"] = frame["strategy"].astype(str) == winning_strategy
        validation_frames.append(frame)
    validation_metrics = pd.concat(validation_frames, ignore_index=True) if validation_frames else pd.DataFrame()
    validation_summary = _summarize_validation(validation_metrics, winning_strategy)
    paired = _paired_validation_deltas(validation_metrics, winning_strategy)

    return ProductAProtocolValidationResult(
        occurrence_sha256=occurrence_sha,
        occurrence_feature_sha256=feature_sha,
        discovery_species=discovery_species,
        validation_species=validation_species,
        winning_data_specification=winning_spec,
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
