"""Sealed-blind Product-A v2.1 discovery experiment.

This experiment asks whether two pre-outcome governance gates repair the
*evaluable evidence structure* of the empirical procedure benchmark without
looking at any sealed occurrence/background outcome:

1. raw predictors must pass the already-declared 0.95 model-pool coverage rule
   in model-pool presences and model-pool background across every M;
2. candidate procedures must have complete finite evidence in every declared
   outer fold, discovery taxon and required M before they can enter selection.

Only discovery taxa fixed by the immutable model-free eligibility artifact are
loaded. Validation taxa and all sealed feature rows are unavailable to this
module's returned data structures.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .candidate_outer_fold_evidence import require_complete_outer_fold_evidence
from .empirical_audit_space import select_empirical_audit_space
from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .niche_recovery_perturbation import select_perturbation_robust_niche_recovery_protocol
from .niche_recovery_procedure import (
    RecoveryProcedureBenchmark,
    benchmark_recovery_procedures,
    select_recovery_procedure,
)
from .niche_recovery_selection import RECOVERY_DIRECTIONS
from .pilot import MODEL_ROLE, OUTER_ROLE_COL
from .prepared_recovery_procedure_cli import (
    _mean_auc_winner,
    _procedure_profile,
    _sha256,
    _validate_cache,
)
from .prepared_taxon_transfer_eligible_cli import _load_and_validate_eligibility
from .validation import make_spatial_partition


def _read_model_pool_csv(
    path: Path,
    taxa: set[str],
    usecols: list[str],
    *,
    chunksize: int = 100_000,
) -> pd.DataFrame:
    """Return only authoritative model-pool rows from a prepared CSV."""

    required = list(dict.fromkeys([*usecols, OUTER_ROLE_COL]))
    frames: list[pd.DataFrame] = []
    for chunk in pd.read_csv(path, usecols=required, chunksize=chunksize):
        keep = (
            chunk["species"].astype(str).isin(taxa)
            & chunk[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
        )
        if keep.any():
            frame = chunk.loc[keep, required].copy()
            if not frame[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE).all():
                raise AssertionError("non-model row crossed the v2.1 development barrier")
            frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=required)
    result = pd.concat(frames, ignore_index=True)
    if not result[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE).all():
        raise AssertionError("non-model row crossed the v2.1 development barrier")
    return result


def _development_selectors(
    metrics: pd.DataFrame,
    *,
    discovery_taxa: tuple[str, ...],
    specs: tuple[str, ...],
    canonical_spec: str,
    expected_outer_folds: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    recovery_columns = tuple(RECOVERY_DIRECTIONS)
    canonical = metrics.loc[
        metrics["perturbation"].astype(str).eq(canonical_spec)
    ].copy()

    canonical_prediction_gate = require_complete_outer_fold_evidence(
        canonical,
        discovery_taxa=discovery_taxa,
        perturbations=(canonical_spec,),
        required_columns=("presence_rank",),
        expected_outer_folds=expected_outer_folds,
    )
    canonical_ecology_gate = require_complete_outer_fold_evidence(
        canonical,
        discovery_taxa=discovery_taxa,
        perturbations=(canonical_spec,),
        required_columns=("presence_rank", *recovery_columns),
        expected_outer_folds=expected_outer_folds,
    )
    all_prediction_gate = require_complete_outer_fold_evidence(
        metrics,
        discovery_taxa=discovery_taxa,
        perturbations=specs,
        required_columns=("presence_rank",),
        expected_outer_folds=expected_outer_folds,
    )
    all_ecology_gate = require_complete_outer_fold_evidence(
        metrics,
        discovery_taxa=discovery_taxa,
        perturbations=specs,
        required_columns=("presence_rank", *recovery_columns),
        expected_outer_folds=expected_outer_folds,
    )

    rows: list[dict[str, object]] = []
    canonical_auc = None
    if canonical_prediction_gate.eligible_candidates:
        eligible = set(canonical_prediction_gate.eligible_candidates)
        canonical_auc = _mean_auc_winner(
            canonical.loc[canonical["candidate"].astype(str).isin(eligible)]
        )
    rows.append(
        {
            "selector": "canonical_auc",
            "candidate": canonical_auc,
            "status": "selected" if canonical_auc else "abstain_complete_outer_evidence",
            "n_complete_evidence_candidates": len(
                canonical_prediction_gate.eligible_candidates
            ),
        }
    )

    canonical_ecology = None
    if canonical_ecology_gate.eligible_candidates:
        eligible = set(canonical_ecology_gate.eligible_candidates)
        try:
            canonical_ecology = select_recovery_procedure(
                RecoveryProcedureBenchmark(
                    canonical.loc[
                        canonical["candidate"].astype(str).isin(eligible)
                    ].copy(),
                    pd.DataFrame(),
                )
            ).candidate
        except ValueError:
            canonical_ecology = None
    rows.append(
        {
            "selector": "canonical_ecology",
            "candidate": canonical_ecology,
            "status": (
                "selected"
                if canonical_ecology
                else "abstain_complete_ecological_outer_evidence"
            ),
            "n_complete_evidence_candidates": len(
                canonical_ecology_gate.eligible_candidates
            ),
        }
    )

    robust = None
    robust_error = None
    if all_ecology_gate.eligible_candidates:
        eligible = set(all_ecology_gate.eligible_candidates)
        robust_metrics = metrics.loc[
            metrics["candidate"].astype(str).isin(eligible)
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
    rows.append(
        {
            "selector": "robust_ecology",
            "candidate": robust,
            "status": "selected" if robust else "abstain_robust_ecological_selection",
            "n_complete_prediction_evidence_candidates": len(
                all_prediction_gate.eligible_candidates
            ),
            "n_complete_evidence_candidates": len(
                all_ecology_gate.eligible_candidates
            ),
            "selection_error": robust_error,
        }
    )

    gates = {
        "canonical_prediction": canonical_prediction_gate,
        "canonical_ecology": canonical_ecology_gate,
        "all_prediction": all_prediction_gate,
        "all_ecology": all_ecology_gate,
    }
    return pd.DataFrame(rows), gates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run sealed-blind v2.1 predictor-coverage + complete-fold ablation."
    )
    parser.add_argument("--prepared-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--candidate-taxa", required=True)
    parser.add_argument("--eligibility-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--canonical-spec", default="buffer_300km")
    parser.add_argument("--procedure-profile", choices=["core_l2"], default="core_l2")
    parser.add_argument("--inner-folds", type=int, default=2)
    parser.add_argument("--outer-folds", type=int, default=2)
    parser.add_argument("--max-predictors", type=int, default=4)
    parser.add_argument("--minimum-predictor-coverage", type=float, default=0.95)
    parser.add_argument("--audit-minimum-joint-coverage", type=float, default=0.80)
    parser.add_argument("--audit-minimum-processes", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260814)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument("--source-artifact-id", default="")
    parser.add_argument("--eligibility-run-id", default="")
    parser.add_argument("--eligibility-artifact-id", default="")
    parser.add_argument("--eligibility-artifact-digest", default="")
    args = parser.parse_args(argv)

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
    if discovery_taxa != ("Nothofagus pumilio", "Eucalyptus pauciflora"):
        raise SystemExit(
            f"unexpected frozen discovery taxa for v2.1 development: {discovery_taxa}"
        )

    all_predictors = tuple(manifest["predictor"].astype(str))
    usecols = [
        "species",
        "longitude",
        "latitude",
        OUTER_ROLE_COL,
        *all_predictors,
    ]
    occurrences = _read_model_pool_csv(
        root / "pilot_occurrences.csv", set(discovery_taxa), usecols
    )
    grid = pd.read_csv(root / "pilot_grid_frozen.csv")
    specs = tuple(grid["name"].astype(str))
    if args.canonical_spec not in specs:
        raise SystemExit(f"canonical spec {args.canonical_spec!r} absent from M grid")
    backgrounds = {
        spec: _read_model_pool_csv(
            root / "specifications" / spec / "background.csv",
            set(discovery_taxa),
            usecols,
        )
        for spec in specs
    }
    procedures = _procedure_profile(
        args.procedure_profile,
        inner_folds=args.inner_folds,
        max_predictors=args.max_predictors,
    )

    metric_frames: list[pd.DataFrame] = []
    trace_frames: list[pd.DataFrame] = []
    status_rows: list[dict[str, object]] = []
    coverage_frames: list[pd.DataFrame] = []
    audit_frames: list[pd.DataFrame] = []
    taxon_predictor_rows: list[dict[str, object]] = []

    for species in discovery_taxa:
        p_model = occurrences.loc[
            occurrences["species"].astype(str).eq(species)
        ].reset_index(drop=True)
        bg_by_spec = {
            spec: backgrounds[spec].loc[
                backgrounds[spec]["species"].astype(str).eq(species)
            ].reset_index(drop=True)
            for spec in specs
        }
        admissibility = select_model_pool_admissible_predictors(
            {spec: (p_model, bg_by_spec[spec]) for spec in specs},
            all_predictors,
            minimum_coverage=args.minimum_predictor_coverage,
        )
        if not admissibility.predictors:
            raise SystemExit(f"no model-pool admissible predictors for {species}")
        coverage = admissibility.ledger.copy()
        coverage["species"] = species
        coverage_frames.append(coverage)
        taxon_predictor_rows.append(
            {
                "species": species,
                "n_candidate_predictors_before_gate": len(all_predictors),
                "n_admissible_predictors": len(admissibility.predictors),
                "admissible_predictors": ",".join(admissibility.predictors),
            }
        )

        audit = select_empirical_audit_space(
            manifest,
            [p_model, *[bg_by_spec[spec] for spec in specs]],
            minimum_predictor_coverage=args.minimum_predictor_coverage,
            minimum_joint_coverage=args.audit_minimum_joint_coverage,
            minimum_processes=args.audit_minimum_processes,
        )
        audit_ledger = audit.ledger.copy()
        audit_ledger["species"] = species
        audit_ledger["selected_audit_predictors"] = ",".join(audit.predictors)
        audit_ledger["minimum_observed_joint_coverage"] = (
            audit.minimum_observed_joint_coverage
        )
        audit_frames.append(audit_ledger)

        for spec_index, spec in enumerate(specs):
            b_model = bg_by_spec[spec]
            random_state = int(args.seed + panel_index[species] * 100 + spec_index)
            partition = make_spatial_partition(
                pd.to_numeric(p_model["longitude"], errors="raise").to_numpy(float),
                pd.to_numeric(p_model["latitude"], errors="raise").to_numpy(float),
                pd.to_numeric(b_model["longitude"], errors="raise").to_numpy(float),
                pd.to_numeric(b_model["latitude"], errors="raise").to_numpy(float),
                n_blocks=max(4, args.outer_folds + 1),
                holdout_fraction=0.20,
                random_state=random_state,
            )
            try:
                benchmark = benchmark_recovery_procedures(
                    p_model,
                    b_model,
                    partition.presence_blocks,
                    partition.background_blocks,
                    admissibility.predictors,
                    audit.predictors,
                    procedures,
                    outer_folds=args.outer_folds,
                )
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                status_rows.append(
                    {
                        "species": species,
                        "perturbation": spec,
                        "status": "abstain_no_evaluable_outer_folds",
                        "error": str(exc),
                        "random_state": random_state,
                    }
                )
                continue
            status_rows.append(
                {
                    "species": species,
                    "perturbation": spec,
                    "status": "success",
                    "error": None,
                    "random_state": random_state,
                }
            )
            fold = benchmark.fold_metrics.copy()
            fold["species"] = species
            fold["perturbation"] = spec
            fold["perturbation_type"] = "sampling_or_background"
            fold["n_admissible_raw_predictors"] = len(admissibility.predictors)
            fold["audit_predictors"] = ",".join(audit.predictors)
            metric_frames.append(fold)
            if not benchmark.selection_trace.empty:
                trace = benchmark.selection_trace.copy()
                trace["species"] = species
                trace["perturbation"] = spec
                trace_frames.append(trace)

    metrics = pd.concat(metric_frames, ignore_index=True) if metric_frames else pd.DataFrame()
    if metrics.empty:
        selectors = pd.DataFrame(
            [
                {"selector": name, "candidate": None, "status": "abstain_no_metrics"}
                for name in ("canonical_auc", "canonical_ecology", "robust_ecology")
            ]
        )
        gates = {}
    else:
        selectors, gates = _development_selectors(
            metrics,
            discovery_taxa=discovery_taxa,
            specs=specs,
            canonical_spec=args.canonical_spec,
            expected_outer_folds=args.outer_folds,
        )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd.concat(coverage_frames, ignore_index=True).to_csv(
        out / "model_pool_predictor_coverage.csv", index=False
    )
    pd.DataFrame(taxon_predictor_rows).to_csv(
        out / "taxon_admissible_predictors.csv", index=False
    )
    pd.concat(audit_frames, ignore_index=True).to_csv(
        out / "audit_space_ledger.csv", index=False
    )
    pd.DataFrame(status_rows).to_csv(out / "benchmark_status.csv", index=False)
    metrics.to_csv(out / "procedure_fold_metrics.csv", index=False)
    (pd.concat(trace_frames, ignore_index=True) if trace_frames else pd.DataFrame()).to_csv(
        out / "procedure_selection_trace.csv", index=False
    )
    selectors.to_csv(out / "development_selectors.csv", index=False)
    for name, result in gates.items():
        result.cell_ledger.to_csv(out / f"outer_evidence_cells__{name}.csv", index=False)
        result.candidate_summary.to_csv(
            out / f"outer_evidence_candidates__{name}.csv", index=False
        )

    contract = {
        "purpose": "product_a_v2_1_preoutcome_discovery_gate_ablation",
        "scientific_promotion_run": False,
        "old_external_sealed_outcomes_read": False,
        "sealed_rows_returned_to_experiment": False,
        "development_evidence": "discovery_taxa_model_pool_only",
        "source_run_id": args.source_run_id,
        "source_artifact_id": args.source_artifact_id,
        "source_feature_cache_contract": source_contract,
        "eligibility_run_id": args.eligibility_run_id,
        "eligibility_artifact_id": args.eligibility_artifact_id,
        "eligibility_artifact_digest": args.eligibility_artifact_digest,
        "eligibility_contract": eligibility_contract,
        "candidate_taxa_config_sha256": _sha256(candidate_path),
        "discovery_taxa": list(discovery_taxa),
        "validation_taxa_loaded": [],
        "original_panel_index_by_species": panel_index,
        "candidate_predictor_gate": {
            "source": "model_pool_presence_and_background_only",
            "minimum_coverage": args.minimum_predictor_coverage,
            "required_across_all_M": True,
        },
        "candidate_outer_fold_gate": {
            "expected_outer_folds": args.outer_folds,
            "missing_fold_is_explicit_evidence_insufficiency": True,
            "finite_prediction_required_per_fold": True,
            "finite_ecological_axes_required_per_fold_for_ecological_selection": True,
        },
        "procedure_profile": args.procedure_profile,
        "n_declared_procedures": len(procedures),
        "inner_folds": args.inner_folds,
        "outer_folds": args.outer_folds,
        "max_predictors": args.max_predictors,
        "canonical_spec": args.canonical_spec,
        "seed": args.seed,
        "hidden_truth_used": False,
    }
    (out / "product_a_v2_1_preoutcome_contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
