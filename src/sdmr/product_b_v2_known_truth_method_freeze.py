"""Freeze one Product-A ecological procedure before Product-B evaluation taxa exist."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

import pandas as pd

from .candidate_outer_fold_evidence import require_complete_outer_fold_evidence
from .niche_recovery_selection import RECOVERY_DIRECTIONS, select_generalization_gated_niche_recovery_protocol
from .product_b_v2_known_truth_contract import M_SPECS, load_product_b_v2_known_truth_contract

ContractLoader = Callable[[str | Path], dict]


def freeze_product_b_v2_method(
    *,
    contract_path: str | Path,
    worker_root: str | Path,
    output_dir: str | Path,
    contract_loader: ContractLoader = load_product_b_v2_known_truth_contract,
) -> dict[str, object]:
    contract = contract_loader(contract_path)
    root = Path(worker_root)
    contracts: list[dict[str, object]] = []
    frames: list[pd.DataFrame] = []
    for path in sorted(root.rglob("contract.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("purpose") != "product_b_v2_known_truth_method_freeze_shard":
            continue
        if row.get("contract_sha256") != contract["contract_sha256"]:
            raise ValueError("method-freeze shard contract mismatch")
        for key in (
            "generating_truth_read",
            "product_b_evaluation_taxa_simulated_or_read",
            "real_empirical_data_read",
            "empirical_sealed_outcomes_read",
        ):
            if row.get(key) is not False:
                raise ValueError(f"method-freeze barrier violated: {key}")
        metrics = pd.read_csv(path.parent / "base_fold_metrics.csv")
        if metrics.empty:
            raise ValueError(f"empty method-freeze metrics: {path.parent}")
        contracts.append(row)
        frames.append(metrics)
    expected_taxa = tuple(contract["method_freeze_taxon_names"])
    expected_keys = {(taxon, m) for taxon in expected_taxa for m in M_SPECS}
    observed_keys = {(str(x["taxon"]), str(x["M"])) for x in contracts}
    if observed_keys != expected_keys or len(contracts) != len(expected_keys):
        raise ValueError("method-freeze taxon x M denominator is incomplete")

    metrics = pd.concat(frames, ignore_index=True)
    required_metrics = ("presence_rank", *tuple(RECOVERY_DIRECTIONS))
    complete = require_complete_outer_fold_evidence(
        metrics,
        discovery_taxa=expected_taxa,
        perturbations=M_SPECS,
        required_columns=required_metrics,
        expected_outer_folds=int(contract["simulation_contract"]["outer_folds"]),
    )
    if not complete.eligible_candidates:
        raise ValueError("no Product-A candidate has complete method-freeze evidence")
    complete_metrics = metrics.loc[
        metrics["candidate"].astype(str).isin(complete.eligible_candidates)
    ].copy()
    adequacy = contract["method_freeze"]["prediction_adequacy"]
    selection = select_generalization_gated_niche_recovery_protocol(
        complete_metrics,
        chance_auc=float(adequacy["chance_auc"]),
        minimum_auc_margin=float(adequacy["minimum_auc_margin"]),
        auc_sem_multiplier=float(adequacy["auc_sem_multiplier"]),
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    complete.cell_ledger.to_csv(out / "complete_cell_ledger.csv", index=False)
    complete.candidate_summary.to_csv(out / "complete_candidate_summary.csv", index=False)
    selection.gate_summary.to_csv(out / "prediction_adequacy_gate.csv", index=False)
    selection.recovery_selection.summary.to_csv(out / "ecological_selection.csv", index=False)
    result = {
        "purpose": "product_b_v2_frozen_product_a_method_pretruth",
        "source_contract_sha256": contract["contract_sha256"],
        "frozen_candidate": str(selection.candidate),
        "eligible_generalization_candidates": list(selection.eligible_candidates),
        "method_freeze_taxa": list(expected_taxa),
        "n_method_freeze_shards": len(contracts),
        "generating_truth_read": False,
        "product_b_evaluation_taxa_simulated_or_read": False,
        "candidate_frozen_before_product_b_evaluation_taxa": True,
        "real_empirical_data_read": False,
        "empirical_sealed_outcomes_read": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--worker-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    freeze_product_b_v2_method(
        contract_path=args.contract, worker_root=args.worker_root, output_dir=args.output_dir
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
