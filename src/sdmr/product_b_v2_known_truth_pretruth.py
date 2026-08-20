"""Freeze Product-B v2 process evidence and unseen-taxon core before truth opens."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .product_b_v2 import (
    pair_process_knockout_losses,
    repeat_process_core_splits,
    summarize_taxon_process_support,
)
from .product_b_v2_known_truth_contract import M_SPECS, load_product_b_v2_known_truth_contract


def freeze_product_b_v2_process_core(
    *,
    contract_path: str | Path,
    method_dir: str | Path,
    worker_root: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    contract = load_product_b_v2_known_truth_contract(contract_path)
    method = json.loads((Path(method_dir) / "contract.json").read_text(encoding="utf-8"))
    if method.get("purpose") != "product_b_v2_frozen_product_a_method_pretruth":
        raise ValueError("Product-B pretruth requires frozen Product-A method")
    if method.get("source_contract_sha256") != contract["contract_sha256"]:
        raise ValueError("method contract mismatch")
    frozen_candidate = str(method["frozen_candidate"])

    contracts: list[dict[str, object]] = []
    base_frames: list[pd.DataFrame] = []
    knockout_frames: list[pd.DataFrame] = []
    for path in sorted(Path(worker_root).rglob("contract.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("purpose") != "product_b_v2_known_truth_process_shard_pretruth":
            continue
        if row.get("source_contract_sha256") != contract["contract_sha256"]:
            raise ValueError("Product-B process shard contract mismatch")
        if str(row.get("frozen_candidate")) != frozen_candidate:
            raise ValueError("Product-B process shards mixed frozen candidates")
        for key in (
            "generating_truth_read",
            "real_empirical_data_read",
            "empirical_sealed_outcomes_read",
            "scientific_threshold_tuning_performed",
        ):
            if row.get(key) is not False:
                raise ValueError(f"Product-B pretruth barrier violated: {key}")
        if row.get("same_spatial_partition_for_base_and_all_knockouts") is not True:
            raise ValueError("base/knockout spatial partition mismatch")
        if row.get("admissibility_computed_across_all_frozen_M") is not True:
            raise ValueError("Product-B shard changed admissibility semantics")
        base = pd.read_csv(path.parent / "base_fold_metrics.csv")
        knockout = pd.read_csv(path.parent / "knockout_fold_metrics.csv")
        if base.empty or knockout.empty:
            raise ValueError(f"empty Product-B shard metrics: {path.parent}")
        contracts.append(row)
        base_frames.append(base)
        knockout_frames.append(knockout)

    taxa = tuple(contract["product_b_evaluation_taxon_names"])
    expected_keys = {(taxon, m) for taxon in taxa for m in M_SPECS}
    observed_keys = {(str(x["taxon"]), str(x["M"])) for x in contracts}
    if observed_keys != expected_keys or len(contracts) != len(expected_keys):
        raise ValueError("Product-B taxon x M denominator is incomplete")
    base = pd.concat(base_frames, ignore_index=True)
    knockout = pd.concat(knockout_frames, ignore_index=True)
    outer_folds = int(contract["simulation_contract"]["outer_folds"])
    expected_folds = tuple(range(outer_folds))
    paired = pair_process_knockout_losses(
        base,
        knockout,
        frozen_candidate=frozen_candidate,
        expected_taxa=taxa,
        expected_M=M_SPECS,
        expected_folds=expected_folds,
    )
    rule = contract["process_constraint_rule"]
    taxon_process = summarize_taxon_process_support(
        paired,
        expected_M=M_SPECS,
        expected_folds=expected_folds,
        min_pareto_worsening_fraction=float(rule["min_pareto_worsening_fraction"]),
        max_pareto_improvement_fraction=float(rule["max_pareto_improvement_fraction"]),
    )
    expected_rows = len(taxa) * len(contract["ecological_process_universe"])
    if len(taxon_process) != expected_rows:
        raise ValueError("Product-B taxon x process denominator is incomplete")
    if not taxon_process["complete_M_fold_evidence"].astype(bool).all():
        raise ValueError("Product-B process inference has incomplete M x fold evidence")

    universality = contract["universality_rule"]
    repeated = repeat_process_core_splits(
        taxon_process,
        seeds=tuple(int(x) for x in universality["split_seeds"]),
        validation_fraction=float(universality["validation_fraction"]),
        min_taxon_support_fraction=float(universality["min_taxon_support_fraction"]),
    )
    stability = repeated.process_stability.copy()
    stable_threshold = float(universality["stable_core_min_validation_confirmation_fraction"])
    stability["stable_universal_core"] = (
        pd.to_numeric(stability["validation_confirmation_stability"], errors="coerce")
        >= stable_threshold - 1e-12
    )
    stable_core = tuple(sorted(stability.loc[stability["stable_universal_core"], "process_domain"].astype(str)))

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paired.to_csv(out / "paired_process_losses.csv", index=False)
    taxon_process.to_csv(out / "taxon_process_summary.csv", index=False)
    repeated.split_summary.to_csv(out / "universality_split_summary.csv", index=False)
    stability.to_csv(out / "process_stability.csv", index=False)
    result = {
        "purpose": "product_b_v2_known_truth_process_core_pretruth_freeze",
        "source_contract_sha256": contract["contract_sha256"],
        "frozen_candidate": frozen_candidate,
        "n_process_shards": len(contracts),
        "n_taxa": len(taxa),
        "n_processes": len(contract["ecological_process_universe"]),
        "M_specs": list(M_SPECS),
        "outer_folds": outer_folds,
        "stable_core_threshold": stable_threshold,
        "stable_universal_core": list(stable_core),
        "all_M_x_fold_evidence_complete": True,
        "process_losses_frozen_before_generating_truth_audit": True,
        "generating_truth_read": False,
        "real_empirical_data_read": False,
        "empirical_sealed_outcomes_read": False,
        "scientific_threshold_tuning_performed": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--method-dir", required=True)
    parser.add_argument("--worker-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    freeze_product_b_v2_process_core(
        contract_path=args.contract,
        method_dir=args.method_dir,
        worker_root=args.worker_root,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
