"""Run one frozen M shard of the v2.6 empirical model-pool worker.

Predictor admissibility is still computed jointly across all three frozen M
specifications before the worker is narrowed to one M. The wrapper also restores
the original M-specific partition seed, so sharding changes only computation
placement, not scientific evidence or partitions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .v2_6_empirical_model_contract import load_v2_6_empirical_model_contract
from . import v2_6_empirical_model_pool_worker as worker


def run_m_shard(
    *,
    contract_path: str | Path,
    partition_contract_path: str | Path,
    process_registry_path: str | Path,
    part_dir: str | Path,
    taxon: str,
    taxon_index: int,
    part_seed: int,
    m_index: int,
    output_dir: str | Path,
) -> dict[str, object]:
    if not 0 <= int(m_index) < len(worker.M_NAMES):
        raise ValueError("m_index must address one of the three frozen M specs")
    original_names = tuple(worker.M_NAMES)
    m_name = original_names[int(m_index)]
    contract = load_v2_6_empirical_model_contract(contract_path)
    root = Path(part_dir)
    materialization = json.loads((root / "contract.json").read_text(encoding="utf-8"))
    if materialization.get("sealed_occurrence_raster_values_extracted") is not False:
        raise ValueError("M shard received opened sealed occurrence environments")

    occurrence_all = pd.read_parquet(root / "model_occurrences.parquet")
    occurrence = occurrence_all.loc[occurrence_all["species"].astype(str).eq(str(taxon))].reset_index(drop=True)
    backgrounds = {}
    for name in original_names:
        frame = pd.read_parquet(root / "M" / name / "model_background.parquet")
        backgrounds[name] = frame.loc[frame["species"].astype(str).eq(str(taxon))].reset_index(drop=True)
    registry = pd.read_csv(process_registry_path)
    audit_predictors = tuple(registry["predictor"].astype(str))
    all_m_admissibility = select_model_pool_admissible_predictors(
        {name: (occurrence, backgrounds[name]) for name in original_names},
        audit_predictors,
        minimum_coverage=float(contract["fixed_design"]["minimum_model_pool_predictor_coverage"]),
    )

    original_selector = worker.select_model_pool_admissible_predictors
    original_partition = worker.make_spatial_partition
    original_worker_names = worker.M_NAMES

    def frozen_selector(*args, **kwargs):
        return all_m_admissibility

    def corrected_partition(*args, **kwargs):
        kwargs = dict(kwargs)
        kwargs["random_state"] = int(kwargs["random_state"]) + int(m_index)
        return original_partition(*args, **kwargs)

    try:
        worker.M_NAMES = (m_name,)
        worker.select_model_pool_admissible_predictors = frozen_selector
        worker.make_spatial_partition = corrected_partition
        result = worker.run_model_pool_worker(
            contract_path=contract_path,
            partition_contract_path=partition_contract_path,
            process_registry_path=process_registry_path,
            part_dir=part_dir,
            taxon=taxon,
            taxon_index=taxon_index,
            part_seed=part_seed,
            output_dir=output_dir,
        )
    finally:
        worker.M_NAMES = original_worker_names
        worker.select_model_pool_admissible_predictors = original_selector
        worker.make_spatial_partition = original_partition

    out = Path(output_dir)
    result["M_specs"] = [m_name]
    result["m_index"] = int(m_index)
    result["admissibility_computed_across_all_frozen_M"] = True
    result["partition_seed_restored_to_original_M_index"] = True
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--partition-contract", required=True)
    parser.add_argument("--process-registry", required=True)
    parser.add_argument("--part-dir", required=True)
    parser.add_argument("--taxon", required=True)
    parser.add_argument("--taxon-index", required=True, type=int)
    parser.add_argument("--part-seed", required=True, type=int)
    parser.add_argument("--m-index", required=True, type=int)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    run_m_shard(
        contract_path=args.contract,
        partition_contract_path=args.partition_contract,
        process_registry_path=args.process_registry,
        part_dir=args.part_dir,
        taxon=args.taxon,
        taxon_index=args.taxon_index,
        part_seed=args.part_seed,
        m_index=args.m_index,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
