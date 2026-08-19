"""Known-truth ablation for Product-A v2.1 pre-outcome robustness gates.

The empirical Product-A v2 procedure was falsified on frozen external taxa. Its
opened sealed values are therefore excluded from this development experiment.
This module uses synthetic plant niches whose generating truth stays hidden until
after discovery-taxon procedure selection. Negative and abstention outcomes are
valid; this is development evidence only, not a real-data promotion run.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .candidate_outer_fold_evidence import require_complete_outer_fold_evidence
from .known_truth import KnownTruthSimulation, known_truth_niche_recovery_profile
from .known_truth_response import (
    DEFAULT_PROCESS_ALIASES,
    infer_response_predictors,
    infer_true_processes,
    known_truth_process_profile,
    known_truth_response_profile,
)
from .known_truth_scenarios import simulate_known_truth_plant_niche
from .model import ModelSpec, score_ecological_suitability
from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .niche_recovery_perturbation import (
    select_perturbation_robust_niche_recovery_protocol,
)
from .niche_recovery_procedure import (
    RecoveryProcedure,
    RecoveryProcedureBenchmark,
    benchmark_recovery_procedures,
    select_recovery_procedure,
)
from .niche_recovery_selection import RECOVERY_DIRECTIONS
from .prepared_recovery_procedure_cli import _mean_auc_winner
from .recovery_procedure_fit import fit_recovery_procedure
from .validation import make_spatial_partition


M_SPECS = ("m_core", "m_mid", "m_wide")
CANONICAL_M = "m_mid"
SPARSE_PREDICTORS = ("sparse_temp_proxy", "sparse_noise")
BASE_ECOLOGICAL_PREDICTORS = (
    "temperature",
    "water",
    "temp_proxy",
    "seasonality",
    "soil",
    "noise",
)
CANDIDATE_ECOLOGICAL_PREDICTORS = (*BASE_ECOLOGICAL_PREDICTORS, *SPARSE_PREDICTORS)
OBSERVATION_PREDICTORS = ("recording_bias",)
REGIMES = (
    "raw_available",
    "raw_complete",
    "coverage_available",
    "coverage_complete",
)
SELECTORS = ("canonical_auc", "canonical_ecology", "robust_ecology")
TRUTH_DIRECTIONS = {
    "niche_overlap_schoener_d_pc12": "max",
    "centroid_distance": "min",
    "breadth_log_sd_error": "min",
    "quantile_profile_error": "min",
    "truth_surface_rank": "max",
    "truth_surface_nrmse": "min",
    "response_curve_error": "min",
    "optimum_error": "min",
    "lower_limit_error": "min",
    "upper_limit_error": "min",
    "driver_process_f1": "max",
}


@dataclass(frozen=True)
class SimulatedTaxonSpec:
    family: str
    seed: int
    role: str

    @property
    def taxon(self) -> str:
        return f"{self.family}__seed{self.seed}"


DISCOVERY_TAXA = (
    SimulatedTaxonSpec("gaussian", 11, "discovery"),
    SimulatedTaxonSpec("asymmetric", 21, "discovery"),
    SimulatedTaxonSpec("interaction", 31, "discovery"),
)
VALIDATION_TAXA = (
    SimulatedTaxonSpec("soft_threshold", 41, "validation"),
    SimulatedTaxonSpec("omitted_driver", 51, "validation"),
    SimulatedTaxonSpec("observation_confounded", 61, "validation"),
)


def _add_structured_sparse_predictors(frame: pd.DataFrame) -> pd.DataFrame:
    """Add deterministic raster-like predictors with spatially structured gaps."""

    required = {
        "longitude",
        "latitude",
        "temp_proxy",
        "seasonality",
        "noise",
        "soil",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise KeyError(f"frame lacks sparse-predictor inputs: {missing}")
    result = frame.copy()
    result["sparse_temp_proxy"] = (
        0.97 * pd.to_numeric(result["temp_proxy"], errors="coerce")
        + 0.03 * pd.to_numeric(result["seasonality"], errors="coerce")
    )
    result["sparse_noise"] = (
        0.80 * pd.to_numeric(result["noise"], errors="coerce")
        + 0.20 * pd.to_numeric(result["soil"], errors="coerce")
    )
    longitude = pd.to_numeric(result["longitude"], errors="coerce")
    latitude = pd.to_numeric(result["latitude"], errors="coerce")
    axis_proxy = longitude + 0.35 * latitude
    axis_noise = longitude - 0.55 * latitude
    proxy_cut = float(axis_proxy.quantile(0.82))
    noise_cut = float(axis_noise.quantile(0.28))
    result.loc[axis_proxy >= proxy_cut, "sparse_temp_proxy"] = np.nan
    result.loc[axis_noise <= noise_cut, "sparse_noise"] = np.nan
    return result


def _augment_simulation(
    simulation: KnownTruthSimulation,
    taxon: str,
) -> KnownTruthSimulation:
    environment = _add_structured_sparse_predictors(simulation.environment)
    occurrences = _add_structured_sparse_predictors(simulation.occurrences)
    background = _add_structured_sparse_predictors(simulation.target_group)
    occurrences["species"] = str(taxon)
    background["species"] = f"target_group_for_{taxon}"
    return KnownTruthSimulation(
        environment=environment,
        occurrences=occurrences,
        target_group=background,
        audit_predictors=simulation.audit_predictors,
        true_suitability_column=simulation.true_suitability_column,
        sampling_effort_column=simulation.sampling_effort_column,
    )


def _simulate_taxon(
    spec: SimulatedTaxonSpec,
    *,
    n_cells: int,
    n_occurrences: int,
    n_target_group: int,
) -> KnownTruthSimulation:
    simulation = simulate_known_truth_plant_niche(
        spec.family,
        seed=int(spec.seed),
        n_cells=int(n_cells),
        n_occurrences=int(n_occurrences),
        n_target_group=int(n_target_group),
        focal_recording_bias_strength=(
            4.0 if spec.family == "observation_confounded" else 0.0
        ),
    )
    return _augment_simulation(simulation, spec.taxon)


def _model_only_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove every generating-truth column before fitting or selection."""

    forbidden = {
        "true_suitability",
        "sampling_effort",
        "focal_recording_multiplier",
    }
    return frame.drop(columns=[c for c in forbidden if c in frame.columns]).copy()


