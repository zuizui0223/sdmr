"""Predeclared unseen known-truth experiment for Product-A v2.2.

This line evaluates a procedure-level ``stable_ecology`` selector after Product-A
v2.1 ended in ``differentiated_not_supported``. Real empirical data and all
previously opened known-truth seeds are excluded. Generating truth is opened only
after discovery-panel selectors are frozen.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .candidate_outer_fold_evidence import require_complete_outer_fold_evidence
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES
from .model_pool_predictor_admissibility import (
    select_model_pool_admissible_predictors,
)
from .niche_recovery_perturbation import (
    select_perturbation_robust_niche_recovery_protocol,
)
from .niche_recovery_procedure import (
    RecoveryProcedure,
    RecoveryProcedureBenchmark,
    select_recovery_procedure,
)
from .niche_recovery_selection import RECOVERY_DIRECTIONS
from .niche_recovery_stability import STABILITY_DIRECTIONS
from .prepared_recovery_procedure_cli import _mean_auc_winner
from .procedure_surface_stability import (
    benchmark_recovery_procedures_with_surface_stability,
    select_stable_recovery_procedure,
)
from .v2_1_known_truth_gate_ablation import (
    CANONICAL_M,
    CANDIDATE_ECOLOGICAL_PREDICTORS,
    M_SPECS,
    SimulatedTaxonSpec,
    TRUTH_DIRECTIONS,
    _fit_and_open_validation_truth,
    _model_only_frame,
    _nested_background_perturbations,
    _procedure_library,
    _rank_truth_evaluation,
    _simulate_taxon,
)
from .validation import make_spatial_partition


SELECTORS = (
    "canonical_auc",
    "canonical_ecology",
    "robust_ecology",
    "stable_ecology",
)
EXPECTED_SELECTION_ORDER = (
    "complete_candidate_evidence",
    "absolute_prediction_adequacy",
    "mean_ecological_recovery_pareto",
    "common_reference_surface_stability_pareto_minimax",
    "parsimony_tiebreak",
)
DECISION_STATES = (
    "surface_stability_supported",
    "surface_stability_indistinguishable",
    "surface_stability_not_supported",
    "surface_stability_unstable_or_abstained",
)


@dataclass(frozen=True)
class SurfaceStabilityPanel:
    name: str
    discovery: tuple[SimulatedTaxonSpec, ...]
    validation: tuple[SimulatedTaxonSpec, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_predeclared_panels(
    path: str | Path,
) -> tuple[dict[str, object], tuple[SurfaceStabilityPanel, ...]]:
    """Load and validate the frozen v2.2 panel contract."""

    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if payload.get("scientific_promotion_run") is not False:
        raise ValueError("v2.2 known-truth panels must not be a promotion run")
    if payload.get("real_empirical_data_read") is not False:
        raise ValueError("v2.2 known-truth panels must not read empirical data")
    if payload.get("old_external_sealed_outcomes_read") is not False:
        raise ValueError("old external sealed outcomes are forbidden")
    if tuple(payload.get("selectors", ())) != SELECTORS:
        raise ValueError("predeclared selectors do not match the v2.2 contract")
    if tuple(payload.get("selection_order", ())) != EXPECTED_SELECTION_ORDER:
        raise ValueError("v2.2 staged selection order changed")
    if set(payload.get("decision_states", ())) != set(DECISION_STATES):
        raise ValueError("v2.2 decision states changed")

    exclusion = payload.get("opened_known_truth_seeds_excluded", {})
    maximum_opened_seed = int(exclusion.get("maximum", -1))
    panels: list[SurfaceStabilityPanel] = []
    seen_names: set[str] = set()
    seen_seeds: set[int] = set()
    for raw_panel in payload.get("panels", ()):
        name = str(raw_panel["name"])
        if name in seen_names:
            raise ValueError(f"duplicate panel name: {name}")
        seen_names.add(name)
        roles: dict[str, tuple[SimulatedTaxonSpec, ...]] = {}
        for role in ("discovery", "validation"):
            specs: list[SimulatedTaxonSpec] = []
            for item in raw_panel.get(role, ()):
                family = str(item["family"])
                seed = int(item["seed"])
                if family not in KNOWN_TRUTH_FAMILIES:
                    raise ValueError(f"unknown known-truth family: {family}")
                if seed <= maximum_opened_seed:
                    raise ValueError(
                        f"seed {seed} is already opened and cannot validate v2.2"
                    )
                if seed in seen_seeds:
                    raise ValueError(f"duplicate v2.2 seed: {seed}")
                seen_seeds.add(seed)
                specs.append(SimulatedTaxonSpec(family, seed, role))
            if len(specs) != 3:
                raise ValueError(f"{name} must have three {role} taxa")
            roles[role] = tuple(specs)
        panels.append(
            SurfaceStabilityPanel(
                name=name,
                discovery=roles["discovery"],
                validation=roles["validation"],
            )
        )
    if len(panels) != 3:
        raise ValueError("v2.2 requires exactly three predeclared panels")
    return payload, tuple(panels)


def _run_discovery_panel(
    panel: SurfaceStabilityPanel,
    *,
    procedures: tuple[RecoveryProcedure, ...],
    n_cells: int,
    n_occurrences: int,
    n_target_group: int,
    minimum_predictor_coverage: float,
    outer_folds: int,
    random_state_offset: int,
    max_stability_reference_rows: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    simulations = {
        spec.taxon: _simulate_taxon(
            spec,
            n_cells=n_cells,
            n_occurrences=n_occurrences,
            n_target_group=n_target_group,
        )
        for spec in panel.discovery
    }
    metric_frames: list[pd.DataFrame] = []
    status_rows: list[dict[str, object]] = []
    coverage_frames: list[pd.DataFrame] = []
    predictor_rows: list[dict[str, object]] = []

    for taxon_index, (taxon, simulation) in enumerate(simulations.items()):
        occurrence = _model_only_frame(simulation.occurrences).reset_index(drop=True)
        backgrounds = {
            name: _model_only_frame(frame).reset_index(drop=True)
            for name, frame in _nested_background_perturbations(simulation).items()
        }
        admissibility = select_model_pool_admissible_predictors(
            {name: (occurrence, backgrounds[name]) for name in M_SPECS},
            CANDIDATE_ECOLOGICAL_PREDICTORS,
            minimum_coverage=minimum_predictor_coverage,
        )
        coverage = admissibility.ledger.copy()
        coverage["panel"] = panel.name
        coverage["species"] = taxon
        coverage_frames.append(coverage)
        predictor_rows.append(
            {
                "panel": panel.name,
                "species": taxon,
                "n_raw_predictors": len(CANDIDATE_ECOLOGICAL_PREDICTORS),
                "n_model_pool_admissible_predictors": len(
                    admissibility.predictors
                ),
                "admissible_predictors": ",".join(admissibility.predictors),
            }
        )

        for perturbation_index, perturbation in enumerate(M_SPECS):
            background = backgrounds[perturbation]
            random_state = int(
                random_state_offset + taxon_index * 100 + perturbation_index
            )
            partition = make_spatial_partition(
                occurrence["longitude"].to_numpy(float),
                occurrence["latitude"].to_numpy(float),
                background["longitude"].to_numpy(float),
                background["latitude"].to_numpy(float),
                n_blocks=max(4, int(outer_folds) + 1),
                holdout_fraction=0.20,
                random_state=random_state,
            )
            try:
                benchmark = benchmark_recovery_procedures_with_surface_stability(
                    occurrence,
                    background,
                    partition.presence_blocks,
                    partition.background_blocks,
                    admissibility.predictors,
                    simulation.audit_predictors,
                    procedures,
                    outer_folds=outer_folds,
                    max_stability_reference_rows=max_stability_reference_rows,
                )
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                status_rows.append(
                    {
                        "panel": panel.name,
                        "species": taxon,
                        "perturbation": perturbation,
                        "status": "abstain_no_evaluable_outer_folds",
                        "error": str(exc),
                        "random_state": random_state,
                    }
                )
                continue
            status_rows.append(
                {
                    "panel": panel.name,
                    "species": taxon,
                    "perturbation": perturbation,
                    "status": "success",
                    "error": None,
                    "random_state": random_state,
                }
            )
            metrics = benchmark.fold_metrics.copy()
            metrics["panel"] = panel.name
            metrics["species"] = taxon
            metrics["perturbation"] = perturbation
            metrics["perturbation_type"] = "sampling_or_background"
            metrics["n_candidate_ecological_predictors"] = len(
                admissibility.predictors
            )
            metric_frames.append(metrics)

    return (
        pd.concat(metric_frames, ignore_index=True)
        if metric_frames
        else pd.DataFrame(),
        pd.DataFrame(status_rows),
        pd.concat(coverage_frames, ignore_index=True),
        pd.DataFrame(predictor_rows),
    )


def _complete_gate(
    metrics: pd.DataFrame,
    *,
    taxa: tuple[str, ...],
    perturbations: tuple[str, ...],
    required_columns: tuple[str, ...],
    expected_outer_folds: int,
):
    return require_complete_outer_fold_evidence(
        metrics,
        discovery_taxa=taxa,
        perturbations=perturbations,
        required_columns=required_columns,
        expected_outer_folds=expected_outer_folds,
    )


def _select_panel(
    metrics: pd.DataFrame,
    *,
    discovery_taxa: tuple[str, ...],
    expected_outer_folds: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Freeze all four selectors before any validation truth is opened."""

    recovery = tuple(RECOVERY_DIRECTIONS)
    stability = tuple(STABILITY_DIRECTIONS)
    canonical = metrics.loc[
        metrics["perturbation"].astype(str).eq(CANONICAL_M)
    ].copy()
    gates = {
        "canonical_prediction": _complete_gate(
            canonical,
            taxa=discovery_taxa,
            perturbations=(CANONICAL_M,),
            required_columns=("presence_rank",),
            expected_outer_folds=expected_outer_folds,
        ),
        "canonical_ecology": _complete_gate(
            canonical,
            taxa=discovery_taxa,
            perturbations=(CANONICAL_M,),
            required_columns=("presence_rank", *recovery),
            expected_outer_folds=expected_outer_folds,
        ),
        "all_ecology": _complete_gate(
            metrics,
            taxa=discovery_taxa,
            perturbations=M_SPECS,
            required_columns=("presence_rank", *recovery),
            expected_outer_folds=expected_outer_folds,
        ),
        "all_stability": _complete_gate(
            metrics,
            taxa=discovery_taxa,
            perturbations=M_SPECS,
            required_columns=("presence_rank", *recovery, *stability),
            expected_outer_folds=expected_outer_folds,
        ),
    }

    rows: list[dict[str, object]] = []

    def append(selector: str, candidate: str | None, error: str | None, gate_name: str):
        rows.append(
            {
                "regime": "coverage_complete",
                "selector": selector,
                "candidate": candidate,
                "status": "selected" if candidate else "abstain_evidence_or_selection",
                "selection_error": error,
                "n_evidence_eligible_candidates": len(
                    gates[gate_name].eligible_candidates
                ),
            }
        )

    auc_candidate = None
    auc_error = None
    if gates["canonical_prediction"].eligible_candidates:
        eligible = set(gates["canonical_prediction"].eligible_candidates)
        try:
            auc_candidate = _mean_auc_winner(
                canonical.loc[canonical["candidate"].astype(str).isin(eligible)]
            )
        except ValueError as exc:
            auc_error = str(exc)
    else:
        auc_error = "no candidate passes complete canonical prediction evidence"
    append("canonical_auc", auc_candidate, auc_error, "canonical_prediction")

    ecology_candidate = None
    ecology_error = None
    if gates["canonical_ecology"].eligible_candidates:
        eligible = set(gates["canonical_ecology"].eligible_candidates)
        try:
            ecology_candidate = select_recovery_procedure(
                RecoveryProcedureBenchmark(
                    canonical.loc[
                        canonical["candidate"].astype(str).isin(eligible)
                    ].copy(),
                    pd.DataFrame(),
                )
            ).candidate
        except ValueError as exc:
            ecology_error = str(exc)
    else:
        ecology_error = "no candidate passes complete canonical ecological evidence"
    append("canonical_ecology", ecology_candidate, ecology_error, "canonical_ecology")

    robust_candidate = None
    robust_error = None
    if gates["all_ecology"].eligible_candidates:
        eligible = set(gates["all_ecology"].eligible_candidates)
        robust_metrics = metrics.loc[
            metrics["candidate"].astype(str).isin(eligible)
        ].copy()
        robust_metrics["perturbation"] = (
            robust_metrics["species"].astype(str)
            + "::"
            + robust_metrics["perturbation"].astype(str)
        )
        try:
            robust_candidate = select_perturbation_robust_niche_recovery_protocol(
                robust_metrics,
                prediction_adequacy_perturbation_types=("sampling_or_background",),
            ).candidate
        except ValueError as exc:
            robust_error = str(exc)
    else:
        robust_error = "no candidate passes complete cross-M ecological evidence"
    append("robust_ecology", robust_candidate, robust_error, "all_ecology")

    stable_candidate = None
    stable_error = None
    if gates["all_stability"].eligible_candidates:
        eligible = set(gates["all_stability"].eligible_candidates)
        try:
            stable_candidate = select_stable_recovery_procedure(
                RecoveryProcedureBenchmark(
                    metrics.loc[
                        metrics["candidate"].astype(str).isin(eligible)
                    ].copy(),
                    pd.DataFrame(),
                )
            ).candidate
        except ValueError as exc:
            stable_error = str(exc)
    else:
        stable_error = "no candidate passes complete surface-stability evidence"
    append("stable_ecology", stable_candidate, stable_error, "all_stability")

    return pd.DataFrame(rows), gates


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
        candidates = {
            selector: (
                None
                if pd.isna(indexed.loc[selector, "candidate"])
                else str(indexed.loc[selector, "candidate"])
            )
            for selector in SELECTORS
        }
        rows.append(
            {
                "panel": str(panel),
                **{
                    f"{selector}_candidate": candidate
                    for selector, candidate in candidates.items()
                },
                "canonical_auc_selected": candidates["canonical_auc"] is not None,
                "stable_ecology_selected": candidates["stable_ecology"] is not None,
                "stable_differs_from_auc": bool(
                    candidates["canonical_auc"] is not None
                    and candidates["stable_ecology"] is not None
                    and candidates["canonical_auc"]
                    != candidates["stable_ecology"]
                ),
            }
        )
    return pd.DataFrame(rows)


