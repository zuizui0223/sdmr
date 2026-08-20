"""Open fresh generating process truth only after Product-B v2 pretruth freeze."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .product_b_v2_known_truth_contract import load_product_b_v2_known_truth_contract


def _true_processes(family: str) -> set[str]:
    true = {"temperature", "water"}
    if str(family) == "omitted_driver":
        true.add("soil")
    return true


def audit_product_b_v2_known_truth(
    *, contract_path: str | Path, pretruth_dir: str | Path, output_dir: str | Path
) -> dict[str, object]:
    contract = load_product_b_v2_known_truth_contract(contract_path)
    root = Path(pretruth_dir)
    frozen = json.loads((root / "contract.json").read_text(encoding="utf-8"))
    if frozen.get("purpose") != "product_b_v2_known_truth_process_core_pretruth_freeze":
        raise ValueError("truth audit requires frozen Product-B process core")
    if frozen.get("source_contract_sha256") != contract["contract_sha256"]:
        raise ValueError("truth audit contract mismatch")
    if frozen.get("process_losses_frozen_before_generating_truth_audit") is not True:
        raise ValueError("process losses were not frozen before truth")
    if frozen.get("generating_truth_read") is not False:
        raise ValueError("pretruth artifact already opened generating truth")
    if frozen.get("scientific_threshold_tuning_performed") is not False:
        raise ValueError("pretruth artifact tuned scientific thresholds")

    summary = pd.read_csv(root / "taxon_process_summary.csv")
    stability = pd.read_csv(root / "process_stability.csv")
    specs = contract["product_b_evaluation_taxa"]
    family_by_taxon = {
        f"{x['family']}__seed{int(x['seed'])}": str(x["family"])
        for x in specs
    }
    expected_taxa = set(contract["product_b_evaluation_taxon_names"])
    if set(summary["taxon"].astype(str)) != expected_taxa:
        raise ValueError("truth audit taxon denominator changed")
    processes = tuple(contract["ecological_process_universe"])

    truth_rows: list[dict[str, object]] = []
    taxon_rows: list[dict[str, object]] = []
    for taxon in sorted(expected_taxa):
        family = family_by_taxon[taxon]
        true = _true_processes(family)
        cell = summary.loc[summary["taxon"].astype(str).eq(taxon)].copy()
        if set(cell["process_domain"].astype(str)) != set(processes):
            raise ValueError(f"process denominator changed for {taxon}")
        inferred = set(
            cell.loc[cell["status"].astype(str).eq("supported_process_constraint"), "process_domain"].astype(str)
        )
        tp = len(inferred & true)
        fp = len(inferred - true)
        fn = len(true - inferred)
        precision = float(tp / len(inferred)) if inferred else 0.0
        recall = float(tp / len(true)) if true else float("nan")
        taxon_rows.append({
            "taxon": taxon,
            "family": family,
            "true_processes": ",".join(sorted(true)),
            "inferred_processes": ",".join(sorted(inferred)),
            "true_positive_processes": tp,
            "false_positive_processes": fp,
            "false_negative_processes": fn,
            "process_precision": precision,
            "process_recall": recall,
        })
        status_by_process = dict(zip(cell["process_domain"].astype(str), cell["status"].astype(str), strict=True))
        for process in processes:
            truth_rows.append({
                "taxon": taxon,
                "family": family,
                "process_domain": process,
                "true_process": process in true,
                "inferred_supported_constraint": status_by_process[process] == "supported_process_constraint",
                "inferred_status": status_by_process[process],
            })

    taxon_audit = pd.DataFrame(taxon_rows)
    truth_table = pd.DataFrame(truth_rows)
    stable_threshold = float(contract["supported_result_requires"]["stable_core_threshold"])
    stable = set(
        stability.loc[
            pd.to_numeric(stability["validation_confirmation_stability"], errors="coerce") >= stable_threshold - 1e-12,
            "process_domain",
        ].astype(str)
    )
    expected_universal = set(contract["known_truth_expectation"]["universal_processes"])
    universal_tp = len(stable & expected_universal)
    universal_recall = float(universal_tp / len(expected_universal))
    false_stable = sorted(stable - expected_universal)
    universal_precision = float(universal_tp / len(stable)) if stable else 0.0
    mean_recall = float(pd.to_numeric(taxon_audit["process_recall"], errors="coerce").mean())
    mean_precision = float(pd.to_numeric(taxon_audit["process_precision"], errors="coerce").mean())

    soil = truth_table.loc[truth_table["process_domain"].astype(str).eq("soil")].copy()
    omitted = soil["family"].astype(str).eq("omitted_driver")
    soil_omitted_support = float(soil.loc[omitted, "inferred_supported_constraint"].astype(bool).mean())
    soil_non_omitted_support = float(soil.loc[~omitted, "inferred_supported_constraint"].astype(bool).mean())

    required = contract["supported_result_requires"]
    supported = bool(
        frozen.get("all_M_x_fold_evidence_complete") is True
        and universal_recall >= float(required["universal_process_recall"]) - 1e-12
        and len(false_stable) <= int(required["false_stable_universal_processes"])
        and mean_recall >= float(required["mean_taxon_process_recall_minimum"]) - 1e-12
        and mean_precision >= float(required["mean_taxon_process_precision_minimum"]) - 1e-12
    )
    decision = "product_b_v2_known_truth_supported" if supported else "product_b_v2_known_truth_not_supported"
    next_action = (
        "retain engine and await explicit Product-A empirical promotion before any empirical Product-B claim"
        if supported
        else "diagnose Product-B process-recovery failures on known truth before empirical Product-B use"
    )
    decision_frame = pd.DataFrame([{
        "decision": decision,
        "stable_universal_core": ",".join(sorted(stable)),
        "expected_universal_processes": ",".join(sorted(expected_universal)),
        "universal_process_recall": universal_recall,
        "universal_process_precision": universal_precision,
        "false_stable_universal_processes": len(false_stable),
        "false_stable_process_names": ",".join(false_stable),
        "mean_taxon_process_recall": mean_recall,
        "mean_taxon_process_precision": mean_precision,
        "soil_support_fraction_omitted_driver": soil_omitted_support,
        "soil_support_fraction_non_omitted": soil_non_omitted_support,
        "next_action": next_action,
    }])

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    truth_table.to_csv(out / "process_truth_table.csv", index=False)
    taxon_audit.to_csv(out / "taxon_truth_audit.csv", index=False)
    stability.to_csv(out / "pretruth_process_stability.csv", index=False)
    decision_frame.to_csv(out / "decision.csv", index=False)
    result = {
        "purpose": "product_b_v2_fresh_known_truth_decision",
        "source_contract_sha256": contract["contract_sha256"],
        "decision": decision,
        "generating_process_truth_opened_after_pretruth_freeze": True,
        "process_losses_frozen_before_generating_truth_audit": True,
        "thresholds_retuned_after_truth": False,
        "real_empirical_data_read": False,
        "empirical_sealed_outcomes_read": False,
        "product_b_formally_unblocked": False,
        "scientific_empirical_product_b_claim_allowed": False,
        "next_action": next_action,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--pretruth-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    audit_product_b_v2_known_truth(
        contract_path=args.contract, pretruth_dir=args.pretruth_dir, output_dir=args.output_dir
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