def _nested_background_perturbations(
    simulation: KnownTruthSimulation,
) -> dict[str, pd.DataFrame]:
    """Construct three deterministic nested accessible-background analogues."""

    occurrence = simulation.occurrences
    background = simulation.target_group.copy()
    center_lon = float(pd.to_numeric(occurrence["longitude"], errors="raise").mean())
    center_lat = float(pd.to_numeric(occurrence["latitude"], errors="raise").mean())
    dx = pd.to_numeric(background["longitude"], errors="raise") - center_lon
    dy = pd.to_numeric(background["latitude"], errors="raise") - center_lat
    background["__distance_to_occurrence_centroid"] = np.sqrt(dx * dx + dy * dy)
    core_cut = float(background["__distance_to_occurrence_centroid"].quantile(0.70))
    mid_cut = float(background["__distance_to_occurrence_centroid"].quantile(0.85))
    result = {
        "m_core": background.loc[
            background["__distance_to_occurrence_centroid"] <= core_cut
        ],
        "m_mid": background.loc[
            background["__distance_to_occurrence_centroid"] <= mid_cut
        ],
        "m_wide": background,
    }
    cleaned: dict[str, pd.DataFrame] = {}
    previous = 0
    for name in M_SPECS:
        frame = result[name].drop(columns="__distance_to_occurrence_centroid").reset_index(
            drop=True
        )
        if len(frame) < 20:
            raise ValueError(f"{name} has insufficient target-group background")
        if len(frame) < previous:
            raise AssertionError("background perturbations must be nested by size")
        previous = len(frame)
        cleaned[name] = frame
    return cleaned


def _procedure_library(
    *,
    inner_folds: int,
    max_predictors: int,
) -> tuple[RecoveryProcedure, ...]:
    procedures: list[RecoveryProcedure] = []
    for model_spec in (
        ModelSpec(C=0.1, degree=1, penalty="l2"),
        ModelSpec(C=1.0, degree=2, penalty="l2"),
    ):
        for strategy in ("all", "vif", "predictive_forward", "niche_forward"):
            procedures.append(
                RecoveryProcedure(
                    strategy,
                    model_spec,
                    inner_folds=int(inner_folds),
                    max_predictors=int(max_predictors),
                    predictive_min_gain=0.0,
                    observation_predictors=OBSERVATION_PREDICTORS,
                )
            )
    return tuple(procedures)


