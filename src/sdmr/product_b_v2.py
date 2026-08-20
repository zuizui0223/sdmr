"""Product-B v2: universal process evidence from niche-geometry degradation.

Product A v2.6 selects/tunes procedures for ecological niche recovery.  Product B
must therefore not fall back to asking only whether a raster/process changes AUC.
This module compares a frozen Product-A ecological procedure with the same
procedure after one ecological process domain is removed, then aggregates the
result across taxa, M specifications and spatial folds.

Positive ``loss_*`` values always mean that removing the process made recovery
worse.  The four ecological axes retain Product-A's Pareto semantics and are not
collapsed into a weighted super-score.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Sequence

import numpy as np
import pandas as pd

from .niche_recovery_selection import RECOVERY_DIRECTIONS


KEY_COLUMNS = ("taxon", "M", "fold")
PROCESS_COLUMN = "excluded_process_domain"


@dataclass(frozen=True)
class ProductBProcessSplitResult:
    discovery_taxa: tuple[str, ...]
    validation_taxa: tuple[str, ...]
    process_summary: pd.DataFrame


@dataclass(frozen=True)
class ProductBRepeatedProcessResult:
    split_summary: pd.DataFrame
    process_stability: pd.DataFrame


def _require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise KeyError(f"{label} missing columns: {sorted(missing)}")


def pair_process_knockout_losses(
    base_metrics: pd.DataFrame,
    knockout_metrics: pd.DataFrame,
    *,
    frozen_candidate: str,
    expected_taxa: Sequence[str] | None = None,
    expected_M: Sequence[str] | None = None,
    expected_folds: Sequence[int] | None = None,
    tolerance: float = 1e-12,
) -> pd.DataFrame:
    """Pair frozen base evidence with one-process-out evidence.

    Parameters
    ----------
    base_metrics
        Product-A model-pool fold metrics for the unmodified procedure.
    knockout_metrics
        Metrics produced by the same procedure with one process domain removed.
        ``base_candidate`` must identify the unmodified Product-A candidate.
    frozen_candidate
        The Product-A ecological representative.  Product B does not reselect it.

    Returns
    -------
    DataFrame
        One row per taxon x M x fold x process domain.  For every ecological
        metric, positive loss means that process removal degraded niche recovery.
    """

    required_base = {*KEY_COLUMNS, "candidate", "presence_rank", *RECOVERY_DIRECTIONS}
    required_knockout = {
        *KEY_COLUMNS,
        "candidate",
        "base_candidate",
        PROCESS_COLUMN,
        "presence_rank",
        *RECOVERY_DIRECTIONS,
    }
    _require_columns(base_metrics, required_base, "base_metrics")
    _require_columns(knockout_metrics, required_knockout, "knockout_metrics")

    base = base_metrics.loc[
        base_metrics["candidate"].astype(str).eq(str(frozen_candidate))
    ].copy()
    knockout = knockout_metrics.loc[
        knockout_metrics["base_candidate"].astype(str).eq(str(frozen_candidate))
    ].copy()
    if base.empty:
        raise ValueError(f"no base evidence for frozen candidate {frozen_candidate!r}")
    if knockout.empty:
        raise ValueError(f"no knockout evidence for frozen candidate {frozen_candidate!r}")

    if base.duplicated(list(KEY_COLUMNS)).any():
        raise ValueError("base evidence is not unique by taxon x M x fold")
    knockout_key = [*KEY_COLUMNS, PROCESS_COLUMN]
    if knockout.duplicated(knockout_key).any():
        raise ValueError("knockout evidence is not unique by taxon x M x fold x process")

    if expected_taxa is not None:
        observed = set(base["taxon"].astype(str))
        expected = {str(x) for x in expected_taxa}
        if observed != expected:
            raise ValueError(
                f"base taxon denominator changed: missing={sorted(expected-observed)}, "
                f"extra={sorted(observed-expected)}"
            )
    if expected_M is not None:
        observed = set(base["M"].astype(str))
        expected = {str(x) for x in expected_M}
        if observed != expected:
            raise ValueError(
                f"base M denominator changed: missing={sorted(expected-observed)}, "
                f"extra={sorted(observed-expected)}"
            )
    if expected_folds is not None:
        expected = {int(x) for x in expected_folds}
        for (taxon, m_name), group in base.groupby(["taxon", "M"], sort=False):
            observed = set(pd.to_numeric(group["fold"], errors="raise").astype(int))
            if observed != expected:
                raise ValueError(
                    f"base fold denominator changed for {taxon} / {m_name}: "
                    f"expected={sorted(expected)}, observed={sorted(observed)}"
                )

    base_keep = [*KEY_COLUMNS, "presence_rank", *RECOVERY_DIRECTIONS]
    renamed = base[base_keep].rename(
        columns={
            "presence_rank": "base_presence_rank",
            **{metric: f"base_{metric}" for metric in RECOVERY_DIRECTIONS},
        }
    )
    ko_keep = [*KEY_COLUMNS, PROCESS_COLUMN, "presence_rank", *RECOVERY_DIRECTIONS]
    ko = knockout[ko_keep].rename(
        columns={
            "presence_rank": "without_process_presence_rank",
            **{metric: f"without_process_{metric}" for metric in RECOVERY_DIRECTIONS},
        }
    )
    paired = ko.merge(renamed, on=list(KEY_COLUMNS), how="inner", validate="many_to_one")
    if len(paired) != len(ko):
        raise ValueError("knockout evidence could not be fully paired to frozen base evidence")

    paired["presence_rank_loss"] = (
        pd.to_numeric(paired["base_presence_rank"], errors="coerce")
        - pd.to_numeric(paired["without_process_presence_rank"], errors="coerce")
    )
    loss_columns: list[str] = []
    for metric, direction in RECOVERY_DIRECTIONS.items():
        base_values = pd.to_numeric(paired[f"base_{metric}"], errors="coerce")
        without_values = pd.to_numeric(paired[f"without_process_{metric}"], errors="coerce")
        loss_col = f"loss_{metric}"
        if direction == "max":
            paired[loss_col] = base_values - without_values
        elif direction == "min":
            paired[loss_col] = without_values - base_values
        else:
            raise ValueError(f"unknown recovery direction for {metric}: {direction}")
        loss_columns.append(loss_col)

    finite = np.isfinite(paired[loss_columns].to_numpy(float)).all(axis=1)
    losses = paired[loss_columns].to_numpy(float)
    nonworse = (losses >= -float(tolerance)).all(axis=1)
    strictly_worse = (losses > float(tolerance)).any(axis=1)
    nonbetter = (losses <= float(tolerance)).all(axis=1)
    strictly_better = (losses < -float(tolerance)).any(axis=1)
    paired["niche_pareto_worsened_by_drop"] = finite & nonworse & strictly_worse
    paired["niche_pareto_improved_by_drop"] = finite & nonbetter & strictly_better
    paired["niche_tradeoff_after_drop"] = finite & ~(
        paired["niche_pareto_worsened_by_drop"] | paired["niche_pareto_improved_by_drop"]
    )
    paired["niche_axes_worsened"] = (losses > float(tolerance)).sum(axis=1)
    paired["niche_axes_improved"] = (losses < -float(tolerance)).sum(axis=1)
    return paired.sort_values(["taxon", PROCESS_COLUMN, "M", "fold"], kind="mergesort").reset_index(drop=True)


def summarize_taxon_process_support(
    paired_losses: pd.DataFrame,
    *,
    expected_M: Sequence[str],
    expected_folds: Sequence[int],
    min_pareto_worsening_fraction: float = 2.0 / 3.0,
    max_pareto_improvement_fraction: float = 1.0 / 3.0,
) -> pd.DataFrame:
    """Collapse M x fold evidence to a taxon-level process necessity profile."""

    required = {
        "taxon",
        "M",
        "fold",
        PROCESS_COLUMN,
        "presence_rank_loss",
        "niche_pareto_worsened_by_drop",
        "niche_pareto_improved_by_drop",
        *{f"loss_{metric}" for metric in RECOVERY_DIRECTIONS},
    }
    _require_columns(paired_losses, required, "paired_losses")
    if not 0 <= min_pareto_worsening_fraction <= 1:
        raise ValueError("min_pareto_worsening_fraction must be in [0, 1]")
    if not 0 <= max_pareto_improvement_fraction <= 1:
        raise ValueError("max_pareto_improvement_fraction must be in [0, 1]")

    expected_m = {str(x) for x in expected_M}
    expected_f = {int(x) for x in expected_folds}
    expected_pairs = len(expected_m) * len(expected_f)
    rows: list[dict[str, object]] = []
    for (taxon, process), group in paired_losses.groupby(["taxon", PROCESS_COLUMN], sort=True):
        m_values = set(group["M"].astype(str))
        fold_cells = set(
            zip(
                group["M"].astype(str),
                pd.to_numeric(group["fold"], errors="coerce").astype("Int64"),
            )
        )
        expected_cells = {(m, f) for m in expected_m for f in expected_f}
        complete = (
            len(group) == expected_pairs
            and m_values == expected_m
            and fold_cells == expected_cells
        )
        worsening_fraction = float(group["niche_pareto_worsened_by_drop"].astype(bool).mean())
        improvement_fraction = float(group["niche_pareto_improved_by_drop"].astype(bool).mean())
        if complete and worsening_fraction >= min_pareto_worsening_fraction and improvement_fraction <= max_pareto_improvement_fraction:
            status = "supported_process_constraint"
        elif complete and improvement_fraction >= min_pareto_worsening_fraction:
            status = "refuted_process_constraint"
        else:
            status = "unresolved"
        row: dict[str, object] = {
            "taxon": str(taxon),
            "process_domain": str(process),
            "complete_M_fold_evidence": bool(complete),
            "n_pairs": int(len(group)),
            "pareto_worsening_fraction": worsening_fraction,
            "pareto_improvement_fraction": improvement_fraction,
            "mean_presence_rank_loss": float(pd.to_numeric(group["presence_rank_loss"], errors="coerce").mean()),
            "status": status,
        }
        for metric in RECOVERY_DIRECTIONS:
            values = pd.to_numeric(group[f"loss_{metric}"], errors="coerce")
            row[f"median_loss_{metric}"] = float(values.median())
            row[f"positive_loss_fraction_{metric}"] = float((values > 0).mean())
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["process_domain", "taxon"], kind="mergesort").reset_index(drop=True)


def discover_validate_process_core(
    taxon_process_summary: pd.DataFrame,
    *,
    validation_fraction: float = 1.0 / 3.0,
    min_taxon_support_fraction: float = 2.0 / 3.0,
    random_state: int = 42,
) -> ProductBProcessSplitResult:
    """Discover universal process candidates in some taxa and confirm on unseen taxa."""

    required = {"taxon", "process_domain", "status", "complete_M_fold_evidence"}
    _require_columns(taxon_process_summary, required, "taxon_process_summary")
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1")
    if not 0 <= min_taxon_support_fraction <= 1:
        raise ValueError("min_taxon_support_fraction must be in [0, 1]")

    data = taxon_process_summary.copy()
    taxa = sorted(data["taxon"].astype(str).unique())
    if len(taxa) < 4:
        raise ValueError("Product-B taxon transfer requires at least four taxa")
    if not data["complete_M_fold_evidence"].astype(bool).all():
        raise ValueError("Product-B universal-process inference requires complete M x fold evidence")

    rng = np.random.default_rng(int(random_state))
    shuffled = np.asarray(taxa, dtype=object)
    rng.shuffle(shuffled)
    n_validation = max(1, int(round(len(shuffled) * float(validation_fraction))))
    n_validation = min(n_validation, len(shuffled) - 2)
    validation_taxa = tuple(sorted(str(x) for x in shuffled[:n_validation]))
    discovery_taxa = tuple(sorted(str(x) for x in shuffled[n_validation:]))

    rows: list[dict[str, object]] = []
    processes = sorted(data["process_domain"].astype(str).unique())
    for process in processes:
        d = data.loc[
            data["process_domain"].astype(str).eq(process)
            & data["taxon"].astype(str).isin(discovery_taxa)
        ]
        v = data.loc[
            data["process_domain"].astype(str).eq(process)
            & data["taxon"].astype(str).isin(validation_taxa)
        ]
        if d["taxon"].nunique() != len(discovery_taxa) or v["taxon"].nunique() != len(validation_taxa):
            raise ValueError(f"process {process!r} does not cover every discovery/validation taxon")
        d_support = float(d["status"].astype(str).eq("supported_process_constraint").mean())
        v_support = float(v["status"].astype(str).eq("supported_process_constraint").mean())
        v_refuted = float(v["status"].astype(str).eq("refuted_process_constraint").mean())
        discovery_core = d_support >= min_taxon_support_fraction
        validation_confirmed = discovery_core and v_support >= min_taxon_support_fraction
        rows.append({
            "process_domain": process,
            "n_discovery_taxa": len(discovery_taxa),
            "n_validation_taxa": len(validation_taxa),
            "discovery_support_fraction": d_support,
            "validation_support_fraction": v_support,
            "validation_refuted_fraction": v_refuted,
            "discovery_core_candidate": bool(discovery_core),
            "validation_confirmed": bool(validation_confirmed),
        })
    return ProductBProcessSplitResult(
        discovery_taxa=discovery_taxa,
        validation_taxa=validation_taxa,
        process_summary=pd.DataFrame(rows).sort_values(
            ["validation_confirmed", "validation_support_fraction", "discovery_support_fraction", "process_domain"],
            ascending=[False, False, False, True],
            kind="mergesort",
        ).reset_index(drop=True),
    )


def repeat_process_core_splits(
    taxon_process_summary: pd.DataFrame,
    *,
    seeds: Iterable[int] = (11, 22, 33, 44, 55),
    validation_fraction: float = 1.0 / 3.0,
    min_taxon_support_fraction: float = 2.0 / 3.0,
) -> ProductBRepeatedProcessResult:
    """Repeat unseen-taxon confirmation without refitting Product A or changing thresholds."""

    frames: list[pd.DataFrame] = []
    seed_list = [int(x) for x in seeds]
    for split_id, seed in enumerate(seed_list):
        result = discover_validate_process_core(
            taxon_process_summary,
            validation_fraction=validation_fraction,
            min_taxon_support_fraction=min_taxon_support_fraction,
            random_state=seed,
        )
        frame = result.process_summary.copy()
        frame["split_id"] = split_id
        frame["seed"] = seed
        frame["discovery_taxa"] = ",".join(result.discovery_taxa)
        frame["validation_taxa"] = ",".join(result.validation_taxa)
        frames.append(frame)
    split_summary = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if split_summary.empty:
        stability = pd.DataFrame(
            columns=["process_domain", "n_splits", "discovery_core_stability", "validation_confirmation_stability"]
        )
    else:
        stability = (
            split_summary.groupby("process_domain", as_index=False)
            .agg(
                n_splits=("split_id", "nunique"),
                discovery_core_stability=("discovery_core_candidate", "mean"),
                validation_confirmation_stability=("validation_confirmed", "mean"),
                mean_validation_support_fraction=("validation_support_fraction", "mean"),
                mean_validation_refuted_fraction=("validation_refuted_fraction", "mean"),
            )
            .sort_values(
                ["validation_confirmation_stability", "discovery_core_stability", "mean_validation_support_fraction", "process_domain"],
                ascending=[False, False, False, True],
                kind="mergesort",
            )
            .reset_index(drop=True)
        )
    return ProductBRepeatedProcessResult(split_summary=split_summary, process_stability=stability)