def surface_stability_decision(
    selector_disagreement: pd.DataFrame,
    summary: pd.DataFrame,
) -> pd.DataFrame:
    """Apply the frozen v2.2 panel-level decision rule."""

    n_panels = int(selector_disagreement["panel"].nunique())
    stable_selected = int(
        selector_disagreement["stable_ecology_selected"].sum()
    )
    auc_selected = int(selector_disagreement["canonical_auc_selected"].sum())
    disagreement_panels = tuple(
        selector_disagreement.loc[
            selector_disagreement["stable_differs_from_auc"].astype(bool),
            "panel",
        ].astype(str)
    )

    evaluable_disagreement = 0
    stable_not_worse = 0
    for panel in disagreement_panels:
        group = summary.loc[summary["panel"].astype(str).eq(panel)].set_index(
            "selector"
        )
        if not {"canonical_auc", "stable_ecology"} <= set(group.index):
            continue
        auc = group.loc["canonical_auc"]
        stable = group.loc["stable_ecology"]
        n_validation = max(
            int(auc["n_validation_taxa"]),
            int(stable["n_validation_taxa"]),
        )
        fully_evaluable = (
            int(auc["n_truth_evaluable"]) == n_validation
            and int(stable["n_truth_evaluable"]) == n_validation
            and n_validation > 0
        )
        if not fully_evaluable:
            continue
        evaluable_disagreement += 1
        not_worse = (
            np.isfinite(float(stable["mean_truth_worst_rank"]))
            and np.isfinite(float(auc["mean_truth_worst_rank"]))
            and float(stable["mean_truth_worst_rank"])
            <= float(auc["mean_truth_worst_rank"]) + 1e-12
            and float(stable["mean_truth_mean_rank"])
            <= float(auc["mean_truth_mean_rank"]) + 1e-12
        )
        stable_not_worse += int(bool(not_worse))

    if stable_selected < n_panels or auc_selected < n_panels:
        decision = "surface_stability_unstable_or_abstained"
    elif not disagreement_panels:
        decision = "surface_stability_indistinguishable"
    elif (
        evaluable_disagreement == len(disagreement_panels)
        and stable_not_worse == len(disagreement_panels)
    ):
        decision = "surface_stability_supported"
    else:
        decision = "surface_stability_not_supported"

    next_action = {
        "surface_stability_supported": (
            "freeze the staged stable selector before a newly rebuilt "
            "sealed-before-M empirical confirmation"
        ),
        "surface_stability_indistinguishable": (
            "retain as negative differentiation evidence; do not confirm empirically"
        ),
        "surface_stability_not_supported": (
            "retain negative evidence and redesign before empirical confirmation"
        ),
        "surface_stability_unstable_or_abstained": (
            "diagnose selector/evidence instability without relaxing gates"
        ),
    }[decision]
    return pd.DataFrame(
        [
            {
                "decision": decision,
                "scientific_promotion_allowed": False,
                "negative_outcome_accepted": True,
                "n_panels": n_panels,
                "n_panels_with_auc_selected": auc_selected,
                "n_panels_with_stable_ecology_selected": stable_selected,
                "n_panels_with_stable_auc_disagreement": len(
                    disagreement_panels
                ),
                "n_disagreement_panels_truth_evaluable": evaluable_disagreement,
                "n_disagreement_panels_stable_not_worse": stable_not_worse,
                "next_action": next_action,
            }
        ]
    )