def _available_candidates(
    metrics: pd.DataFrame,
    *,
    taxa: tuple[str, ...],
    perturbations: tuple[str, ...],
    required_columns: tuple[str, ...],
) -> tuple[tuple[str, ...], pd.DataFrame]:
    """Require one finite fold per taxon × perturbation, but not every fold."""

    required = {"candidate", "species", "perturbation", *required_columns}
    missing = sorted(required - set(metrics.columns))
    if missing:
        raise KeyError(f"metrics lacks available-evidence columns: {missing}")
    rows: list[dict[str, object]] = []
    candidates = tuple(sorted(metrics["candidate"].dropna().astype(str).unique()))
    for candidate in candidates:
        candidate_rows = metrics.loc[metrics["candidate"].astype(str).eq(candidate)]
        for species in taxa:
            for perturbation in perturbations:
                cell = candidate_rows.loc[
                    candidate_rows["species"].astype(str).eq(species)
                    & candidate_rows["perturbation"].astype(str).eq(perturbation)
                ]
                finite = True
                missing_columns = []
                for column in required_columns:
                    values = pd.to_numeric(cell[column], errors="coerce").to_numpy(float)
                    if not np.isfinite(values).any():
                        finite = False
                        missing_columns.append(column)
                rows.append(
                    {
                        "candidate": candidate,
                        "species": species,
                        "perturbation": perturbation,
                        "n_available_folds": int(cell["fold"].nunique())
                        if "fold" in cell.columns
                        else int(len(cell)),
                        "evidence_available": bool(finite),
                        "missing_or_nonfinite_columns": ",".join(missing_columns),
                    }
                )
    ledger = pd.DataFrame(rows)
    expected_cells = len(taxa) * len(perturbations)
    if ledger.empty:
        return (), ledger
    summary = (
        ledger.groupby("candidate", as_index=False)
        .agg(
            n_required_cells=("evidence_available", "size"),
            n_available_cells=("evidence_available", "sum"),
        )
    )
    summary["eligible_available_evidence"] = (
        summary["n_required_cells"].eq(expected_cells)
        & summary["n_available_cells"].eq(expected_cells)
    )
    ledger = ledger.merge(summary, on="candidate", how="left", validate="many_to_one")
    eligible = tuple(
        ledger.loc[ledger["eligible_available_evidence"].astype(bool), "candidate"]
        .drop_duplicates()
        .astype(str)
    )
    return eligible, ledger


def _candidate_gate(
    metrics: pd.DataFrame,
    *,
    gate: str,
    taxa: tuple[str, ...],
    perturbations: tuple[str, ...],
    required_columns: tuple[str, ...],
    expected_outer_folds: int,
) -> tuple[tuple[str, ...], pd.DataFrame, pd.DataFrame]:
    if gate == "available":
        eligible, ledger = _available_candidates(
            metrics,
            taxa=taxa,
            perturbations=perturbations,
            required_columns=required_columns,
        )
        summary = (
            ledger[
                [
                    "candidate",
                    "n_required_cells",
                    "n_available_cells",
                    "eligible_available_evidence",
                ]
            ]
            .drop_duplicates()
            .reset_index(drop=True)
            if not ledger.empty
            else pd.DataFrame()
        )
        return eligible, ledger, summary
    if gate != "complete":
        raise ValueError("gate must be 'available' or 'complete'")
    result = require_complete_outer_fold_evidence(
        metrics,
        discovery_taxa=taxa,
        perturbations=perturbations,
        required_columns=required_columns,
        expected_outer_folds=expected_outer_folds,
    )
    return result.eligible_candidates, result.cell_ledger, result.candidate_summary


