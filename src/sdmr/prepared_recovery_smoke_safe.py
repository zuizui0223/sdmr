"""Small abstention-safe runner for the empirical Product-A v2 plumbing smoke.

This is intentionally not the scientific promotion CLI. It proves that strict
frozen feature evidence can run through nested procedure CV, selector abstention,
final model-pool refitting and outer-sealed answer checking.

The 43-variable candidate universe is deliberately kept separate from the
niche-recovery audit space. Audit axes are process representatives selected from
model-pool availability only; outer sealed rows never influence audit-axis choice.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .empirical_audit_space import select_empirical_audit_space
from .empirical_product_a_v2 import EmpiricalNichePerturbation
from .niche_recovery_perturbation import select_perturbation_robust_niche_recovery_protocol
from .niche_recovery_procedure import RecoveryProcedureBenchmark, benchmark_recovery_procedures, select_recovery_procedure
from .prepared_recovery_procedure_cli import _load_taxa, _mean_auc_winner, _procedure_profile, _read_selected_csv, _sealed_score, _validate_cache
from .predictor_process_registry import PredictorProcessRegistry
from .procedure_ecological_certificate import build_procedure_ecological_certificate
from .recovery_procedure_fit import fit_recovery_procedure
from .robustness_certificate import build_perturbation_robustness_certificate


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prepared-dir", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--taxa", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--canonical-spec", default="buffer_300km")
    p.add_argument("--inner-folds", type=int, default=2)
    p.add_argument("--outer-folds", type=int, default=2)
    p.add_argument("--max-predictors", type=int, default=2)
    p.add_argument("--seed", type=int, default=20260816)
    p.add_argument("--source-run-id", default="")
    p.add_argument("--source-artifact-id", default="")
    args = p.parse_args(argv)

    root = Path(args.prepared_dir)
    manifest = pd.read_csv(args.manifest)
    source_contract = _validate_cache(root, manifest)
    taxa = _load_taxa(Path(args.taxa))
    registry = PredictorProcessRegistry.from_candidate_manifest(manifest)
    predictors = tuple(manifest["predictor"].astype(str))
    usecols = ["species", "longitude", "latitude", "__sdmr_outer_role", *predictors]
    occurrences = _read_selected_csv(root / "pilot_occurrences.csv", set(taxa), usecols)
    grid = pd.read_csv(root / "pilot_grid_frozen.csv")
    specs = tuple(grid["name"].astype(str))
    backgrounds = {
        spec: _read_selected_csv(root / "specifications" / spec / "background.csv", set(taxa), usecols)
        for spec in specs
    }
    procedures = _procedure_profile("smoke_linear", inner_folds=args.inner_folds, max_predictors=args.max_predictors)
    procedure_by_label = {x.label: x for x in procedures}

    metric_frames = []
    selector_rows = []
    robustness_rows = []
    audit_rows = []
    final_fit_rows = []
    sealed_rows = []
    certificate_rows = []

    for taxon_i, species in enumerate(taxa):
        occ = occurrences.loc[occurrences["species"].astype(str).eq(species)].reset_index(drop=True)
        model_occ = occ.loc[occ["__sdmr_outer_role"].astype(str).eq("model")].reset_index(drop=True)
        model_frames = [model_occ]
        for spec in specs:
            bg = backgrounds[spec].loc[backgrounds[spec]["species"].astype(str).eq(species)].reset_index(drop=True)
            model_frames.append(
                bg.loc[bg["__sdmr_outer_role"].astype(str).eq("model")].reset_index(drop=True)
            )
        audit = select_empirical_audit_space(
            manifest,
            model_frames,
            minimum_predictor_coverage=0.95,
            minimum_joint_coverage=0.80,
            minimum_processes=4,
        )
        audit_predictors = audit.predictors
        audit_ledger = audit.ledger.copy()
        audit_ledger["species"] = species
        audit_ledger["selected_audit_predictors"] = ",".join(audit_predictors)
        audit_ledger["minimum_observed_joint_coverage"] = audit.minimum_observed_joint_coverage
        audit_rows.append(audit_ledger)

        perturbations = {}
        species_metrics = []
        for spec_i, spec in enumerate(specs):
            bg = backgrounds[spec].loc[backgrounds[spec]["species"].astype(str).eq(species)].reset_index(drop=True)
            perturbation = EmpiricalNichePerturbation.from_preassigned_outer_roles(
                spec, "sampling_or_background", occ, bg,
                n_spatial_blocks=max(4, args.outer_folds + 1),
                random_state=args.seed + taxon_i * 100 + spec_i,
            )
            perturbations[spec] = perturbation
            bench = benchmark_recovery_procedures(
                perturbation.presence, perturbation.background,
                perturbation.presence_groups, perturbation.background_groups,
                predictors, audit_predictors, procedures, outer_folds=args.outer_folds,
            )
            frame = bench.fold_metrics.copy()
            frame["species"] = species
            frame["perturbation"] = spec
            frame["perturbation_type"] = "sampling_or_background"
            frame["audit_predictors"] = ",".join(audit_predictors)
            metric_frames.append(frame)
            species_metrics.append(frame)

        metrics = pd.concat(species_metrics, ignore_index=True)
        canonical_metrics = metrics.loc[metrics["perturbation"].eq(args.canonical_spec)].copy()
        canonical_auc = _mean_auc_winner(canonical_metrics)
        canonical_ecology = None
        canonical_ecology_error = None
        try:
            canonical_ecology = select_recovery_procedure(
                RecoveryProcedureBenchmark(canonical_metrics, pd.DataFrame())
            ).candidate
        except ValueError as exc:
            canonical_ecology_error = str(exc)

        robust_selection = None
        robust_error = None
        try:
            robust_selection = select_perturbation_robust_niche_recovery_protocol(
                metrics, prediction_adequacy_perturbation_types=("sampling_or_background",)
            )
            robust_label = robust_selection.candidate
        except ValueError as exc:
            robust_label = None
            robust_error = str(exc)
        robust_cert = build_perturbation_robustness_certificate(
            metrics, selection=robust_selection, selection_error=robust_error
        )
        robustness_rows.append({
            "species": species,
            "status": robust_cert.status,
            "selected_procedure": robust_cert.selected_candidate,
            "selection_error": robust_cert.selection_error,
            "near_complete_candidates": ",".join(robust_cert.near_complete_candidates),
            "critical_perturbations": ",".join(robust_cert.critical_perturbations),
            "max_passed_perturbations": robust_cert.max_passed_perturbations,
            "n_perturbations": robust_cert.n_perturbations,
        })

        winners = {
            "canonical_auc": canonical_auc,
            "canonical_ecology": canonical_ecology,
            "robust_ecology": robust_label,
        }
        for selector, label in winners.items():
            if selector == "canonical_ecology" and label is None:
                status = "abstain_incomplete_recovery_profile"
                error = canonical_ecology_error
            elif selector == "robust_ecology" and label is None:
                status = robust_cert.status
                error = robust_cert.selection_error
            else:
                status = "selected"
                error = None
            selector_rows.append({
                "species": species,
                "selector": selector,
                "procedure": label,
                "status": status,
                "selection_error": error,
            })

        canonical_final = None
        robust_final = None
        for selector, label in winners.items():
            if label is None:
                final_fit_rows.append({
                    "species": species,
                    "selector": selector,
                    "procedure": None,
                    "final_fit_status": "not_attempted_selector_abstained",
                    "final_fit_error": (
                        canonical_ecology_error
                        if selector == "canonical_ecology"
                        else robust_cert.selection_error
                    ),
                })
                continue
            try:
                fitted = fit_recovery_procedure(
                    perturbations[args.canonical_spec].presence,
                    perturbations[args.canonical_spec].background,
                    perturbations[args.canonical_spec].presence_groups,
                    perturbations[args.canonical_spec].background_groups,
                    predictors, audit_predictors, procedure_by_label[label],
                )
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                final_fit_rows.append({
                    "species": species,
                    "selector": selector,
                    "procedure": label,
                    "final_fit_status": "abstain_final_fit",
                    "final_fit_error": str(exc),
                })
                continue
            final_fit_rows.append({
                "species": species,
                "selector": selector,
                "procedure": label,
                "final_fit_status": "success",
                "final_fit_error": None,
                "selected_predictors": ",".join(fitted.selected_predictors),
                "selected_ecological_predictors": ",".join(fitted.selected_ecological_predictors),
            })
            sealed_rows.append({
                "species": species,
                "selector": selector,
                "procedure": label,
                "perturbation": args.canonical_spec,
                "audit_predictors": ",".join(audit_predictors),
                **_sealed_score(perturbations[args.canonical_spec], fitted, audit_predictors),
            })
            if selector == "canonical_ecology":
                canonical_final = fitted
            elif selector == "robust_ecology":
                robust_final = fitted

        cert = build_procedure_ecological_certificate(
            canonical_final.selected_predictors if canonical_final else None,
            robust_final.selected_predictors if robust_final else None,
            process_groups=registry.process_aliases(),
            canonical_label=canonical_ecology,
            robust_label=robust_label,
        )
        certificate_rows.append({"species": species, **cert.as_dict()})

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd.concat(metric_frames, ignore_index=True).to_csv(out / "procedure_fold_metrics.csv", index=False)
    pd.DataFrame(selector_rows).to_csv(out / "procedure_selector_choices.csv", index=False)
    pd.DataFrame(robustness_rows).to_csv(out / "robustness_certificates.csv", index=False)
    pd.concat(audit_rows, ignore_index=True).to_csv(out / "audit_space_ledger.csv", index=False)
    pd.DataFrame(final_fit_rows).to_csv(out / "final_fit_status.csv", index=False)
    pd.DataFrame(sealed_rows).to_csv(out / "outer_sealed_validation.csv", index=False)
    pd.DataFrame(certificate_rows).to_csv(out / "ecological_inference_certificates.csv", index=False)
    contract = {
        "purpose": "empirical_product_a_v2_plumbing_smoke",
        "scientific_promotion_run": False,
        "source_run_id": args.source_run_id,
        "source_artifact_id": args.source_artifact_id,
        "source_feature_cache_contract": source_contract,
        "taxa": list(taxa),
        "m_grid_as_sensitivity": True,
        "outer_sealed_before_M": True,
        "outer_sealed_opened_after_procedure_selection": True,
        "candidate_object": "procedure_not_fixed_predictor_set",
        "candidate_predictor_universe_size": len(predictors),
        "audit_space_source": "model_pool_availability_and_predeclared_manifest_process_only",
        "audit_minimum_predictor_coverage": 0.95,
        "audit_minimum_joint_coverage": 0.80,
        "sealed_rows_used_for_audit_axis_selection": False,
        "canonical_ecology_abstention_is_valid_result": True,
        "robust_abstention_is_valid_result": True,
        "final_fit_abstention_is_valid_result": True,
        "no_post_selection_fallback_procedure": True,
        "prediction_ecology_weighted_super_score": False,
        "hidden_truth_used": False,
    }
    (out / "product_a_v2_empirical_contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
