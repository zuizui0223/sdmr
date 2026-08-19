"""Sealed-blind discovery stage for Product-A v2.4 process knockouts.

This stage executes the predeclared base and process-knockout procedure library on
D1--D3 discovery taxa only. It freezes complete/adequate base products and the
admitted process-exclusion routes before any discovery generating truth or any
validation taxon is accessed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .niche_recovery_procedure import benchmark_recovery_procedures
from .preoutcome_artifact_normalization import LEGACY_OUTER_CV_RENAMES
from .process_exclusion_certificate import summarize_knockout_discovery_evidence
from .v2_1_known_truth_gate_ablation import (
    CANDIDATE_ECOLOGICAL_PREDICTORS,
    M_SPECS,
    _model_only_frame,
    _nested_background_perturbations,
    _procedure_library,
    _simulate_taxon,
)
from .v2_3_ecological_certificate_experiment import _freeze_products
from .v2_4_exclusion_certificate_experiment import (
    ExclusionCertificatePanel,
    load_exclusion_certificate_config,
)
from .validation import make_spatial_partition


FORBIDDEN_GENERATING_COLUMNS = {
    "true_suitability",
    "sampling_effort",
    "focal_recording_multiplier",
}


def _split_csv(value: object) -> tuple[str, ...]:
    if value is None or pd.isna(value) or not str(value):
        return ()
    return tuple(x for x in str(value).split(",") if x)


def _assert_model_only(frame: pd.DataFrame) -> None:
    forbidden = sorted(FORBIDDEN_GENERATING_COLUMNS & set(frame.columns))
    if forbidden:
        raise AssertionError(
            "generating truth crossed the discovery barrier: " + ", ".join(forbidden)
        )


def _normalize_outer_cv_metric_labels(frame: pd.DataFrame) -> pd.DataFrame:
    """Rename only verified model-pool outer-CV labels and reject all others."""

    sealed_like = {
        str(column)
        for column in frame.columns
        if str(column).lower().startswith("sealed_")
        or str(column).lower().startswith("n_sealed_")
    }
    unknown = sorted(sealed_like - set(LEGACY_OUTER_CV_RENAMES))
    if unknown:
        raise ValueError(
            "unknown sealed-looking discovery metrics are forbidden: "
            + ", ".join(unknown)
        )
    active = {
        source: target
        for source, target in LEGACY_OUTER_CV_RENAMES.items()
        if source in frame.columns
    }
    collisions = sorted(target for target in active.values() if target in frame.columns)
    if collisions:
        raise ValueError(
            "outer-CV normalization would overwrite columns: "
            + ", ".join(collisions)
        )
    return frame.rename(columns=active)


def _benchmark_library(
    occurrence: pd.DataFrame,
    background: pd.DataFrame,
    *,
    ecological_predictors: tuple[str, ...],
    audit_predictors: tuple[str, ...],
    procedures,
    outer_folds: int,
    random_state: int,
):
    partition = make_spatial_partition(
        occurrence["longitude"].to_numpy(float),
        occurrence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        n_blocks=max(4, int(outer_folds) + 1),
        holdout_fraction=0.20,
        random_state=int(random_state),
    )
    return benchmark_recovery_procedures(
        occurrence,
        background,
        partition.presence_blocks,
        partition.background_blocks,
        ecological_predictors,
        audit_predictors,
        procedures,
        outer_folds=int(outer_folds),
    )


def _decorate_metrics(
    frame: pd.DataFrame,
    *,
    panel: str,
    species: str,
    perturbation: str,
    candidate_type: str,
) -> pd.DataFrame:
    metrics = _normalize_outer_cv_metric_labels(frame.copy())
    metrics["panel"] = panel
    metrics["species"] = species
    metrics["perturbation"] = perturbation
    metrics["perturbation_type"] = "sampling_or_background"
    metrics["candidate_type"] = candidate_type
    return metrics


def run_knockout_discovery_panel(
    panel_config: str | Path,
    panel_name: str,
) -> dict[str, Any]:
    """Run one frozen v2.4 discovery panel without reading generating truth."""

    config, panels, registry = load_exclusion_certificate_config(panel_config)
    panel_by_name = {panel.name: panel for panel in panels}
    if str(panel_name) not in panel_by_name:
        raise ValueError(f"unknown frozen v2.4 panel: {panel_name}")
    panel: ExclusionCertificatePanel = panel_by_name[str(panel_name)]
    panel_index = tuple(panel_by_name).index(panel.name)
    simulation_contract = config["simulation_contract"]
    n_cells = int(simulation_contract["n_cells"])
    n_occurrences = int(simulation_contract["n_occurrences"])
    n_target_group = int(simulation_contract["n_target_group"])
    inner_folds = int(simulation_contract["inner_folds"])
    outer_folds = int(simulation_contract["outer_folds"])
    max_predictors = int(simulation_contract["max_predictors"])
    minimum_predictor_coverage = float(
        simulation_contract["minimum_predictor_coverage"]
    )
    if tuple(simulation_contract["M_specs"]) != M_SPECS:
        raise ValueError("v2.4 M grid differs from the frozen implementation")

    procedures = _procedure_library(
        inner_folds=inner_folds,
        max_predictors=max_predictors,
    )
    base_labels = tuple(procedure.label for procedure in procedures)
    if base_labels != tuple(config["base_procedures"]):
        raise ValueError("v2.4 procedure library differs from the frozen config")

    simulations = {
        spec.taxon: _simulate_taxon(
            spec,
            n_cells=n_cells,
            n_occurrences=n_occurrences,
            n_target_group=n_target_group,
        )
        for spec in panel.discovery
    }
    base_metric_frames: list[pd.DataFrame] = []
    knockout_metric_frames: list[pd.DataFrame] = []
    status_rows: list[dict[str, object]] = []
    coverage_frames: list[pd.DataFrame] = []
    predictor_rows: list[dict[str, object]] = []
    process_registry = {
        str(process): group.copy()
        for process, group in registry.groupby("excluded_process", sort=False)
    }

    for taxon_index, (taxon, simulation) in enumerate(simulations.items()):
        occurrence = _model_only_frame(simulation.occurrences).reset_index(drop=True)
        backgrounds = {
            name: _model_only_frame(frame).reset_index(drop=True)
            for name, frame in _nested_background_perturbations(simulation).items()
        }
        _assert_model_only(occurrence)
        for frame in backgrounds.values():
            _assert_model_only(frame)

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
                "n_admissible_predictors": len(admissibility.predictors),
                "admissible_predictors": ",".join(admissibility.predictors),
            }
        )

        for perturbation_index, perturbation in enumerate(M_SPECS):
            background = backgrounds[perturbation]
            random_state = int(
                140000
                + panel_index * 10000
                + taxon_index * 100
                + perturbation_index
            )
            try:
                benchmark = _benchmark_library(
                    occurrence,
                    background,
                    ecological_predictors=tuple(admissibility.predictors),
                    audit_predictors=tuple(simulation.audit_predictors),
                    procedures=procedures,
                    outer_folds=outer_folds,
                    random_state=random_state,
                )
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                status_rows.append(
                    {
                        "panel": panel.name,
                        "species": taxon,
                        "perturbation": perturbation,
                        "library": "base",
                        "excluded_process": None,
                        "status": "abstain_no_evaluable_outer_folds",
                        "error": str(exc),
                        "random_state": random_state,
                    }
                )
            else:
                status_rows.append(
                    {
                        "panel": panel.name,
                        "species": taxon,
                        "perturbation": perturbation,
                        "library": "base",
                        "excluded_process": None,
                        "status": "success",
                        "error": None,
                        "random_state": random_state,
                    }
                )
                if not benchmark.fold_metrics.empty:
                    base_metric_frames.append(
                        _decorate_metrics(
                            benchmark.fold_metrics,
                            panel=panel.name,
                            species=taxon,
                            perturbation=perturbation,
                            candidate_type="base",
                        )
                    )

            for process_index, (process, group) in enumerate(
                process_registry.items()
            ):
                excluded = set(_split_csv(group.iloc[0]["excluded_predictors"]))
                retained = tuple(
                    predictor
                    for predictor in admissibility.predictors
                    if predictor not in excluded
                )
                knockout_state = int(random_state + 1000 + process_index * 10)
                if not retained:
                    status_rows.append(
                        {
                            "panel": panel.name,
                            "species": taxon,
                            "perturbation": perturbation,
                            "library": "knockout",
                            "excluded_process": process,
                            "status": "abstain_no_retained_ecological_predictors",
                            "error": None,
                            "random_state": knockout_state,
                        }
                    )
                    continue
                try:
                    knockout_benchmark = _benchmark_library(
                        occurrence,
                        background,
                        ecological_predictors=retained,
                        audit_predictors=tuple(simulation.audit_predictors),
                        procedures=procedures,
                        outer_folds=outer_folds,
                        random_state=knockout_state,
                    )
                except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                    status_rows.append(
                        {
                            "panel": panel.name,
                            "species": taxon,
                            "perturbation": perturbation,
                            "library": "knockout",
                            "excluded_process": process,
                            "status": "abstain_no_evaluable_outer_folds",
                            "error": str(exc),
                            "random_state": knockout_state,
                        }
                    )
                    continue
                status_rows.append(
                    {
                        "panel": panel.name,
                        "species": taxon,
                        "perturbation": perturbation,
                        "library": "knockout",
                        "excluded_process": process,
                        "status": "success",
                        "error": None,
                        "random_state": knockout_state,
                    }
                )
                if knockout_benchmark.fold_metrics.empty:
                    continue
                metrics = _decorate_metrics(
                    knockout_benchmark.fold_metrics,
                    panel=panel.name,
                    species=taxon,
                    perturbation=perturbation,
                    candidate_type="process_knockout",
                )
                metrics["base_candidate"] = metrics["candidate"].astype(str)
                label_map = group.set_index("base_candidate")["candidate"].astype(str)
                metrics["candidate"] = metrics["base_candidate"].map(label_map)
                if metrics["candidate"].isna().any():
                    raise AssertionError(
                        "knockout benchmark emitted an unknown base candidate"
                    )
                metrics["procedure"] = metrics["candidate"]
                metrics["excluded_process"] = process
                metrics["excluded_predictors"] = ",".join(sorted(excluded))
                metrics["n_retained_candidate_predictors"] = len(retained)
                knockout_metric_frames.append(metrics)

    base_metrics = (
        pd.concat(base_metric_frames, ignore_index=True)
        if base_metric_frames
        else pd.DataFrame()
    )
    knockout_metrics = (
        pd.concat(knockout_metric_frames, ignore_index=True)
        if knockout_metric_frames
        else pd.DataFrame()
    )
    discovery_taxa = tuple(spec.taxon for spec in panel.discovery)
    if base_metrics.empty:
        base_products = pd.DataFrame(
            [
                {
                    "product": product,
                    "status": "unavailable",
                    "n_candidates": 0,
                    "candidates": None,
                    "error": "no base discovery metrics",
                }
                for product in (
                    "canonical_auc_point",
                    "complete_adequate_certificate",
                    "ecological_pareto_certificate",
                )
            ]
        )
    else:
        base_products, _ = _freeze_products(
            base_metrics,
            discovery_taxa=discovery_taxa,
            expected_outer_folds=outer_folds,
        )
    base_products["panel"] = panel.name

    discovery = summarize_knockout_discovery_evidence(
        knockout_metrics,
        registry,
        discovery_taxa=discovery_taxa,
        perturbations=M_SPECS,
        expected_outer_folds=outer_folds,
        chance_auc=float(config["prediction_adequacy"]["chance_auc"]),
        minimum_auc_margin=float(
            config["prediction_adequacy"]["minimum_auc_margin"]
        ),
        auc_sem_multiplier=float(
            config["prediction_adequacy"]["auc_sem_multiplier"]
        ),
    )
    candidate_summary = discovery.candidate_summary.copy()
    candidate_summary["panel"] = panel.name
    process_summary = discovery.process_summary.copy()
    process_summary["panel"] = panel.name
    cell_ledger = discovery.cell_ledger.copy()
    cell_ledger["panel"] = panel.name

    contract = {
        "purpose": "product_a_v2_4_sealed_blind_knockout_discovery_panel",
        "panel": panel.name,
        "scientific_promotion_run": False,
        "scientific_promotion_allowed": False,
        "real_empirical_data_read": False,
        "discovery_generating_truth_read": False,
        "validation_taxa_simulated_or_read": False,
        "validation_truth_read": False,
        "old_external_sealed_outcomes_read": False,
        "discovery_taxa": list(discovery_taxa),
        "discovery_seeds": [spec.seed for spec in panel.discovery],
        "validation_seeds_reserved_unopened": [
            spec.seed for spec in panel.validation
        ],
        "n_base_procedures": len(procedures),
        "n_processes": int(registry["excluded_process"].nunique()),
        "n_declared_knockout_routes": len(registry),
        "n_complete_knockout_routes": int(
            candidate_summary["complete_outer_evidence"].sum()
        ),
        "n_admitted_knockout_routes": int(
            candidate_summary["admitted_knockout"].sum()
        ),
        "process_states": process_summary[
            ["process", "discovery_process_state"]
        ].to_dict(orient="records"),
        "simulation_contract": config["simulation_contract"],
        "legacy_outer_cv_labels_normalized": sorted(LEGACY_OUTER_CV_RENAMES),
    }
    return {
        "contract": contract,
        "base_products": base_products,
        "base_metrics": base_metrics,
        "knockout_metrics": knockout_metrics,
        "knockout_candidate_summary": candidate_summary,
        "knockout_process_summary": process_summary,
        "knockout_cell_ledger": cell_ledger,
        "benchmark_status": pd.DataFrame(status_rows),
        "predictor_coverage": pd.concat(coverage_frames, ignore_index=True),
        "admissible_predictors": pd.DataFrame(predictor_rows),
        "knockout_registry": registry,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-config", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    result = run_knockout_discovery_panel(args.panel_config, args.panel)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name in (
        "base_products",
        "base_metrics",
        "knockout_metrics",
        "knockout_candidate_summary",
        "knockout_process_summary",
        "knockout_cell_ledger",
        "benchmark_status",
        "predictor_coverage",
        "admissible_predictors",
        "knockout_registry",
    ):
        result[name].to_csv(out / f"{name}.csv", index=False)
    (out / "contract.json").write_text(
        json.dumps(result["contract"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