def _select_regime(
    metrics: pd.DataFrame,
    *,
    regime: str,
    discovery_taxa: tuple[str, ...],
    canonical_m: str,
    expected_outer_folds: int,
) -> tuple[pd.DataFrame, dict[str, tuple[pd.DataFrame, pd.DataFrame]]]:
    if metrics.empty:
        return (
            pd.DataFrame(
                [
                    {
                        "regime": regime,
                        "selector": selector,
                        "candidate": None,
                        "status": "abstain_no_discovery_metrics",
                        "selection_error": "no discovery metrics",
                        "n_evidence_eligible_candidates": 0,
                    }
                    for selector in SELECTORS
                ]
            ),
            {},
        )
    gate = "complete" if regime.endswith("complete") else "available"
    canonical = metrics.loc[metrics["perturbation"].astype(str).eq(canonical_m)].copy()
    recovery = tuple(RECOVERY_DIRECTIONS)
    gate_specs = {
        "canonical_prediction": (canonical, (canonical_m,), ("presence_rank",)),
        "canonical_ecology": (
            canonical,
            (canonical_m,),
            ("presence_rank", *recovery),
        ),
        "all_ecology": (
            metrics,
            M_SPECS,
            ("presence_rank", *recovery),
        ),
    }
    eligible: dict[str, tuple[str, ...]] = {}
    ledgers: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for name, (frame, perturbations, columns) in gate_specs.items():
        candidates, cells, summary = _candidate_gate(
            frame,
            gate=gate,
            taxa=discovery_taxa,
            perturbations=tuple(perturbations),
            required_columns=tuple(columns),
            expected_outer_folds=expected_outer_folds,
        )
        eligible[name] = candidates
        ledgers[name] = (cells, summary)

    rows: list[dict[str, object]] = []
    canonical_auc = None
    canonical_auc_error = None
    if eligible["canonical_prediction"]:
        try:
            canonical_auc = _mean_auc_winner(
                canonical.loc[
                    canonical["candidate"].astype(str).isin(
                        set(eligible["canonical_prediction"])
                    )
                ]
            )
        except ValueError as exc:
            canonical_auc_error = str(exc)
    else:
        canonical_auc_error = "no candidate passes the declared evidence gate"
    rows.append(
        {
            "regime": regime,
            "selector": "canonical_auc",
            "candidate": canonical_auc,
            "status": "selected" if canonical_auc else "abstain_evidence_or_selection",
            "selection_error": canonical_auc_error,
            "n_evidence_eligible_candidates": len(eligible["canonical_prediction"]),
        }
    )

    canonical_ecology = None
    canonical_ecology_error = None
    if eligible["canonical_ecology"]:
        try:
            canonical_ecology = select_recovery_procedure(
                RecoveryProcedureBenchmark(
                    canonical.loc[
                        canonical["candidate"].astype(str).isin(
                            set(eligible["canonical_ecology"])
                        )
                    ].copy(),
                    pd.DataFrame(),
                )
            ).candidate
        except ValueError as exc:
            canonical_ecology_error = str(exc)
    else:
        canonical_ecology_error = "no candidate passes the declared evidence gate"
    rows.append(
        {
            "regime": regime,
            "selector": "canonical_ecology",
            "candidate": canonical_ecology,
            "status": "selected"
            if canonical_ecology
            else "abstain_evidence_or_selection",
            "selection_error": canonical_ecology_error,
            "n_evidence_eligible_candidates": len(eligible["canonical_ecology"]),
        }
    )

    robust = None
    robust_error = None
    if eligible["all_ecology"]:
        robust_metrics = metrics.loc[
            metrics["candidate"].astype(str).isin(set(eligible["all_ecology"]))
        ].copy()
        robust_metrics["perturbation"] = (
            robust_metrics["species"].astype(str)
            + "::"
            + robust_metrics["perturbation"].astype(str)
        )
        try:
            robust = select_perturbation_robust_niche_recovery_protocol(
                robust_metrics,
                prediction_adequacy_perturbation_types=("sampling_or_background",),
            ).candidate
        except ValueError as exc:
            robust_error = str(exc)
    else:
        robust_error = "no candidate passes the declared evidence gate"
    rows.append(
        {
            "regime": regime,
            "selector": "robust_ecology",
            "candidate": robust,
            "status": "selected" if robust else "abstain_evidence_or_selection",
            "selection_error": robust_error,
            "n_evidence_eligible_candidates": len(eligible["all_ecology"]),
        }
    )
    return pd.DataFrame(rows), ledgers


