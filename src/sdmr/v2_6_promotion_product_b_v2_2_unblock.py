"""Mechanical Product-A v2.6 promotion and Product-B v2.2 unblock gate.

This gate adds no ecological threshold. It composes only decisions whose
scientific criteria and exact source identities were frozen before outcomes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .v2_6_promotion_product_b_unblock import (
    EXPECTED_A_EMP,
    EXPECTED_A_KT,
    _a_empirical,
    _a_known_truth,
    _contract,
    _sha256,
    _single_decision,
)

PURPOSE = "product_a_v2_6_promotion_and_product_b_v2_2_unblock_preoutcome_contract"
EXPECTED_B_KT = {
    "version": "v2.2",
    "implementation_sha": "88580599bdb278273ea80fc039fd2204f5aac8a6",
    "frozen_ref": "frozen/product-b-v2-2-88580599",
    "workflow_file": "product-b-v2-2-known-truth.yml",
    "artifact_name": "product-b-v2-2-fresh-known-truth-decision",
    "expected_purpose": "product_b_v2_2_fresh_known_truth_decision",
    "required_decision": "product_b_v2_known_truth_supported",
    "requires_single_run_for_frozen_source": True,
    "predecessor_run_id": 32356754388,
    "predecessor_failure_stage": "process_shard",
    "predecessor_generating_truth_opened": False,
}


def load_promotion_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != PURPOSE:
        raise ValueError("Product-B v2.2 promotion/unblock purpose changed")
    for key in (
        "contract_frozen_before_empirical_product_a_outcome",
        "contract_frozen_before_product_b_v2_2_known_truth_outcome",
        "product_b_v2_2_source_frozen_before_outcome",
    ):
        if payload.get(key) is not True:
            raise ValueError(f"promotion contract requires {key}=true")
    if payload.get("new_postoutcome_scientific_thresholds") is not False:
        raise ValueError("promotion gate cannot add post-outcome thresholds")
    if payload.get("known_truth_product_a_source") != EXPECTED_A_KT:
        raise ValueError("known-truth Product-A source changed")
    if payload.get("independent_empirical_product_a_source") != EXPECTED_A_EMP:
        raise ValueError("independent empirical Product-A source changed")
    if payload.get("fresh_known_truth_product_b_v2_2_source") != EXPECTED_B_KT:
        raise ValueError("fresh known-truth Product-B v2.2 source changed")

    a_rule = payload.get("product_a_promotion_rule", {})
    if a_rule.get("logic") != "all_required_predeclared_decisions_supported":
        raise ValueError("Product-A promotion logic changed")
    for key in (
        "requires_known_truth_product_a_support",
        "requires_independent_empirical_product_a_support",
        "requires_empirical_prediction_guardrail",
        "requires_empirical_ecological_support",
        "requires_empirical_process_reproducibility_support",
        "requires_no_post_sealed_retuning",
        "requires_all_information_barriers",
        "adds_no_new_metric_threshold",
    ):
        if a_rule.get(key) is not True:
            raise ValueError(f"Product-A promotion rule requires {key}=true")

    b_rule = payload.get("product_b_v2_2_unblock_rule", {})
    if b_rule.get("logic") != "product_a_promoted_and_product_b_v2_2_fresh_known_truth_supported":
        raise ValueError("Product-B v2.2 unblock logic changed")
    for key in (
        "requires_product_a_v2_6_promotion",
        "requires_product_b_v2_2_known_truth_support",
        "requires_zero_posttruth_retuning",
        "adds_no_new_metric_threshold",
    ):
        if b_rule.get(key) is not True:
            raise ValueError(f"Product-B v2.2 unblock rule requires {key}=true")
    if payload.get("failure_semantics", {}).get("threshold_relaxation_after_failure_forbidden") is not True:
        raise ValueError("threshold relaxation after failure must remain forbidden")
    payload["contract_sha256"] = _sha256(source)
    return payload


def _b_known_truth(root: Path) -> tuple[bool, dict[str, Any], pd.Series]:
    c = _contract(root)
    row = _single_decision(root)
    if c.get("purpose") != EXPECTED_B_KT["expected_purpose"]:
        raise ValueError("Product-B v2.2 known-truth purpose mismatch")
    if str(c.get("decision")) != str(row["decision"]):
        raise ValueError("Product-B v2.2 contract/CSV decision mismatch")
    for key in (
        "generating_process_truth_opened_after_pretruth_freeze",
        "process_losses_frozen_before_generating_truth_audit",
    ):
        if c.get(key) is not True:
            raise ValueError(f"Product-B v2.2 information barrier failed: {key}")
    for key in (
        "thresholds_retuned_after_truth",
        "real_empirical_data_read",
        "empirical_sealed_outcomes_read",
        "product_b_formally_unblocked",
        "scientific_empirical_product_b_claim_allowed",
    ):
        if c.get(key) is not False:
            raise ValueError(f"Product-B v2.2 source requires {key}=false")
    return str(row["decision"]) == EXPECTED_B_KT["required_decision"], c, row


def apply_promotion_and_unblock(
    *,
    contract_path: str | Path,
    product_a_known_truth_dir: str | Path,
    product_a_empirical_dir: str | Path,
    product_b_known_truth_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    config = load_promotion_contract(contract_path)
    a_kt_ok, a_kt = _a_known_truth(Path(product_a_known_truth_dir))
    a_emp_ok, a_emp, a_emp_row = _a_empirical(Path(product_a_empirical_dir))
    b_kt_ok, b_kt, b_row = _b_known_truth(Path(product_b_known_truth_dir))

    product_a_promoted = bool(a_kt_ok and a_emp_ok)
    product_b_unblocked = bool(product_a_promoted and b_kt_ok)
    if product_b_unblocked:
        overall = "product_a_v2_6_promoted_product_b_v2_2_unblocked"
    elif product_a_promoted:
        overall = "product_a_v2_6_promoted_product_b_v2_2_blocked"
    else:
        overall = "product_a_v2_6_not_promoted_product_b_v2_2_blocked"

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "decision": overall,
        "product_a_known_truth_supported": a_kt_ok,
        "product_a_empirical_supported": a_emp_ok,
        "product_a_v2_6_promoted": product_a_promoted,
        "product_b_v2_2_known_truth_supported": b_kt_ok,
        "product_b_v2_2_unblocked": product_b_unblocked,
        "new_postoutcome_scientific_thresholds": False,
        "fundamental_niche_claim_allowed": False,
        "causal_physiological_driver_claim_allowed": False,
    }]).to_csv(out / "decision.csv", index=False)

    (out / "promoted_product_a_v2_6_protocol.json").write_text(json.dumps({
        "purpose": "promoted_product_a_v2_6_protocol",
        "promotion_contract_sha256": config["contract_sha256"],
        "promoted": product_a_promoted,
        "product": config["promoted_product_a_identity"],
        "known_truth_source": EXPECTED_A_KT,
        "empirical_source": EXPECTED_A_EMP,
        "known_truth_decision": str(a_kt.get("decision")),
        "empirical_decision": str(a_emp.get("decision")),
        "empirical_prediction_guardrail": bool(a_emp_row.get("prediction_guardrail", False)),
        "empirical_ecological_support": bool(a_emp_row.get("ecological_support", False)),
        "empirical_process_reproducibility_support": bool(a_emp_row.get("process_reproducibility_support", False)),
        "new_postoutcome_scientific_thresholds": False,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    (out / "product_b_v2_2_formal_unblock_contract.json").write_text(json.dumps({
        "purpose": "product_b_v2_2_formal_unblock_contract",
        "promotion_contract_sha256": config["contract_sha256"],
        "unblocked": product_b_unblocked,
        "product": config["unblocked_product_b_identity"],
        "product_a_v2_6_promoted": product_a_promoted,
        "product_b_v2_2_known_truth_supported": b_kt_ok,
        "product_b_known_truth_source": EXPECTED_B_KT,
        "product_b_known_truth_decision": str(b_kt.get("decision")),
        "known_truth_universal_process_recall": float(b_row.get("universal_process_recall", float("nan"))),
        "known_truth_mean_taxon_process_precision": float(b_row.get("mean_taxon_process_precision", float("nan"))),
        "new_postoutcome_scientific_thresholds": False,
        "empirical_product_b_execution_allowed": product_b_unblocked,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = {
        "purpose": "product_a_v2_6_promotion_and_product_b_v2_2_unblock_decision",
        "promotion_contract_sha256": config["contract_sha256"],
        "decision": overall,
        "product_a_v2_6_promoted": product_a_promoted,
        "product_b_v2_2_unblocked": product_b_unblocked,
        "new_postoutcome_scientific_thresholds": False,
        "threshold_relaxation_after_failure": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--product-a-known-truth-dir", required=True)
    parser.add_argument("--product-a-empirical-dir", required=True)
    parser.add_argument("--product-b-known-truth-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    apply_promotion_and_unblock(
        contract_path=args.contract,
        product_a_known_truth_dir=args.product_a_known_truth_dir,
        product_a_empirical_dir=args.product_a_empirical_dir,
        product_b_known_truth_dir=args.product_b_known_truth_dir,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
