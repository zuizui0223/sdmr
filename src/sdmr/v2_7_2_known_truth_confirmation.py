"""Predeclared known-truth confirmation for Product-A v2.7.2 determinism.

This lane exists because the v2.7.1 fresh sharding parity experiment changed a
selected predictor when liblinear was run in independent processes with
``random_state=None``. v2.7.2 changes only estimator identity by freezing the
model random state, then checks both reproducibility and ecological non-regression
on new known-truth seeds.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .ecological_inference_certificate import audit_ecological_inference_certificates
from .known_truth_replicated_observation_experiment import (
    run_known_truth_replicated_observation_experiment,
)
from .known_truth_perturbation import DEFAULT_KNOWN_TRUTH_PERTURBATIONS
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES, standard_known_truth_candidates
from .transport_parity import assert_transport_frame_parity
from .v2_7_2_deterministic_procedure_library import seed_recovery_candidates

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "configs" / "product_a_v2_7_2_deterministic_successor_contract.json"
ROBUST_SELECTOR = "replicated_observation_perturbation_robust_niche_recovery"


def load_contract(path: str | Path = CONTRACT_PATH) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_7_2_deterministic_successor_preoutcome_contract":
        raise ValueError("wrong v2.7.2 deterministic successor contract")
    if payload.get("frozen_before_v2_7_2_known_truth_outcome") is not True:
        raise ValueError("v2.7.2 successor was not frozen before known truth")
    if payload["v2_7_1_stop_rule"].get("open_current_fresh_sealed_outcomes_under_modified_estimator_allowed") is not False:
        raise ValueError("v2.7.2 may not open the old v2.7.1 sealed lane")
    implementation = payload["implementation_change"]
    if implementation.get("successor_model_random_state") != 0:
        raise ValueError("v2.7.2 model random state changed")
    if implementation.get("weighted_super_score_allowed") is not False:
        raise ValueError("v2.7.2 cannot introduce a weighted super score")
    confirmation = payload["known_truth_confirmation"]
    if tuple(confirmation.get("families", ())) != tuple(KNOWN_TRUTH_FAMILIES):
        raise ValueError("v2.7.2 known-truth families changed")
    if tuple(int(x) for x in confirmation.get("seeds", ())) != tuple(range(3101, 3111)):
        raise ValueError("v2.7.2 known-truth seeds changed")
    if int(confirmation.get("n_cases", -1)) != 60:
        raise ValueError("v2.7.2 known-truth denominator changed")
    determinism = payload["determinism_gate"]
    if determinism.get("fail_closed_on_any_discrete_difference") is not True:
        raise ValueError("v2.7.2 determinism gate no longer fails closed")
    if determinism.get("tolerance_may_not_be_changed_after_outcome") is not True:
        raise ValueError("v2.7.2 determinism tolerance is not frozen")
    return payload


def _scientific_decision(
    choices: pd.DataFrame,
    signals: pd.DataFrame,
    certificates: pd.DataFrame,
    contract: dict,
) -> dict[str, object]:
    gate = contract["scientific_nonregression_gate"]
    expected = int(contract["known_truth_confirmation"]["n_cases"])
    robust = choices.loc[choices["selector"].astype(str).eq(ROBUST_SELECTOR)]
    coverage = float(len(robust) / expected)

    certificate_precision = float(certificates["stable_core_precision"].mean())
    certificate_recall = float(certificates["stable_core_recall"].mean())
    certificate_f1 = float(certificates["stable_core_f1"].mean())

    case_signal = (
        signals.groupby(["scenario", "seed"], as_index=False)
        .agg(global_correction_active=("global_correction_active", "first"))
    )
    confounded = case_signal.loc[case_signal["scenario"].astype(str).eq("observation_confounded")]
    other = case_signal.loc[~case_signal["scenario"].astype(str).eq("observation_confounded")]
    confounded_activation = float(confounded["global_correction_active"].astype(bool).mean())
    other_activation = float(other["global_correction_active"].astype(bool).mean())

    checks = {
        "robust_selector_selection_coverage": coverage >= float(gate["robust_selector_selection_coverage_min"]),
        "stable_core_precision": certificate_precision >= float(gate["stable_core_precision_min"]),
        "stable_core_recall": certificate_recall >= float(gate["stable_core_recall_min"]),
        "stable_core_f1": certificate_f1 >= float(gate["stable_core_f1_min"]),
        "observation_confounded_correction_activation": confounded_activation >= float(gate["observation_confounded_correction_activation_fraction_min"]),
        "non_observation_confounded_correction_specificity": other_activation <= float(gate["non_observation_confounded_correction_activation_fraction_max"]),
    }
    return {
        "purpose": "product_a_v2_7_2_known_truth_scientific_nonregression_decision",
        "supported": bool(all(checks.values())),
        "checks": checks,
        "robust_selector_selection_coverage": coverage,
        "mean_stable_core_precision": certificate_precision,
        "mean_stable_core_recall": certificate_recall,
        "mean_stable_core_f1": certificate_f1,
        "observation_confounded_activation_fraction": confounded_activation,
        "non_observation_confounded_activation_fraction": other_activation,
        "post_outcome_threshold_tuning_allowed": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }


def run_confirmation(output_dir: str | Path, *, contract_path: str | Path = CONTRACT_PATH) -> dict[str, object]:
    contract = load_contract(contract_path)
    cfg = contract["known_truth_confirmation"]
    random_state = int(cfg["model_random_state"])
    candidates = seed_recovery_candidates(
        standard_known_truth_candidates(), random_state=random_state
    )

    choices, truth, summary, metrics, signals = run_known_truth_replicated_observation_experiment(
        families=tuple(cfg["families"]),
        seeds=tuple(int(x) for x in cfg["seeds"]),
        candidates=candidates,
        perturbations=DEFAULT_KNOWN_TRUTH_PERTURBATIONS,
        n_cells=int(cfg["n_cells"]),
        n_occurrences=int(cfg["n_occurrences"]),
        n_target_group=int(cfg["n_target_group"]),
        n_spatial_blocks=int(cfg["n_spatial_blocks"]),
        inner_folds=int(cfg["inner_folds"]),
        min_background=int(cfg["minimum_background"]),
    )

    forbidden = {
        "true_suitability",
        "truth_surface_rank",
        "truth_surface_nrmse",
        "driver_process_f1",
    }
    leaked = sorted(forbidden.intersection(metrics.columns))
    if leaked:
        raise RuntimeError(f"hidden truth leaked into selection evidence: {leaked}")

    certificates = audit_ecological_inference_certificates(choices)
    decision = _scientific_decision(choices, signals, certificates, contract)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    choices.to_csv(out / "selector_choices.csv", index=False)
    truth.to_csv(out / "truth_evaluation.csv", index=False)
    summary.to_csv(out / "selector_truth_summary.csv", index=False)
    metrics.to_csv(out / "candidate_fold_metrics.csv", index=False)
    signals.to_csv(out / "observation_signal_summary.csv", index=False)
    certificates.to_csv(out / "ecological_inference_certificates.csv", index=False)
    (out / "scientific_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    run_receipt = {
        "purpose": "product_a_v2_7_2_known_truth_replicate_receipt",
        "families": list(cfg["families"]),
        "seeds": list(cfg["seeds"]),
        "n_cases": int(cfg["n_cases"]),
        "model_random_state": random_state,
        "candidate_names": sorted(candidates),
        "hidden_truth_used_during_selection": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    (out / "run_receipt.json").write_text(
        json.dumps(run_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return decision


def compare_replicates(
    first_dir: str | Path,
    second_dir: str | Path,
    output_dir: str | Path,
    *,
    contract_path: str | Path = CONTRACT_PATH,
) -> dict[str, object]:
    contract = load_contract(contract_path)
    det = contract["determinism_gate"]
    rtol = float(det["numeric_relative_tolerance"])
    atol = float(det["numeric_absolute_tolerance"])
    first = Path(first_dir)
    second = Path(second_dir)

    summaries = {}
    for filename in (
        "selector_choices.csv",
        "candidate_fold_metrics.csv",
        "observation_signal_summary.csv",
        "ecological_inference_certificates.csv",
        "truth_evaluation.csv",
        "selector_truth_summary.csv",
    ):
        a = pd.read_csv(first / filename)
        b = pd.read_csv(second / filename)
        result = assert_transport_frame_parity(a, b, rtol=rtol, atol=atol)
        summaries[filename] = result.as_dict()

    decision_a = json.loads((first / "scientific_decision.json").read_text(encoding="utf-8"))
    decision_b = json.loads((second / "scientific_decision.json").read_text(encoding="utf-8"))
    if decision_a != decision_b:
        raise AssertionError("independent deterministic replicates produced different scientific decisions")

    result = {
        "purpose": "product_a_v2_7_2_known_truth_determinism_decision",
        "determinism_passed": True,
        "scientific_nonregression_supported": bool(decision_a["supported"]),
        "numeric_relative_tolerance": rtol,
        "numeric_absolute_tolerance": atol,
        "frame_summaries": summaries,
        "post_outcome_tolerance_change_allowed": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "determinism_decision.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "scientific_decision.json").write_text(
        json.dumps(decision_a, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--output-dir", required=True)
    compare = sub.add_parser("compare")
    compare.add_argument("--first-dir", required=True)
    compare.add_argument("--second-dir", required=True)
    compare.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "run":
        run_confirmation(args.output_dir)
    else:
        compare_replicates(args.first_dir, args.second_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
