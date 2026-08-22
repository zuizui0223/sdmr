"""Mechanical pre-outcome promotion gate for Product-A v2.7.1.

This module adds no scientific threshold.  It maps the already frozen predecessor
known-truth support and the exact fresh taxon-holdout empirical decision onto a
claim-bounded Product-A promotion state.  Product-B remains a separate gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .v2_6_promotion_product_b_unblock import _a_known_truth

PURPOSE = "product_a_v2_7_1_fresh_promotion_preoutcome_contract"
EXPECTED_KNOWN_TRUTH = {
    "run_id": 32251711573,
    "head_sha": "715f62ef453636e0e60a4a04d3fa71fdbfdf57a9",
    "artifact_id": 9364873176,
    "artifact_digest": "sha256:78cda9c4c1e8a0ddab8371bf324d214cc9b8a76d1ebd65ad562da6de5913e3ba",
    "artifact_name": "product-a-v2-6-fresh-validation-decision",
    "expected_purpose": "product_a_v2_6_predeclared_fresh_validation_decision",
    "required_decision": "v2_6_supported",
    "role": "predecessor_method_known_truth_support_not_direct_validation_of_v2_7_1_partition",
}
EXPECTED_FRESH = {
    "run_id": 32552745281,
    "implementation_sha": "1f158006c0b5dbdd93af70632464727405ababfe",
    "frozen_ref": "frozen/product-a-v2-7-1-fresh-confirmation-1f158006",
    "workflow_file": "product-a-v2-7-1-fresh-confirmation.yml",
    "artifact_name": "product-a-v2-7-1-fresh-taxon-holdout-confirmation-decision",
    "expected_purpose": "product_a_v2_7_1_fresh_taxon_holdout_empirical_confirmation_decision",
    "required_decision": "empirical_confirmation_supported",
    "requires_single_workflow_dispatch_run_for_frozen_identity": True,
    "independence_axis": "taxon_holdout_not_temporal",
    "sealed_audit_artifacts_observed_before_contract": 0,
    "decision_artifacts_observed_before_contract": 0,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_fresh_promotion_contract(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("purpose") != PURPOSE:
        raise ValueError("fresh v2.7.1 promotion purpose changed")
    if payload.get("contract_frozen_before_fresh_sealed_outcome") is not True:
        raise ValueError("fresh promotion contract must be frozen before sealed outcome")
    if payload.get("new_postoutcome_scientific_thresholds") is not False:
        raise ValueError("fresh promotion cannot add post-outcome thresholds")
    if payload.get("inherited_known_truth_source") != EXPECTED_KNOWN_TRUTH:
        raise ValueError("fresh promotion predecessor known-truth source changed")
    if payload.get("fresh_taxon_holdout_source") != EXPECTED_FRESH:
        raise ValueError("fresh promotion empirical source changed")
    rule = payload.get("promotion_rule", {})
    if rule.get("logic") != "inherited_known_truth_supported_and_exact_fresh_taxon_holdout_supported":
        raise ValueError("fresh promotion logic changed")
    for key in (
        "requires_inherited_known_truth_support",
        "requires_all_6_fresh_parts_available",
        "requires_fresh_prediction_guardrail",
        "requires_fresh_ecological_support",
        "requires_fresh_process_reproducibility_support",
        "requires_no_post_sealed_retuning",
        "requires_no_post_outcome_candidate_reselection",
        "requires_all_information_barriers",
        "adds_no_new_metric_threshold",
    ):
        if rule.get(key) is not True:
            raise ValueError(f"fresh promotion rule requires {key}=true")
    mapping = payload.get("state_mapping", {})
    if mapping != {
        "empirical_confirmation_supported": "product_a_v2_7_1_promoted",
        "empirical_confirmation_not_supported": "product_a_v2_7_1_not_promoted",
        "empirical_confirmation_unavailable": "product_a_v2_7_1_not_promoted",
    }:
        raise ValueError("fresh promotion state mapping changed")
    identity = payload.get("promoted_product_identity", {})
    for key in (
        "fundamental_niche_claim_allowed",
        "temporal_independence_claim_allowed",
        "causal_physiological_driver_claim_allowed",
        "universal_process_claim_allowed",
    ):
        if identity.get(key) is not False:
            raise ValueError(f"fresh promoted claim boundary requires {key}=false")
    product_b = payload.get("product_b", {})
    if product_b != {
        "automatically_unblocked_by_product_a_promotion": False,
        "separate_formal_unblock_gate_required": True,
        "empirical_use_unblocked_by_this_contract": False,
    }:
        raise ValueError("fresh promotion cannot alter Product-B boundary")
    failure = payload.get("failure_semantics", {})
    if failure.get("threshold_relaxation_after_outcome_forbidden") is not True:
        raise ValueError("fresh promotion forbids post-outcome threshold relaxation")
    if failure.get("candidate_reselection_after_outcome_forbidden") is not True:
        raise ValueError("fresh promotion forbids post-outcome candidate reselection")
    payload["contract_sha256"] = _sha256(source)
    return payload


def _load_contract(root: Path) -> dict[str, Any]:
    return json.loads((root / "contract.json").read_text(encoding="utf-8"))


def _single_decision(root: Path) -> pd.Series:
    frame = pd.read_csv(root / "decision.csv")
    if len(frame) != 1:
        raise ValueError("fresh empirical decision artifact must contain exactly one row")
    return frame.iloc[0]


def _fresh_empirical(root: Path) -> tuple[bool, dict[str, Any], pd.Series]:
    contract = _load_contract(root)
    row = _single_decision(root)
    if contract.get("purpose") != EXPECTED_FRESH["expected_purpose"]:
        raise ValueError("fresh Product-A empirical purpose mismatch")
    if str(contract.get("decision")) != str(row["decision"]):
        raise ValueError("fresh empirical contract/CSV decision mismatch")
    if int(contract.get("n_parts", -1)) != 6:
        raise ValueError("fresh empirical confirmation must contain exactly six parts")
    for key in (
        "scientific_promotion_allowed",
        "product_b_unblocked",
        "development_thresholds_retuned_from_fresh_outcomes",
        "fresh_thresholds_retuned_after_sealed_read",
        "post_outcome_candidate_reselection_performed",
        "temporal_independence_claim_allowed",
    ):
        if contract.get(key) is not False:
            raise ValueError(f"fresh empirical source requires {key}=false")
    if contract.get("independence_axis") != "taxon_holdout_not_temporal":
        raise ValueError("fresh empirical independence axis changed")
    decision = str(row["decision"])
    if decision not in {
        "empirical_confirmation_supported",
        "empirical_confirmation_not_supported",
        "empirical_confirmation_unavailable",
    }:
        raise ValueError("unknown fresh empirical confirmation state")
    supported = decision == EXPECTED_FRESH["required_decision"]
    if supported:
        if int(contract.get("n_available_parts", -1)) != 6:
            raise ValueError("supported fresh empirical decision requires all six parts available")
        for column in (
            "all_empirical_evidence_available",
            "prediction_guardrail",
            "ecological_support",
            "process_reproducibility_support",
        ):
            if not bool(row[column]):
                raise ValueError(f"supported fresh empirical decision lacks {column}=true")
    return supported, contract, row


def apply_fresh_promotion(
    *, contract_path: str | Path, known_truth_dir: str | Path,
    fresh_empirical_dir: str | Path, output_dir: str | Path,
) -> dict[str, Any]:
    config = load_fresh_promotion_contract(contract_path)
    known_truth_supported, known_truth = _a_known_truth(Path(known_truth_dir))
    fresh_supported, fresh_contract, fresh_row = _fresh_empirical(Path(fresh_empirical_dir))
    fresh_state = str(fresh_row["decision"])
    promoted = bool(known_truth_supported and fresh_supported)
    decision = config["state_mapping"][fresh_state] if known_truth_supported else "product_a_v2_7_1_not_promoted"
    if (decision == "product_a_v2_7_1_promoted") != promoted:
        raise AssertionError("fresh Product-A promotion state is internally inconsistent")

    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "decision": decision,
        "inherited_known_truth_supported": bool(known_truth_supported),
        "fresh_taxon_holdout_decision": fresh_state,
        "fresh_taxon_holdout_supported": bool(fresh_supported),
        "fresh_all_six_parts_available": int(fresh_contract.get("n_available_parts", -1)) == 6,
        "fresh_prediction_guardrail": bool(fresh_row.get("prediction_guardrail", False)),
        "fresh_ecological_support": bool(fresh_row.get("ecological_support", False)),
        "fresh_process_reproducibility_support": bool(fresh_row.get("process_reproducibility_support", False)),
        "product_a_v2_7_1_promoted": promoted,
        "product_b_empirical_use_unblocked": False,
        "new_postoutcome_scientific_thresholds": False,
        "post_outcome_candidate_reselection": False,
        "fundamental_niche_claim_allowed": False,
        "temporal_independence_claim_allowed": False,
        "causal_physiological_driver_claim_allowed": False,
        "universal_process_claim_allowed": False,
    }]).to_csv(out / "decision.csv", index=False)
    protocol = {
        "purpose": "promoted_product_a_v2_7_1_protocol",
        "promotion_contract_sha256": config["contract_sha256"],
        "promoted": promoted,
        "product": config["promoted_product_identity"],
        "known_truth_source": EXPECTED_KNOWN_TRUTH,
        "fresh_taxon_holdout_source": EXPECTED_FRESH,
        "known_truth_decision": str(known_truth.get("decision")),
        "fresh_empirical_decision": fresh_state,
        "new_postoutcome_scientific_thresholds": False,
        "product_b_empirical_use_unblocked": False,
    }
    (out / "promoted_product_a_v2_7_1_protocol.json").write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    result = {
        "purpose": "product_a_v2_7_1_fresh_promotion_decision",
        "promotion_contract_sha256": config["contract_sha256"],
        "decision": decision,
        "product_a_v2_7_1_promoted": promoted,
        "fresh_taxon_holdout_decision": fresh_state,
        "product_b_empirical_use_unblocked": False,
        "new_postoutcome_scientific_thresholds": False,
        "threshold_relaxation_after_outcome": False,
        "candidate_reselection_after_outcome": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", required=True)
    p.add_argument("--known-truth-dir", required=True)
    p.add_argument("--fresh-empirical-dir", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args(argv)
    apply_fresh_promotion(
        contract_path=a.contract,
        known_truth_dir=a.known_truth_dir,
        fresh_empirical_dir=a.fresh_empirical_dir,
        output_dir=a.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
