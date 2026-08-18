"""Predeclared known-truth experiment for Product-A v2.3 certificates.

Discovery data freeze complete/adequate and ecological-Pareto candidate sets.
Validation procedures are then refit under every M without access to generating
truth. A certificate is available only when every retained procedure × M member
fits and produces a complete ecological response surface. Truth opens afterwards
for process and boundary coverage audits.
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
from .ecological_certificate import (
    audit_certificate_against_truth,
    audit_point_response_against_truth,
    build_ecological_certificate,
    response_point_estimates,
    select_ecological_candidate_sets,
)
from .known_truth_response import (
    DEFAULT_PROCESS_ALIASES,
    infer_response_predictors,
    infer_true_processes,
)
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES
from .model import score_ecological_suitability
from .model_pool_predictor_admissibility import (
    select_model_pool_admissible_predictors,
)
from .niche_recovery_procedure import (
    RecoveryProcedure,
    benchmark_recovery_procedures,
)
from .prepared_recovery_procedure_cli import _mean_auc_winner
from .recovery_procedure_fit import fit_recovery_procedure
from .v2_1_known_truth_gate_ablation import (
    CANONICAL_M,
    CANDIDATE_ECOLOGICAL_PREDICTORS,
    M_SPECS,
    SimulatedTaxonSpec,
    _model_only_frame,
    _nested_background_perturbations,
    _procedure_library,
    _simulate_taxon,
)
from .validation import make_spatial_partition


PRODUCTS = (
    "canonical_auc_point",
    "complete_adequate_certificate",
    "ecological_pareto_certificate",
)
EXPECTED_SET_ORDER = (
    "complete_candidate_evidence",
    "absolute_prediction_adequacy",
    "ecological_recovery_pareto_set",
)
DECISION_STATES = (
    "identified_set_supported",
    "identified_set_trivial",
    "identified_set_not_supported",
    "identified_set_unavailable",
)


@dataclass(frozen=True)
class CertificatePanel:
    name: str
    discovery: tuple[SimulatedTaxonSpec, ...]
    validation: tuple[SimulatedTaxonSpec, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_certificate_panels(
    path: str | Path,
) -> tuple[dict[str, object], tuple[CertificatePanel, ...]]:
    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if payload.get("scientific_promotion_run") is not False:
        raise ValueError("v2.3 certificate panels cannot be promotion runs")
    if payload.get("real_empirical_data_read") is not False:
        raise ValueError("v2.3 certificate panels cannot read empirical data")
    if payload.get("old_external_sealed_outcomes_read") is not False:
        raise ValueError("old external sealed outcomes are forbidden")
    if tuple(payload.get("products", ())) != PRODUCTS:
        raise ValueError("v2.3 products changed after predeclaration")
    if tuple(payload.get("candidate_set_order", ())) != EXPECTED_SET_ORDER:
        raise ValueError("v2.3 candidate-set order changed")
    semantics = payload.get("process_set_semantics", {})
    if semantics.get("support_frequency_threshold", "missing") is not None:
        raise ValueError("v2.3 process sets must not use a support threshold")
    if set(payload.get("decision_states", ())) != set(DECISION_STATES):
        raise ValueError("v2.3 decision states changed")

    maximum_opened_seed = int(
        payload.get("opened_known_truth_seeds_excluded", {}).get("maximum", -1)
    )
    panels: list[CertificatePanel] = []
    names: set[str] = set()
    seeds: set[int] = set()
    for raw_panel in payload.get("panels", ()):
        name = str(raw_panel["name"])
        if name in names:
            raise ValueError(f"duplicate panel name: {name}")
        names.add(name)
        roles: dict[str, tuple[SimulatedTaxonSpec, ...]] = {}
        for role in ("discovery", "validation"):
            specs: list[SimulatedTaxonSpec] = []
            for raw_spec in raw_panel.get(role, ()):
                family = str(raw_spec["family"])
                seed = int(raw_spec["seed"])
                if family not in KNOWN_TRUTH_FAMILIES:
                    raise ValueError(f"unknown known-truth family: {family}")
                if seed <= maximum_opened_seed:
                    raise ValueError(f"seed {seed} was previously opened")
                if seed in seeds:
                    raise ValueError(f"duplicate v2.3 seed: {seed}")
                seeds.add(seed)
                specs.append(SimulatedTaxonSpec(family, seed, role))
            if len(specs) != 3:
                raise ValueError(f"{name} must contain three {role} taxa")
            roles[role] = tuple(specs)
        panels.append(
            CertificatePanel(
                name=name,
                discovery=roles["discovery"],
                validation=roles["validation"],
            )
        )
    if len(panels) != 3:
        raise ValueError("v2.3 requires exactly three panels")
    return payload, tuple(panels)


def _process_aliases() -> dict[str, str]:
    aliases = dict(DEFAULT_PROCESS_ALIASES)
    aliases.update(
        {
            "sparse_temp_proxy": "temperature",
            "sparse_noise": "noise",
        }
    )
    return aliases


def _process_groups(predictors: tuple[str, ...]) -> tuple[str, ...]:
    aliases = _process_aliases()
    groups = {
        aliases.get(str(predictor), str(predictor))
        for predictor in predictors
    }
    groups.discard("observation_process")
    return tuple(sorted(groups))


def _process_universe() -> tuple[str, ...]:
    return _process_groups(tuple(CANDIDATE_ECOLOGICAL_PREDICTORS))


def _run_discovery_panel(
    panel: CertificatePanel,
    *,
    procedures: tuple[RecoveryProcedure, ...],
    n_cells: int,
    n_occurrences: int,
    n_target_group: int,
    minimum_predictor_coverage: float,
    outer_folds: int,
    random_state_offset: int,
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
                "n_admissible_predictors": len(admissibility.predictors),
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
                benchmark = benchmark_recovery_procedures(
                    occurrence,
                    background,
                    partition.presence_blocks,
                    partition.background_blocks,
                    admissibility.predictors,
                    simulation.audit_predictors,
                    procedures,
                    outer_folds=outer_folds,
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
            metric_frames.append(metrics)

    return (
        pd.concat(metric_frames, ignore_index=True)
        if metric_frames
        else pd.DataFrame(),
        pd.DataFrame(status_rows),
        pd.concat(coverage_frames, ignore_index=True),
        pd.DataFrame(predictor_rows),
    )


def _freeze_products(
    metrics: pd.DataFrame,
    *,
    discovery_taxa: tuple[str, ...],
    expected_outer_folds: int,
) -> tuple[pd.DataFrame, Any]:
    sets = select_ecological_candidate_sets(
        metrics,
        discovery_taxa=discovery_taxa,
        perturbations=M_SPECS,
        expected_outer_folds=expected_outer_folds,
    )
    canonical = metrics.loc[
        metrics["perturbation"].astype(str).eq(CANONICAL_M)
    ].copy()
    canonical_gate = require_complete_outer_fold_evidence(
        canonical,
        discovery_taxa=discovery_taxa,
        perturbations=(CANONICAL_M,),
        required_columns=("presence_rank",),
        expected_outer_folds=expected_outer_folds,
    )
    canonical_auc = None
    canonical_error = None
    if canonical_gate.eligible_candidates:
        eligible = set(canonical_gate.eligible_candidates)
        try:
            canonical_auc = _mean_auc_winner(
                canonical.loc[canonical["candidate"].astype(str).isin(eligible)]
            )
        except ValueError as exc:
            canonical_error = str(exc)
    else:
        canonical_error = "no complete canonical AUC candidate"

    rows = [
        {
            "product": "canonical_auc_point",
            "status": "frozen" if canonical_auc else "unavailable",
            "n_candidates": int(canonical_auc is not None),
            "candidates": canonical_auc,
            "error": canonical_error,
        },
        {
            "product": "complete_adequate_certificate",
            "status": "frozen" if sets.adequate_candidates else "unavailable",
            "n_candidates": len(sets.adequate_candidates),
            "candidates": ",".join(sets.adequate_candidates),
            "error": None if sets.adequate_candidates else "empty adequate set",
        },
        {
            "product": "ecological_pareto_certificate",
            "status": (
                "frozen" if sets.ecological_pareto_candidates else "unavailable"
            ),
            "n_candidates": len(sets.ecological_pareto_candidates),
            "candidates": ",".join(sets.ecological_pareto_candidates),
            "error": (
                None
                if sets.ecological_pareto_candidates
                else "empty ecological recovery Pareto set"
            ),
        },
    ]
    return pd.DataFrame(rows), sets


def _parse_candidates(value: object) -> tuple[str, ...]:
    if value is None or pd.isna(value) or not str(value):
        return ()
    return tuple(x for x in str(value).split(",") if x)


def _fit_validation_taxon(
    *,
    panel: str,
    simulation,
    products: pd.DataFrame,
    procedures: tuple[RecoveryProcedure, ...],
    minimum_predictor_coverage: float,
    prediction_surface_coverage_floor: float,
    inner_folds: int,
    random_state_offset: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    procedure_by_label = {procedure.label: procedure for procedure in procedures}
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
    taxon = str(occurrence["species"].iloc[0])
    coverage = admissibility.ledger.copy()
    coverage["panel"] = panel
    coverage["species"] = taxon

    product_candidates = {
        str(row.product): _parse_candidates(row.candidates)
        for row in products.itertuples(index=False)
    }
    unique_candidates = sorted(
        set().union(*[set(values) for values in product_candidates.values()])
    )
    expected_members: dict[str, tuple[str, ...]] = {
        "canonical_auc_point": (
            (f"{product_candidates['canonical_auc_point'][0]}::{CANONICAL_M}",)
            if product_candidates["canonical_auc_point"]
            else ()
        ),
        "complete_adequate_certificate": tuple(
            f"{candidate}::{perturbation}"
            for candidate in product_candidates["complete_adequate_certificate"]
            for perturbation in M_SPECS
        ),
        "ecological_pareto_certificate": tuple(
            f"{candidate}::{perturbation}"
            for candidate in product_candidates["ecological_pareto_certificate"]
            for perturbation in M_SPECS
        ),
    }

    fit_rows: list[dict[str, object]] = []
    fit_cache: dict[str, dict[str, object]] = {}
    for candidate_index, candidate in enumerate(unique_candidates):
        procedure = procedure_by_label.get(candidate)
        if procedure is None:
            raise KeyError(f"unknown frozen procedure: {candidate}")
        perturbations = (
            M_SPECS
            if candidate
            in set(product_candidates["complete_adequate_certificate"])
            | set(product_candidates["ecological_pareto_certificate"])
            else (CANONICAL_M,)
        )
        for perturbation_index, perturbation in enumerate(perturbations):
            member_id = f"{candidate}::{perturbation}"
            background = backgrounds[perturbation]
            partition = make_spatial_partition(
                occurrence["longitude"].to_numpy(float),
                occurrence["latitude"].to_numpy(float),
                background["longitude"].to_numpy(float),
                background["latitude"].to_numpy(float),
                n_blocks=max(4, int(inner_folds) + 1),
                holdout_fraction=0.20,
                random_state=int(
                    random_state_offset
                    + candidate_index * 100
                    + perturbation_index
                ),
            )
            base = {
                "panel": panel,
                "species": taxon,
                "member_id": member_id,
                "candidate": candidate,
                "perturbation": perturbation,
            }
            try:
                fitted = fit_recovery_procedure(
                    occurrence,
                    background,
                    partition.presence_blocks,
                    partition.background_blocks,
                    admissibility.predictors,
                    simulation.audit_predictors,
                    procedure,
                )
                predicted = score_ecological_suitability(
                    fitted.model,
                    simulation.environment,
                    fitted.selected_predictors,
                    observation_predictors=procedure.observation_predictors,
                    observation_reference=background,
                )
                surface_coverage = float(np.isfinite(predicted).mean())
                if surface_coverage < float(prediction_surface_coverage_floor):
                    raise ValueError(
                        "prediction surface coverage below predeclared floor: "
                        f"{surface_coverage:.6f}"
                    )
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                fit_rows.append(
                    {
                        **base,
                        "fit_status": "abstain_member_fit",
                        "fit_error": str(exc),
                        "prediction_surface_coverage": float("nan"),
                    }
                )
                continue
            processes = _process_groups(fitted.selected_ecological_predictors)
            fit_cache[member_id] = {
                "predicted": predicted,
                "processes": processes,
                "selected_predictors": fitted.selected_predictors,
                "selected_ecological_predictors": (
                    fitted.selected_ecological_predictors
                ),
            }
            fit_rows.append(
                {
                    **base,
                    "fit_status": "success",
                    "fit_error": None,
                    "prediction_surface_coverage": surface_coverage,
                    "selected_predictors": ",".join(fitted.selected_predictors),
                    "selected_ecological_predictors": ",".join(
                        fitted.selected_ecological_predictors
                    ),
                    "selected_processes": ",".join(processes),
                }
            )

    # The generating truth and true response axes are first accessed after every
    # product and procedure × M member has been frozen and fit.
    environment = simulation.environment
    truth = environment[simulation.true_suitability_column].to_numpy(float)
    response_predictors = infer_response_predictors(environment)
    true_response = response_point_estimates(
        environment,
        truth,
        response_predictors,
        member_id="truth",
    )
    true_processes = infer_true_processes(environment)

    audit_rows: list[dict[str, object]] = []
    boundary_frames: list[pd.DataFrame] = []
    interval_frames: list[pd.DataFrame] = []
    point_frames: list[pd.DataFrame] = []
    for product in PRODUCTS:
        members = expected_members[product]
        base = {
            "panel": panel,
            "species": taxon,
            "family": str(environment["scenario"].iloc[0]),
            "seed": int(taxon.rsplit("seed", 1)[1]),
            "product": product,
            "n_expected_members": len(members),
        }
        if not members or any(member not in fit_cache for member in members):
            audit_rows.append(
                {
                    **base,
                    "certificate_status": "unavailable_incomplete_member_fits",
                    "n_successful_members": int(
                        sum(member in fit_cache for member in members)
                    ),
                }
            )
            continue
        member_processes = {
            member: fit_cache[member]["processes"] for member in members
        }
        response_frames = [
            response_point_estimates(
                environment,
                fit_cache[member]["predicted"],
                response_predictors,
                member_id=member,
            )
            for member in members
        ]
        responses = pd.concat(response_frames, ignore_index=True)
        required_response_rows = len(members) * len(response_predictors) * 3
        if (
            len(responses) != required_response_rows
            or not np.isfinite(
                pd.to_numeric(responses["estimate"], errors="coerce")
            ).all()
        ):
            audit_rows.append(
                {
                    **base,
                    "certificate_status": "unavailable_incomplete_member_response",
                    "n_successful_members": len(members),
                }
            )
            continue
        certificate = build_ecological_certificate(
            member_processes,
            responses,
            process_universe=_process_universe(),
        )
        summary, boundary = audit_certificate_against_truth(
            certificate,
            true_processes=true_processes,
            truth_response_estimates=true_response,
        )
        point_summary: dict[str, object] = {}
        if product == "canonical_auc_point":
            point_summary, point_audit = audit_point_response_against_truth(
                responses,
                true_response,
            )
            point_audit["panel"] = panel
            point_audit["species"] = taxon
            point_audit["product"] = product
            point_frames.append(point_audit)
        audit_rows.append(
            {
                **base,
                "certificate_status": "complete",
                "n_successful_members": len(members),
                **summary,
                **point_summary,
            }
        )
        boundary["panel"] = panel
        boundary["species"] = taxon
        boundary["product"] = product
        boundary_frames.append(boundary)
        intervals = certificate.boundary_intervals.copy()
        intervals["panel"] = panel
        intervals["species"] = taxon
        intervals["product"] = product
        interval_frames.append(intervals)

    return (
        pd.DataFrame(fit_rows),
        pd.DataFrame(audit_rows),
        pd.concat(boundary_frames, ignore_index=True)
        if boundary_frames
        else pd.DataFrame(),
        pd.concat(interval_frames, ignore_index=True)
        if interval_frames
        else pd.DataFrame(),
        pd.concat(point_frames, ignore_index=True)
        if point_frames
        else pd.DataFrame(),
        coverage,
    )


def _product_summary(audit: pd.DataFrame) -> pd.DataFrame:
    if audit.empty:
        return pd.DataFrame()
    data = audit.copy()
    data["complete"] = data["certificate_status"].astype(str).eq("complete")
    numeric = (
        "n_false_necessary_processes",
        "possible_process_recall",
        "possible_process_precision",
        "boundary_coverage_fraction",
        "mean_normalized_interval_width",
        "n_possible_processes",
        "n_necessary_processes",
        "mean_normalized_absolute_error",
    )
    for column in numeric:
        if column not in data:
            data[column] = float("nan")
    return (
        data.groupby(["panel", "product"], as_index=False)
        .agg(
            n_validation_taxa=("species", "nunique"),
            n_complete_certificates=("complete", "sum"),
            total_false_necessary_processes=(
                "n_false_necessary_processes",
                "sum",
            ),
            mean_possible_process_recall=("possible_process_recall", "mean"),
            mean_possible_process_precision=("possible_process_precision", "mean"),
            mean_boundary_coverage=("boundary_coverage_fraction", "mean"),
            mean_interval_width=("mean_normalized_interval_width", "mean"),
            mean_possible_processes=("n_possible_processes", "mean"),
            mean_necessary_processes=("n_necessary_processes", "mean"),
            mean_canonical_point_error=(
                "mean_normalized_absolute_error",
                "mean",
            ),
        )
        .sort_values(["panel", "product"], kind="mergesort")
        .reset_index(drop=True)
    )


def identified_set_decision(summary: pd.DataFrame) -> pd.DataFrame:
    panels = tuple(sorted(summary["panel"].astype(str).unique()))
    available = True
    full_truth_coverage = True
    no_worse_coverage = True
    no_broader = True
    strict_sharpness_panels = 0

    for panel in panels:
        group = summary.loc[summary["panel"].astype(str).eq(panel)].set_index(
            "product"
        )
        required = {
            "complete_adequate_certificate",
            "ecological_pareto_certificate",
            "canonical_auc_point",
        }
        if not required <= set(group.index):
            available = False
            continue
        complete = group.loc["complete_adequate_certificate"]
        pareto = group.loc["ecological_pareto_certificate"]
        n_validation = int(pareto["n_validation_taxa"])
        panel_available = (
            int(pareto["n_complete_certificates"]) == n_validation
            and int(complete["n_complete_certificates"]) == n_validation
            and n_validation > 0
        )
        available &= panel_available
        if not panel_available:
            continue
        panel_truth = (
            int(pareto["total_false_necessary_processes"]) == 0
            and float(pareto["mean_possible_process_recall"]) >= 1.0 - 1e-12
            and float(pareto["mean_boundary_coverage"]) >= 1.0 - 1e-12
        )
        full_truth_coverage &= panel_truth
        panel_no_worse = (
            int(pareto["total_false_necessary_processes"])
            <= int(complete["total_false_necessary_processes"])
            and float(pareto["mean_possible_process_recall"])
            >= float(complete["mean_possible_process_recall"]) - 1e-12
            and float(pareto["mean_boundary_coverage"])
            >= float(complete["mean_boundary_coverage"]) - 1e-12
        )
        no_worse_coverage &= panel_no_worse
        process_no_broader = (
            float(pareto["mean_possible_processes"])
            <= float(complete["mean_possible_processes"]) + 1e-12
        )
        interval_no_broader = (
            float(pareto["mean_interval_width"])
            <= float(complete["mean_interval_width"]) + 1e-12
        )
        no_broader &= process_no_broader and interval_no_broader
        strict = (
            float(pareto["mean_possible_processes"])
            < float(complete["mean_possible_processes"]) - 1e-12
            or float(pareto["mean_interval_width"])
            < float(complete["mean_interval_width"]) - 1e-12
        )
        strict_sharpness_panels += int(strict)

    if not available or len(panels) != 3:
        decision = "identified_set_unavailable"
    elif not full_truth_coverage or not no_worse_coverage or not no_broader:
        decision = "identified_set_not_supported"
    elif strict_sharpness_panels > 0:
        decision = "identified_set_supported"
    else:
        decision = "identified_set_trivial"

    next_action = {
        "identified_set_supported": (
            "retain the certificate method for a later newly rebuilt "
            "sealed-before-M confirmation"
        ),
        "identified_set_trivial": (
            "retain as honest but uninformative partial identification; do not confirm"
        ),
        "identified_set_not_supported": (
            "retain negative evidence and diagnose certificate coverage/sharpness"
        ),
        "identified_set_unavailable": (
            "diagnose incomplete adequate sets/member fits without relaxing gates"
        ),
    }[decision]
    return pd.DataFrame(
        [
            {
                "decision": decision,
                "scientific_promotion_allowed": False,
                "negative_or_trivial_outcome_accepted": True,
                "n_panels": len(panels),
                "all_panels_available": available,
                "full_truth_coverage": full_truth_coverage,
                "coverage_no_worse_than_complete_adequate": no_worse_coverage,
                "pareto_no_broader_than_complete_adequate": no_broader,
                "n_panels_with_strict_sharpness_gain": strict_sharpness_panels,
                "next_action": next_action,
            }
        ]
    )


def run_certificate_experiment(
    panel_config: str | Path,
    *,
    n_cells: int = 1700,
    n_occurrences: int = 170,
    n_target_group: int = 680,
    inner_folds: int = 2,
    outer_folds: int = 2,
    max_predictors: int = 4,
    minimum_predictor_coverage: float = 0.95,
    prediction_surface_coverage_floor: float = 0.95,
) -> dict[str, Any]:
    config_path = Path(panel_config)
    config, panels = load_certificate_panels(config_path)
    procedures = _procedure_library(
        inner_folds=inner_folds,
        max_predictors=max_predictors,
    )

    product_frames: list[pd.DataFrame] = []
    discovery_metric_frames: list[pd.DataFrame] = []
    discovery_status_frames: list[pd.DataFrame] = []
    discovery_coverage_frames: list[pd.DataFrame] = []
    discovery_predictor_frames: list[pd.DataFrame] = []
    member_fit_frames: list[pd.DataFrame] = []
    audit_frames: list[pd.DataFrame] = []
    boundary_frames: list[pd.DataFrame] = []
    interval_frames: list[pd.DataFrame] = []
    point_frames: list[pd.DataFrame] = []
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
            random_state_offset=90000 + panel_index * 1000,
        )
        products, candidate_sets = _freeze_products(
            metrics,
            discovery_taxa=tuple(spec.taxon for spec in panel.discovery),
            expected_outer_folds=outer_folds,
        )
        products["panel"] = panel.name
        products["n_complete_candidates"] = len(
            candidate_sets.complete_candidates
        )
        product_frames.append(products)
        discovery_metric_frames.append(metrics)
        discovery_status_frames.append(status)
        discovery_coverage_frames.append(coverage)
        discovery_predictor_frames.append(predictors)

        for validation_index, spec in enumerate(panel.validation):
            simulation = _simulate_taxon(
                spec,
                n_cells=n_cells,
                n_occurrences=n_occurrences,
                n_target_group=n_target_group,
            )
            (
                fits,
                audits,
                boundaries,
                intervals,
                point_audits,
                validation_coverage,
            ) = _fit_validation_taxon(
                panel=panel.name,
                simulation=simulation,
                products=products.drop(columns=["panel", "n_complete_candidates"]),
                procedures=procedures,
                minimum_predictor_coverage=minimum_predictor_coverage,
                prediction_surface_coverage_floor=(
                    prediction_surface_coverage_floor
                ),
                inner_folds=inner_folds,
                random_state_offset=(
                    100000 + panel_index * 10000 + validation_index * 1000
                ),
            )
            member_fit_frames.append(fits)
            audit_frames.append(audits)
            if not boundaries.empty:
                boundary_frames.append(boundaries)
            if not intervals.empty:
                interval_frames.append(intervals)
            if not point_audits.empty:
                point_frames.append(point_audits)
            validation_coverage_frames.append(validation_coverage)

    audits = pd.concat(audit_frames, ignore_index=True)
    summary = _product_summary(audits)
    decision = identified_set_decision(summary)
    contract = {
        "purpose": "product_a_v2_3_predeclared_set_valued_certificate",
        "scientific_promotion_run": False,
        "scientific_promotion_allowed": False,
        "real_empirical_data_read": False,
        "old_external_sealed_outcomes_read": False,
        "previously_opened_known_truth_used_for_validation": False,
        "discovery_candidate_sets_frozen_before_validation_truth": True,
        "single_winner_selected_from_pareto_set": False,
        "process_support_frequency_threshold": None,
        "panel_config": str(config_path),
        "panel_config_sha256": _sha256(config_path),
        "products": list(PRODUCTS),
        "candidate_set_order": list(EXPECTED_SET_ORDER),
        "panels": [panel.name for panel in panels],
        "discovery_seeds": [
            spec.seed for panel in panels for spec in panel.discovery
        ],
        "validation_seeds": [
            spec.seed for panel in panels for spec in panel.validation
        ],
        "process_universe": list(_process_universe()),
        "inner_folds": int(inner_folds),
        "outer_folds": int(outer_folds),
        "max_predictors": int(max_predictors),
        "minimum_predictor_coverage": float(minimum_predictor_coverage),
        "prediction_surface_coverage_floor": float(
            prediction_surface_coverage_floor
        ),
        "decision": str(decision.iloc[0]["decision"]),
        "supported_result_only_allows": config.get(
            "supported_result_only_allows"
        ),
    }
    return {
        "contract": contract,
        "products": pd.concat(product_frames, ignore_index=True),
        "discovery_metrics": pd.concat(
            discovery_metric_frames,
            ignore_index=True,
        ),
        "discovery_status": pd.concat(
            discovery_status_frames,
            ignore_index=True,
        ),
        "discovery_coverage": pd.concat(
            discovery_coverage_frames,
            ignore_index=True,
        ),
        "discovery_predictors": pd.concat(
            discovery_predictor_frames,
            ignore_index=True,
        ),
        "member_fits": pd.concat(member_fit_frames, ignore_index=True),
        "certificate_audit": audits,
        "boundary_audit": (
            pd.concat(boundary_frames, ignore_index=True)
            if boundary_frames
            else pd.DataFrame()
        ),
        "certificate_intervals": (
            pd.concat(interval_frames, ignore_index=True)
            if interval_frames
            else pd.DataFrame()
        ),
        "canonical_point_audit": (
            pd.concat(point_frames, ignore_index=True)
            if point_frames
            else pd.DataFrame()
        ),
        "validation_coverage": pd.concat(
            validation_coverage_frames,
            ignore_index=True,
        ),
        "product_summary": summary,
        "decision": decision,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--n-cells", type=int, default=1700)
    parser.add_argument("--n-occurrences", type=int, default=170)
    parser.add_argument("--n-target-group", type=int, default=680)
    parser.add_argument("--inner-folds", type=int, default=2)
    parser.add_argument("--outer-folds", type=int, default=2)
    parser.add_argument("--max-predictors", type=int, default=4)
    parser.add_argument("--minimum-predictor-coverage", type=float, default=0.95)
    parser.add_argument(
        "--prediction-surface-coverage-floor",
        type=float,
        default=0.95,
    )
    args = parser.parse_args(argv)

    result = run_certificate_experiment(
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
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name in (
        "products",
        "discovery_metrics",
        "discovery_status",
        "discovery_coverage",
        "discovery_predictors",
        "member_fits",
        "certificate_audit",
        "boundary_audit",
        "certificate_intervals",
        "canonical_point_audit",
        "validation_coverage",
        "product_summary",
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
