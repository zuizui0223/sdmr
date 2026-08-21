"""Sealed-blind real-data diagnostic for Product-A v2.7 audit support.

This lane intentionally does not fit or select a candidate model.  It reuses only
v2.6 model-pool materialization to ask whether a process-representative,
partition-aware audit space can make the ecological recovery metrics
mathematically evaluable before any candidate benchmark begins.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .v2_6_empirical_model_contract import load_v2_6_empirical_model_contract
from .v2_6_empirical_model_pool_worker import M_NAMES, _partition_contract
from .v2_7_audit_support_contract import load_v2_7_audit_support_contract
from .v2_7_empirical_audit_support import (
    audit_support_ledger,
    select_partition_aware_empirical_audit_space,
)
from .validation import make_spatial_partition

PURPOSE = "product_a_v2_7_empirical_audit_support_diagnostic"


def run_audit_support_diagnostic(
    *,
    development_contract_path: str | Path,
    model_contract_path: str | Path,
    partition_contract_path: str | Path,
    process_registry_path: str | Path,
    part_dir: str | Path,
    taxon: str,
    taxon_index: int,
    part_seed: int,
    output_dir: str | Path,
) -> dict[str, object]:
    development = load_v2_7_audit_support_contract(development_contract_path)
    model_contract = load_v2_6_empirical_model_contract(model_contract_path)
    partition_contract = _partition_contract(partition_contract_path)
    if int(part_seed) not in {int(x) for x in model_contract["fixed_design"]["split_seeds"]}:
        raise ValueError("audit-support diagnostic part seed is not frozen")
    if not 0 <= int(taxon_index) < 12:
        raise ValueError("audit-support diagnostic taxon_index must be 0..11")

    root = Path(part_dir)
    materialization = json.loads((root / "contract.json").read_text(encoding="utf-8"))
    for key in (
        "sealed_occurrence_raster_values_extracted",
        "sealed_background_raster_values_extracted",
    ):
        if materialization.get(key) is not False:
            raise ValueError(f"v2.7 diagnostic requires {key}=false")
    if int(materialization.get("seed", -1)) != int(part_seed):
        raise ValueError("v2.7 diagnostic materialization seed differs from requested seed")

    occurrences_all = pd.read_parquet(root / "model_occurrences.parquet")
    occurrence = occurrences_all.loc[
        occurrences_all["species"].astype(str).eq(str(taxon))
    ].reset_index(drop=True)
    if occurrence.empty:
        raise ValueError(f"v2.7 diagnostic model-pool occurrence missing taxon: {taxon}")
    backgrounds: dict[str, pd.DataFrame] = {}
    partitions = {}
    for m_index, name in enumerate(M_NAMES):
        frame = pd.read_parquet(root / "M" / name / "model_background.parquet")
        background = frame.loc[frame["species"].astype(str).eq(str(taxon))].reset_index(drop=True)
        if background.empty:
            raise ValueError(f"v2.7 diagnostic model-pool background missing {taxon} in {name}")
        backgrounds[name] = background
        partition_seed = int(part_seed) + int(taxon_index) * 100 + int(m_index)
        partitions[name] = make_spatial_partition(
            occurrence["longitude"].to_numpy(float),
            occurrence["latitude"].to_numpy(float),
            background["longitude"].to_numpy(float),
            background["latitude"].to_numpy(float),
            n_blocks=int(partition_contract["n_spatial_blocks"]),
            holdout_fraction=float(partition_contract["partition_holdout_fraction"]),
            random_state=partition_seed,
        )

    registry = pd.read_csv(process_registry_path)
    required_registry = {"predictor", "empirical_process_domain"}
    missing = required_registry - set(registry.columns)
    if missing:
        raise KeyError(f"v2.7 audit registry missing columns: {sorted(missing)}")
    manifest = registry[["predictor", "empirical_process_domain"]].rename(
        columns={"empirical_process_domain": "process"}
    )
    full_predictors = tuple(manifest["predictor"].astype(str))
    audit_cfg = development["audit_space"]
    outer_folds = int(model_contract["fixed_design"]["procedure_library"]["outer_folds"])

    legacy_support = audit_support_ledger(
        occurrence,
        backgrounds,
        partitions,
        full_predictors,
        outer_folds=outer_folds,
        minimum_fit_background_rows=int(audit_cfg["minimum_complete_fit_background_rows_per_M_fold"]),
        minimum_evaluation_background_rows=int(audit_cfg["minimum_complete_evaluation_background_rows_per_M_fold"]),
        minimum_heldout_occurrence_rows=int(audit_cfg["minimum_complete_heldout_occurrence_rows_per_M_fold"]),
    )

    available = False
    error: str | None = None
    selected_predictors: tuple[str, ...] = ()
    selected_processes: tuple[str, ...] = ()
    support = pd.DataFrame()
    pruning = pd.DataFrame()
    base_ledger = pd.DataFrame()
    try:
        selected = select_partition_aware_empirical_audit_space(
            manifest,
            occurrence,
            backgrounds,
            partitions,
            outer_folds=outer_folds,
            minimum_predictor_coverage=float(audit_cfg["minimum_predictor_coverage"]),
            minimum_joint_coverage=float(audit_cfg["minimum_joint_coverage"]),
            minimum_processes=int(audit_cfg["minimum_processes"]),
            minimum_fit_background_rows=int(audit_cfg["minimum_complete_fit_background_rows_per_M_fold"]),
            minimum_evaluation_background_rows=int(audit_cfg["minimum_complete_evaluation_background_rows_per_M_fold"]),
            minimum_heldout_occurrence_rows=int(audit_cfg["minimum_complete_heldout_occurrence_rows_per_M_fold"]),
        )
    except ValueError as exc:
        error = str(exc)
    else:
        available = True
        selected_predictors = selected.predictors
        selected_processes = selected.processes
        support = selected.support_ledger.copy()
        pruning = selected.pruning_ledger.copy()
        base_ledger = selected.base_audit_ledger.copy()
        if not support["audit_support_complete"].astype(bool).all():
            raise AssertionError("v2.7 diagnostic marked available without complete fold support")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    legacy_support.to_csv(out / "legacy_43_predictor_audit_support.csv", index=False)
    support.to_csv(out / "v2_7_audit_support.csv", index=False)
    pruning.to_csv(out / "v2_7_audit_pruning.csv", index=False)
    base_ledger.to_csv(out / "v2_7_base_audit_space_ledger.csv", index=False)
    result = {
        "purpose": PURPOSE,
        "development_contract_sha256": development["contract_sha256"],
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": int(part_seed),
        "M_specs": list(M_NAMES),
        "outer_folds": outer_folds,
        "candidate_predictor_universe_size": len(full_predictors),
        "candidate_predictor_universe_unchanged": len(full_predictors) == 43,
        "legacy_43_predictor_supported_M_fold_cells": int(
            legacy_support["audit_support_complete"].astype(bool).sum()
        ),
        "total_M_fold_cells": int(len(legacy_support)),
        "audit_support_available": bool(available),
        "audit_support_unavailable_reason": error,
        "selected_audit_predictors": list(selected_predictors),
        "selected_audit_processes": list(selected_processes),
        "n_selected_audit_processes": len(selected_processes),
        "audit_space_frozen_before_candidate_benchmark": True,
        "candidate_scores_read": False,
        "candidate_response_magnitudes_read": False,
        "process_knockout_outcomes_read": False,
        "sealed_occurrence_environment_read": False,
        "sealed_background_environment_read": False,
        "development_only": True,
        "scientific_promotion_allowed": False,
        "independent_empirical_confirmation_claim_allowed": False,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development-contract", required=True)
    parser.add_argument("--model-contract", required=True)
    parser.add_argument("--partition-contract", required=True)
    parser.add_argument("--process-registry", required=True)
    parser.add_argument("--part-dir", required=True)
    parser.add_argument("--taxon", required=True)
    parser.add_argument("--taxon-index", type=int, required=True)
    parser.add_argument("--part-seed", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    run_audit_support_diagnostic(
        development_contract_path=args.development_contract,
        model_contract_path=args.model_contract,
        partition_contract_path=args.partition_contract,
        process_registry_path=args.process_registry,
        part_dir=args.part_dir,
        taxon=args.taxon,
        taxon_index=args.taxon_index,
        part_seed=args.part_seed,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
