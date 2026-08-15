"""Contrast conventional score-selected SDMs with the SDMR transfer-stable selector.

AUC/Boyce are useful local model-evaluation scores; Product A asks a different
question: which *selection procedure* survives distribution shift across taxa
and plausible accessible-area (M) assumptions.

Three discovery-frozen selectors are compared:

- ``canonical_m_auc``: highest mean presence-background AUC-equivalent score in
  one predeclared canonical M;
- ``canonical_m_boyce``: highest mean Boyce score in that same M;
- ``sdmr_m_robust``: the universe x strategy selected by the robust cross-M
  Product-A procedure.

A fourth, deliberately stronger conventional baseline is evaluated per unseen
species x M case:

- ``local_nested_auc``: run the full candidate universe x strategy benchmark on
  that species' *model pool only*, choose the row with the highest inner spatial
  CV AUC-equivalent score, and then open the already sealed outer rows. Thus
  SDMR is compared not only with a fixed conventional recipe but also with the
  ordinary practice of tuning a model locally by nested spatial CV.

No selector may use its outer sealed score to choose itself. No weighted
super-score is invented: the output is a paired transfer test on identical
unseen species x M cases. We also report the descriptive inner-to-outer
``generalization_gap`` (outer sealed AUC-equivalent minus inner spatial-CV
AUC-equivalent) so optimism caused by local tuning is visible rather than folded
into a new composite score.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .method import benchmark_species_methods
from .universe import CandidateUniverse


@dataclass
class SelectorContrastResult:
    choices: pd.DataFrame
    transfer_metrics: pd.DataFrame
    transfer_summary: pd.DataFrame
    paired_deltas: pd.DataFrame


def _normalized_universes(
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


def _best_discovery_combo(
    discovery_metrics: pd.DataFrame,
    *,
    canonical_specification: str,
    metric: str,
) -> tuple[str, str, float]:
    required = {"data_specification", "universe", "strategy", metric, "n_predictors"}
    missing = required - set(discovery_metrics.columns)
    if missing:
        raise KeyError(f"discovery metrics missing columns: {sorted(missing)}")
    data = discovery_metrics.loc[
        discovery_metrics["data_specification"].astype(str) == str(canonical_specification)
    ].copy()
    if not len(data):
        raise ValueError(f"canonical M specification {canonical_specification!r} is absent from discovery metrics")
    data[metric] = pd.to_numeric(data[metric], errors="coerce")
    summary = (
        data.groupby(["universe", "strategy"], as_index=False)
        .agg(
            selector_score=(metric, "mean"),
            n_finite=(metric, lambda x: int(np.isfinite(pd.to_numeric(x, errors="coerce")).sum())),
            mean_predictors=("n_predictors", "mean"),
        )
    )
    summary = summary.loc[
        (summary["n_finite"] > 0) & summary["selector_score"].notna()
    ].copy()
    if not len(summary):
        raise ValueError(f"no finite {metric} values are available in canonical M {canonical_specification!r}")
    summary = summary.sort_values(
        ["selector_score", "mean_predictors", "universe", "strategy"],
        ascending=[False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    row = summary.iloc[0]
    return str(row["universe"]), str(row["strategy"]), float(row["selector_score"])


def freeze_selector_choices(
    discovery_metrics: pd.DataFrame,
    *,
    canonical_specification: str,
    sdmr_universe: str,
    sdmr_strategy: str,
) -> pd.DataFrame:
    """Freeze cross-taxon selectors using discovery evidence only."""
    auc_u, auc_s, auc_score = _best_discovery_combo(
        discovery_metrics,
        canonical_specification=canonical_specification,
        metric="presence_rank",
    )
    boyce_u, boyce_s, boyce_score = _best_discovery_combo(
        discovery_metrics,
        canonical_specification=canonical_specification,
        metric="boyce",
    )
    rows = [
        {
            "selector": "sdmr_m_robust",
            "universe": str(sdmr_universe),
            "strategy": str(sdmr_strategy),
            "selection_metric": "cross_M_within_case_rank",
            "selection_score": np.nan,
            "canonical_specification": str(canonical_specification),
        },
        {
            "selector": "canonical_m_auc",
            "universe": auc_u,
            "strategy": auc_s,
            "selection_metric": "presence_rank_auc_equivalent",
            "selection_score": auc_score,
            "canonical_specification": str(canonical_specification),
        },
        {
            "selector": "canonical_m_boyce",
            "universe": boyce_u,
            "strategy": boyce_s,
            "selection_metric": "boyce",
            "selection_score": boyce_score,
            "canonical_specification": str(canonical_specification),
        },
    ]
    choices = pd.DataFrame(rows)
    sdmr_pair = (str(sdmr_universe), str(sdmr_strategy))
    choices["same_method_as_sdmr"] = [
        (str(row.universe), str(row.strategy)) == sdmr_pair for row in choices.itertuples(index=False)
    ]
    return choices


def _summarize_transfer(metrics: pd.DataFrame) -> pd.DataFrame:
    if not len(metrics):
        return pd.DataFrame()
    data = metrics.copy()
    data["presence_rank"] = pd.to_numeric(data["presence_rank"], errors="coerce")
    data["inner_presence_rank"] = pd.to_numeric(data.get("inner_presence_rank"), errors="coerce")
    data["generalization_gap"] = data["presence_rank"] - data["inner_presence_rank"]
    case_cols = ["data_specification", "species"]
    best = data.groupby(case_cols)["presence_rank"].transform("max")
    data["case_win"] = (data["presence_rank"] >= best - 1e-12).astype(float)
    per_spec = (
        data.groupby(["selector", "data_specification"], as_index=False)
        .agg(
            spec_mean_presence_rank=("presence_rank", "mean"),
            spec_mean_generalization_gap=("generalization_gap", "mean"),
        )
    )
    robustness = (
        per_spec.groupby("selector", as_index=False)
        .agg(
            worst_M_mean_presence_rank=("spec_mean_presence_rank", "min"),
            best_M_mean_presence_rank=("spec_mean_presence_rank", "max"),
            sd_M_mean_presence_rank=("spec_mean_presence_rank", "std"),
            worst_M_mean_generalization_gap=("spec_mean_generalization_gap", "min"),
            n_specs=("data_specification", "nunique"),
        )
    )
    summary = (
        data.groupby("selector", as_index=False)
        .agg(
            n_species=("species", "nunique"),
            n_cases=("presence_rank", "size"),
            mean_inner_presence_rank=("inner_presence_rank", "mean"),
            mean_presence_rank=("presence_rank", "mean"),
            median_presence_rank=("presence_rank", "median"),
            mean_generalization_gap=("generalization_gap", "mean"),
            median_generalization_gap=("generalization_gap", "median"),
            mean_boyce=("boyce", "mean"),
            case_win_fraction=("case_win", "mean"),
        )
        .merge(robustness, on="selector", how="left")
    )
    return summary.sort_values(
        ["mean_presence_rank", "worst_M_mean_presence_rank", "case_win_fraction", "selector"],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _paired_against_sdmr(metrics: pd.DataFrame) -> pd.DataFrame:
    if not len(metrics):
        return pd.DataFrame()
    pivot = metrics.pivot_table(
        index=["data_specification", "species"],
        columns="selector",
        values="presence_rank",
        aggfunc="first",
    )
    if "sdmr_m_robust" not in pivot.columns:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for comparator in ("canonical_m_auc", "canonical_m_boyce", "local_nested_auc"):
        if comparator not in pivot.columns:
            continue
        paired = pivot[["sdmr_m_robust", comparator]].dropna()
        for (specification, species), values in paired.iterrows():
            rows.append(
                {
                    "data_specification": str(specification),
                    "species": str(species),
                    "reference_selector": "sdmr_m_robust",
                    "comparator": comparator,
                    "delta_presence_rank": float(values["sdmr_m_robust"] - values[comparator]),
                }
            )
    return pd.DataFrame(rows)


def evaluate_selector_transfer(
    specifications: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    universes: Mapping[str, Sequence[str] | CandidateUniverse],
    choices: pd.DataFrame,
    validation_species: Sequence[str],
    *,
    species_col: str = "species",
    random_state: int = 42,
    **method_kwargs,
) -> SelectorContrastResult:
    """Evaluate frozen and local nested selectors on identical unseen cases."""
    required = {"selector", "universe", "strategy"}
    missing = required - set(choices.columns)
    if missing:
        raise KeyError(f"selector choices missing columns: {sorted(missing)}")
    normalized = _normalized_universes(universes)
    species = [str(x) for x in validation_species]
    if not species:
        raise ValueError("validation_species must not be empty")

    cache: dict[tuple[str, str, str], pd.DataFrame] = {}

    def benchmark_rows(
        spec_name: str,
        occurrences: pd.DataFrame,
        background: pd.DataFrame,
        universe_name: str,
        species_name: str,
        species_index: int,
    ) -> pd.DataFrame:
        key = (str(spec_name), str(universe_name), str(species_name))
        if key not in cache:
            universe = normalized[str(universe_name)]
            benchmark = benchmark_species_methods(
                occurrences,
                background,
                universe.predictors,
                species_name=species_name,
                species_col=species_col,
                random_state=random_state + 100_000 + species_index,
                **method_kwargs,
            )
            cache[key] = benchmark.sealed_metrics.copy()
        return cache[key]

    rows: list[pd.DataFrame] = []
    for choice in choices.itertuples(index=False):
        selector = str(choice.selector)
        universe_name = str(choice.universe)
        strategy = str(choice.strategy)
        if universe_name not in normalized:
            raise KeyError(f"unknown selected universe {universe_name!r}")
        for spec_name, (occurrences, background) in specifications.items():
            for i, species_name in enumerate(species):
                metrics = benchmark_rows(
                    str(spec_name), occurrences, background, universe_name, species_name, i
                )
                selected = metrics.loc[metrics["strategy"].astype(str) == strategy].copy()
                if len(selected) != 1:
                    raise ValueError(
                        f"selector {selector!r} expected one strategy row for {species_name!r} "
                        f"in {spec_name!r}, found {len(selected)}"
                    )
                selected["selector"] = selector
                selected["selection_metric"] = str(choice.selection_metric)
                selected["selected_universe"] = universe_name
                selected["selected_strategy"] = strategy
                selected["data_specification"] = str(spec_name)
                rows.append(selected)

    # Strong conventional baseline: for each unseen species x M case, select
    # the candidate model by *inner* spatial-CV AUC only. Outer sealed metrics
    # are never consulted until after the row has been frozen.
    for spec_name, (occurrences, background) in specifications.items():
        for i, species_name in enumerate(species):
            candidate_frames: list[pd.DataFrame] = []
            for universe_name in normalized:
                frame = benchmark_rows(
                    str(spec_name), occurrences, background, universe_name, species_name, i
                ).copy()
                frame["selected_universe"] = str(universe_name)
                candidate_frames.append(frame)
            candidates = pd.concat(candidate_frames, ignore_index=True)
            candidates["inner_presence_rank"] = pd.to_numeric(
                candidates["inner_presence_rank"], errors="coerce"
            )
            candidates = candidates.loc[np.isfinite(candidates["inner_presence_rank"])].copy()
            if not len(candidates):
                raise ValueError(
                    f"local_nested_auc found no finite inner-CV candidate for {species_name!r} in {spec_name!r}"
                )
            candidates = candidates.sort_values(
                ["inner_presence_rank", "n_predictors", "selected_universe", "strategy"],
                ascending=[False, True, True, True],
                kind="mergesort",
            ).reset_index(drop=True)
            selected = candidates.iloc[[0]].copy()
            selected["selector"] = "local_nested_auc"
            selected["selection_metric"] = "model_pool_inner_spatial_cv_presence_rank"
            selected["selected_strategy"] = selected["strategy"].astype(str)
            selected["data_specification"] = str(spec_name)
            rows.append(selected)

    metrics = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if len(metrics):
        metrics["inner_presence_rank"] = pd.to_numeric(metrics["inner_presence_rank"], errors="coerce")
        metrics["presence_rank"] = pd.to_numeric(metrics["presence_rank"], errors="coerce")
        metrics["generalization_gap"] = metrics["presence_rank"] - metrics["inner_presence_rank"]
    return SelectorContrastResult(
        choices=choices.reset_index(drop=True),
        transfer_metrics=metrics,
        transfer_summary=_summarize_transfer(metrics),
        paired_deltas=_paired_against_sdmr(metrics),
    )


def benchmark_selector_contrast(
    specifications: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]],
    universes: Mapping[str, Sequence[str] | CandidateUniverse],
    discovery_metrics: pd.DataFrame,
    validation_species: Sequence[str],
    *,
    canonical_specification: str,
    sdmr_universe: str,
    sdmr_strategy: str,
    species_col: str = "species",
    random_state: int = 42,
    **method_kwargs,
) -> SelectorContrastResult:
    """Freeze selectors without validation feedback, then compare transfer."""
    choices = freeze_selector_choices(
        discovery_metrics,
        canonical_specification=canonical_specification,
        sdmr_universe=sdmr_universe,
        sdmr_strategy=sdmr_strategy,
    )
    return evaluate_selector_transfer(
        specifications,
        universes,
        choices,
        validation_species,
        species_col=species_col,
        random_state=random_state,
        **method_kwargs,
    )
