"""Cross-taxon empirical transfer for Product-A v2 on strict prepared evidence.

Discovery taxa choose *procedure labels* using model-pool evidence only.  Validation
species are never allowed to affect those labels.  The frozen procedures may
select taxon-specific predictor subsets when refit on a validation taxon's model
pool, but authoritative outer-sealed rows are opened only after every validation
fit attempt is complete.  This is the Product-A v2 analogue of the older
prediction-transfer taxon split, with ecological recovery and abstention retained
as first-class outcomes.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .ecological_inference_certificate import EcologicalInferenceCertificate
from .empirical_audit_space import EmpiricalAuditSpace, select_empirical_audit_space
from .empirical_product_a_v2 import EmpiricalNichePerturbation
from .niche_recovery_perturbation import (
    PerturbationRobustNicheRecoverySelection,
    select_perturbation_robust_niche_recovery_protocol,
)
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
from .procedure_ecological_certificate import build_procedure_ecological_certificate
from .recovery_procedure_fit import FittedRecoveryProcedure, fit_recovery_procedure
from .robustness_certificate import build_perturbation_robustness_certificate


def _load_taxon_role_config(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"scientific_name", "role"}
    missing = required - set(frame.columns)
    if missing:
        raise SystemExit(f"taxon transfer config missing columns: {sorted(missing)}")
    frame = frame.copy()
    frame["scientific_name"] = frame["scientific_name"].astype(str)
    frame["role"] = frame["role"].astype(str)
    if frame["scientific_name"].duplicated().any():
        dup = sorted(frame.loc[frame["scientific_name"].duplicated(), "scientific_name"].unique())
        raise SystemExit(f"taxon transfer config contains duplicate taxa: {dup}")
    bad_roles = sorted(set(frame["role"]) - {"discovery", "validation"})
    if bad_roles:
        raise SystemExit(f"unknown taxon transfer roles: {bad_roles}")
    if int(frame["role"].eq("discovery").sum()) < 2:
        raise SystemExit("taxon transfer requires at least two discovery taxa")
    if int(frame["role"].eq("validation").sum()) < 2:
        raise SystemExit("stage1 taxon transfer requires at least two validation taxa")
    return frame


def _validate_outcome_blind_panel(
    root: Path,
    roles: pd.DataFrame,
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Verify panel/roles are derivable from frozen pre-outcome metadata only."""

    role_counts = pd.read_csv(
        root / "pilot_occurrences.csv",
        usecols=["species", "__sdmr_outer_role"],
    )
    model_counts = (
        role_counts.loc[role_counts["__sdmr_outer_role"].astype(str).eq("model")]
        .groupby("species")
        .size()
        .sort_values(kind="mergesort")
    )
    panel = tuple(roles["scientific_name"].astype(str))
    expected_panel = tuple(model_counts.index.astype(str)[: len(panel)])
    if set(panel) != set(expected_panel):
        raise SystemExit(
            "stage1 panel must be exactly the smallest model-pool occurrence taxa; "
            f"expected={expected_panel} configured={tuple(panel)}"
        )

    observed_counts = {sp: int(model_counts.loc[sp]) for sp in panel}
    if "model_presence_count" in roles.columns:
        configured_counts = {
            str(row.scientific_name): int(row.model_presence_count)
            for row in roles.itertuples(index=False)
        }
        mismatched = {
            sp: {"configured": configured_counts[sp], "observed": observed_counts[sp]}
            for sp in panel
            if configured_counts.get(sp) != observed_counts[sp]
        }
        if mismatched:
            raise SystemExit(f"configured model-pool counts drifted: {mismatched}")

    seed = int(contract.get("seed", 0))
    validation_fraction = float(contract.get("taxon_validation_fraction_for_future_search", 0.25))
    if not 0 < validation_fraction < 1:
        raise SystemExit("strict cache lacks a valid frozen taxon validation fraction")
    shuffled = np.array(sorted(panel), dtype=object)
    np.random.default_rng(seed).shuffle(shuffled)
    n_validation = max(2, int(math.ceil(len(panel) * validation_fraction)))
    n_validation = min(n_validation, len(panel) - 2)
    expected_validation = set(str(x) for x in shuffled[:n_validation])
    observed_validation = set(
        roles.loc[roles["role"].eq("validation"), "scientific_name"].astype(str)
    )
    if observed_validation != expected_validation:
        raise SystemExit(
            "validation taxa are not the deterministic frozen-seed split; "
            f"expected={sorted(expected_validation)} configured={sorted(observed_validation)}"
        )

    return {
        "panel_selection": "smallest_model_pool_occurrence_counts_only",
        "frozen_role_seed": seed,
        "frozen_validation_fraction": validation_fraction,
        "validation_count_rule": "max_2_then_ceil_panel_times_frozen_fraction",
        "expected_panel": list(expected_panel),
        "observed_model_presence_counts": observed_counts,
        "expected_validation_taxa": sorted(expected_validation),
    }