def _run_discovery_universe(
    simulations: dict[str, KnownTruthSimulation],
    *,
    universe: str,
    procedures: tuple[RecoveryProcedure, ...],
    minimum_predictor_coverage: float,
    outer_folds: int,
    random_state_offset: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
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
        coverage["species"] = taxon
        coverage["universe"] = universe
        coverage_frames.append(coverage)
        predictors = (
            CANDIDATE_ECOLOGICAL_PREDICTORS
            if universe == "raw"
            else admissibility.predictors
        )
        predictor_rows.append(
            {
                "species": taxon,
                "universe": universe,
                "n_raw_predictors": len(CANDIDATE_ECOLOGICAL_PREDICTORS),
                "n_model_pool_admissible_predictors": len(admissibility.predictors),
                "n_used_predictors": len(predictors),
                "used_predictors": ",".join(predictors),
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
                benchmark = benchmark_recovery_procedures(
                    occurrence,
                    background,
                    partition.presence_blocks,
                    partition.background_blocks,
                    predictors,
                    simulation.audit_predictors,
                    procedures,
                    outer_folds=outer_folds,
                )
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                status_rows.append(
                    {
                        "species": taxon,
                        "universe": universe,
                        "perturbation": perturbation,
                        "status": "abstain_no_evaluable_outer_folds",
                        "error": str(exc),
                        "random_state": random_state,
                    }
                )
                continue
            status_rows.append(
                {
                    "species": taxon,
                    "universe": universe,
                    "perturbation": perturbation,
                    "status": "success",
                    "error": None,
                    "random_state": random_state,
                }
            )
            metrics = benchmark.fold_metrics.copy()
            metrics["species"] = taxon
            metrics["universe"] = universe
            metrics["perturbation"] = perturbation
            metrics["perturbation_type"] = "sampling_or_background"
            metrics["n_candidate_ecological_predictors"] = len(predictors)
            metric_frames.append(metrics)
    return (
        pd.concat(metric_frames, ignore_index=True) if metric_frames else pd.DataFrame(),
        pd.DataFrame(status_rows),
        pd.concat(coverage_frames, ignore_index=True),
        pd.DataFrame(predictor_rows),
    )


def _fit_and_open_validation_truth(
    simulations: dict[str, KnownTruthSimulation],
    selectors: pd.DataFrame,
    procedures: tuple[RecoveryProcedure, ...],
    *,
    minimum_predictor_coverage: float,
    prediction_surface_coverage_floor: float,
    inner_folds: int,
    random_state_offset: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    procedure_by_label = {procedure.label: procedure for procedure in procedures}
    fit_rows: list[dict[str, object]] = []
    truth_rows: list[dict[str, object]] = []
    coverage_frames: list[pd.DataFrame] = []
    process_aliases = dict(DEFAULT_PROCESS_ALIASES)
    process_aliases.update(
        {"sparse_temp_proxy": "temperature", "sparse_noise": "noise"}
    )

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
        coverage["species"] = taxon
        coverage["taxon_role"] = "validation"
        coverage_frames.append(coverage)
        canonical_background = backgrounds[CANONICAL_M]
        partition = make_spatial_partition(
            occurrence["longitude"].to_numpy(float),
            occurrence["latitude"].to_numpy(float),
            canonical_background["longitude"].to_numpy(float),
            canonical_background["latitude"].to_numpy(float),
            n_blocks=max(4, int(inner_folds) + 1),
            holdout_fraction=0.20,
            random_state=int(random_state_offset + taxon_index),
        )
        for row in selectors.itertuples(index=False):
            regime = str(row.regime)
            selector = str(row.selector)
            candidate = None if pd.isna(row.candidate) else str(row.candidate)
            universe = "coverage" if regime.startswith("coverage") else "raw"
            predictors = (
                admissibility.predictors
                if universe == "coverage"
                else CANDIDATE_ECOLOGICAL_PREDICTORS
            )
            base = {
                "species": taxon,
                "family": str(simulation.environment["scenario"].iloc[0]),
                "seed": int(taxon.rsplit("seed", 1)[1]),
                "regime": regime,
                "selector": selector,
                "universe": universe,
                "procedure": candidate,
                "n_candidate_ecological_predictors": len(predictors),
            }
            if candidate is None:
                fit_rows.append(
                    {
                        **base,
                        "fit_status": "not_attempted_discovery_selector_abstained",
                        "fit_error": None,
                    }
                )
                truth_rows.append(
                    {
                        **base,
                        "truth_status": "not_evaluable_discovery_selector_abstained",
                        "prediction_surface_coverage": float("nan"),
                    }
                )
                continue
            procedure = procedure_by_label.get(candidate)
            if procedure is None:
                raise KeyError(f"frozen selector refers to unknown procedure {candidate!r}")
            try:
                fitted = fit_recovery_procedure(
                    occurrence,
                    canonical_background,
                    partition.presence_blocks,
                    partition.background_blocks,
                    predictors,
                    simulation.audit_predictors,
                    procedure,
                )
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                fit_rows.append(
                    {**base, "fit_status": "abstain_final_fit", "fit_error": str(exc)}
                )
                truth_rows.append(
                    {
                        **base,
                        "truth_status": "not_evaluable_final_fit_abstained",
                        "prediction_surface_coverage": float("nan"),
                    }
                )
                continue
            fit_rows.append(
                {
                    **base,
                    "fit_status": "success",
                    "fit_error": None,
                    "selected_predictors": ",".join(fitted.selected_predictors),
                    "selected_ecological_predictors": ",".join(
                        fitted.selected_ecological_predictors
                    ),
                    "n_selected_predictors": len(fitted.selected_predictors),
                }
            )

            # Truth is first opened here, after discovery selectors are frozen and
            # the validation model has been fit without truth columns.
            environment = simulation.environment
            predicted = score_ecological_suitability(
                fitted.model,
                environment,
                fitted.selected_predictors,
                observation_predictors=procedure.observation_predictors,
                observation_reference=canonical_background,
            )
            surface_coverage = float(np.isfinite(predicted).mean())
            truth = environment[simulation.true_suitability_column].to_numpy(float)
            if surface_coverage < float(prediction_surface_coverage_floor):
                truth_rows.append(
                    {
                        **base,
                        "truth_status": "abstain_prediction_surface_coverage",
                        "prediction_surface_coverage": surface_coverage,
                        "selected_ecological_predictors": ",".join(
                            fitted.selected_ecological_predictors
                        ),
                    }
                )
                continue
            niche = known_truth_niche_recovery_profile(
                environment,
                predicted,
                truth,
                simulation.audit_predictors,
            )
            response = known_truth_response_profile(
                environment,
                predicted,
                truth,
                infer_response_predictors(environment),
            )
            process = known_truth_process_profile(
                fitted.selected_ecological_predictors,
                infer_true_processes(environment),
                process_aliases=process_aliases,
            )
            payload = {**niche.as_dict(), **response.as_dict(), **process.as_dict()}
            finite_truth = all(
                np.isfinite(float(payload[column])) for column in TRUTH_DIRECTIONS
            )
            truth_rows.append(
                {
                    **base,
                    "truth_status": "complete"
                    if finite_truth
                    else "abstain_nonfinite_truth_metric",
                    "prediction_surface_coverage": surface_coverage,
                    "selected_ecological_predictors": ",".join(
                        fitted.selected_ecological_predictors
                    ),
                    **payload,
                }
            )
    return (
        pd.DataFrame(fit_rows),
        pd.DataFrame(truth_rows),
        pd.concat(coverage_frames, ignore_index=True),
    )


def _rank_truth_evaluation(truth: pd.DataFrame) -> pd.DataFrame:
    data = truth.copy()
    if data.empty:
        return data
    complete = data["truth_status"].astype(str).eq("complete")
    rank_columns: list[str] = []
    for metric, direction in TRUTH_DIRECTIONS.items():
        column = f"truth_rank__{metric}"
        values = pd.to_numeric(data[metric], errors="coerce")
        data[column] = float("nan")
        for _, index in data.loc[complete].groupby("species").groups.items():
            data.loc[index, column] = values.loc[index].rank(
                method="min", ascending=direction == "min"
            )
        rank_columns.append(column)
    data["truth_worst_metric_rank"] = data[rank_columns].max(axis=1, skipna=False)
    data["truth_mean_metric_rank"] = data[rank_columns].mean(axis=1, skipna=False)
    data["truth_co_winner"] = False
    for _, group in data.loc[complete].groupby("species"):
        best_worst = float(group["truth_worst_metric_rank"].min())
        finalists = group.loc[
            np.isclose(group["truth_worst_metric_rank"], best_worst, equal_nan=False)
        ]
        best_mean = float(finalists["truth_mean_metric_rank"].min())
        winners = finalists.index[
            np.isclose(finalists["truth_mean_metric_rank"], best_mean, equal_nan=False)
        ]
        data.loc[winners, "truth_co_winner"] = True
    return data


def _truth_summary(truth: pd.DataFrame) -> pd.DataFrame:
    if truth.empty:
        return pd.DataFrame()
    data = truth.copy()
    data["truth_evaluable"] = data["truth_status"].astype(str).eq("complete")
    aggregation: dict[str, tuple[str, str]] = {
        "n_validation_taxa": ("species", "nunique"),
        "n_truth_evaluable": ("truth_evaluable", "sum"),
        "truth_co_win_fraction": ("truth_co_winner", "mean"),
        "mean_prediction_surface_coverage": ("prediction_surface_coverage", "mean"),
        "mean_truth_worst_rank": ("truth_worst_metric_rank", "mean"),
        "mean_truth_mean_rank": ("truth_mean_metric_rank", "mean"),
    }
    for metric in TRUTH_DIRECTIONS:
        aggregation[f"mean_{metric}"] = (metric, "mean")
    return (
        data.groupby(["regime", "selector"], as_index=False)
        .agg(**aggregation)
        .sort_values(
            [
                "regime",
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


def _decision_ledger(
    selectors: pd.DataFrame,
    summary: pd.DataFrame,
    *,
    n_validation_taxa: int,
) -> pd.DataFrame:
    v21_selection = selectors.loc[selectors["regime"].eq("coverage_complete")]
    selected_count = int(v21_selection["status"].astype(str).eq("selected").sum())
    auc_rows = summary.loc[
        summary["regime"].eq("coverage_complete")
        & summary["selector"].eq("canonical_auc")
    ]
    ecology_rows = summary.loc[
        summary["regime"].eq("coverage_complete")
        & summary["selector"].isin(("canonical_ecology", "robust_ecology"))
    ].copy()
    if not ecology_rows.empty:
        ecology_rows = ecology_rows.sort_values(
            [
                "n_truth_evaluable",
                "mean_truth_worst_rank",
                "mean_truth_mean_rank",
                "selector",
            ],
            ascending=[False, True, True, True],
            na_position="last",
            kind="mergesort",
        )
    best_ecology = ecology_rows.iloc[0] if not ecology_rows.empty else None
    auc = auc_rows.iloc[0] if not auc_rows.empty else None

    evidence_rows = selectors.loc[
        selectors["selector"].eq("robust_ecology")
        & selectors["regime"].isin(("raw_complete", "coverage_complete"))
    ].set_index("regime")
    raw_complete_candidates = (
        int(evidence_rows.loc["raw_complete", "n_evidence_eligible_candidates"])
        if "raw_complete" in evidence_rows.index
        else 0
    )
    coverage_complete_candidates = (
        int(evidence_rows.loc["coverage_complete", "n_evidence_eligible_candidates"])
        if "coverage_complete" in evidence_rows.index
        else 0
    )
    evidence_restored_or_preserved = (
        coverage_complete_candidates >= raw_complete_candidates
        and coverage_complete_candidates > 0
    )

    ecological_not_worse_than_auc = False
    all_validation_evaluable = False
    best_selector = None
    if best_ecology is not None:
        best_selector = str(best_ecology["selector"])
        all_validation_evaluable = int(best_ecology["n_truth_evaluable"]) == int(
            n_validation_taxa
        )
    if best_ecology is not None and auc is not None:
        ecology_n = int(best_ecology["n_truth_evaluable"])
        auc_n = int(auc["n_truth_evaluable"])
        ecological_not_worse_than_auc = (
            ecology_n >= auc_n
            and (
                auc_n == 0
                or (
                    np.isfinite(float(best_ecology["mean_truth_worst_rank"]))
                    and np.isfinite(float(auc["mean_truth_worst_rank"]))
                    and float(best_ecology["mean_truth_worst_rank"])
                    <= float(auc["mean_truth_worst_rank"]) + 1e-12
                    and float(best_ecology["mean_truth_mean_rank"])
                    <= float(auc["mean_truth_mean_rank"]) + 1e-12
                )
            )
        )

    if (
        selected_count == len(SELECTORS)
        and evidence_restored_or_preserved
        and all_validation_evaluable
        and ecological_not_worse_than_auc
    ):
        status = "supported"
    elif selected_count > 0 and evidence_restored_or_preserved:
        status = "partially_supported"
    else:
        status = "not_supported"
    return pd.DataFrame(
        [
            {
                "decision": status,
                "scientific_promotion_allowed": False,
                "negative_outcome_accepted": True,
                "n_coverage_complete_selectors_selected": selected_count,
                "raw_complete_robust_eligible_candidates": raw_complete_candidates,
                "coverage_complete_robust_eligible_candidates": coverage_complete_candidates,
                "evidence_restored_or_preserved": evidence_restored_or_preserved,
                "best_coverage_complete_ecological_selector": best_selector,
                "all_validation_taxa_truth_evaluable_for_best_ecology": all_validation_evaluable,
                "best_ecology_not_worse_than_canonical_auc": ecological_not_worse_than_auc,
                "interpretation": (
                    "development support only; freeze before a newly rebuilt "
                    "sealed-before-M confirmation"
                    if status == "supported"
                    else "retain as development/negative evidence; do not promote"
                ),
            }
        ]
    )


def run_known_truth_gate_ablation(
    *,
    n_cells: int = 2200,
    n_occurrences: int = 220,
    n_target_group: int = 850,
    inner_folds: int = 2,
    outer_folds: int = 2,
    max_predictors: int = 4,
    minimum_predictor_coverage: float = 0.95,
    prediction_surface_coverage_floor: float = 0.95,
) -> dict[str, Any]:
    procedures = _procedure_library(
        inner_folds=inner_folds, max_predictors=max_predictors
    )
    discovery_simulations = {
        spec.taxon: _simulate_taxon(
            spec,
            n_cells=n_cells,
            n_occurrences=n_occurrences,
            n_target_group=n_target_group,
        )
        for spec in DISCOVERY_TAXA
    }
    discovery_outputs = {}
    # Raw and coverage universes use identical partitions for a paired ablation.
    for universe, offset in (("raw", 11000), ("coverage", 11000)):
        discovery_outputs[universe] = _run_discovery_universe(
            discovery_simulations,
            universe=universe,
            procedures=procedures,
            minimum_predictor_coverage=minimum_predictor_coverage,
            outer_folds=outer_folds,
            random_state_offset=offset,
        )

    selector_frames: list[pd.DataFrame] = []
    gate_outputs: dict[str, dict[str, tuple[pd.DataFrame, pd.DataFrame]]] = {}
    for regime in REGIMES:
        universe = "coverage" if regime.startswith("coverage") else "raw"
        selectors, ledgers = _select_regime(
            discovery_outputs[universe][0],
            regime=regime,
            discovery_taxa=tuple(discovery_simulations),
            canonical_m=CANONICAL_M,
            expected_outer_folds=outer_folds,
        )
        selector_frames.append(selectors)
        gate_outputs[regime] = ledgers
    selectors = pd.concat(selector_frames, ignore_index=True)

    validation_simulations = {
        spec.taxon: _simulate_taxon(
            spec,
            n_cells=n_cells,
            n_occurrences=n_occurrences,
            n_target_group=n_target_group,
        )
        for spec in VALIDATION_TAXA
    }
    validation_fit, truth, validation_coverage = _fit_and_open_validation_truth(
        validation_simulations,
        selectors,
        procedures,
        minimum_predictor_coverage=minimum_predictor_coverage,
        prediction_surface_coverage_floor=prediction_surface_coverage_floor,
        inner_folds=inner_folds,
        random_state_offset=31000,
    )
    truth = _rank_truth_evaluation(truth)
    summary = _truth_summary(truth)
    decision = _decision_ledger(
        selectors, summary, n_validation_taxa=len(validation_simulations)
    )
    return {
        "procedures": procedures,
        "discovery_outputs": discovery_outputs,
        "selectors": selectors,
        "gate_outputs": gate_outputs,
        "validation_fit": validation_fit,
        "truth": truth,
        "summary": summary,
        "validation_coverage": validation_coverage,
        "decision": decision,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Product-A v2.1 pre-outcome gates against unseen known truth."
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--n-cells", type=int, default=2200)
    parser.add_argument("--n-occurrences", type=int, default=220)
    parser.add_argument("--n-target-group", type=int, default=850)
    parser.add_argument("--inner-folds", type=int, default=2)
    parser.add_argument("--outer-folds", type=int, default=2)
    parser.add_argument("--max-predictors", type=int, default=4)
    parser.add_argument("--minimum-predictor-coverage", type=float, default=0.95)
    parser.add_argument("--prediction-surface-coverage-floor", type=float, default=0.95)
    args = parser.parse_args(argv)
    output = run_known_truth_gate_ablation(
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
    for universe, (metrics, status, coverage, predictor_summary) in output[
        "discovery_outputs"
    ].items():
        metrics.to_csv(out / f"discovery_fold_metrics__{universe}.csv", index=False)
        status.to_csv(out / f"discovery_benchmark_status__{universe}.csv", index=False)
        coverage.to_csv(out / f"discovery_predictor_coverage__{universe}.csv", index=False)
        predictor_summary.to_csv(
            out / f"discovery_predictor_universe__{universe}.csv", index=False
        )
    output["selectors"].to_csv(out / "discovery_frozen_selectors.csv", index=False)
    for regime, ledgers in output["gate_outputs"].items():
        for name, (cells, summary) in ledgers.items():
            cells.to_csv(out / f"evidence_cells__{regime}__{name}.csv", index=False)
            summary.to_csv(
                out / f"evidence_candidates__{regime}__{name}.csv", index=False
            )
    output["validation_fit"].to_csv(out / "validation_fit_status.csv", index=False)
    output["truth"].to_csv(out / "validation_truth_evaluation.csv", index=False)
    output["summary"].to_csv(out / "validation_truth_summary.csv", index=False)
    output["validation_coverage"].to_csv(
        out / "validation_predictor_coverage.csv", index=False
    )
    output["decision"].to_csv(out / "development_decision.csv", index=False)

    contract = {
        "purpose": "product_a_v2_1_preoutcome_known_truth_gate_ablation",
        "scientific_promotion_run": False,
        "real_empirical_data_read": False,
        "old_external_sealed_outcomes_read": False,
        "selection_never_uses_truth": True,
        "truth_columns_removed_before_discovery_selection": True,
        "validation_truth_opened_after_all_discovery_selectors_frozen": True,
        "negative_and_abstention_outcomes_accepted": True,
        "discovery_taxa": [
            {"taxon": spec.taxon, "family": spec.family, "seed": spec.seed}
            for spec in DISCOVERY_TAXA
        ],
        "validation_taxa": [
            {"taxon": spec.taxon, "family": spec.family, "seed": spec.seed}
            for spec in VALIDATION_TAXA
        ],
        "background_perturbations": list(M_SPECS),
        "canonical_background": CANONICAL_M,
        "regimes": list(REGIMES),
        "selectors": list(SELECTORS),
        "candidate_predictor_gate": {
            "minimum_coverage": args.minimum_predictor_coverage,
            "model_pool_only": True,
            "required_across_all_M": True,
            "sparse_predictors": list(SPARSE_PREDICTORS),
        },
        "candidate_outer_fold_gate": {
            "expected_outer_folds": args.outer_folds,
            "missing_fold_is_explicit_evidence_insufficiency": True,
        },
        "truth_surface_coverage_floor": args.prediction_surface_coverage_floor,
        "procedure_labels": [procedure.label for procedure in output["procedures"]],
        "n_cells": args.n_cells,
        "n_occurrences": args.n_occurrences,
        "n_target_group": args.n_target_group,
        "inner_folds": args.inner_folds,
        "outer_folds": args.outer_folds,
        "max_predictors": args.max_predictors,
        "development_decision": str(output["decision"].iloc[0]["decision"]),
        "promotion_requirement": (
            "freeze v2.1 before a newly rebuilt sealed-before-M split or another "
            "genuinely unused external evidence line"
        ),
    }
    (out / "product_a_v2_1_known_truth_contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
