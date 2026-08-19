"""Fit and serialize frozen empirical representatives using model-pool rows only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from .recovery_procedure_fit import fit_recovery_procedure
from .validation import make_spatial_partition
from .v2_6_empirical_model_contract import load_v2_6_empirical_model_contract
from .v2_6_empirical_model_pool_worker import M_NAMES, _partition_contract, _procedure_library


def freeze_final_models(
    *,
    contract_path: str | Path,
    partition_contract_path: str | Path,
    part_dir: str | Path,
    worker_dir: str | Path,
    pretruth_dir: str | Path,
    taxon: str,
    taxon_index: int,
    output_dir: str | Path,
) -> dict[str, object]:
    contract = load_v2_6_empirical_model_contract(contract_path)
    partition_contract = _partition_contract(partition_contract_path)
    part = Path(part_dir)
    materialization = json.loads((part / "contract.json").read_text(encoding="utf-8"))
    if materialization.get("sealed_occurrence_raster_values_extracted") is not False:
        raise ValueError("final fitting cannot consume opened sealed environments")
    pretruth = json.loads((Path(pretruth_dir) / "contract.json").read_text(encoding="utf-8"))
    if pretruth.get("purpose") != "product_a_v2_6_empirical_part_pretruth_freeze":
        raise ValueError("final fitting requires a frozen empirical pretruth artifact")
    if pretruth.get("sealed_occurrence_environment_read") is not False:
        raise ValueError("pretruth artifact already crossed the sealed barrier")
    worker = json.loads((Path(worker_dir) / "contract.json").read_text(encoding="utf-8"))
    if worker.get("taxon") != str(taxon):
        raise ValueError("model-pool worker taxon differs from final-fit taxon")
    if worker.get("sealed_occurrence_environment_read") is not False:
        raise ValueError("model-pool worker opened sealed environments")

    part_seed = int(worker["part_seed"])
    ecological_predictors = tuple(str(x) for x in worker["admissible_predictors"])
    if not ecological_predictors:
        raise ValueError("final fitting has no frozen admissible predictors")
    audit_predictors = tuple(pd.read_csv(contract["fixed_design"]["process_registry_path"])["predictor"].astype(str))
    procedures = {procedure.label: procedure for procedure in _procedure_library(contract)}
    representatives = {
        "ecological": str(pretruth["ecological_representative"]),
        "auc": str(pretruth["auc_representative"]),
    }
    for label in representatives.values():
        if label not in procedures:
            raise ValueError(f"pretruth representative is not in frozen procedure library: {label}")

    occurrence_all = pd.read_parquet(part / "model_occurrences.parquet")
    occurrence = occurrence_all.loc[occurrence_all["species"].astype(str).eq(str(taxon))].reset_index(drop=True)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    selected_rows = []
    trace_frames = []

    for m_index, name in enumerate(M_NAMES):
        background_all = pd.read_parquet(part / "M" / name / "model_background.parquet")
        background = background_all.loc[background_all["species"].astype(str).eq(str(taxon))].reset_index(drop=True)
        partition_seed = part_seed + int(taxon_index) * 100 + int(m_index)
        partition = make_spatial_partition(
            occurrence["longitude"].to_numpy(float),
            occurrence["latitude"].to_numpy(float),
            background["longitude"].to_numpy(float),
            background["latitude"].to_numpy(float),
            n_blocks=int(partition_contract["n_spatial_blocks"]),
            holdout_fraction=float(partition_contract["partition_holdout_fraction"]),
            random_state=partition_seed,
        )
        m_out = out / "M" / name
        m_out.mkdir(parents=True, exist_ok=True)
        fitted_by_candidate = {}
        for role, candidate in representatives.items():
            if candidate not in fitted_by_candidate:
                fitted_by_candidate[candidate] = fit_recovery_procedure(
                    occurrence,
                    background,
                    partition.presence_blocks,
                    partition.background_blocks,
                    ecological_predictors,
                    audit_predictors,
                    procedures[candidate],
                    chance_auc=float(contract["fixed_design"]["prediction_adequacy"]["chance_auc"]),
                    minimum_auc_margin=float(contract["fixed_design"]["prediction_adequacy"]["minimum_auc_margin"]),
                    auc_sem_multiplier=float(contract["fixed_design"]["prediction_adequacy"]["auc_sem_multiplier"]),
                )
            fitted = fitted_by_candidate[candidate]
            model_file = f"{role}_model.joblib"
            joblib.dump(fitted.model, m_out / model_file)
            selected_rows.append({
                "taxon": str(taxon), "M": name, "role": role, "candidate": candidate,
                "model": fitted.procedure.model_spec.label,
                "selected_predictors": ",".join(fitted.selected_predictors),
                "selected_ecological_predictors": ",".join(fitted.selected_ecological_predictors),
                "n_predictors": len(fitted.selected_predictors),
                "model_file": str(Path("M") / name / model_file),
                "partition_seed": partition_seed,
            })
            if not fitted.selection_trace.empty:
                trace = fitted.selection_trace.copy()
                trace["taxon"] = str(taxon); trace["M"] = name; trace["role"] = role; trace["candidate"] = candidate
                trace_frames.append(trace)

    selected = pd.DataFrame(selected_rows)
    selected.to_csv(out / "frozen_final_models.csv", index=False)
    traces = pd.concat(trace_frames, ignore_index=True) if trace_frames else pd.DataFrame()
    traces.to_csv(out / "final_selection_trace.csv", index=False)
    result = {
        "purpose": "product_a_v2_6_empirical_final_models_presealed",
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "part_seed": part_seed,
        "n_M": len(M_NAMES),
        "representatives": representatives,
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_final_selection": False,
        "final_models_serialized_before_sealed_audit": True,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--partition-contract", required=True)
    parser.add_argument("--part-dir", required=True)
    parser.add_argument("--worker-dir", required=True)
    parser.add_argument("--pretruth-dir", required=True)
    parser.add_argument("--taxon", required=True)
    parser.add_argument("--taxon-index", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    freeze_final_models(
        contract_path=args.contract,
        partition_contract_path=args.partition_contract,
        part_dir=args.part_dir,
        worker_dir=args.worker_dir,
        pretruth_dir=args.pretruth_dir,
        taxon=args.taxon,
        taxon_index=args.taxon_index,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