def _audit_for_species(
    species: str,
    species_occ: pd.DataFrame,
    backgrounds: dict[str, pd.DataFrame],
    specs: tuple[str, ...],
    manifest: pd.DataFrame,
    *,
    minimum_predictor_coverage: float,
    minimum_joint_coverage: float,
    minimum_processes: int,
) -> EmpiricalAuditSpace:
    model_occ = species_occ.loc[
        species_occ["__sdmr_outer_role"].astype(str).eq("model")
    ].reset_index(drop=True)
    frames: list[pd.DataFrame] = [model_occ]
    for spec in specs:
        species_bg = backgrounds[spec].loc[
            backgrounds[spec]["species"].astype(str).eq(species)
        ].reset_index(drop=True)
        frames.append(
            species_bg.loc[
                species_bg["__sdmr_outer_role"].astype(str).eq("model")
            ].reset_index(drop=True)
        )
    return select_empirical_audit_space(
        manifest,
        frames,
        minimum_predictor_coverage=minimum_predictor_coverage,
        minimum_joint_coverage=minimum_joint_coverage,
        minimum_processes=minimum_processes,
    )


def _build_perturbations(
    species: str,
    species_occ: pd.DataFrame,
    backgrounds: dict[str, pd.DataFrame],
    specs: tuple[str, ...],
    *,
    outer_folds: int,
    seed: int,
    taxon_index: int,
) -> dict[str, EmpiricalNichePerturbation]:
    result: dict[str, EmpiricalNichePerturbation] = {}
    for spec_index, spec in enumerate(specs):
        species_bg = backgrounds[spec].loc[
            backgrounds[spec]["species"].astype(str).eq(species)
        ].reset_index(drop=True)
        result[spec] = EmpiricalNichePerturbation.from_preassigned_outer_roles(
            spec,
            "sampling_or_background",
            species_occ,
            species_bg,
            n_spatial_blocks=max(4, outer_folds + 1),
            random_state=seed + taxon_index * 100 + spec_index,
        )
    return result


def _freeze_discovery_selectors(
    metrics: pd.DataFrame,
    *,
    canonical_spec: str,
) -> tuple[dict[str, str | None], dict[str, str | None], PerturbationRobustNicheRecoverySelection | None, Any]:
    canonical = metrics.loc[metrics["perturbation"].astype(str).eq(canonical_spec)].copy()
    canonical_auc = _mean_auc_winner(canonical)

    canonical_ecology: str | None = None
    canonical_error: str | None = None
    try:
        canonical_ecology = select_recovery_procedure(
            RecoveryProcedureBenchmark(canonical, pd.DataFrame())
        ).candidate
    except ValueError as exc:
        canonical_error = str(exc)

    robust_metrics = metrics.copy()
    robust_metrics["perturbation"] = (
        robust_metrics["species"].astype(str)
        + "::"
        + robust_metrics["perturbation"].astype(str)
    )
    robust_selection: PerturbationRobustNicheRecoverySelection | None = None
    robust_error: str | None = None
    try:
        robust_selection = select_perturbation_robust_niche_recovery_protocol(
            robust_metrics,
            prediction_adequacy_perturbation_types=("sampling_or_background",),
        )
        robust = robust_selection.candidate
    except ValueError as exc:
        robust = None
        robust_error = str(exc)
    robust_certificate = build_perturbation_robustness_certificate(
        robust_metrics,
        selection=robust_selection,
        selection_error=robust_error,
    )
    winners = {
        "canonical_auc": canonical_auc,
        "canonical_ecology": canonical_ecology,
        "robust_ecology": robust,
    }
    errors = {
        "canonical_auc": None,
        "canonical_ecology": canonical_error,
        "robust_ecology": robust_certificate.selection_error,
    }
    return winners, errors, robust_selection, robust_certificate