def run_surface_stability_experiment(
    panel_config: str | Path,
    *,
    n_cells: int = 1800,
    n_occurrences: int = 180,
    n_target_group: int = 700,
    inner_folds: int = 2,
    outer_folds: int = 2,
    max_predictors: int = 4,
    minimum_predictor_coverage: float = 0.95,
    prediction_surface_coverage_floor: float = 0.95,
    max_stability_reference_rows: int = 256,
) -> dict[str, Any]:
    config_path = Path(panel_config)
    config, panels = load_predeclared_panels(config_path)
    procedures = _procedure_library(
        inner_folds=inner_folds,
        max_predictors=max_predictors,
    )

    selector_frames: list[pd.DataFrame] = []
    metric_frames: list[pd.DataFrame] = []
    status_frames: list[pd.DataFrame] = []
    coverage_frames: list[pd.DataFrame] = []
    predictor_frames: list[pd.DataFrame] = []
    evidence_frames: list[pd.DataFrame] = []
    fit_frames: list[pd.DataFrame] = []
    truth_frames: list[pd.DataFrame] = []
    validation_coverage_frames: list[pd.DataFrame] = []

    for panel_index, panel in enumerate(panels):
        metrics, status, coverage, predictors = _run_discovery_panel(
            panel,
            procedures=procedures,
            n_cells=n_cells,
            n_occurrences=n_occurrences,
            n_target_group=n_target_group,
            minimum_predictor_coverage=minimum_predictor_coverage,
            outer_folds=outer_folds,
            random_state_offset=70000 + panel_index * 1000,
            max_stability_reference_rows=max_stability_reference_rows,
        )
        selectors, gates = _select_panel(
            metrics,
            discovery_taxa=tuple(spec.taxon for spec in panel.discovery),
            expected_outer_folds=outer_folds,
        )
        selectors["panel"] = panel.name
        selector_frames.append(selectors)
        metric_frames.append(metrics)
        status_frames.append(status)
        coverage_frames.append(coverage)
        predictor_frames.append(predictors)
        for gate_name, gate in gates.items():
            summary = gate.candidate_summary.copy()
            summary["panel"] = panel.name
            summary["gate"] = gate_name
            evidence_frames.append(summary)

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
            random_state_offset=80000 + panel_index * 1000,
        )
        for frame in (fit, truth, validation_coverage):
            frame["panel"] = panel.name
        fit_frames.append(fit)
        truth_frames.append(truth)
        validation_coverage_frames.append(validation_coverage)

    selectors = pd.concat(selector_frames, ignore_index=True)
    validation_truth = _rank_truth_evaluation(
        pd.concat(truth_frames, ignore_index=True)
    )
    validation_summary = _panel_truth_summary(validation_truth)
    disagreement = _selector_disagreement(selectors)
    decision = surface_stability_decision(disagreement, validation_summary)

    contract = {
        "purpose": "product_a_v2_2_predeclared_surface_stability_known_truth",
        "scientific_promotion_run": False,
        "real_empirical_data_read": False,
        "old_external_sealed_outcomes_read": False,
        "previously_opened_known_truth_used_for_validation": False,
        "selection_never_uses_truth": True,
        "validation_truth_opened_after_panel_selectors_frozen": True,
        "panel_config": str(config_path),
        "panel_config_sha256": _sha256(config_path),
        "selectors": list(SELECTORS),
        "selection_order": list(EXPECTED_SELECTION_ORDER),
        "panels": [panel.name for panel in panels],
        "discovery_seeds": [
            spec.seed for panel in panels for spec in panel.discovery
        ],
        "validation_seeds": [
            spec.seed for panel in panels for spec in panel.validation
        ],
        "minimum_predictor_coverage": float(minimum_predictor_coverage),
        "prediction_surface_coverage_floor": float(
            prediction_surface_coverage_floor
        ),
        "inner_folds": int(inner_folds),
        "outer_folds": int(outer_folds),
        "max_predictors": int(max_predictors),
        "max_stability_reference_rows": int(max_stability_reference_rows),
        "recovery_stability_combined_weighted_score": False,
        "decision": str(decision.iloc[0]["decision"]),
        "scientific_promotion_allowed": False,
        "supported_result_only_allows": config.get(
            "supported_result_only_allows"
        ),
    }
    return {
        "contract": contract,
        "procedures": procedures,
        "selectors": selectors,
        "discovery_metrics": pd.concat(metric_frames, ignore_index=True),
        "discovery_status": pd.concat(status_frames, ignore_index=True),
        "discovery_coverage": pd.concat(coverage_frames, ignore_index=True),
        "discovery_predictors": pd.concat(predictor_frames, ignore_index=True),
        "evidence_summary": pd.concat(evidence_frames, ignore_index=True),
        "validation_fit": pd.concat(fit_frames, ignore_index=True),
        "validation_truth": validation_truth,
        "validation_summary": validation_summary,
        "validation_coverage": pd.concat(
            validation_coverage_frames,
            ignore_index=True,
        ),
        "selector_disagreement": disagreement,
        "decision": decision,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--n-cells", type=int, default=1800)
    parser.add_argument("--n-occurrences", type=int, default=180)
    parser.add_argument("--n-target-group", type=int, default=700)
    parser.add_argument("--inner-folds", type=int, default=2)
    parser.add_argument("--outer-folds", type=int, default=2)
    parser.add_argument("--max-predictors", type=int, default=4)
    parser.add_argument("--minimum-predictor-coverage", type=float, default=0.95)
    parser.add_argument(
        "--prediction-surface-coverage-floor",
        type=float,
        default=0.95,
    )
    parser.add_argument(
        "--max-stability-reference-rows",
        type=int,
        default=256,
    )
    args = parser.parse_args(argv)

    result = run_surface_stability_experiment(
        args.panel_config,
        n_cells=args.n_cells,
        n_occurrences=args.n_occurrences,
        n_target_group=args.n_target_group,
        inner_folds=args.inner_folds,
        outer_folds=args.outer_folds,
        max_predictors=args.max_predictors,
        minimum_predictor_coverage=args.minimum_predictor_coverage,
        prediction_surface_coverage_floor=(
            args.prediction_surface_coverage_floor
        ),
        max_stability_reference_rows=args.max_stability_reference_rows,
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
    (out / "contract.json").write_text(
        json.dumps(result["contract"], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
