"""Candidate-environment universe tuning for Product A.

The variable universe itself is a modelling choice. SDMR therefore allows
BIOCLIM19, the broader precomputed CHELSA-bioclim set, and the complete active
candidate manifest to compete under the same discovery/validation taxon and
sealed-spatial information barriers.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from .drivers import validate_candidate_manifest
from .method import benchmark_species_methods


@dataclass(frozen=True)
class CandidateUniverse:
    name: str
    predictors: tuple[str, ...]

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(list(self.predictors), separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass
class UniverseMethodValidationResult:
    discovery_species: list[str]
    validation_species: list[str]
    winning_universe: str
    winning_strategy: str
    winning_predictors: list[str]
    winning_universe_sha256: str
    discovery_metrics: pd.DataFrame
    discovery_summary: pd.DataFrame
    validation_metrics: pd.DataFrame


def candidate_universes_from_manifest(manifest: pd.DataFrame) -> dict[str, CandidateUniverse]:
    """Build nested, interpretable predictor universes from the active manifest."""

    data = validate_candidate_manifest(manifest)
    all_predictors = data["predictor"].astype(str).tolist()
    bioclim19 = data.loc[data["candidate_class"].astype(str) == "core_climate", "predictor"].astype(str).tolist()
    chelsa_bioclim = data.loc[data["source"].astype(str) == "CHELSA-bioclim", "predictor"].astype(str).tolist()
    if not bioclim19:
        raise ValueError("manifest does not define a non-empty core_climate/BIOCLIM universe")
    if not chelsa_bioclim:
        raise ValueError("manifest does not define a non-empty CHELSA-bioclim universe")
    if not set(bioclim19).issubset(set(chelsa_bioclim)):
        raise ValueError("core_climate predictors must be contained in CHELSA-bioclim universe")
    if not set(chelsa_bioclim).issubset(set(all_predictors)):
        raise ValueError("CHELSA-bioclim universe must be contained in active_all")
    return {
        "bioclim19": CandidateUniverse("bioclim19", tuple(bioclim19)),
        "chelsa_bioclim": CandidateUniverse("chelsa_bioclim", tuple(chelsa_bioclim)),
        "active_all": CandidateUniverse("active_all", tuple(all_predictors)),
    }


def _normalize_universes(
    universes: Mapping[str, Sequence[str] | CandidateUniverse],
) -> dict[str, CandidateUniverse]:
    out: dict[str, CandidateUniverse] = {}
    for name, value in universes.items():
        if isinstance(value, CandidateUniverse):
            universe = value
        else:
            universe = CandidateUniverse(str(name), tuple(dict.fromkeys(str(x) for x in value)))
        if not universe.predictors:
            raise ValueError(f"candidate universe {name!r} is empty")
        if universe.name != str(name):
            universe = CandidateUniverse(str(name), universe.predictors)
        out[str(name)] = universe
    if not out:
        raise ValueError("At least one candidate universe is required")
    return out


def _summarize_universe_method_metrics(metrics: pd.DataFrame, universes: Mapping[str, CandidateUniverse]) -> pd.DataFrame:
    required = {"species", "universe", "strategy", "presence_rank", "n_predictors"}
    missing = required - set(metrics.columns)
    if missing:
        raise KeyError(f"discovery metrics missing columns: {sorted(missing)}")
    data = metrics.copy()
    best = data.groupby("species")["presence_rank"].transform("max")
    data["global_win"] = (data["presence_rank"] >= best - 1e-12).astype(float)
    summary = (
        data.groupby(["universe", "strategy"], as_index=False)
        .agg(
            n_species=("species", "nunique"),
            mean_presence_rank=("presence_rank", "mean"),
            median_presence_rank=("presence_rank", "median"),
            global_win_fraction=("global_win", "mean"),
            mean_predictors=("n_predictors", "mean"),
        )
    )
    summary["n_candidates"] = summary["universe"].map(lambda name: len(universes[str(name)].predictors))
    summary["universe_sha256"] = summary["universe"].map(lambda name: universes[str(name)].fingerprint)
    return summary.sort_values(
        ["mean_presence_rank", "global_win_fraction", "mean_predictors", "n_candidates", "universe", "strategy"],
        ascending=[False, False, True, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def benchmark_method_universe_taxon_split(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    universes: Mapping[str, Sequence[str] | CandidateUniverse],
    *,
    species_col: str = "species",
    taxon_validation_fraction: float = 0.20,
    random_state: int = 42,
    **method_kwargs,
) -> UniverseMethodValidationResult:
    """Choose predictor universe + method on discovery taxa; test only that choice on unseen taxa.

    The same per-species random state is reused across candidate universes so all
    universe/strategy comparisons see identical spatially sealed answer-check
    blocks. Validation taxa are not used to choose the winning combination.
    """

    if not 0 < taxon_validation_fraction < 1:
        raise ValueError("taxon_validation_fraction must be between 0 and 1")
    normalized = _normalize_universes(universes)
    species = sorted(set(occurrences[species_col].astype(str)) & set(background[species_col].astype(str)))
    if len(species) < 4:
        raise ValueError("At least four species are required for universe-level taxon validation")

    rng = np.random.default_rng(random_state)
    shuffled = np.array(species, dtype=object)
    rng.shuffle(shuffled)
    n_validation = max(1, int(round(len(shuffled) * taxon_validation_fraction)))
    n_validation = min(n_validation, len(shuffled) - 2)
    validation_species = sorted(str(x) for x in shuffled[:n_validation])
    discovery_species = sorted(str(x) for x in shuffled[n_validation:])

    discovery_frames: list[pd.DataFrame] = []
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
                    universe=universe_name,
                    universe_sha256=universe.fingerprint,
                    n_candidates=len(universe.predictors),
                )
            )
    discovery_metrics = pd.concat(discovery_frames, ignore_index=True)
    discovery_summary = _summarize_universe_method_metrics(discovery_metrics, normalized)
    winner = discovery_summary.iloc[0]
    winning_universe = str(winner["universe"])
    winning_strategy = str(winner["strategy"])
    universe = normalized[winning_universe]

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
        selected = result.sealed_metrics.loc[
            result.sealed_metrics["strategy"].astype(str) == winning_strategy
        ].copy()
        validation_frames.append(
            selected.assign(
                universe=winning_universe,
                universe_sha256=universe.fingerprint,
                n_candidates=len(universe.predictors),
                selected_by_discovery=True,
            )
        )
    validation_metrics = pd.concat(validation_frames, ignore_index=True) if validation_frames else pd.DataFrame()
    return UniverseMethodValidationResult(
        discovery_species=discovery_species,
        validation_species=validation_species,
        winning_universe=winning_universe,
        winning_strategy=winning_strategy,
        winning_predictors=list(universe.predictors),
        winning_universe_sha256=universe.fingerprint,
        discovery_metrics=discovery_metrics,
        discovery_summary=discovery_summary,
        validation_metrics=validation_metrics,
    )
