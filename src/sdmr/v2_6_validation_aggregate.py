"""Run the frozen v2.5 validation calculation under v2.6 provenance.

The scientific calculation and decision thresholds are unchanged. This module only
adapts worker/calibration provenance after v2.5 failed availability and v2.6 restored
predeclared calibration redundancy. Reserved validation truth 501--523 remains opened
only inside the inherited aggregate after all model-only products are frozen.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from . import v2_5_validation_aggregate as base
from .v2_6_contract import load_v2_6_contract
from .v2_6_validation_contract import load_v2_6_validation_contract

SOURCE_CONTRACT_SHA256 = "fab5f822954580b903018216ce2f2ea2aeef6f41492cc350f108ef0223e1434a"
EXPECTED_WORKERS = 54


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _load_workers(root: Path, *, source_contract_sha256: str) -> dict[str, Any]:
    contracts: list[dict[str, Any]] = []
    expected_frames: list[pd.DataFrame] = []
    key_frames: list[pd.DataFrame] = []
    fit_frames: list[pd.DataFrame] = []
    response_frames: list[pd.DataFrame] = []
    candidate_frames: list[pd.DataFrame] = []
    for path in sorted(root.rglob("contract.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("purpose") != "product_a_v2_6_model_only_refit_worker":
            continue
        if row.get("role") != "validation":
            raise ValueError("fresh validation contains a non-validation worker")
        if row.get("contract_sha256") != source_contract_sha256:
            raise ValueError("validation worker used a different frozen v2.6 contract")
        for flag in (
            "generating_truth_read", "real_empirical_data_read",
            "candidate_selection_performed", "scientific_threshold_tuning_performed",
        ):
            if row.get(flag) is not False:
                raise ValueError(f"fresh validation violates {flag}=false")
        worker = path.parent
        expected = _read_csv(worker / "expected_members.csv")
        keys = _read_csv(worker / "expected_response_keys.csv")
        fits = _read_csv(worker / "fit_ledger.csv")
        responses = _read_csv(worker / "response_estimates.csv")
        candidates = _read_csv(worker / "frozen_candidates.csv")
        for frame, label in ((expected, "expected_members"), (keys, "expected_response_keys"), (fits, "fit_ledger"), (candidates, "frozen_candidates")):
            if frame.empty:
                raise ValueError(f"validation worker {worker} has empty {label}")
        contracts.append(row)
        expected_frames.append(expected)
        key_frames.append(keys)
        fit_frames.append(fits)
        if not responses.empty:
            response_frames.append(responses)
        candidates["worker_panel"] = row["panel"]
        candidates["worker_species"] = row["species"]
        candidates["worker_group"] = row["group"]
        candidate_frames.append(candidates)
    if len(contracts) != EXPECTED_WORKERS:
        raise ValueError(f"expected {EXPECTED_WORKERS} validation workers, found {len(contracts)}")
    unique = {(str(r["panel"]), int(r["taxon_index"]), str(r["group"])) for r in contracts}
    if len(unique) != EXPECTED_WORKERS:
        raise ValueError("validation worker panel x taxon x group keys are not unique")
    responses = pd.concat(response_frames, ignore_index=True) if response_frames else pd.DataFrame()
    if responses.empty:
        raise ValueError("no successful fresh validation responses were supplied")
    return {
        "contracts": contracts,
        "expected_members": pd.concat(expected_frames, ignore_index=True),
        "expected_response_keys": pd.concat(key_frames, ignore_index=True),
        "fit_ledger": pd.concat(fit_frames, ignore_index=True),
        "response_estimates": responses,
        "frozen_candidates": pd.concat(candidate_frames, ignore_index=True),
    }


def _verify_calibration(root: Path, *, source_contract_sha256: str):
    contract = json.loads((root / "contract.json").read_text(encoding="utf-8"))
    if contract.get("purpose") != "product_a_v2_6_frozen_calibration_radii":
        raise ValueError("source is not frozen v2.6 calibration")
    if contract.get("source_contract_sha256") != source_contract_sha256:
        raise ValueError("v2.6 calibration derives from a different base contract")
    if contract.get("all_required_validation_keys_calibrated") is not True:
        raise ValueError("v2.6 calibration does not cover every validation key")
    if int(contract.get("minimum_complete_calibration_taxa_per_key", -1)) != 2:
        raise ValueError("v2.6 calibration minimum changed")
    if int(contract.get("minimum_observed_complete_calibration_taxa_per_key", -1)) < 2:
        raise ValueError("v2.6 calibration has fewer than two complete taxa")
    for key in (
        "raw_envelopes_frozen_before_calibration_truth_read",
        "calibration_generating_truth_read_after_raw_freeze",
    ):
        if contract.get(key) is not True:
            raise ValueError(f"v2.6 calibration barrier failed: {key}")
    for key in (
        "reserved_validation_taxa_simulated_or_read",
        "reserved_validation_truth_read",
        "validation_truth_used_for_calibration",
        "candidate_selection_performed_during_calibration",
        "scientific_threshold_tuning_performed_during_calibration",
    ):
        if contract.get(key) is not False:
            raise ValueError(f"v2.6 calibration provenance failed: {key}")
    calibration = pd.read_csv(root / "calibration.csv")
    if len(calibration) != 27 or not calibration["calibration_status"].astype(str).eq("complete").all():
        raise ValueError("v2.6 calibration must contain 27 complete keys")
    if calibration["calibration_uses_validation_truth"].fillna(True).astype(bool).any():
        raise ValueError("v2.6 calibration records validation truth use")
    return contract, calibration


def run_v2_6_validation_aggregate(**kwargs):
    original_contract_loader = base.load_v2_5_contract
    original_validation_loader = base.load_v2_5_validation_contract
    original_worker_loader = base._load_validation_workers
    original_calibration_verify = base._verify_calibration
    original_source_sha = base.SOURCE_CALIBRATION_CONTRACT_SHA256
    try:
        base.load_v2_5_contract = load_v2_6_contract
        base.load_v2_5_validation_contract = load_v2_6_validation_contract
        base._load_validation_workers = _load_workers
        base._verify_calibration = _verify_calibration
        base.SOURCE_CALIBRATION_CONTRACT_SHA256 = SOURCE_CONTRACT_SHA256
        result = base.run_v2_5_validation_aggregate(**kwargs)
    finally:
        base.load_v2_5_contract = original_contract_loader
        base.load_v2_5_validation_contract = original_validation_loader
        base._load_validation_workers = original_worker_loader
        base._verify_calibration = original_calibration_verify
        base.SOURCE_CALIBRATION_CONTRACT_SHA256 = original_source_sha

    out = Path(kwargs["output_dir"])
    contract = result["contract"]
    contract["purpose"] = "product_a_v2_6_predeclared_fresh_validation_decision"
    contract["decision"] = str(contract["decision"]).replace("v2_5_", "v2_6_")
    contract["calibration_version"] = "v2.6"
    contract["minimum_complete_calibration_taxa_per_key"] = 2
    contract["internal_compatibility_product_label"] = "v2_5_exclusion_calibrated_certificate"
    (out / "contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    decision_path = out / "decision.csv"
    decision = pd.read_csv(decision_path)
    decision["decision"] = decision["decision"].astype(str).str.replace("v2_5_", "v2_6_", regex=False)
    decision["next_action"] = decision["next_action"].astype(str).str.replace("v2.5", "v2.6", regex=False)
    decision.to_csv(decision_path, index=False)
    result["contract"] = contract
    result["decision"] = decision
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-contract", required=True)
    parser.add_argument("--validation-contract", required=True)
    parser.add_argument("--worker-root", required=True)
    parser.add_argument("--discovery-root", required=True)
    parser.add_argument("--calibration-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--calibration-run-id", required=True)
    parser.add_argument("--calibration-head-sha", required=True)
    parser.add_argument("--calibration-artifact-id", required=True)
    parser.add_argument("--calibration-artifact-digest", required=True)
    args = parser.parse_args(argv)
    run_v2_6_validation_aggregate(
        base_contract_path=args.base_contract,
        validation_contract_path=args.validation_contract,
        worker_root=args.worker_root,
        discovery_root=args.discovery_root,
        calibration_root=args.calibration_root,
        output_dir=args.output_dir,
        calibration_run_id=args.calibration_run_id,
        calibration_head_sha=args.calibration_head_sha,
        calibration_artifact_id=args.calibration_artifact_id,
        calibration_artifact_digest=args.calibration_artifact_digest,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
