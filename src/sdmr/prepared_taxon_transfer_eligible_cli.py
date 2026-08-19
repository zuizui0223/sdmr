"""Eligibility-gated cross-taxon Product-A v2 transfer on strict prepared data.

The original outcome-blind candidate panel is preserved as provenance. A separate
pre-model spatial-support artifact can declare taxa structurally ineligible using
model-pool coordinates and row counts only. Procedure labels are then frozen on
the eligible discovery taxa, and eligible validation taxa remain unavailable to
selection. Original candidate-panel indices are retained when deriving spatial
partition seeds, so removing an ineligible taxon cannot silently change the
partitions of the remaining taxa.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .empirical_product_a_v2 import EmpiricalNichePerturbation
from .predictor_process_registry import PredictorProcessRegistry
from .prepared_recovery_procedure_cli import (
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
)
from .prepared_taxon_transfer_safe_cli import _freeze_with_explicit_missing_cells
from .recovery_procedure_fit import FittedRecoveryProcedure, fit_recovery_procedure


def _load_and_validate_eligibility(
    eligibility_dir: Path,
    source_contract: dict[str, Any],
    candidate_taxa_path: Path,
    *,
    outer_folds: int,
    seed: int,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, int]]:
    contract_path = eligibility_dir / "taxon_transfer_spatial_eligibility_contract.json"
    roles_path = eligibility_dir / "eligible_taxon_roles.csv"
    if not contract_path.exists() or not roles_path.exists():
        raise SystemExit("eligibility artifact lacks contract or eligible_taxon_roles.csv")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    roles = _load_taxon_role_config(roles_path)

    required_flags = {
        "scientific_promotion_run": False,
        "model_scores_used": False,
        "environmental_predictor_values_used": False,
        "hidden_truth_used": False,
        "sealed_rows_used_for_eligibility": False,
        "eligibility_uses_model_pool_coordinates_and_row_counts_only": True,
    }
    mismatches = {
        key: {"expected": expected, "observed": contract.get(key)}
        for key, expected in required_flags.items()
        if contract.get(key) != expected
    }
    if mismatches:
        raise SystemExit(f"eligibility artifact violates pre-model contract: {mismatches}")

    source_occ_sha = str(source_contract.get("featured_occurrence_csv_sha256", ""))
    eligibility_occ_sha = str(
        contract.get("source_feature_cache_contract", {}).get(
            "featured_occurrence_csv_sha256", ""
        )
    )
    if not source_occ_sha or eligibility_occ_sha != source_occ_sha:
        raise SystemExit("eligibility artifact is not tied to the same frozen occurrence cache")
    if str(contract.get("candidate_taxa_config_sha256", "")) != _sha256(candidate_taxa_path):
        raise SystemExit("eligibility artifact candidate-panel fingerprint differs from repository config")
    if int(contract.get("outer_folds", -1)) != int(outer_folds):
        raise SystemExit("transfer outer-fold count differs from frozen eligibility screen")
    if int(contract.get("spatial_partition_seed", -1)) != int(seed):
        raise SystemExit("transfer spatial seed differs from frozen eligibility screen")
    if int(contract.get("n_spatial_blocks", -1)) != max(4, int(outer_folds) + 1):
        raise SystemExit("transfer spatial-block count differs from frozen eligibility screen")

    eligible = tuple(str(x) for x in contract.get("eligible_taxa", []))
    if set(roles["scientific_name"].astype(str)) != set(eligible):
        raise SystemExit("eligible role file does not match eligibility contract")
    expected_roles = {
        str(k): str(v) for k, v in dict(contract.get("role_assignments", {})).items()
    }
    observed_roles = {
        str(row.scientific_name): str(row.role) for row in roles.itertuples(index=False)
    }
    if observed_roles != expected_roles:
        raise SystemExit(
            f"eligible role assignments drifted: expected={expected_roles} observed={observed_roles}"
        )

    panel_index = {
        str(k): int(v) for k, v in dict(contract.get("panel_index_by_species", {})).items()
    }
    if not set(eligible).issubset(panel_index):
        raise SystemExit("eligibility contract lacks original candidate-panel indices")
    if "original_panel_index" in roles.columns:
        observed_index = {
            str(row.scientific_name): int(row.original_panel_index)
            for row in roles.itertuples(index=False)
        }
        expected_index = {species: panel_index[species] for species in eligible}
        if observed_index != expected_index:
            raise SystemExit("eligible role file changed original candidate-panel indices")
    return roles, contract, panel_index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Product-A v2 transfer after a model-free spatial eligibility gate."
    )
    parser.add_argument("--prepared-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--candidate-taxa", required=True)
    parser.add_argument("--eligibility-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--canonical-spec", default="buffer_300km")
    parser.add_argument(
        "--procedure-profile", choices=["smoke_linear", "core_l2"], default="smoke_linear"
    )
    parser.add_argument("--inner-folds", type=int, default=2)
    parser.add_argument("--outer-folds", type=int, default=2)
    parser.add_argument("--max-predictors", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260814)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument("--source-artifact-id", default="")
    parser.add_argument("--eligibility-run-id", default="")
    parser.add_argument("--eligibility-artifact-id", default="")
    parser.add_argument("--eligibility-artifact-digest", default="")
    parser.add_argument(
        "--purpose", default="empirical_product_a_v2_eligibility_gated_transfer_smoke"
    )
    parser.add_argument("--audit-minimum-predictor-coverage", type=float, default=0.95)
    parser.add_argument("--audit-minimum-joint-coverage", type=float, default=0.80)
    parser.add_argument("--audit-minimum-processes", type=int, default=4)
    args = parser.parse_args(argv)
    if args.inner_folds < 2 or args.outer_folds < 2 or args.max_predictors < 1:
        parser.error("inner/outer folds must be >=2 and max-predictors >=1")

    root = Path(args.prepared_dir)
    manifest_path = Path(args.manifest)
    candidate_path = Path(args.candidate_taxa)
    eligibility_dir = Path(args.eligibility_dir)
    manifest = pd.read_csv(manifest_path)
    source_contract = _validate_cache(root, manifest)
    roles, eligibility_contract, panel_index = _load_and_validate_eligibility(
        eligibility_dir,
        source_contract,
        candidate_path,
        outer_folds=args.outer_folds,
        seed=args.seed,
    )
    discovery_taxa = tuple(
        roles.loc[roles["role"].astype(str).eq("discovery"), "scientific_name"].astype(str)
    )
    validation_taxa = tuple(
        roles.loc[roles["role"].astype(str).eq("validation"), "scientific_name"].astype(str)
    )
    panel_taxa = tuple(roles["scientific_name"].astype(str))

    predictors = tuple(manifest["predictor"].astype(str))
    process_groups = PredictorProcessRegistry.from_candidate_manifest(manifest).process_aliases()
    required_cols = ["species", "longitude", "latitude", "__sdmr_outer_role", *predictors]
    occurrences = _read_selected_csv(root / "pilot_occurrences.csv", set(panel_taxa), required_cols)
    grid = pd.read_csv(root / "pilot_grid_frozen.csv")
    specs = tuple(grid["name"].astype(str))
    if args.canonical_spec not in specs:
        raise SystemExit(f"canonical spec {args.canonical_spec!r} absent from frozen M grid")
    backgrounds = {
        spec: _read_selected_csv(
            root / "specifications" / spec / "background.csv", set(panel_taxa), required_cols
        )
        for spec in specs
    }
    procedures = _procedure_profile(
        args.procedure_profile,
        inner_folds=args.inner_folds,
        max_predictors=args.max_predictors,
    )
    procedure_by_label = {procedure.label: procedure for procedure in procedures}

    metric_frames: list[pd.DataFrame] = []
    trace_frames: list[pd.DataFrame] = []
    benchmark_status_rows: list[dict[str, Any]] = []
    audit_frames: list[pd.DataFrame] = []

    for species in discovery_taxa:
        species_occ = occurrences.loc[
            occurrences["species"].astype(str).eq(species)
        ].reset_index(drop=True)
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
            taxon_index=panel_index[species],
        )
        for spec in specs:
            perturbation = perturbations[spec]
            try:
                benchmark = __import__(
                    "sdmr.niche_recovery_procedure", fromlist=["benchmark_recovery_procedures"]
                ).benchmark_recovery_procedures(
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
        else:
            status = "abstain_canonical_discovery_evidence"
        selector_rows.append(
            {
                "selector": selector,
                "procedure": label,
                "status": status,
                "selection_error": selector_errors[selector],
                "selection_scope": "spatially_eligible_discovery_taxa_model_pool_only",
            }
        )

    validation_fit_rows: list[dict[str, Any]] = []
    validation_perturbations: dict[str, dict[str, EmpiricalNichePerturbation]] = {}
    validation_audit: dict[str, tuple[str, ...]] = {}
    fitted_by_key: dict[tuple[str, str, str], FittedRecoveryProcedure] = {}
    canonical_by_species: dict[str, FittedRecoveryProcedure | None] = {}
    robust_by_species: dict[str, FittedRecoveryProcedure | None] = {}

    # Fit every validation species/selector/M from model-pool evidence first.
    # No authoritative validation sealed row is scored until this entire phase ends.
    for species in validation_taxa:
        species_occ = occurrences.loc[
            occurrences["species"].astype(str).eq(species)
        ].reset_index(drop=True)
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
            taxon_index=panel_index[species],
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
                        "selected_ecological_predictors": ",".join(
                            fitted.selected_ecological_predictors
                        ),
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

    # Sealed opening phase: all model-pool fitting is already frozen above.
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
    pd.DataFrame(certificate_rows).to_csv(
        out / "validation_ecological_inference_certificates.csv", index=False
    )

    run_contract = {
        "purpose": args.purpose,
        "scientific_promotion_run": False,
        "source_run_id": args.source_run_id,
        "source_artifact_id": args.source_artifact_id,
        "source_feature_cache_contract": source_contract,
        "eligibility_run_id": args.eligibility_run_id,
        "eligibility_artifact_id": args.eligibility_artifact_id,
        "eligibility_artifact_digest": args.eligibility_artifact_digest,
        "eligibility_contract": eligibility_contract,
        "eligibility_contract_sha256": _sha256(
            eligibility_dir / "taxon_transfer_spatial_eligibility_contract.json"
        ),
        "eligible_roles_sha256": _sha256(eligibility_dir / "eligible_taxon_roles.csv"),
        "original_candidate_panel_taxa": eligibility_contract["candidate_panel_taxa"],
        "ineligible_taxa": eligibility_contract["ineligible_taxa"],
        "eligible_taxa": list(panel_taxa),
        "original_panel_index_by_species": panel_index,
        "discovery_taxa": list(discovery_taxa),
        "validation_taxa": list(validation_taxa),
        "eligibility_applied_before_candidate_model_fitting": True,
        "ineligible_taxa_removed_by_model_outcomes": False,
        "original_panel_indices_preserved_for_spatial_seeds": True,
        "validation_taxa_used_for_discovery_selection": False,
        "validation_sealed_opened_after_all_validation_fit_attempts": True,
        "validation_results_can_change_frozen_selector": False,
        "no_post_validation_fallback_procedure": True,
        "missing_discovery_benchmark_cell_is_abstention_not_dropped": True,
        "canonical_selectors_require_complete_canonical_discovery_cells": True,
        "canonical_candidate_requires_evidence_in_every_discovery_taxon": True,
        "robust_selector_requires_complete_discovery_taxon_by_M_cells": True,
        "candidate_object": "procedure_not_fixed_predictor_set",
        "candidate_predictor_universe_size": len(predictors),
        "audit_space_source": "model_pool_availability_and_predeclared_manifest_process_only",
        "sealed_rows_used_for_audit_axis_selection": False,
        "outer_sealed_before_M": True,
        "m_grid_as_sensitivity": True,
        "hidden_truth_used": False,
        "procedure_profile": args.procedure_profile,
        "procedure_labels": list(procedure_by_label),
        "inner_folds": args.inner_folds,
        "outer_folds": args.outer_folds,
        "max_predictors": args.max_predictors,
        "canonical_spec": args.canonical_spec,
        "seed": args.seed,
        "frozen_selectors": winners,
    }
    (out / "product_a_v2_eligible_taxon_transfer_contract.json").write_text(
        json.dumps(run_contract, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
