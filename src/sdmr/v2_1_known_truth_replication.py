"""Repeated unseen-seed replication for Product-A v2.1 selector differentiation.

The first known-truth gate ablation showed that model-pool coverage restored full
prediction surfaces, but canonical ecological recovery and canonical AUC selected
the same procedure while the cross-M robust selector abstained.  This module
predeclares three unused simulation panels and repeats the coverage-complete path
without reading empirical data or changing thresholds, procedures, selectors, or
truth metrics.  Validation truth is opened only after each panel's discovery
selectors are frozen.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .v2_1_known_truth_gate_ablation import (
    CANONICAL_M,
    SELECTORS,
    SimulatedTaxonSpec,
    TRUTH_DIRECTIONS,
    _fit_and_open_validation_truth,
    _procedure_library,
    _rank_truth_evaluation,
    _run_discovery_universe,
    _select_regime,
    _simulate_taxon,
)


@dataclass(frozen=True)
class ReplicationPanel:
    name: str
    discovery: tuple[SimulatedTaxonSpec, ...]
    validation: tuple[SimulatedTaxonSpec, ...]


PANELS = (
    ReplicationPanel(
        "panel_1",
        (
            SimulatedTaxonSpec("gaussian", 71, "discovery"),
            SimulatedTaxonSpec("asymmetric", 81, "discovery"),
            SimulatedTaxonSpec("interaction", 91, "discovery"),
        ),
        (
            SimulatedTaxonSpec("soft_threshold", 101, "validation"),
            SimulatedTaxonSpec("omitted_driver", 111, "validation"),
            SimulatedTaxonSpec("observation_confounded", 121, "validation"),
        ),
    ),
    ReplicationPanel(
        "panel_2",
        (
            SimulatedTaxonSpec("gaussian", 72, "discovery"),
            SimulatedTaxonSpec("asymmetric", 82, "discovery"),
            SimulatedTaxonSpec("interaction", 92, "discovery"),
        ),
        (
            SimulatedTaxonSpec("soft_threshold", 102, "validation"),
            SimulatedTaxonSpec("omitted_driver", 112, "validation"),
            SimulatedTaxonSpec("observation_confounded", 122, "validation"),
        ),
    ),
    ReplicationPanel(
        "panel_3",
        (
            SimulatedTaxonSpec("gaussian", 73, "discovery"),
            SimulatedTaxonSpec("asymmetric", 83, "discovery"),
            SimulatedTaxonSpec("interaction", 93, "discovery"),
        ),
        (
            SimulatedTaxonSpec("soft_threshold", 103, "validation"),
            SimulatedTaxonSpec("omitted_driver", 113, "validation"),
            SimulatedTaxonSpec("observation_confounded", 123, "validation"),
        ),
    ),
)


def _panel_truth_summary(truth: pd.DataFrame) -> pd.DataFrame:
    if truth.empty:
        return pd.DataFrame()
    data = truth.copy()
    data["truth_evaluable"] = data["truth_status"].astype(str).eq("complete")
    aggregation: dict[str, tuple[str, str]] = {
        "n_validation_taxa": ("species", "nunique"),
        "n_truth_evaluable": ("truth_evaluable", "sum"),
        "truth_co_win_fraction": ("truth_co_winner", "mean"),
        "mean_prediction_surface_coverage": (
            "prediction_surface_coverage",
            "mean",
        ),
        "mean_truth_worst_rank": ("truth_worst_metric_rank", "mean"),
        "mean_truth_mean_rank": ("truth_mean_metric_rank", "mean"),
    }
    for metric in TRUTH_DIRECTIONS:
        aggregation[f"mean_{metric}"] = (metric, "mean")
    return (
        data.groupby(["panel", "selector"], as_index=False)
        .agg(**aggregation)
        .sort_values(
            [
                "panel",
                "n_truth_evaluable",
                "mean_truth_worst_rank",
                "mean_truth_mean_rank",
                "selector",
            ],
            ascending=[True, False, True, True, True],
            na_position="last",
            kind="mergesort",
        )
        .reset_index(drop=True)
    )


def _selector_disagreement(selectors: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for panel, group in selectors.groupby("panel", sort=True):
        indexed = group.set_index("selector")
        auc = indexed.loc["canonical_auc"]
        ecology = indexed.loc["canonical_ecology"]
        robust = indexed.loc["robust_ecology"]
        auc_candidate = None if pd.isna(auc["candidate"]) else str(auc["candidate"])
        ecology_candidate = (
            None if pd.isna(ecology["candidate"]) else str(ecology["candidate"])
        )
        robust_candidate = (
            None if pd.isna(robust["candidate"]) else str(robust["candidate"])
        )
        pair_selected = auc_candidate is not None and ecology_candidate is not None
        rows.append(
            {
                "panel": str(panel),
                "canonical_auc_candidate": auc_candidate,
                "canonical_ecology_candidate": ecology_candidate,
                "robust_ecology_candidate": robust_candidate,
                "canonical_pair_selected": pair_selected,
                "canonical_selectors_disagree": bool(
                    pair_selected and auc_candidate != ecology_candidate
                ),
                "robust_selector_selected": robust_candidate is not None,
                "canonical_auc_eligible_candidates": int(
                    auc["n_evidence_eligible_candidates"]
                ),
                "canonical_ecology_eligible_candidates": int(
                    ecology["n_evidence_eligible_candidates"]
                ),
                "robust_ecology_eligible_candidates": int(
                    robust["n_evidence_eligible_candidates"]
                ),
                "robust_selection_error": robust.get("selection_error", None),
            }
        )
    return pd.DataFrame(rows)


def _replication_decision(
    selector_disagreement: pd.DataFrame,
    summary: pd.DataFrame,
) -> pd.DataFrame:
    n_panels = int(selector_disagreement["panel"].nunique())
    n_pair_selected = int(selector_disagreement["canonical_pair_selected"].sum())
    n_disagreement = int(selector_disagreement["canonical_selectors_disagree"].sum())
    n_robust_selected = int(selector_disagreement["robust_selector_selected"].sum())

    ecology_not_worse_panels = 0
    evaluable_disagreement_panels = 0
    for panel in selector_disagreement.loc[
        selector_disagreement["canonical_selectors_disagree"].astype(bool), "panel"
    ]:
        group = summary.loc[summary["panel"].astype(str).eq(str(panel))].set_index(
            "selector"
        )
        if not {"canonical_auc", "canonical_ecology"} <= set(group.index):
            continue
        auc = group.loc["canonical_auc"]
        ecology = group.loc["canonical_ecology"]
        auc_n = int(auc["n_truth_evaluable"])
        ecology_n = int(ecology["n_truth_evaluable"])
        if auc_n == 0 and ecology_n == 0:
            continue
        evaluable_disagreement_panels += 1
        not_worse = ecology_n >= auc_n
        if auc_n > 0 and ecology_n > 0:
            not_worse &= (
                np.isfinite(float(ecology["mean_truth_worst_rank"]))
                and np.isfinite(float(auc["mean_truth_worst_rank"]))
                and float(ecology["mean_truth_worst_rank"])
                <= float(auc["mean_truth_worst_rank"]) + 1e-12
                and float(ecology["mean_truth_mean_rank"])
                <= float(auc["mean_truth_mean_rank"]) + 1e-12
            )
        ecology_not_worse_panels += int(bool(not_worse))

    if n_pair_selected < n_panels:
        decision = "canonical_selection_unstable"
        next_action = (
            "retain v2.1 as development only; do not rebuild empirical confirmation"
        )
    elif n_disagreement == 0:
        decision = "selector_indistinguishable"
        next_action = (
            "current ecological objective is not differentiated from canonical AUC; "
            "open a separately governed surface-stability selector development line"
        )
    elif (
        evaluable_disagreement_panels == n_disagreement
        and ecology_not_worse_panels == n_disagreement
    ):
        decision = "differentiated_supported"
        next_action = (
            "freeze before a newly rebuilt sealed-before-M empirical confirmation"
        )
    else:
        decision = "differentiated_not_supported"
        next_action = (
            "retain negative evidence and redesign the ecological selector before confirmation"
        )
    return pd.DataFrame(
        [
            {
                "decision": decision,
                "scientific_promotion_allowed": False,
                "negative_outcome_accepted": True,
                "n_panels": n_panels,
                "n_panels_with_canonical_pair_selected": n_pair_selected,
                "n_panels_with_canonical_selector_disagreement": n_disagreement,
                "n_disagreement_panels_truth_evaluable": evaluable_disagreement_panels,
                "n_disagreement_panels_ecology_not_worse": ecology_not_worse_panels,
                "n_panels_with_robust_selector_selected": n_robust_selected,
                "next_action": next_action,
            }
        ]
    )


def run_replication(
    *,
    n_cells: int = 1800,
    n_occurrences: int = 180,
    n_target_group: int = 700,
    inner_folds: int = 2,
    outer_folds: int = 2,
    max_predictors: int = 4,
    minimum_predictor_coverage: float = 0.95,
    prediction_surface_coverage_floor: float = 0.95,
) -> dict[str, Any]:
    procedures = _procedure_library(
        inner_folds=inner_folds,
        max_predictors=max_predictors,
    )
    selector_frames: list[pd.DataFrame] = []
    metric_frames: list[pd.DataFrame] = []
    status_frames: list[pd.DataFrame] = []
    coverage_frames: list[pd.DataFrame] = []
    predictor_frames: list[pd.DataFrame] = []
    fit_frames: list[pd.DataFrame] = []
    truth_frames: list[pd.DataFrame] = []
    validation_coverage_frames: list[pd.DataFrame] = []
    evidence_summaries: list[pd.DataFrame] = []

    for panel_index, panel in enumerate(PANELS):
        discovery = {
            spec.taxon: _simulate_taxon(
                spec,
                n_cells=n_cells,
                n_occurrences=n_occurrences,
                n_target_group=n_target_group,
            )
            for spec in panel.discovery
        }
        metrics, status, coverage, predictors = _run_discovery_universe(
            discovery,
            universe="coverage",
            procedures=procedures,
            minimum_predictor_coverage=minimum_predictor_coverage,
            outer_folds=outer_folds,
            random_state_offset=50000 + panel_index * 1000,
        )
        selectors, gates = _select_regime(
            metrics,
            regime="coverage_complete",
            discovery_taxa=tuple(discovery),
            canonical_m=CANONICAL_M,
            expected_outer_folds=outer_folds,
        )
        selectors["panel"] = panel.name
        selector_frames.append(selectors)
        for frame in (metrics, status, coverage, predictors):
            frame["panel"] = panel.name
        metric_frames.append(metrics)
        status_frames.append(status)
        coverage_frames.append(coverage)
        predictor_frames.append(predictors)
        for gate_name, (_, summary) in gates.items():
            summary = summary.copy()
            summary["panel"] = panel.name
            summary["gate"] = gate_name
            evidence_summaries.append(summary)

        validation = {
            spec.taxon: _simulate_taxon(
                spec,
                n_cells=n_cells,
                n_occurrences=n_occurrences,
                n_target_group=n_target_group,
            )
            for spec in panel.validation
        }
        fit, truth, validation_coverage = _fit_and_open_validation_truth(
            validation,
            selectors.drop(columns="panel"),
            procedures,
            minimum_predictor_coverage=minimum_predictor_coverage,
            prediction_surface_coverage_floor=prediction_surface_coverage_floor,
            inner_folds=inner_folds,
            random_state_offset=60000 + panel_index * 1000,
        )
        for frame in (fit, truth, validation_coverage):
            frame["panel"] = panel.name
        fit_frames.append(fit)
        truth_frames.append(truth)
        validation_coverage_frames.append(validation_coverage)

    selectors = pd.concat(selector_frames, ignore_index=True)
    truth = _rank_truth_evaluation(pd.concat(truth_frames, ignore_index=True))
    summary = _panel_truth_summary(truth)
    disagreement = _selector_disagreement(selectors)
    decision = _replication_decision(disagreement, summary)
    return {
        "procedures": procedures,
        "selectors": selectors,
        "discovery_metrics": pd.concat(metric_frames, ignore_index=True),
        "discovery_status": pd.concat(status_frames, ignore_index=True),
        "discovery_coverage": pd.concat(coverage_frames, ignore_index=True),
        "discovery_predictors": pd.concat(predictor_frames, ignore_index=True),
        "evidence_summary": pd.concat(evidence_summaries, ignore_index=True),
        "validation_fit": pd.concat(fit_frames, ignore_index=True),
        "validation_truth": truth,
        "validation_summary": summary,
        "validation_coverage": pd.concat(
            validation_coverage_frames, ignore_index=True
        ),
        "selector_disagreement": disagreement,
        "decision": decision,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--n-cells", type=int, default=1800)
    parser.add_argument("--n-occurrences", type=int, default=180)
    parser.add_argument("--n-target-group", type=int, default=700)
    parser.add_argument("--inner-folds", type=int, default=2)
    parser.add_argument("--outer-folds", type=int, default=2)
    parser.add_argument("--max-predictors", type=int, default=4)
    parser.add_argument("--minimum-predictor-coverage", type=float, default=0.95)
    parser.add_argument(
        "--prediction-surface-coverage-floor", type=float, default=0.95
    )
    args = parser.parse_args(argv)
    result = run_replication(
        n_cells=args.n_cells,
        n_occurrences=args.n_occurrences,
        n_target_group=args.n_target_group,
        inner_folds=args.inner_folds,
        outer_folds=args.outer_folds,
        max_predictors=args.max_predictors,
        minimum_predictor_coverage=args.minimum_predictor_coverage,
        prediction_surface_coverage_floor=args.prediction_surface_coverage_floor,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name in (
        "selectors",
        "discovery_metrics",
        "discovery_status",
        "discovery_coverage",
        "discovery_predictors",
        "evidence_summary",
        "validation_fit",
        "validation_truth",
        "validation_summary",
        "validation_coverage",
        "selector_disagreement",
        "decision",
    ):
        result[name].to_csv(out / f"{name}.csv", index=False)

    contract = {
        "purpose": "product_a_v2_1_repeated_unseen_seed_selector_replication",
        "scientific_promotion_run": False,
        "real_empirical_data_read": False,
        "old_external_sealed_outcomes_read": False,
        "thresholds_or_procedures_changed_after_first_truth_panel": False,
        "selection_never_uses_truth": True,
        "validation_truth_opened_after_panel_selectors_frozen": True,
        "negative_and_abstention_outcomes_accepted": True,
        "regime": "coverage_complete",
        "minimum_predictor_coverage": args.minimum_predictor_coverage,
        "prediction_surface_coverage_floor": args.prediction_surface_coverage_floor,
        "panels": [
            {
                "name": panel.name,
                "discovery": [
                    {"family": spec.family, "seed": spec.seed, "taxon": spec.taxon}
                    for spec in panel.discovery
                ],
                "validation": [
                    {"family": spec.family, "seed": spec.seed, "taxon": spec.taxon}
                    for spec in panel.validation
                ],
            }
            for panel in PANELS
        ],
        "procedure_labels": [p.label for p in result["procedures"]],
        "selectors": list(SELECTORS),
        "n_cells": args.n_cells,
        "n_occurrences": args.n_occurrences,
        "n_target_group": args.n_target_group,
        "inner_folds": args.inner_folds,
        "outer_folds": args.outer_folds,
        "max_predictors": args.max_predictors,
        "decision": str(result["decision"].iloc[0]["decision"]),
        "promotion_requirement": (
            "no empirical confirmation until ecological selection is differentiated "
            "from conventional AUC or that lack of differentiation is accepted as "
            "the scientific conclusion"
        ),
    }
    (out / "replication_contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
