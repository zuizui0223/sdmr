"""Mechanical formal-unblock gate for Product-B v3.

No ecological threshold is introduced here. Product B can be formally unblocked
only when the separately frozen Product-A continuation promotion decision is
positive and the exact frozen Product-B v3 fresh known-truth decision is positive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

PURPOSE = "product_b_v3_formal_unblock_preoutcome_contract"
EXPECTED_A = {
    "implementation_sha": "247857614d3844d44a390027c6f06fabb990a38d",
    "frozen_ref": "frozen/product-a-v2-6-continuation-promotion-24785761",
    "workflow_file": "product-a-v2-6-continuation-promotion.yml",
    "artifact_name": "product-a-v2-6-continuation-promotion-decision",
    "expected_purpose": "product_a_v2_6_continuation_promotion_decision",
    "required_decision": "product_a_v2_6_promoted",
    "requires_single_workflow_dispatch_run_for_frozen_source": True,
    "underlying_empirical_continuation_sha": "da421c88717b193a1c1046c4d6920e841a4b7584",
    "underlying_empirical_continuation_ref": "frozen/product-a-v2-6-presealed-continuation-da421c88",
}
EXPECTED_B = {
    "implementation_sha": "06350e55541f3ae0d846985edb196b68c536e2ab",
    "frozen_ref": "frozen/product-b-v3-06350e55",
    "workflow_file": "product-b-v3-known-truth.yml",
    "artifact_name": "product-b-v3-fresh-known-truth-decision",
    "expected_purpose": "product_b_v3_fresh_known_truth_decision",
    "required_decision": "product_b_v3_known_truth_supported",
    "requires_single_workflow_dispatch_run_for_frozen_source": True,
    "opened_generating_truth_seed_maximum_before_run": 523,
    "fresh_evaluation_seeds": list(range(701, 713)),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_product_b_v3_unblock_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != PURPOSE:
        raise ValueError("Product-B v3 formal-unblock purpose changed")
    for key in (
        "contract_frozen_before_product_a_continuation_sealed_outcome",
        "contract_frozen_before_product_b_v3_known_truth_outcome",
    ):
        if payload.get(key) is not True:
            raise ValueError(f"Product-B v3 unblock contract requires {key}=true")
    if payload.get("new_postoutcome_scientific_thresholds") is not False:
        raise ValueError("Product-B v3 unblock cannot add post-outcome thresholds")
    if payload.get("product_a_promotion_source") != EXPECTED_A:
        raise ValueError("Product-A promotion source changed")
    if payload.get("product_b_v3_known_truth_source") != EXPECTED_B:
        raise ValueError("Product-B v3 known-truth source changed")
    rule = payload.get("unblock_rule", {})
    if rule.get("logic") != "product_a_v2_6_promoted_and_product_b_v3_known_truth_supported":
        raise ValueError("Product-B v3 unblock logic changed")
    for key in (
        "requires_product_a_promotion",
        "requires_product_b_v3_known_truth_support",
        "requires_zero_posttruth_retuning",
        "adds_no_new_metric_threshold",
    ):
        if rule.get(key) is not True:
            raise ValueError(f"Product-B v3 unblock rule requires {key}=true")
    if payload.get("failure_semantics", {}).get("threshold_relaxation_after_outcome_forbidden") is not True:
        raise ValueError("threshold relaxation after outcome must remain forbidden")
    identity = payload.get("unblocked_product_identity", {})
    if identity.get("weighted_super_score") is not False or identity.get("presence_rank_role") != "guardrail_only":
        raise ValueError("Product-B v3 identity changed")
    payload["contract_sha256"] = _sha(source)
    return payload


def _contract(root: Path) -> dict[str, Any]:
    return json.loads((root / "contract.json").read_text(encoding="utf-8"))


def _decision(root: Path) -> pd.Series:
    frame = pd.read_csv(root / "decision.csv")
    if len(frame) != 1:
        raise ValueError("source decision artifact must contain exactly one row")
    return frame.iloc[0]


def _product_a_promoted(root: Path) -> tuple[bool, dict[str, Any], pd.Series]:
    contract = _contract(root); row = _decision(root)
    if contract.get("purpose") != EXPECTED_A["expected_purpose"]:
        raise ValueError("Product-A promotion purpose mismatch")
    if str(contract.get("decision")) != str(row["decision"]):
        raise ValueError("Product-A promotion contract/CSV mismatch")
    if contract.get("new_postoutcome_scientific_thresholds") is not False:
        raise ValueError("Product-A promotion added post-outcome thresholds")
    if contract.get("threshold_relaxation_after_outcome") is not False:
        raise ValueError("Product-A promotion relaxed thresholds")
    if contract.get("product_b_empirical_use_unblocked") is not False:
        raise ValueError("Product-A promotion improperly unblocked Product B")
    promoted = str(row["decision"]) == EXPECTED_A["required_decision"]
    if promoted and not bool(row.get("product_a_v2_6_promoted", False)):
        raise ValueError("Product-A promoted decision lacks promoted=true")
    return promoted, contract, row


def _product_b_supported(root: Path) -> tuple[bool, dict[str, Any], pd.Series]:
    contract = _contract(root); row = _decision(root)
    if contract.get("purpose") != EXPECTED_B["expected_purpose"]:
        raise ValueError("Product-B v3 known-truth purpose mismatch")
    if str(contract.get("decision")) != str(row["decision"]):
        raise ValueError("Product-B v3 contract/CSV mismatch")
    for key in (
        "generating_process_truth_opened_after_pretruth_freeze",
        "process_losses_frozen_before_generating_truth_audit",
    ):
        if contract.get(key) is not True:
            raise ValueError(f"Product-B v3 known-truth barrier failed: {key}")
    for key in (
        "thresholds_retuned_after_truth",
        "real_empirical_data_read",
        "empirical_sealed_outcomes_read",
        "product_b_formally_unblocked",
        "scientific_empirical_product_b_claim_allowed",
    ):
        if contract.get(key) is not False:
            raise ValueError(f"Product-B v3 known-truth source requires {key}=false")
    if contract.get("product_a_representative_available_before_process_audit") is not True:
        raise ValueError("Product-B v3 truth audit lacks Product-A representative provenance")
    supported = str(row["decision"]) == EXPECTED_B["required_decision"]
    return supported, contract, row


def apply_product_b_v3_unblock(
    *, contract_path: str | Path, product_a_promotion_dir: str | Path,
    product_b_known_truth_dir: str | Path, output_dir: str | Path,
) -> dict[str, Any]:
    config = load_product_b_v3_unblock_contract(contract_path)
    a_ok, a_contract, a_row = _product_a_promoted(Path(product_a_promotion_dir))
    b_ok, b_contract, b_row = _product_b_supported(Path(product_b_known_truth_dir))
    unblocked = bool(a_ok and b_ok)
    if unblocked:
        decision = "product_b_v3_formally_unblocked"
    elif a_ok:
        decision = "product_a_v2_6_promoted_product_b_v3_blocked"
    else:
        decision = "product_a_v2_6_not_promoted_product_b_v3_blocked"
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "decision": decision,
        "product_a_v2_6_promoted": a_ok,
        "product_b_v3_known_truth_supported": b_ok,
        "product_b_v3_formally_unblocked": unblocked,
        "new_postoutcome_scientific_thresholds": False,
        "fundamental_niche_claim_allowed": False,
        "causal_physiological_driver_claim_allowed": False,
    }]).to_csv(out / "decision.csv", index=False)
    unblock = {
        "purpose": "product_b_v3_formal_unblock_contract",
        "unblocked": unblocked,
        "unblock_contract_sha256": config["contract_sha256"],
        "product": config["unblocked_product_identity"],
        "product_a_promotion_source": EXPECTED_A,
        "product_b_known_truth_source": EXPECTED_B,
        "product_a_promotion_decision": str(a_contract.get("decision")),
        "product_b_known_truth_decision": str(b_contract.get("decision")),
        "known_truth_universal_process_recall": float(b_row.get("universal_process_recall", float("nan"))),
        "known_truth_mean_taxon_process_precision": float(b_row.get("mean_taxon_process_precision", float("nan"))),
        "empirical_product_b_execution_allowed": unblocked,
        "new_postoutcome_scientific_thresholds": False,
    }
    (out / "product_b_v3_formal_unblock_contract.json").write_text(json.dumps(unblock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = {
        "purpose": "product_b_v3_formal_unblock_decision",
        "unblock_contract_sha256": config["contract_sha256"],
        "decision": decision,
        "product_a_v2_6_promoted": a_ok,
        "product_b_v3_known_truth_supported": b_ok,
        "product_b_v3_formally_unblocked": unblocked,
        "new_postoutcome_scientific_thresholds": False,
        "threshold_relaxation_after_outcome": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--product-a-promotion-dir", required=True)
    parser.add_argument("--product-b-known-truth-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    apply_product_b_v3_unblock(
        contract_path=args.contract,
        product_a_promotion_dir=args.product_a_promotion_dir,
        product_b_known_truth_dir=args.product_b_known_truth_dir,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
