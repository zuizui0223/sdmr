"""Mechanical Product-A v2.6 promotion gate for the pagination-safe continuation v2."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .v2_6_promotion_product_b_unblock import _a_known_truth

PURPOSE = "product_a_v2_6_continuation_v2_promotion_preoutcome_contract"
EXPECTED_KNOWN_TRUTH = {
    "run_id": 32251711573,
    "head_sha": "715f62ef453636e0e60a4a04d3fa71fdbfdf57a9",
    "artifact_id": 9364873176,
    "artifact_digest": "sha256:78cda9c4c1e8a0ddab8371bf324d214cc9b8a76d1ebd65ad562da6de5913e3ba",
    "artifact_name": "product-a-v2-6-fresh-validation-decision",
    "expected_purpose": "product_a_v2_6_predeclared_fresh_validation_decision",
    "required_decision": "v2_6_supported",
}
EXPECTED_EMPIRICAL = {
    "implementation_sha": "d560076793199b5486b7d2c678eeb4b4c551a81f",
    "frozen_ref": "frozen/product-a-v2-6-continuation-v2-d5600767",
    "workflow_file": "product-a-v2-6-empirical-presealed-continuation-v2.yml",
    "artifact_name": "product-a-v2-6-independent-empirical-confirmation-decision-continuation-v2",
    "expected_purpose": "product_a_v2_6_independent_empirical_confirmation_decision",
    "required_decision": "empirical_confirmation_supported",
    "requires_single_workflow_dispatch_run_for_frozen_source": True,
    "source_presealed_run_id": 32323931807,
    "source_presealed_head_sha": "7f79dd10f312c42168f0d80496c7299d0e629cad",
    "failed_predecessor_continuation_run_id": 32434610154,
    "failed_predecessor_pretruth_artifacts": 0,
    "failed_predecessor_sealed_audit_artifacts": 0,
    "failed_predecessor_sealed_environment_opened": False,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_continuation_v2_promotion_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != PURPOSE:
        raise ValueError("Product-A continuation v2 promotion purpose changed")
    if payload.get("contract_frozen_before_continuation_v2_sealed_outcome") is not True:
        raise ValueError("continuation v2 promotion was not frozen before sealed outcome")
    if payload.get("new_postoutcome_scientific_thresholds") is not False:
        raise ValueError("continuation v2 promotion cannot add post-outcome thresholds")
    if payload.get("known_truth_source") != EXPECTED_KNOWN_TRUTH:
        raise ValueError("known-truth source changed")
    if payload.get("independent_empirical_continuation_v2_source") != EXPECTED_EMPIRICAL:
        raise ValueError("continuation v2 empirical source changed")
    rule = payload.get("promotion_rule", {})
    if rule.get("logic") != "known_truth_supported_and_independent_empirical_continuation_v2_supported":
        raise ValueError("continuation v2 promotion logic changed")
    for key in (
        "requires_known_truth_support",
        "requires_empirical_prediction_guardrail",
        "requires_empirical_ecological_support",
        "requires_empirical_process_reproducibility_support",
        "requires_no_post_sealed_retuning",
        "requires_all_information_barriers",
        "adds_no_new_metric_threshold",
    ):
        if rule.get(key) is not True:
            raise ValueError(f"continuation v2 promotion rule requires {key}=true")
    failure = payload.get("failure_semantics", {})
    if failure.get("threshold_relaxation_after_outcome_forbidden") is not True:
        raise ValueError("threshold relaxation after continuation v2 outcome must remain forbidden")
    payload["contract_sha256"] = _sha256(source)
    return payload


def _load_contract(root: Path) -> dict[str, Any]:
    return json.loads((root / "contract.json").read_text(encoding="utf-8"))


def _single_decision(root: Path) -> pd.Series:
    frame = pd.read_csv(root / "decision.csv")
    if len(frame) != 1:
        raise ValueError("continuation v2 decision artifact must contain exactly one row")
    return frame.iloc[0]


def _empirical_continuation_v2(root: Path) -> tuple[bool, dict[str, Any], pd.Series]:
    contract = _load_contract(root)
    row = _single_decision(root)
    if contract.get("purpose") != EXPECTED_EMPIRICAL["expected_purpose"]:
        raise ValueError("continuation v2 empirical purpose mismatch")
    if str(contract.get("decision")) != str(row["decision"]):
        raise ValueError("continuation v2 contract/CSV decision mismatch")
    if int(contract.get("n_parts", -1)) != 6:
        raise ValueError("continuation v2 empirical decision must contain six parts")
    for key in (
        "known_truth_thresholds_retuned_from_empirical_outcomes",
        "empirical_thresholds_retuned_after_sealed_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if contract.get(key) is not False:
            raise ValueError(f"continuation v2 empirical source requires {key}=false")
    supported = str(row["decision"]) == EXPECTED_EMPIRICAL["required_decision"]
    if supported:
        for column in (
            "all_empirical_evidence_available",
            "prediction_guardrail",
            "ecological_support",
            "process_reproducibility_support",
        ):
            if not bool(row[column]):
                raise ValueError(f"supported continuation v2 decision lacks {column}=true")
    return supported, contract, row


def apply_continuation_v2_promotion(
    *,
    contract_path: str | Path,
    known_truth_dir: str | Path,
    empirical_continuation_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    config = load_continuation_v2_promotion_contract(contract_path)
    kt_ok, kt = _a_known_truth(Path(known_truth_dir))
    emp_ok, emp, emp_row = _empirical_continuation_v2(Path(empirical_continuation_dir))
    promoted = bool(kt_ok and emp_ok)
    decision = "product_a_v2_6_promoted" if promoted else "product_a_v2_6_not_promoted"
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "decision": decision,
        "known_truth_supported": kt_ok,
        "independent_empirical_continuation_v2_supported": emp_ok,
        "product_a_v2_6_promoted": promoted,
        "empirical_prediction_guardrail": bool(emp_row.get("prediction_guardrail", False)),
        "empirical_ecological_support": bool(emp_row.get("ecological_support", False)),
        "empirical_process_reproducibility_support": bool(emp_row.get("process_reproducibility_support", False)),
        "new_postoutcome_scientific_thresholds": False,
        "fundamental_niche_claim_allowed": False,
        "causal_physiological_driver_claim_allowed": False,
    }]).to_csv(out / "decision.csv", index=False)
    (out / "promoted_product_a_v2_6_protocol.json").write_text(json.dumps({
        "purpose": "promoted_product_a_v2_6_protocol",
        "promotion_contract_sha256": config["contract_sha256"],
        "promoted": promoted,
        "product": config["promoted_product_identity"],
        "known_truth_source": EXPECTED_KNOWN_TRUTH,
        "empirical_continuation_v2_source": EXPECTED_EMPIRICAL,
        "known_truth_decision": str(kt.get("decision")),
        "empirical_decision": str(emp.get("decision")),
        "new_postoutcome_scientific_thresholds": False,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = {
        "purpose": "product_a_v2_6_continuation_v2_promotion_decision",
        "promotion_contract_sha256": config["contract_sha256"],
        "decision": decision,
        "product_a_v2_6_promoted": promoted,
        "product_b_empirical_use_unblocked": False,
        "new_postoutcome_scientific_thresholds": False,
        "threshold_relaxation_after_outcome": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--known-truth-dir", required=True)
    parser.add_argument("--empirical-continuation-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    apply_continuation_v2_promotion(
        contract_path=args.contract,
        known_truth_dir=args.known_truth_dir,
        empirical_continuation_dir=args.empirical_continuation_dir,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
