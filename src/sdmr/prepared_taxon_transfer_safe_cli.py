"""Abstention-safe cross-taxon Product-A v2 transfer orchestration.

A discovery taxon × M cell can legitimately fail to produce evaluable spatial
outer folds.  That is evidence insufficiency, not a reason to change the seed,
relax the recovery profile, or silently drop the cell.  This runner records those
cells explicitly.  Canonical selectors require complete canonical-M discovery
evidence; the cross-M robust selector requires every predeclared discovery taxon
× M cell.  Validation taxa remain unavailable to all discovery selection.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .empirical_product_a_v2 import EmpiricalNichePerturbation
from .niche_recovery_perturbation import select_perturbation_robust_niche_recovery_protocol
from .niche_recovery_procedure import (
    RecoveryProcedureBenchmark,
    benchmark_recovery_procedures,
    select_recovery_procedure,
)
from .predictor_process_registry import PredictorProcessRegistry
from .prepared_recovery_procedure_cli import (
    _mean_auc_winner,
    _procedure_profile,
    _read_selected_csv,
    _sealed_score,
    _sha256,
    _validate_cache,
)
from .prepared_taxon_transfer_cli import (
    _audit_for_species,
    _build_perturbations,
    _certificate_row,
    _load_taxon_role_config,
    _validate_outcome_blind_panel,
)
from .recovery_procedure_fit import FittedRecoveryProcedure, fit_recovery_procedure
from .robustness_certificate import build_perturbation_robustness_certificate


def _freeze_with_explicit_missing_cells(
    metrics: pd.DataFrame,
    benchmark_status: pd.DataFrame,
    discovery_taxa: tuple[str, ...],
    specs: tuple[str, ...],
    *,
    canonical_spec: str,
) -> tuple[dict[str, str | None], dict[str, str | None], dict[str, Any]]:
    successful = set(
        zip(
            benchmark_status.loc[benchmark_status["status"].eq("success"), "species"].astype(str),
            benchmark_status.loc[benchmark_status["status"].eq("success"), "perturbation"].astype(str),
        )
    )
    expected = {(sp, spec) for sp in discovery_taxa for spec in specs}
    missing = sorted(expected - successful)
    missing_canonical = sorted(sp for sp in discovery_taxa if (sp, canonical_spec) not in successful)

    winners: dict[str, str | None] = {
        "canonical_auc": None,
        "canonical_ecology": None,
        "robust_ecology": None,
    }
    errors: dict[str, str | None] = {key: None for key in winners}

    if missing_canonical:
        message = "missing canonical-M discovery benchmark cells: " + ",".join(missing_canonical)
        errors["canonical_auc"] = message
        errors["canonical_ecology"] = message
    else:
        canonical = metrics.loc[metrics["perturbation"].astype(str).eq(canonical_spec)].copy()
        winners["canonical_auc"] = _mean_auc_winner(canonical)
        try:
            winners["canonical_ecology"] = select_recovery_procedure(
                RecoveryProcedureBenchmark(canonical, pd.DataFrame())
            ).candidate
        except ValueError as exc:
            errors["canonical_ecology"] = str(exc)

    robust_payload: dict[str, Any]
    if missing:
        errors["robust_ecology"] = (
            "missing discovery taxon x M benchmark cells: "
            + ";".join(f"{sp}::{spec}" for sp, spec in missing)
        )
        robust_payload = {
            "status": "abstain_missing_discovery_benchmark_cells",
            "selected_procedure": None,
            "selection_error": errors["robust_ecology"],
            "near_complete_candidates": "",
            "critical_perturbations": ";".join(f"{sp}::{spec}" for sp, spec in missing),
            "max_passed_perturbations": len(expected) - len(missing),
            "n_perturbations": len(expected),
        }
    else:
        robust_metrics = metrics.copy()
        robust_metrics["perturbation"] = (
            robust_metrics["species"].astype(str)
            + "::"
            + robust_metrics["perturbation"].astype(str)
        )
        selection = None
        selection_error = None
        try:
            selection = select_perturbation_robust_niche_recovery_protocol(
                robust_metrics,
                prediction_adequacy_perturbation_types=("sampling_or_background",),
            )
            winners["robust_ecology"] = selection.candidate
        except ValueError as exc:
            selection_error = str(exc)
            errors["robust_ecology"] = selection_error
        certificate = build_perturbation_robustness_certificate(
            robust_metrics,
            selection=selection,
            selection_error=selection_error,
        )
        robust_payload = {
            "status": certificate.status,
            "selected_procedure": certificate.selected_candidate,
            "selection_error": certificate.selection_error,
            "near_complete_candidates": ",".join(certificate.near_complete_candidates),
            "critical_perturbations": ",".join(certificate.critical_perturbations),
            "max_passed_perturbations": certificate.max_passed_perturbations,
            "n_perturbations": certificate.n_perturbations,
        }

    return winners, errors, robust_payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--taxa", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--canonical-spec", default="buffer_300km")
    parser.add_argument("--procedure-profile", choices=["smoke_linear", "core_l2"], default="smoke_linear")
    parser.add_argument("--inner-folds", type=int, default=2)
    parser.add_argument("--outer-folds", type=int, default=2)
    parser.add_argument("--max-predictors", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260814)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument("--source-artifact-id", default="")
    parser.add_argument("--purpose", default="empirical_product_a_v2_cross_taxon_transfer_stage1")
    parser.add_argument("--audit-minimum-predictor-coverage", type=float, default=0.95)
    parser.add_argument("--audit-minimum-joint-coverage", type=float, default=0.80)
    parser.add_argument("--audit-minimum-processes", type=int, default=4)
    args = parser.parse_args(argv)

    root = Path(args.prepared_dir)
    manifest_path = Path(args.manifest)
    roles_path = Path(args.taxa)
    manifest = pd.read_csv(manifest_path)
    contract = _validate_cache(root, manifest)
    roles = _load_taxon_role_config(roles_path)
    panel_contract = _validate_outcome_blind_panel(root, roles, contract)
    discovery_taxa = tuple(roles.loc[roles["role"].eq("discovery"), "scientific_name"].astype(str))
    validation_taxa = tuple(roles.loc[roles["role"].eq("validation"), "scientific_name"].astype(str))
    panel_taxa = tuple(roles["scientific_name"].astype(str))

    predictors = tuple(manifest["predictor"].astype(str))
    process_groups = PredictorProcessRegistry.from_candidate_manifest(manifest).process_aliases()
    required_cols = ["species", "longitude", "latitude", "__sdmr_outer_role", *predictors]
    occurrences = _read_selected_csv(root / "pilot_occurrences.csv", set(panel_taxa), required_cols)
    grid = pd.read_csv(root / "pilot_grid_frozen.csv")
    specs = tuple(grid["name"].astype(str))
    backgrounds = {
        spec: _read_selected_csv(
            root / "specifications" / spec / "background.csv", set(panel_taxa), required_cols
        )
        for spec in specs
    }
    procedures = _procedure_profile(
        args.procedure_profile, inner_folds=args.inner_folds, max_predictors=args.max_predictors
    )
    procedure_by_label = {procedure.label: procedure for procedure in procedures}

    metric_frames: list[pd.DataFrame] = []
    trace_frames: list[pd.DataFrame] = []
    benchmark_status_rows: list[dict[str, Any]] = []
    audit_frames: list[pd.DataFrame] = []

    for taxon_index, species in enumerate(discovery_taxa):
        species_occ = occurrences.loc[occurrences["species"].astype(str).eq(species)].reset_index(drop=True)
        audit = _audit_for_species(
            species,
            species_occ,
            backgrounds,
            specs,
            manifest,
            minimum_predictor_coverage=args.audit_minimum_predictor_coverage,
            minimum_joint_coverage=args.audit_minimum_joint_coverage,
            minimum_processes=args.audit_minimum_processes,
        )
        ledger = audit.ledger.copy()
        ledger["species"] = species
        ledger["taxon_role"] = "discovery"
        ledger["selected_audit_predictors"] = ",".join(audit.predictors)
        ledger["minimum_observed_joint_coverage"] = audit.minimum_observed_joint_coverage
        audit_frames.append(ledger)
        perturbations = _build_perturbations(
            species,
            species_occ,
            backgrounds,
            specs,
            outer_folds=args.outer_folds,
            seed=args.seed,
            taxon_index=taxon_index,
        )
        for spec in specs:
            perturbation = perturbations[spec]
            try:
                benchmark = benchmark_recovery_procedures(
                    perturbation.presence,
                    perturbation.background,
                    perturbation.presence_groups,
                    perturbation.background_groups,
                    predictors,
                    audit.predictors,
                    procedures,
                    outer_folds=args.outer_folds,
                )
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                benchmark_status_rows.append(
                    {
                        "species": species,
                        "perturbation": spec,
                        "status": "abstain_no_evaluable_outer_folds",
                        "error": str(exc),
                    }
                )
                continue
            benchmark_status_rows.append(
                {"species": species, "perturbation": spec, "status": "success", "error": None}
            )
            fold = benchmark.fold_metrics.copy()
            fold["species"] = species
            fold["taxon_role"] = "discovery"
            fold["perturbation"] = spec
            fold["perturbation_type"] = "sampling_or_background"
            fold["audit_predictors"] = ",".join(audit.predictors)
            metric_frames.append(fold)
            if not benchmark.selection_trace.empty:
                trace = benchmark.selection_trace.copy()
                trace["species"] = species
                trace["taxon_role"] = "discovery"
                trace["perturbation"] = spec
                trace_frames.append(trace)

    discovery_metrics = pd.concat(metric_frames, ignore_index=True) if metric_frames else pd.DataFrame()
    benchmark_status = pd.DataFrame(benchmark_status_rows)
    winners, selector_errors, robust_payload = _freeze_with_explicit_missing_cells(
        discovery_metrics,
        benchmark_status,
        discovery_taxa,
        specs,
        canonical_spec=args.canonical_spec,
    )
    selector_rows = []
    for selector, label in winners.items():
        if label is not None:
            status = "selected"
        elif selector == "robust_ecology":
            status = robust_payload["status"]
        elif selector == "canonical_ecology" and selector_errors[selector]:
            status = "abstain_canonical_discovery_evidence"
        else:
            status = "abstain_canonical_discovery_evidence"
        selector_rows.append(
            {
                "selector": selector,
                "procedure": label,
                "status": status,
                "selection_error": selector_errors[selector],
                "selection_scope": "discovery_taxa_model_pool_only",
            }
        )

    validation_fit_rows: list[dict[str, Any]] = []
    validation_perturbations: dict[str, dict[str, EmpiricalNichePerturbation]] = {}
    validation_audit: dict[str, tuple[str, ...]] = {}
    fitted_by_key: dict[tuple[str, str, str], FittedRecoveryProcedure] = {}
    canonical_by_species: dict[str, FittedRecoveryProcedure | None] = {}
    robust_by_species: dict[str, FittedRecoveryProcedure | None] = {}

    for taxon_offset, species in enumerate(validation_taxa, start=len(discovery_taxa)):
        species_occ = occurrences.loc[occurrences["species"].astype(str).eq(species)].reset_index(drop=True)
        audit = _audit_for_species(
            species,
            species_occ,
            backgrounds,
            specs,
            manifest,
            minimum_predictor_coverage=args.audit_minimum_predictor_coverage,
            minimum_joint_coverage=args.audit_minimum_joint_coverage,
            minimum_processes=args.audit_minimum_processes,
        )
        validation_audit[species] = audit.predictors
        ledger = audit.ledger.copy()
        ledger["species"] = species
        ledger["taxon_role"] = "validation"
        ledger["selected_audit_predictors"] = ",".join(audit.predictors)
        ledger["minimum_observed_joint_coverage"] = audit.minimum_observed_joint_coverage
        audit_frames.append(ledger)
        perturbations = _build_perturbations(
            species,
            species_occ,
            backgrounds,
            specs,
            outer_folds=args.outer_folds,
            seed=args.seed,
            taxon_index=taxon_offset,
        )
        validation_perturbations[species] = perturbations
        canonical_by_species[species] = None
        robust_by_species[species] = None
        for selector, label in winners.items():
            if label is None:
                for spec in specs:
                    validation_fit_rows.append(
                        {
                            "species": species,
                            "selector": selector,
                            "procedure": None,
                            "perturbation": spec,
                            "final_fit_status": "not_attempted_discovery_selector_abstained",
                            "final_fit_error": selector_errors[selector],
                        }
                    )
                continue
            procedure = procedure_by_label[label]
            for spec in specs:
                perturbation = perturbations[spec]
                try:
                    fitted = fit_recovery_procedure(
                        perturbation.presence,
                        perturbation.background,
                        perturbation.presence_groups,
                        perturbation.background_groups,
                        predictors,
                        audit.predictors,
                        procedure,
                    )
                except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                    validation_fit_rows.append(
                        {
                            "species": species,
                            "selector": selector,
                            "procedure": label,
                            "perturbation": spec,
                            "final_fit_status": "abstain_final_fit",
                            "final_fit_error": str(exc),
                        }
                    )
                    continue
                fitted_by_key[(species, selector, spec)] = fitted
                validation_fit_rows.append(
                    {
                        "species": species,
                        "selector": selector,
                        "procedure": label,
                        "perturbation": spec,
                        "final_fit_status": "success",
                        "final_fit_error": None,
                        "selected_predictors": ",".join(fitted.selected_predictors),
                        "selected_ecological_predictors": ",".join(fitted.selected_ecological_predictors),
                        "n_predictors": len(fitted.selected_predictors),
                    }
                )
                if spec == args.canonical_spec and selector == "canonical_ecology":
                    canonical_by_species[species] = fitted
                if spec == args.canonical_spec and selector == "robust_ecology":
                    robust_by_species[species] = fitted

    certificate_rows = [
        _certificate_row(
            species,
            canonical_by_species[species],
            robust_by_species[species],
            process_groups=process_groups,
            canonical_label=winners["canonical_ecology"],
            robust_label=winners["robust_ecology"],
        )
        for species in validation_taxa
    ]

    sealed_rows: list[dict[str, Any]] = []
    for (species, selector, spec), fitted in fitted_by_key.items():
        sealed_rows.append(
            {
                "species": species,
                "taxon_role": "validation",
                "selector": selector,
                "procedure": fitted.procedure.label,
                "perturbation": spec,
                **_sealed_score(
                    validation_perturbations[species][spec],
                    fitted,
                    validation_audit[species],
                ),
            }
        )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    discovery_metrics.to_csv(out / "discovery_procedure_fold_metrics.csv", index=False)
    benchmark_status.to_csv(out / "discovery_benchmark_status.csv", index=False)
    (pd.concat(trace_frames, ignore_index=True) if trace_frames else pd.DataFrame()).to_csv(
        out / "discovery_selection_trace.csv", index=False
    )
    pd.DataFrame(selector_rows).to_csv(out / "frozen_discovery_selectors.csv", index=False)
    pd.DataFrame([robust_payload]).to_csv(out / "discovery_robustness_certificate.csv", index=False)
    pd.concat(audit_frames, ignore_index=True).to_csv(out / "audit_space_ledger.csv", index=False)
    pd.DataFrame(validation_fit_rows).to_csv(out / "validation_final_fit_status.csv", index=False)
    pd.DataFrame(sealed_rows).to_csv(out / "validation_outer_sealed.csv", index=False)
    pd.DataFrame(certificate_rows).to_csv(out / "validation_ecological_inference_certificates.csv", index=False)

    run_contract = {
        "purpose": args.purpose,
        "scientific_promotion_run": False,
        "source_run_id": args.source_run_id,
        "source_artifact_id": args.source_artifact_id,
        "source_feature_cache_contract": contract,
        "panel_contract": panel_contract,
        "taxa_config": str(roles_path),
        "taxa_config_sha256": _sha256(roles_path),
        "discovery_taxa": list(discovery_taxa),
        "validation_taxa": list(validation_taxa),
        "validation_taxa_used_for_discovery_selection": False,
        "validation_sealed_opened_after_all_validation_fit_attempts": True,
        "validation_results_can_change_frozen_selector": False,
        "no_post_validation_fallback_procedure": True,
        "missing_discovery_benchmark_cell_is_abstention_not_dropped": True,
        "canonical_selectors_require_complete_canonical_discovery_cells": True,
        "robust_selector_requires_complete_discovery_taxon_by_M_cells": True,
        "candidate_object": "procedure_not_fixed_predictor_set",
        "candidate_predictor_universe_size": len(predictors),
        "audit_space_source": "model_pool_availability_and_predeclared_manifest_process_only",
        "sealed_rows_used_for_audit_axis_selection": False,
        "outer_sealed_before_M": True,
        "m_grid_as_sensitivity": True,
        "hidden_truth_used": False,
        "procedure_profile": args.procedure_profile,
        "inner_folds": args.inner_folds,
        "outer_folds": args.outer_folds,
        "max_predictors": args.max_predictors,
        "canonical_spec": args.canonical_spec,
        "seed": args.seed,
        "frozen_selectors": winners,
    }
    (out / "product_a_v2_taxon_transfer_contract.json").write_text(
        json.dumps(run_contract, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
