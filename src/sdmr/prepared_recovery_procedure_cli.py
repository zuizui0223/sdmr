"""Run Product-A v2 recovery procedures on strict frozen feature evidence.

This CLI never downloads GBIF or environmental rasters. It consumes a prepared
feature-cache bundle whose contract already proves outer-sealed-before-M,
M-as-sensitivity and complete environmental extraction. Procedure tuning sees
model-pool rows only; authoritative outer-sealed rows are opened only after
canonical/robust procedures have been selected and refit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .ecological_response_profile import ecological_response_profile
from .metrics import continuous_boyce_index, presence_rank_score
from .model import ModelSpec, score_ecological_suitability, score_relative_suitability
from .model_criteria import or10
from .niche_recovery_perturbation import select_perturbation_robust_niche_recovery_protocol
from .niche_recovery_procedure import (
    RecoveryProcedure,
    RecoveryProcedureBenchmark,
    benchmark_recovery_procedures,
    select_recovery_procedure,
)
from .observation_corrected_recovery import observation_corrected_heldout_niche_recovery_profile
from .predictor_process_registry import PredictorProcessRegistry
from .procedure_ecological_certificate import build_procedure_ecological_certificate
from .recovery_procedure_fit import fit_recovery_procedure
from .empirical_product_a_v2 import EmpiricalNichePerturbation


REQUIRED_CACHE_CONTRACT = {
    "outer_sealed_before_M": True,
    "M_grid_as_sensitivity": True,
    "contains_method_winner": False,
    "status": "prepared_feature_evidence_only_no_method_selection",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_cache(root: Path, manifest: pd.DataFrame) -> dict[str, object]:
    contract_path = root / "feature_cache_contract.json"
    if not contract_path.exists():
        raise SystemExit(f"missing strict feature cache contract: {contract_path}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    mismatches = {
        key: {"expected": expected, "observed": contract.get(key)}
        for key, expected in REQUIRED_CACHE_CONTRACT.items()
        if contract.get(key) != expected
    }
    if mismatches:
        raise SystemExit(f"prepared feature cache is not Product-A v2 admissible: {mismatches}")
    n_predictors = int(manifest["predictor"].astype(str).nunique())
    if int(contract.get("n_predictors", -1)) != n_predictors:
        raise SystemExit(
            "feature-cache predictor count differs from manifest: "
            f"contract={contract.get('n_predictors')} manifest={n_predictors}"
        )
    occurrence = root / "pilot_occurrences.csv"
    grid = root / "pilot_grid_frozen.csv"
    if not occurrence.exists() or not grid.exists():
        raise SystemExit("strict feature cache lacks pilot_occurrences.csv or pilot_grid_frozen.csv")
    expected_occ_sha = str(contract.get("featured_occurrence_csv_sha256", ""))
    if expected_occ_sha and _sha256(occurrence) != expected_occ_sha:
        raise SystemExit("strict feature-cache occurrence checksum mismatch")
    return contract


def _load_taxa(path: Path) -> tuple[str, ...]:
    frame = pd.read_csv(path)
    column = "scientific_name" if "scientific_name" in frame.columns else "species"
    if column not in frame.columns:
        raise SystemExit("taxa config must contain scientific_name or species")
    taxa = tuple(dict.fromkeys(frame[column].dropna().astype(str)))
    if not taxa:
        raise SystemExit("taxa config is empty")
    return taxa


def _read_selected_csv(
    path: Path,
    taxa: set[str],
    usecols: list[str],
    *,
    chunksize: int = 100_000,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=chunksize):
        keep = chunk["species"].astype(str).isin(taxa)
        if keep.any():
            frames.append(chunk.loc[keep].copy())
    if not frames:
        return pd.DataFrame(columns=usecols)
    return pd.concat(frames, ignore_index=True)


def _procedure_profile(name: str, *, inner_folds: int, max_predictors: int) -> tuple[RecoveryProcedure, ...]:
    if name == "smoke_linear":
        spec = ModelSpec(C=1.0, degree=1, penalty="l2")
        return (
            RecoveryProcedure("all", spec, inner_folds=inner_folds, max_predictors=max_predictors),
            RecoveryProcedure(
                "vif",
                spec,
                inner_folds=inner_folds,
                max_predictors=max_predictors,
                vif_threshold=5.0,
            ),
            RecoveryProcedure(
                "predictive_forward",
                spec,
                inner_folds=inner_folds,
                max_predictors=max_predictors,
                predictive_min_gain=0.0,
            ),
            RecoveryProcedure(
                "niche_forward",
                spec,
                inner_folds=inner_folds,
                max_predictors=max_predictors,
            ),
        )
    if name == "core_l2":
        procedures: list[RecoveryProcedure] = []
        for degree in (1, 2):
            for C in (0.1, 1.0, 10.0):
                spec = ModelSpec(C=C, degree=degree, penalty="l2")
                for strategy in ("all", "vif", "predictive_forward", "niche_forward"):
                    procedures.append(
                        RecoveryProcedure(
                            strategy,
                            spec,
                            inner_folds=inner_folds,
                            max_predictors=max_predictors,
                            predictive_min_gain=0.0,
                        )
                    )
        return tuple(procedures)
    raise ValueError(f"unknown procedure profile: {name!r}")


def _mean_auc_winner(metrics: pd.DataFrame) -> str:
    summary = (
        metrics.groupby("candidate", as_index=False)["presence_rank"]
        .mean()
        .sort_values(["presence_rank", "candidate"], ascending=[False, True], kind="mergesort")
    )
    if summary.empty:
        raise ValueError("no canonical procedure AUC evidence")
    return str(summary.iloc[0]["candidate"])


def _sealed_score(
    perturbation: EmpiricalNichePerturbation,
    fitted,
    audit_predictors: tuple[str, ...],
) -> dict[str, object]:
    assert perturbation.sealed_presence is not None
    assert perturbation.sealed_background is not None
    predictors = fitted.selected_predictors
    train_p = score_relative_suitability(fitted.model, perturbation.presence, predictors)
    sealed_p = score_relative_suitability(fitted.model, perturbation.sealed_presence, predictors)
    sealed_b = score_relative_suitability(fitted.model, perturbation.sealed_background, predictors)
    ecological_b = score_ecological_suitability(
        fitted.model,
        perturbation.sealed_background,
        predictors,
        observation_predictors=fitted.procedure.observation_predictors,
        observation_reference=perturbation.background,
    )
    weights = np.ones(len(perturbation.sealed_presence), dtype=float)
    profile = observation_corrected_heldout_niche_recovery_profile(
        perturbation.background,
        perturbation.sealed_background,
        perturbation.sealed_presence,
        ecological_b,
        weights,
        audit_predictors,
    )
    return {
        "presence_rank": presence_rank_score(sealed_p, sealed_b),
        "continuous_boyce": continuous_boyce_index(sealed_p, sealed_b),
        "or10": or10(train_p, sealed_p),
        "n_model_presence": len(perturbation.presence),
        "n_sealed_presence": len(perturbation.sealed_presence),
        "n_model_background": len(perturbation.background),
        "n_sealed_background": len(perturbation.sealed_background),
        **profile.as_dict(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Product-A v2 procedure recovery on a strict frozen feature cache."
    )
    parser.add_argument("--prepared-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--taxa", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--canonical-spec", default="buffer_300km")
    parser.add_argument("--procedure-profile", choices=["smoke_linear", "core_l2"], default="smoke_linear")
    parser.add_argument("--inner-folds", type=int, default=2)
    parser.add_argument("--outer-folds", type=int, default=3)
    parser.add_argument("--max-predictors", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260816)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument("--source-artifact-id", default="")
    parser.add_argument("--purpose", default="empirical_product_a_v2_plumbing_smoke")
    args = parser.parse_args(argv)
    if args.inner_folds < 2 or args.outer_folds < 2 or args.max_predictors < 1:
        parser.error("inner/outer folds must be >=2 and max-predictors >=1")

    root = Path(args.prepared_dir)
    manifest_path = Path(args.manifest)
    taxa_path = Path(args.taxa)
    manifest = pd.read_csv(manifest_path)
    contract = _validate_cache(root, manifest)
    taxa = _load_taxa(taxa_path)
    registry = PredictorProcessRegistry.from_candidate_manifest(manifest)
    ecological_predictors = tuple(manifest["predictor"].astype(str))
    audit_predictors = ecological_predictors
    process_groups = registry.process_aliases()
    required_cols = [
        "species", "longitude", "latitude", "__sdmr_outer_role",
        *ecological_predictors,
    ]

    occurrences = _read_selected_csv(
        root / "pilot_occurrences.csv", set(taxa), required_cols
    )
    observed_taxa = set(occurrences["species"].astype(str))
    missing_taxa = sorted(set(taxa) - observed_taxa)
    if missing_taxa:
        raise SystemExit(f"strict feature cache lacks configured taxa: {missing_taxa}")

    grid = pd.read_csv(root / "pilot_grid_frozen.csv")
    specs = tuple(grid["name"].astype(str))
    if args.canonical_spec not in specs:
        raise SystemExit(f"canonical spec {args.canonical_spec!r} absent from frozen M grid")
    backgrounds: dict[str, pd.DataFrame] = {}
    for spec in specs:
        path = root / "specifications" / spec / "background.csv"
        if not path.exists():
            raise SystemExit(f"missing prepared background: {path}")
        backgrounds[spec] = _read_selected_csv(path, set(taxa), required_cols)

    procedures = _procedure_profile(
        args.procedure_profile,
        inner_folds=args.inner_folds,
        max_predictors=args.max_predictors,
    )
    procedure_by_label = {p.label: p for p in procedures}
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    all_fold_metrics: list[pd.DataFrame] = []
    all_traces: list[pd.DataFrame] = []
    selector_rows: list[dict[str, object]] = []
    final_predictor_rows: list[dict[str, object]] = []
    sealed_rows: list[dict[str, object]] = []
    certificate_rows: list[dict[str, object]] = []
    response_summary_rows: list[pd.DataFrame] = []
    response_curve_rows: list[pd.DataFrame] = []

    for taxon_index, species in enumerate(taxa):
        species_occ = occurrences.loc[occurrences["species"].astype(str).eq(species)].reset_index(drop=True)
        perturbations: dict[str, EmpiricalNichePerturbation] = {}
        metric_frames: list[pd.DataFrame] = []
        for spec_index, spec in enumerate(specs):
            species_bg = backgrounds[spec].loc[
                backgrounds[spec]["species"].astype(str).eq(species)
            ].reset_index(drop=True)
            perturbation = EmpiricalNichePerturbation.from_preassigned_outer_roles(
                spec,
                "sampling_or_background",
                species_occ,
                species_bg,
                n_spatial_blocks=max(4, args.outer_folds + 1),
                random_state=args.seed + taxon_index * 100 + spec_index,
            )
            perturbations[spec] = perturbation
            benchmark = benchmark_recovery_procedures(
                perturbation.presence,
                perturbation.background,
                perturbation.presence_groups,
                perturbation.background_groups,
                ecological_predictors,
                audit_predictors,
                procedures,
                outer_folds=args.outer_folds,
            )
            fold = benchmark.fold_metrics.copy()
            fold["species"] = species
            fold["perturbation"] = spec
            fold["perturbation_type"] = "sampling_or_background"
            metric_frames.append(fold)
            all_fold_metrics.append(fold)
            if not benchmark.selection_trace.empty:
                trace = benchmark.selection_trace.copy()
                trace["species"] = species
                trace["perturbation"] = spec
                all_traces.append(trace)

        species_metrics = pd.concat(metric_frames, ignore_index=True)
        canonical_metrics = species_metrics.loc[
            species_metrics["perturbation"].eq(args.canonical_spec)
        ].copy()
        canonical_benchmark = RecoveryProcedureBenchmark(
            fold_metrics=canonical_metrics,
            selection_trace=pd.DataFrame(),
        )
        canonical_ecology = select_recovery_procedure(canonical_benchmark).candidate
        canonical_auc = _mean_auc_winner(canonical_metrics)
        robust = select_perturbation_robust_niche_recovery_protocol(
            species_metrics,
            prediction_adequacy_perturbation_types=("sampling_or_background",),
        ).candidate
        winners = {
            "canonical_auc": canonical_auc,
            "canonical_ecology": canonical_ecology,
            "robust_ecology": robust,
        }
        selector_rows.extend(
            {
                "species": species,
                "selector": selector,
                "procedure": label,
            }
            for selector, label in winners.items()
        )

        canonical_final = None
        robust_final = None
        for selector, label in winners.items():
            procedure = procedure_by_label[label]
            for spec in specs:
                perturbation = perturbations[spec]
                fitted = fit_recovery_procedure(
                    perturbation.presence,
                    perturbation.background,
                    perturbation.presence_groups,
                    perturbation.background_groups,
                    ecological_predictors,
                    audit_predictors,
                    procedure,
                )
                final_predictor_rows.append(
                    {
                        "species": species,
                        "selector": selector,
                        "procedure": label,
                        "perturbation": spec,
                        "selected_predictors": ",".join(fitted.selected_predictors),
                        "selected_ecological_predictors": ",".join(
                            fitted.selected_ecological_predictors
                        ),
                        "n_predictors": len(fitted.selected_predictors),
                    }
                )
                sealed_rows.append(
                    {
                        "species": species,
                        "selector": selector,
                        "procedure": label,
                        "perturbation": spec,
                        **_sealed_score(perturbation, fitted, audit_predictors),
                    }
                )
                if spec == args.canonical_spec and selector == "canonical_ecology":
                    canonical_final = fitted
                if spec == args.canonical_spec and selector == "robust_ecology":
                    robust_final = fitted

        if canonical_final is not None and robust_final is not None:
            certificate = build_procedure_ecological_certificate(
                canonical_final.selected_predictors,
                robust_final.selected_predictors,
                canonical_observation_predictors=canonical_final.procedure.observation_predictors,
                robust_observation_predictors=robust_final.procedure.observation_predictors,
                process_groups=process_groups,
                canonical_label=canonical_ecology,
                robust_label=robust,
            )
            certificate_rows.append({"species": species, **certificate.as_dict()})
            canonical_perturbation = perturbations[args.canonical_spec]
            for selector, fitted in (
                ("canonical_ecology", canonical_final),
                ("robust_ecology", robust_final),
            ):
                ecological_surface = score_ecological_suitability(
                    fitted.model,
                    canonical_perturbation.background,
                    fitted.selected_predictors,
                    observation_predictors=fitted.procedure.observation_predictors,
                    observation_reference=canonical_perturbation.background,
                )
                profile = ecological_response_profile(
                    canonical_perturbation.background,
                    ecological_surface,
                    fitted.selected_ecological_predictors,
                )
                summary = profile.summary.copy()
                summary["species"] = species
                summary["selector"] = selector
                summary["procedure"] = fitted.procedure.label
                response_summary_rows.append(summary)
                curves = profile.curves.copy()
                curves["species"] = species
                curves["selector"] = selector
                curves["procedure"] = fitted.procedure.label
                response_curve_rows.append(curves)

    fold_metrics = pd.concat(all_fold_metrics, ignore_index=True)
    traces = pd.concat(all_traces, ignore_index=True) if all_traces else pd.DataFrame()
    selectors = pd.DataFrame(selector_rows)
    final_predictors = pd.DataFrame(final_predictor_rows)
    sealed = pd.DataFrame(sealed_rows)
    certificates = pd.DataFrame(certificate_rows)
    response_summary = (
        pd.concat(response_summary_rows, ignore_index=True)
        if response_summary_rows else pd.DataFrame()
    )
    response_curves = (
        pd.concat(response_curve_rows, ignore_index=True)
        if response_curve_rows else pd.DataFrame()
    )

    fold_metrics.to_csv(out / "procedure_fold_metrics.csv", index=False)
    traces.to_csv(out / "procedure_selection_trace.csv", index=False)
    selectors.to_csv(out / "procedure_selector_choices.csv", index=False)
    final_predictors.to_csv(out / "final_predictor_sets.csv", index=False)
    sealed.to_csv(out / "outer_sealed_validation.csv", index=False)
    certificates.to_csv(out / "ecological_inference_certificates.csv", index=False)
    response_summary.to_csv(out / "ecological_response_summary.csv", index=False)
    response_curves.to_csv(out / "ecological_response_curves.csv", index=False)

    run_contract = {
        "purpose": args.purpose,
        "prepared_feature_mode": True,
        "source_run_id": args.source_run_id,
        "source_artifact_id": args.source_artifact_id,
        "source_feature_cache_contract": contract,
        "prepared_dir": str(root),
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "taxa_config": str(taxa_path),
        "taxa": list(taxa),
        "procedure_profile": args.procedure_profile,
        "procedure_labels": list(procedure_by_label),
        "inner_folds": args.inner_folds,
        "outer_folds": args.outer_folds,
        "max_predictors": args.max_predictors,
        "canonical_spec": args.canonical_spec,
        "m_grid_as_sensitivity": True,
        "outer_sealed_before_M": True,
        "outer_sealed_opened_after_procedure_selection": True,
        "candidate_object": "procedure_not_fixed_predictor_set",
        "prediction_ecology_weighted_super_score": False,
        "hidden_truth_used": False,
        "observation_process_predictors": [],
        "scientific_promotion_run": False if "smoke" in args.purpose else None,
        "seed": args.seed,
    }
    (out / "product_a_v2_empirical_contract.json").write_text(
        json.dumps(run_contract, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
