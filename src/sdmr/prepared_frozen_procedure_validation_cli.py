"""External taxon validation of an already-frozen Product-A v2 procedure.

No procedure selection occurs here.  A selector label is read from an immutable
source artifact where it was frozen using discovery taxa only.  The exact
procedure is refit independently on each target taxon's model pool and every fit
attempt is completed before any target sealed row is scored.  A separate
model-outcome-free eligibility artifact defines the target validation taxa and
preserves original candidate-panel indices for spatial seeds.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .predictor_process_registry import PredictorProcessRegistry
from .prepared_recovery_procedure_cli import (
    _procedure_profile,
    _read_selected_csv,
    _sealed_score,
    _sha256,
    _validate_cache,
)
from .prepared_taxon_transfer_cli import _audit_for_species, _build_perturbations
from .prepared_taxon_transfer_eligible_cli import _load_and_validate_eligibility
from .recovery_procedure_fit import FittedRecoveryProcedure, fit_recovery_procedure
from .sealed_evaluation_status import classify_sealed_evaluation, complete_row_count


def _load_frozen_procedure_source(
    source_dir: Path,
    source_cache_contract: dict[str, Any],
    *,
    selector: str,
    expected_profile: str,
    expected_inner_folds: int,
    expected_max_predictors: int,
) -> tuple[str, dict[str, Any]]:
    contract_path = source_dir / "product_a_v2_eligible_taxon_transfer_contract.json"
    selectors_path = source_dir / "frozen_discovery_selectors.csv"
    if not contract_path.exists() or not selectors_path.exists():
        raise SystemExit("frozen-procedure artifact lacks contract or selector table")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    selectors = pd.read_csv(selectors_path)

    source_occ_sha = str(source_cache_contract.get("featured_occurrence_csv_sha256", ""))
    frozen_occ_sha = str(
        contract.get("source_feature_cache_contract", {}).get(
            "featured_occurrence_csv_sha256", ""
        )
    )
    if not source_occ_sha or frozen_occ_sha != source_occ_sha:
        raise SystemExit("frozen procedure is not tied to the same strict occurrence cache")
    required = {
        "validation_taxa_used_for_discovery_selection": False,
        "validation_sealed_opened_after_all_validation_fit_attempts": True,
        "validation_results_can_change_frozen_selector": False,
        "no_post_validation_fallback_procedure": True,
        "hidden_truth_used": False,
    }
    mismatches = {
        key: {"expected": expected, "observed": contract.get(key)}
        for key, expected in required.items()
        if contract.get(key) != expected
    }
    if mismatches:
        raise SystemExit(f"frozen-procedure source violates information barrier: {mismatches}")
    if str(contract.get("procedure_profile")) != str(expected_profile):
        raise SystemExit("frozen procedure profile differs from external-validation profile")
    if int(contract.get("inner_folds", -1)) != int(expected_inner_folds):
        raise SystemExit("frozen procedure inner-fold count differs from external validation")
    if int(contract.get("max_predictors", -1)) != int(expected_max_predictors):
        raise SystemExit("frozen procedure max-predictors differs from external validation")

    row = selectors.loc[selectors["selector"].astype(str).eq(str(selector))]
    if len(row) != 1:
        raise SystemExit(f"selector {selector!r} is not uniquely present in frozen artifact")
    record = row.iloc[0]
    if str(record.get("status")) != "selected":
        raise SystemExit(f"frozen source selector {selector!r} did not select a procedure")
    label = str(record.get("procedure", ""))
    if not label or label.lower() == "nan":
        raise SystemExit("frozen source selected an empty procedure label")
    return label, contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate an already-frozen Product-A v2 procedure on external eligible taxa."
    )
    parser.add_argument("--prepared-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--candidate-taxa", required=True)
    parser.add_argument("--eligibility-dir", required=True)
    parser.add_argument("--frozen-procedure-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--selector", default="canonical_ecology")
    parser.add_argument("--canonical-spec", default="buffer_300km")
    parser.add_argument("--procedure-profile", choices=["core_l2"], default="core_l2")
    parser.add_argument("--inner-folds", type=int, default=2)
    parser.add_argument("--outer-folds", type=int, default=2)
    parser.add_argument("--max-predictors", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260814)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument("--source-artifact-id", default="")
    parser.add_argument("--eligibility-run-id", default="")
    parser.add_argument("--eligibility-artifact-id", default="")
    parser.add_argument("--eligibility-artifact-digest", default="")
    parser.add_argument("--frozen-procedure-run-id", default="")
    parser.add_argument("--frozen-procedure-artifact-id", default="")
    parser.add_argument("--frozen-procedure-artifact-digest", default="")
    parser.add_argument(
        "--purpose", default="empirical_product_a_v2_frozen_procedure_external_validation"
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
    frozen_dir = Path(args.frozen_procedure_dir)
    manifest = pd.read_csv(manifest_path)
    source_contract = _validate_cache(root, manifest)
    roles, eligibility_contract, panel_index = _load_and_validate_eligibility(
        eligibility_dir,
        source_contract,
        candidate_path,
        outer_folds=args.outer_folds,
        seed=args.seed,
    )
    frozen_label, frozen_contract = _load_frozen_procedure_source(
        frozen_dir,
        source_contract,
        selector=args.selector,
        expected_profile=args.procedure_profile,
        expected_inner_folds=args.inner_folds,
        expected_max_predictors=args.max_predictors,
    )
    procedures = _procedure_profile(
        args.procedure_profile,
        inner_folds=args.inner_folds,
        max_predictors=args.max_predictors,
    )
    procedure_by_label = {procedure.label: procedure for procedure in procedures}
    if frozen_label not in procedure_by_label:
        raise SystemExit(f"frozen procedure label is absent from declared profile: {frozen_label}")
    procedure = procedure_by_label[frozen_label]

    target_taxa = tuple(
        roles.loc[roles["role"].astype(str).eq("validation"), "scientific_name"].astype(str)
    )
    if len(target_taxa) < 2:
        raise SystemExit("external validation requires at least two eligible validation taxa")
    source_validation_taxa = set(str(x) for x in frozen_contract.get("validation_taxa", []))

    predictors = tuple(manifest["predictor"].astype(str))
    required_cols = ["species", "longitude", "latitude", "__sdmr_outer_role", *predictors]
    occurrences = _read_selected_csv(root / "pilot_occurrences.csv", set(target_taxa), required_cols)
    grid = pd.read_csv(root / "pilot_grid_frozen.csv")
    specs = tuple(grid["name"].astype(str))
    if args.canonical_spec not in specs:
        raise SystemExit(f"canonical spec {args.canonical_spec!r} absent from frozen M grid")
    backgrounds = {
        spec: _read_selected_csv(
            root / "specifications" / spec / "background.csv",
            set(target_taxa),
            required_cols,
        )
        for spec in specs
    }

    audit_frames: list[pd.DataFrame] = []
    perturbations_by_species: dict[str, dict[str, Any]] = {}
    audit_by_species: dict[str, tuple[str, ...]] = {}
    fit_rows: list[dict[str, Any]] = []
    fitted_by_key: dict[tuple[str, str], FittedRecoveryProcedure] = {}

    # Phase 1: fit the already-frozen procedure on every target model pool.
    # No target sealed score is opened until all target×M fit attempts finish.
    for species in target_taxa:
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
        audit_by_species[species] = audit.predictors
        ledger = audit.ledger.copy()
        ledger["species"] = species
        ledger["taxon_role"] = "external_validation"
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
        perturbations_by_species[species] = perturbations
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
                fit_rows.append(
                    {
                        "species": species,
                        "perturbation": spec,
                        "procedure": frozen_label,
                        "final_fit_status": "abstain_final_fit",
                        "final_fit_error": str(exc),
                        "source_validation_exposed": species in source_validation_taxa,
                    }
                )
                continue
            fitted_by_key[(species, spec)] = fitted
            fit_rows.append(
                {
                    "species": species,
                    "perturbation": spec,
                    "procedure": frozen_label,
                    "final_fit_status": "success",
                    "final_fit_error": None,
                    "selected_predictors": ",".join(fitted.selected_predictors),
                    "selected_ecological_predictors": ",".join(
                        fitted.selected_ecological_predictors
                    ),
                    "n_predictors": len(fitted.selected_predictors),
                    "source_validation_exposed": species in source_validation_taxa,
                }
            )

    # Phase 2: after all fits are frozen, open target sealed rows once.
    sealed_rows: list[dict[str, Any]] = []
    for (species, spec), fitted in fitted_by_key.items():
        perturbation = perturbations_by_species[species][spec]
        payload = _sealed_score(
            perturbation,
            fitted,
            audit_by_species[species],
        )
        n_complete_presence = complete_row_count(
            perturbation.sealed_presence, fitted.selected_predictors
        )
        n_complete_background = complete_row_count(
            perturbation.sealed_background, fitted.selected_predictors
        )
        status = classify_sealed_evaluation(
            payload,
            n_complete_sealed_presence=n_complete_presence,
            n_complete_sealed_background=n_complete_background,
        )
        sealed_rows.append(
            {
                "species": species,
                "taxon_role": "external_validation",
                "perturbation": spec,
                "procedure": frozen_label,
                "source_validation_exposed": species in source_validation_taxa,
                "n_complete_sealed_presence_for_model": n_complete_presence,
                "n_complete_sealed_background_for_model": n_complete_background,
                "sealed_evaluation_status": status,
                **payload,
            }
        )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd.concat(audit_frames, ignore_index=True).to_csv(
        out / "audit_space_ledger.csv", index=False
    )
    pd.DataFrame(fit_rows).to_csv(out / "validation_final_fit_status.csv", index=False)
    pd.DataFrame(sealed_rows).to_csv(out / "validation_outer_sealed.csv", index=False)
    pd.DataFrame(
        [
            {
                "species": species,
                "source_validation_exposed": species in source_validation_taxa,
                "external_validation_fresh_relative_to_source_artifact": (
                    species not in source_validation_taxa
                ),
                "original_panel_index": panel_index[species],
            }
            for species in target_taxa
        ]
    ).to_csv(out / "validation_taxon_provenance.csv", index=False)

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
        "frozen_procedure_run_id": args.frozen_procedure_run_id,
        "frozen_procedure_artifact_id": args.frozen_procedure_artifact_id,
        "frozen_procedure_artifact_digest": args.frozen_procedure_artifact_digest,
        "frozen_procedure_contract_sha256": _sha256(
            frozen_dir / "product_a_v2_eligible_taxon_transfer_contract.json"
        ),
        "selector": args.selector,
        "frozen_procedure": frozen_label,
        "frozen_procedure_selected_before_this_validation": True,
        "procedure_reselection_in_external_validation": False,
        "target_validation_taxa": list(target_taxa),
        "source_artifact_validation_taxa": sorted(source_validation_taxa),
        "fresh_relative_to_source_artifact": [
            species for species in target_taxa if species not in source_validation_taxa
        ],
        "previously_exposed_in_source_validation": [
            species for species in target_taxa if species in source_validation_taxa
        ],
        "original_panel_index_by_species": panel_index,
        "original_panel_indices_preserved_for_spatial_seeds": True,
        "eligibility_applied_before_candidate_model_fitting": True,
        "validation_sealed_opened_after_all_validation_fit_attempts": True,
        "validation_results_can_change_frozen_procedure": False,
        "no_post_validation_fallback_procedure": True,
        "sealed_evaluation_unavailability_is_explicit_abstention": True,
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
    }
    (out / "product_a_v2_frozen_procedure_external_validation_contract.json").write_text(
        json.dumps(run_contract, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
