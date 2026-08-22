"""Sealed-blind v2.7.1 worker using evidence-balanced folds and a frozen audit space."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .niche_recovery_procedure import benchmark_recovery_procedures
from .v2_6_empirical_model_pool_worker import M_NAMES, _procedure_library
from .v2_7_1_evidence_balanced_partition import make_evidence_balanced_spatial_partitions
from .v2_7_empirical_audit_support import select_partition_aware_empirical_audit_space
from .v2_7_1_fresh_contract import load_v2_7_1_fresh_confirmation_contract

PURPOSE = "product_a_v2_7_1_fresh_model_pool_worker"


def _audit_manifest(registry: pd.DataFrame) -> pd.DataFrame:
    return registry[["predictor", "empirical_process_domain"]].rename(columns={"empirical_process_domain": "process"})


def _write_unavailable(out: Path, *, taxon: str, taxon_index: int, part_seed: int, stage: str, error: str) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame().to_csv(out / "base_fold_metrics.csv", index=False)
    pd.DataFrame().to_csv(out / "knockout_fold_metrics.csv", index=False)
    pd.DataFrame([{"taxon": taxon, "group": "worker", "status": "unavailable", "error": error}]).to_csv(out / "worker_status.csv", index=False)
    pd.DataFrame().to_csv(out / "predictor_coverage.csv", index=False)
    pd.DataFrame().to_csv(out / "selection_trace.csv", index=False)
    result = {
        "purpose": PURPOSE, "available": False, "unavailable_stage": stage, "unavailable_reason": error,
        "taxon": str(taxon), "taxon_index": int(taxon_index), "part_seed": int(part_seed),
        "sealed_occurrence_environment_read": False, "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False, "candidate_model_fitting_performed": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_fresh_model_pool_worker(
    *, contract_path: str | Path, process_registry_path: str | Path, part_dir: str | Path,
    taxon: str, taxon_index: int, part_seed: int, output_dir: str | Path,
) -> dict[str, object]:
    contract = load_v2_7_1_fresh_confirmation_contract(contract_path)
    if int(part_seed) not in {int(x) for x in contract["fixed_design"]["split_seeds"]}:
        raise ValueError("fresh part seed is not frozen")
    if not 0 <= int(taxon_index) < 12:
        raise ValueError("fresh taxon_index must be 0..11")
    out = Path(output_dir)
    root = Path(part_dir)
    materialization = json.loads((root / "contract.json").read_text(encoding="utf-8"))
    if materialization.get("purpose") != "product_a_v2_7_1_fresh_part_model_pool_materialization":
        raise ValueError("fresh worker received the wrong materialization")
    if materialization.get("sealed_occurrence_raster_values_extracted") is not False or materialization.get("sealed_background_raster_values_extracted") is not False:
        raise ValueError("fresh worker received opened sealed environments")
    if int(materialization.get("seed", -1)) != int(part_seed):
        raise ValueError("fresh worker seed differs from materialization")

    occurrences_all = pd.read_parquet(root / "model_occurrences.parquet")
    occurrence = occurrences_all.loc[occurrences_all["species"].astype(str).eq(str(taxon))].reset_index(drop=True)
    if occurrence.empty:
        raise ValueError(f"fresh model-pool occurrence data missing taxon: {taxon}")
    backgrounds = {}
    for name in M_NAMES:
        frame = pd.read_parquet(root / "M" / name / "model_background.parquet")
        frame = frame.loc[frame["species"].astype(str).eq(str(taxon))].reset_index(drop=True)
        if frame.empty:
            raise ValueError(f"fresh model-pool background missing {taxon} in {name}")
        backgrounds[name] = frame

    registry = pd.read_csv(process_registry_path)
    all_audit_predictors = tuple(registry["predictor"].astype(str))
    audit_cfg = contract["v2_7_1_partition_aware_audit_space"]
    admissibility = select_model_pool_admissible_predictors(
        {name: (occurrence, backgrounds[name]) for name in M_NAMES}, all_audit_predictors,
        minimum_coverage=float(audit_cfg["minimum_predictor_coverage"]),
    )
    ecological_predictors = tuple(admissibility.predictors)
    if not ecological_predictors:
        return _write_unavailable(out, taxon=taxon, taxon_index=taxon_index, part_seed=part_seed,
            stage="predictor_admissibility", error="no predictor passed the frozen 0.95 model-pool coverage gate")

    fold_cfg = contract["v2_7_1_evidence_balanced_partition"]
    partition_seed = int(part_seed) + int(taxon_index) * 100 + 271
    try:
        partition = make_evidence_balanced_spatial_partitions(
            occurrence["longitude"].to_numpy(float), occurrence["latitude"].to_numpy(float),
            {name: (backgrounds[name]["longitude"].to_numpy(float), backgrounds[name]["latitude"].to_numpy(float)) for name in M_NAMES},
            n_microblocks=int(fold_cfg["spatial_microblocks"]), outer_folds=int(fold_cfg["outer_folds"]),
            minimum_evaluation_occurrences=int(fold_cfg["minimum_evaluation_occurrences_per_fold"]),
            minimum_evaluation_background_rows=int(fold_cfg["minimum_evaluation_background_rows_per_M_fold"]),
            minimum_training_background_rows=int(fold_cfg["minimum_training_background_rows_per_M_fold"]),
            assignment_attempts=int(fold_cfg["assignment_attempts"]), random_state=partition_seed,
        )
    except ValueError as exc:
        return _write_unavailable(out, taxon=taxon, taxon_index=taxon_index, part_seed=part_seed, stage="structural_partition", error=str(exc))

    partitions = {name: partition.for_M(name) for name in M_NAMES}
    try:
        selected_audit = select_partition_aware_empirical_audit_space(
            _audit_manifest(registry), occurrence, backgrounds, partitions,
            outer_folds=int(fold_cfg["outer_folds"]),
            minimum_predictor_coverage=float(audit_cfg["minimum_predictor_coverage"]),
            minimum_joint_coverage=float(audit_cfg["minimum_joint_coverage"]),
            minimum_processes=int(audit_cfg["minimum_processes"]),
            minimum_fit_background_rows=int(audit_cfg["minimum_complete_fit_background_rows_per_M_fold"]),
            minimum_evaluation_background_rows=int(audit_cfg["minimum_complete_evaluation_background_rows_per_M_fold"]),
            minimum_heldout_occurrence_rows=int(audit_cfg["minimum_complete_heldout_occurrence_rows_per_M_fold"]),
        )
    except ValueError as exc:
        return _write_unavailable(out, taxon=taxon, taxon_index=taxon_index, part_seed=part_seed, stage="audit_space", error=str(exc))

    audit_predictors = tuple(selected_audit.predictors)
    procedures = _procedure_library(contract)
    adequacy = contract["fixed_design"]["prediction_adequacy"]
    domain_predictors = {
        str(domain): tuple(registry.loc[registry["empirical_process_domain"].astype(str).eq(str(domain)), "predictor"].astype(str))
        for domain in contract["fixed_design"]["process_domains"]
    }
    base_frames, knockout_frames, trace_frames, status_rows = [], [], [], []
    for name in M_NAMES:
        background = backgrounds[name]
        common = dict(
            presence=occurrence, background=background,
            presence_groups=partition.presence_folds, background_groups=partition.background_folds[name],
            audit_predictors=audit_predictors, procedures=procedures,
            outer_folds=int(contract["fixed_design"]["procedure_library"]["outer_folds"]),
            chance_auc=float(adequacy["chance_auc"]), minimum_auc_margin=float(adequacy["minimum_auc_margin"]),
            auc_sem_multiplier=float(adequacy["auc_sem_multiplier"]),
        )
        try:
            base = benchmark_recovery_procedures(ecological_predictors=ecological_predictors, **common)
        except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
            status_rows.append({"taxon": taxon, "M": name, "group": "base", "status": "failed", "error": str(exc), "partition_seed": partition_seed})
        else:
            metrics = base.fold_metrics.copy(); metrics["taxon"] = taxon; metrics["M"] = name; metrics["group"] = "base"
            metrics["excluded_process_domain"] = None; metrics["partition_seed"] = partition_seed; base_frames.append(metrics)
            if not base.selection_trace.empty:
                trace = base.selection_trace.copy(); trace["taxon"] = taxon; trace["M"] = name; trace["group"] = "base"; trace_frames.append(trace)
            status_rows.append({"taxon": taxon, "M": name, "group": "base", "status": "success", "error": None, "partition_seed": partition_seed})
        for domain in contract["fixed_design"]["process_domains"]:
            excluded = set(domain_predictors[str(domain)])
            retained = tuple(p for p in ecological_predictors if p not in excluded)
            if not retained:
                status_rows.append({"taxon": taxon, "M": name, "group": str(domain), "status": "failed_no_retained_predictors", "error": None, "partition_seed": partition_seed})
                continue
            try:
                result = benchmark_recovery_procedures(ecological_predictors=retained, **common)
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                status_rows.append({"taxon": taxon, "M": name, "group": str(domain), "status": "failed", "error": str(exc), "partition_seed": partition_seed})
                continue
            metrics = result.fold_metrics.copy(); metrics["base_candidate"] = metrics["candidate"].astype(str)
            metrics["candidate"] = metrics["base_candidate"].astype(str) + "::exclude::" + str(domain); metrics["procedure"] = metrics["candidate"]
            metrics["taxon"] = taxon; metrics["M"] = name; metrics["group"] = str(domain); metrics["excluded_process_domain"] = str(domain)
            metrics["excluded_predictors"] = ",".join(sorted(excluded & set(ecological_predictors))); metrics["partition_seed"] = partition_seed
            knockout_frames.append(metrics)
            if not result.selection_trace.empty:
                trace = result.selection_trace.copy(); trace["taxon"] = taxon; trace["M"] = name; trace["group"] = str(domain); trace_frames.append(trace)
            status_rows.append({"taxon": taxon, "M": name, "group": str(domain), "status": "success", "error": None, "partition_seed": partition_seed})

    out.mkdir(parents=True, exist_ok=True)
    (pd.concat(base_frames, ignore_index=True) if base_frames else pd.DataFrame()).to_csv(out / "base_fold_metrics.csv", index=False)
    (pd.concat(knockout_frames, ignore_index=True) if knockout_frames else pd.DataFrame()).to_csv(out / "knockout_fold_metrics.csv", index=False)
    pd.DataFrame(status_rows).to_csv(out / "worker_status.csv", index=False)
    admissibility.ledger.to_csv(out / "predictor_coverage.csv", index=False)
    (pd.concat(trace_frames, ignore_index=True) if trace_frames else pd.DataFrame()).to_csv(out / "selection_trace.csv", index=False)
    partition.support_ledger.to_csv(out / "evidence_balanced_partition_support.csv", index=False)
    partition.attempt_ledger.to_csv(out / "evidence_balanced_partition_attempts.csv", index=False)
    selected_audit.support_ledger.to_csv(out / "audit_support.csv", index=False)
    selected_audit.pruning_ledger.to_csv(out / "audit_pruning.csv", index=False)
    selected_audit.base_audit_ledger.to_csv(out / "base_audit_space.csv", index=False)
    pd.DataFrame({"row_index": np.arange(len(occurrence)), "fold": partition.presence_folds, "microblock": partition.presence_microblocks}).to_csv(out / "partition_presence.csv", index=False)
    for name in M_NAMES:
        pd.DataFrame({"row_index": np.arange(len(backgrounds[name])), "fold": partition.background_folds[name], "microblock": partition.background_microblocks[name]}).to_csv(out / f"partition_background__{name}.csv", index=False)

    result = {
        "purpose": PURPOSE, "available": True, "taxon": str(taxon), "taxon_index": int(taxon_index), "part_seed": int(part_seed),
        "M_specs": list(M_NAMES), "partition_seed": partition_seed, "selected_assignment_attempt": int(partition.selected_attempt),
        "n_admissible_predictors": len(ecological_predictors), "admissible_predictors": list(ecological_predictors),
        "audit_predictors": list(audit_predictors), "audit_processes": list(selected_audit.processes),
        "sealed_occurrence_environment_read": False, "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False, "candidate_model_fitting_performed": True,
        "candidate_scores_used_for_partition_or_audit_selection": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(); p.add_argument("--contract", required=True); p.add_argument("--process-registry", required=True)
    p.add_argument("--part-dir", required=True); p.add_argument("--taxon", required=True); p.add_argument("--taxon-index", type=int, required=True)
    p.add_argument("--part-seed", type=int, required=True); p.add_argument("--output-dir", required=True); a = p.parse_args(argv)
    run_fresh_model_pool_worker(contract_path=a.contract, process_registry_path=a.process_registry, part_dir=a.part_dir,
        taxon=a.taxon, taxon_index=a.taxon_index, part_seed=a.part_seed, output_dir=a.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
