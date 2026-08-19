"""Sealed-blind model-pool worker for one empirical taxon across all frozen M specs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .model import ModelSpec
from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .niche_recovery_procedure import RecoveryProcedure, benchmark_recovery_procedures
from .validation import make_spatial_partition
from .v2_6_empirical_model_contract import load_v2_6_empirical_model_contract

M_NAMES = ("buffer_150km", "buffer_300km", "buffer_500km")


def _procedure_library(contract: dict) -> tuple[RecoveryProcedure, ...]:
    frozen = contract["fixed_design"]["procedure_library"]
    procedures = []
    for spec in frozen["model_specs"]:
        model_spec = ModelSpec(C=float(spec["C"]), degree=int(spec["degree"]), penalty=str(spec["penalty"]))
        for strategy in frozen["strategies"]:
            procedures.append(
                RecoveryProcedure(
                    strategy=str(strategy),
                    model_spec=model_spec,
                    inner_folds=int(frozen["inner_folds"]),
                    max_predictors=int(frozen["max_predictors"]),
                    vif_threshold=float(frozen["vif_threshold"]),
                    predictive_min_gain=float(frozen["predictive_min_gain"]),
                    observation_predictors=tuple(frozen["observation_predictors"]),
                )
            )
    if len(procedures) != 8 or len({p.label for p in procedures}) != 8:
        raise ValueError("empirical v2.6 procedure library must contain exactly eight unique procedures")
    return tuple(procedures)


def _partition_contract(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_6_empirical_model_pool_partition_contract":
        raise ValueError("empirical partition purpose changed")
    if int(payload.get("n_spatial_blocks", -1)) != 5:
        raise ValueError("empirical model-pool block count changed")
    if abs(float(payload.get("partition_holdout_fraction", -1)) - 0.20) > 1e-12:
        raise ValueError("empirical model-pool partition fraction changed")
    if payload.get("partition_seed_formula") != "part_seed + taxon_index*100 + M_index":
        raise ValueError("empirical model-pool partition seed formula changed")
    for key in (
        "partition_uses_model_pool_rows_only",
        "same_partition_shared_by_all_base_and_knockout_procedures_within_taxon_M",
    ):
        if payload.get(key) is not True:
            raise ValueError(f"empirical partition contract changed: {key}")
    for key in ("sealed_occurrence_coordinates_used", "sealed_environment_values_used"):
        if payload.get(key) is not False:
            raise ValueError(f"empirical model-pool worker requires {key}=false")
    return payload


def run_model_pool_worker(
    *,
    contract_path: str | Path,
    partition_contract_path: str | Path,
    process_registry_path: str | Path,
    part_dir: str | Path,
    taxon: str,
    taxon_index: int,
    part_seed: int,
    output_dir: str | Path,
) -> dict[str, object]:
    contract = load_v2_6_empirical_model_contract(contract_path)
    partition_contract = _partition_contract(partition_contract_path)
    if int(part_seed) not in {int(x) for x in contract["fixed_design"]["split_seeds"]}:
        raise ValueError("part seed is not frozen")
    if not 0 <= int(taxon_index) < 12:
        raise ValueError("taxon_index must be 0..11")

    root = Path(part_dir)
    materialization = json.loads((root / "contract.json").read_text(encoding="utf-8"))
    if materialization.get("sealed_occurrence_raster_values_extracted") is not False:
        raise ValueError("model-pool worker received a materialization that opened sealed occurrence environments")
    if materialization.get("sealed_background_raster_values_extracted") is not False:
        raise ValueError("model-pool worker received a materialization that opened sealed background environments")
    if int(materialization.get("seed", -1)) != int(part_seed):
        raise ValueError("part materialization seed differs from requested worker seed")

    occurrences_all = pd.read_parquet(root / "model_occurrences.parquet")
    occurrence = occurrences_all.loc[occurrences_all["species"].astype(str).eq(str(taxon))].reset_index(drop=True)
    if occurrence.empty:
        raise ValueError(f"model-pool occurrence data missing taxon: {taxon}")
    backgrounds = {}
    for name in M_NAMES:
        frame = pd.read_parquet(root / "M" / name / "model_background.parquet")
        frame = frame.loc[frame["species"].astype(str).eq(str(taxon))].reset_index(drop=True)
        if frame.empty:
            raise ValueError(f"model-pool background missing {taxon} in {name}")
        backgrounds[name] = frame

    registry = pd.read_csv(process_registry_path)
    audit_predictors = tuple(registry["predictor"].astype(str))
    admissibility = select_model_pool_admissible_predictors(
        {name: (occurrence, backgrounds[name]) for name in M_NAMES},
        audit_predictors,
        minimum_coverage=float(contract["fixed_design"]["minimum_model_pool_predictor_coverage"]),
    )
    ecological_predictors = tuple(admissibility.predictors)
    if not ecological_predictors:
        raise ValueError("no CHELSA predictor passed the frozen model-pool coverage gate")
    procedures = _procedure_library(contract)
    adequacy = contract["fixed_design"]["prediction_adequacy"]

    domain_predictors = {
        str(domain): tuple(
            registry.loc[registry["empirical_process_domain"].astype(str).eq(str(domain)), "predictor"].astype(str)
        )
        for domain in contract["fixed_design"]["process_domains"]
    }
    base_frames = []
    knockout_frames = []
    status_rows = []
    trace_frames = []

    for m_index, name in enumerate(M_NAMES):
        background = backgrounds[name]
        partition_seed = int(part_seed) + int(taxon_index) * 100 + int(m_index)
        partition = make_spatial_partition(
            occurrence["longitude"].to_numpy(float),
            occurrence["latitude"].to_numpy(float),
            background["longitude"].to_numpy(float),
            background["latitude"].to_numpy(float),
            n_blocks=int(partition_contract["n_spatial_blocks"]),
            holdout_fraction=float(partition_contract["partition_holdout_fraction"]),
            random_state=partition_seed,
        )
        common = dict(
            presence=occurrence,
            background=background,
            presence_groups=partition.presence_blocks,
            background_groups=partition.background_blocks,
            audit_predictors=audit_predictors,
            procedures=procedures,
            outer_folds=int(contract["fixed_design"]["procedure_library"]["outer_folds"]),
            chance_auc=float(adequacy["chance_auc"]),
            minimum_auc_margin=float(adequacy["minimum_auc_margin"]),
            auc_sem_multiplier=float(adequacy["auc_sem_multiplier"]),
        )
        try:
            base = benchmark_recovery_procedures(
                ecological_predictors=ecological_predictors,
                **common,
            )
        except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
            status_rows.append({
                "taxon": str(taxon), "M": name, "group": "base", "status": "failed",
                "error": str(exc), "partition_seed": partition_seed,
            })
        else:
            metrics = base.fold_metrics.copy()
            metrics["taxon"] = str(taxon)
            metrics["M"] = name
            metrics["group"] = "base"
            metrics["excluded_process_domain"] = None
            metrics["partition_seed"] = partition_seed
            base_frames.append(metrics)
            if not base.selection_trace.empty:
                trace = base.selection_trace.copy()
                trace["taxon"] = str(taxon); trace["M"] = name; trace["group"] = "base"
                trace_frames.append(trace)
            status_rows.append({
                "taxon": str(taxon), "M": name, "group": "base", "status": "success",
                "error": None, "partition_seed": partition_seed,
            })

        for domain in contract["fixed_design"]["process_domains"]:
            excluded = set(domain_predictors[str(domain)])
            retained = tuple(p for p in ecological_predictors if p not in excluded)
            if not retained:
                status_rows.append({
                    "taxon": str(taxon), "M": name, "group": str(domain),
                    "status": "failed_no_retained_predictors", "error": None,
                    "partition_seed": partition_seed,
                })
                continue
            try:
                result = benchmark_recovery_procedures(
                    ecological_predictors=retained,
                    **common,
                )
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                status_rows.append({
                    "taxon": str(taxon), "M": name, "group": str(domain), "status": "failed",
                    "error": str(exc), "partition_seed": partition_seed,
                })
                continue
            metrics = result.fold_metrics.copy()
            metrics["base_candidate"] = metrics["candidate"].astype(str)
            metrics["candidate"] = metrics["base_candidate"].astype(str) + "::exclude::" + str(domain)
            metrics["procedure"] = metrics["candidate"]
            metrics["taxon"] = str(taxon)
            metrics["M"] = name
            metrics["group"] = str(domain)
            metrics["excluded_process_domain"] = str(domain)
            metrics["excluded_predictors"] = ",".join(sorted(excluded & set(ecological_predictors)))
            metrics["partition_seed"] = partition_seed
            knockout_frames.append(metrics)
            if not result.selection_trace.empty:
                trace = result.selection_trace.copy()
                trace["taxon"] = str(taxon); trace["M"] = name; trace["group"] = str(domain)
                trace_frames.append(trace)
            status_rows.append({
                "taxon": str(taxon), "M": name, "group": str(domain), "status": "success",
                "error": None, "partition_seed": partition_seed,
            })

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base_metrics = pd.concat(base_frames, ignore_index=True) if base_frames else pd.DataFrame()
    knockout_metrics = pd.concat(knockout_frames, ignore_index=True) if knockout_frames else pd.DataFrame()
    traces = pd.concat(trace_frames, ignore_index=True) if trace_frames else pd.DataFrame()
    base_metrics.to_csv(out / "base_fold_metrics.csv", index=False)
    knockout_metrics.to_csv(out / "knockout_fold_metrics.csv", index=False)
    pd.DataFrame(status_rows).to_csv(out / "worker_status.csv", index=False)
    admissibility.ledger.to_csv(out / "predictor_coverage.csv", index=False)
    traces.to_csv(out / "selection_trace.csv", index=False)
    worker_contract = {
        "purpose": "product_a_v2_6_empirical_model_pool_worker",
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": int(part_seed),
        "M_specs": list(M_NAMES),
        "n_admissible_predictors": len(ecological_predictors),
        "admissible_predictors": list(ecological_predictors),
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "old_real_model_outputs_reused": False,
        "old_real_sealed_outcomes_read": False,
    }
    (out / "contract.json").write_text(json.dumps(worker_contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return worker_contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--partition-contract", required=True)
    parser.add_argument("--process-registry", required=True)
    parser.add_argument("--part-dir", required=True)
    parser.add_argument("--taxon", required=True)
    parser.add_argument("--taxon-index", required=True, type=int)
    parser.add_argument("--part-seed", required=True, type=int)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    run_model_pool_worker(
        contract_path=args.contract,
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