def _certificate_row(
    species: str,
    canonical: FittedRecoveryProcedure | None,
    robust: FittedRecoveryProcedure | None,
    *,
    process_groups: dict[str, str],
    canonical_label: str | None,
    robust_label: str | None,
) -> dict[str, Any]:
    certificate: EcologicalInferenceCertificate = build_procedure_ecological_certificate(
        canonical.selected_predictors if canonical else None,
        robust.selected_predictors if robust else None,
        canonical_observation_predictors=(
            canonical.procedure.observation_predictors if canonical else ()
        ),
        robust_observation_predictors=(
            robust.procedure.observation_predictors if robust else ()
        ),
        process_groups=process_groups,
        canonical_label=canonical_label,
        robust_label=robust_label,
    )
    return {"species": species, **certificate.as_dict()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Freeze Product-A v2 procedures on discovery taxa and test them on unseen taxa."
    )
    parser.add_argument("--prepared-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--taxa", required=True)
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
    parser.add_argument("--purpose", default="empirical_product_a_v2_cross_taxon_transfer_stage1")
    parser.add_argument("--audit-minimum-predictor-coverage", type=float, default=0.95)
    parser.add_argument("--audit-minimum-joint-coverage", type=float, default=0.80)
    parser.add_argument("--audit-minimum-processes", type=int, default=4)
    args = parser.parse_args(argv)
    if args.inner_folds < 2 or args.outer_folds < 2 or args.max_predictors < 1:
        parser.error("inner/outer folds must be >=2 and max-predictors >=1")

    root = Path(args.prepared_dir)
    manifest_path = Path(args.manifest)
    roles_path = Path(args.taxa)
    manifest = pd.read_csv(manifest_path)
    contract = _validate_cache(root, manifest)
    roles = _load_taxon_role_config(roles_path)
    panel_contract = _validate_outcome_blind_panel(root, roles, contract)
    discovery_taxa = tuple(
        roles.loc[roles["role"].eq("discovery"), "scientific_name"].astype(str)
    )
    validation_taxa = tuple(
        roles.loc[roles["role"].eq("validation"), "scientific_name"].astype(str)
    )
    panel_taxa = tuple(roles["scientific_name"].astype(str))

    predictors = tuple(manifest["predictor"].astype(str))
    registry = PredictorProcessRegistry.from_candidate_manifest(manifest)
    process_groups = registry.process_aliases()
    required_cols = [
        "species", "longitude", "latitude", "__sdmr_outer_role", *predictors
    ]
    occurrences = _read_selected_csv(
        root / "pilot_occurrences.csv", set(panel_taxa), required_cols
    )
    grid = pd.read_csv(root / "pilot_grid_frozen.csv")
    specs = tuple(grid["name"].astype(str))
    if args.canonical_spec not in specs:
        raise SystemExit(f"canonical spec {args.canonical_spec!r} absent from frozen M grid")
    backgrounds = {
        spec: _read_selected_csv(
            root / "specifications" / spec / "background.csv",
            set(panel_taxa),
            required_cols,
        )
        for spec in specs
    }
    procedures = _procedure_profile(
        args.procedure_profile,
        inner_folds=args.inner_folds,
        max_predictors=args.max_predictors,
    )
    procedure_by_label = {procedure.label: procedure for procedure in procedures}

    discovery_metric_frames: list[pd.DataFrame] = []
    discovery_trace_frames: list[pd.DataFrame] = []
    audit_rows: list[pd.DataFrame] = []

    for taxon_index, species in enumerate(discovery_taxa):
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
        audit_rows.append(ledger)
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
            fold = benchmark.fold_metrics.copy()
            fold["species"] = species
            fold["taxon_role"] = "discovery"
            fold["perturbation"] = spec
            fold["perturbation_type"] = "sampling_or_background"
            fold["audit_predictors"] = ",".join(audit.predictors)
            discovery_metric_frames.append(fold)
            if not benchmark.selection_trace.empty:
                trace = benchmark.selection_trace.copy()
                trace["species"] = species
                trace["taxon_role"] = "discovery"
                trace["perturbation"] = spec
                discovery_trace_frames.append(trace)

    discovery_metrics = pd.concat(discovery_metric_frames, ignore_index=True)
    winners, selector_errors, robust_selection, robust_cert = _freeze_discovery_selectors(
        discovery_metrics,
        canonical_spec=args.canonical_spec,
    )
    selector_rows: list[dict[str, Any]] = []
    for selector, label in winners.items():
        if label is not None:
            status = "selected"
        elif selector == "canonical_ecology":
            status = "abstain_incomplete_recovery_profile"
        else:
            status = robust_cert.status
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
    validation_audit_rows: list[pd.DataFrame] = []
    validation_perturbations: dict[str, dict[str, EmpiricalNichePerturbation]] = {}
    fitted_by_key: dict[tuple[str, str, str], FittedRecoveryProcedure] = {}
    canonical_by_species: dict[str, FittedRecoveryProcedure | None] = {}
    robust_by_species: dict[str, FittedRecoveryProcedure | None] = {}

    # Phase 1: build every validation audit space and fit every frozen selector
    # using model-pool evidence only. No sealed scoring occurs in this phase.
    for taxon_offset, species in enumerate(validation_taxa, start=len(discovery_taxa)):
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
        ledger["taxon_role"] = "validation"
        ledger["selected_audit_predictors"] = ",".join(audit.predictors)
        ledger["minimum_observed_joint_coverage"] = audit.minimum_observed_joint_coverage
        validation_audit_rows.append(ledger)
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
                            "audit_predictors": ",".join(audit.predictors),
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
                            "audit_predictors": ",".join(audit.predictors),
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
                        "audit_predictors": ",".join(audit.predictors),
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

    # Phase 2: only after every validation fit has been attempted do we open the
    # authoritative sealed rows. Results cannot trigger fallback/reselection.
    sealed_rows: list[dict[str, Any]] = []
    audit_by_species: dict[str, tuple[str, ...]] = {}
    for frame in validation_audit_rows:
        species = str(frame["species"].iloc[0])
        selected = frame.loc[frame["selected"].astype(bool), "representative_predictor"].dropna().astype(str)
        audit_by_species[species] = tuple(selected)
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
                    audit_by_species[species],
                ),
            }
        )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    discovery_metrics.to_csv(out / "discovery_procedure_fold_metrics.csv", index=False)
    (
        pd.concat(discovery_trace_frames, ignore_index=True)
        if discovery_trace_frames else pd.DataFrame()
    ).to_csv(out / "discovery_selection_trace.csv", index=False)
    pd.DataFrame(selector_rows).to_csv(out / "frozen_discovery_selectors.csv", index=False)
    pd.DataFrame(
        [
            {
                "status": robust_cert.status,
                "selected_procedure": robust_cert.selected_candidate,
                "selection_error": robust_cert.selection_error,
                "near_complete_candidates": ",".join(robust_cert.near_complete_candidates),
                "critical_perturbations": ",".join(robust_cert.critical_perturbations),
                "max_passed_perturbations": robust_cert.max_passed_perturbations,
                "n_perturbations": robust_cert.n_perturbations,
            }
        ]
    ).to_csv(out / "discovery_robustness_certificate.csv", index=False)
    pd.concat([*audit_rows, *validation_audit_rows], ignore_index=True).to_csv(
        out / "audit_space_ledger.csv", index=False
    )
    pd.DataFrame(validation_fit_rows).to_csv(out / "validation_final_fit_status.csv", index=False)
    pd.DataFrame(sealed_rows).to_csv(out / "validation_outer_sealed.csv", index=False)
    pd.DataFrame(certificate_rows).to_csv(
        out / "validation_ecological_inference_certificates.csv", index=False
    )

    run_contract = {
        "purpose": args.purpose,
        "scientific_promotion_run": False,
        "prepared_feature_mode": True,
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
        "candidate_object": "procedure_not_fixed_predictor_set",
        "candidate_predictor_universe_size": len(predictors),
        "audit_space_source": "model_pool_availability_and_predeclared_manifest_process_only",
        "sealed_rows_used_for_audit_axis_selection": False,
        "m_grid_as_sensitivity": True,
        "outer_sealed_before_M": True,
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
    (out / "product_a_v2_taxon_transfer_contract.json").write_text(
        json.dumps(run_contract, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
