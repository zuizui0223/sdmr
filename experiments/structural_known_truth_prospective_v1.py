"""One-shot, source-locked synthetic prospective structural-process benchmark.

Do NOT import this module from tests to call evaluate_prospective with
unopened target seeds. Test contract validation only until activation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from sdmr.structural_known_truth_v1 import WORLDS, generate_forest_world, score_forest_world
from sdmr.structural_process_benchmarks_v1 import (
    COMPARATORS, TRUTH_POSITIVES, aggregate_comparators
)
from sdmr.structural_process_gate_v1 import assess_forest_development

EXPECTED_SEEDS = tuple(range(96001, 96011))
EXPECTED_WORLD_ORDER = WORLDS
EXPECTED_COMPARATORS = COMPARATORS
SCHEMA = "sdmr.structural_process_known_truth_prospective.v1"


def verify_design(contract: dict) -> None:
    """Validation without any target outcome access or RNG opening."""
    required = {
        "schema": SCHEMA,
        "status": "design_frozen_before_unused_seed_opening",
        "evidence_class": "synthetic_prospective_only",
        "worlds": list(EXPECTED_WORLD_ORDER),
        "positive_worlds": [w for w in WORLDS if w in TRUTH_POSITIVES],
        "seeds": list(EXPECTED_SEEDS),
        "n_regions": 8,
        "sites_per_region": 64,
        "n_cases": 80,
        "per_world_cases": 10,
        "positive_cases": 30,
        "null_cases": 50,
        "comparators": list(EXPECTED_COMPARATORS),
        "primary_comparator": "all_carriers_with_observation_audit",
    }
    for name, expected in required.items():
        if contract.get(name) != expected:
            raise ValueError(f"frozen prospective design mismatch: {name}")

    gates = contract.get("gate", {})
    frozen = {
        "positive_recovery_min": 27,
        "false_positive_max": 1,
        "unresolved_observation_selection_min": 10,
        "omitted_driver_unavailable_min": 10,
        "shared_carrier_recovery_min": 9,
        "no_causal_claims_required": True,
        "no_empirical_promotion_required": True,
        "complete_denominator_required": True,
    }
    if gates != frozen:
        raise ValueError("prospective gate thresholds or scope changed")
    method = contract.get("methods", {})
    if not method or not isinstance(method, dict):
        raise ValueError("frozen method semantics missing")
    if method.get("observation_flag") != (
        "oracle-provided source-audit eligibility; NOT learned from outcomes"
    ):
        raise ValueError("observation evidence-boundary disclosure changed")
    if method.get("time_axis") != (
        "same-interval change association; NOT future prediction"
    ):
        raise ValueError("temporal estimand boundary changed")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def verify_one_shot_source(
    execution: dict, activation_text: str, contract_path: Path,
) -> None:
    """Strict source barrier before ANY generator call."""
    if execution.get("status") != "source_frozen_before_first_open":
        raise ValueError("no prior full-source freeze")
    if execution.get("source_commit") != git("rev-parse", "HEAD^^"):
        raise ValueError("unexpected scientific source commit")
    if git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD^") != (
        "configs/structural_process_kt_prospective_v1_execution.json"
    ):
        raise ValueError("pre-activation commit changed scientific source")
    if git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD") != (
        "configs/structural_process_kt_prospective_v1_activate.lock"
    ):
        raise ValueError("activation commit modified more than execute lock")
    required_lock = (
        "structural_kt_v1_activate=one_shot\n"
        "prospective_seeds=96001-96010\n"
        "worlds=8\n"
        "source_freeze_sha=" + execution["source_commit"] + "\n"
        "no_real_ecology=true\n"
    )
    if activation_text != required_lock:
        raise ValueError("activation lock identity mismatch")
    hashes = execution.get("source_blobs")
    if not isinstance(hashes, dict) or len(hashes) < 7:
        raise ValueError("missing original source-file hash manifest")
    mandatory = {
        str(contract_path),
        "src/sdmr/contextual_structure_evidence.py",
        "src/sdmr/structural_known_truth_v1.py",
        "src/sdmr/structural_process_gate_v1.py",
        "src/sdmr/structural_process_benchmarks_v1.py",
        "experiments/structural_known_truth_prospective_v1.py",
        ".github/workflows/sdmr-structural-kt-prospective-v1.yml",
    }
    if set(hashes) != mandatory:
        raise ValueError("incorrect prospective source-manifest file universe")
    for path, exact_sha in hashes.items():
        if git("hash-object", path) != exact_sha:
            raise ValueError(f"source bytes drifted: {path}")
    if Path("results/structural_known_truth_prospective_v1_result.json").exists():
        raise ValueError("archived result already present; cannot reopen")


def evaluate_prospective(contract: dict) -> dict:
    """Must be called ONLY after verify_one_shot_source succeeded."""
    scores = [
        score_forest_world(
            generate_forest_world(world, seed,
                                  n_regions=contract["n_regions"],
                                  sites_per_region=contract["sites_per_region"])
        )
        for seed in EXPECTED_SEEDS for world in EXPECTED_WORLD_ORDER
    ]
    states = [assess_forest_development(s) for s in scores]
    if len(scores) != 80 or len({(s.world, s.seed) for s in scores}) != 80:
        raise AssertionError("prospective denominator incomplete")
    if any(st.causal_process_identified or st.empirical_promotion_authorized
           for st in states):
        raise AssertionError("forbidden causal/empirical synthetic promotion")

    comp = [asdict(c) for c in aggregate_comparators(scores)]
    primary = comp[-1]
    gates = contract["gate"]
    unresolved_selection = sum(
        s.world == "observation_selection" and st.state == "unresolved"
        for s, st in zip(scores, states)
    )
    unavailable_missing = sum(
        s.world == "omitted_driver" and st.state == "unavailable"
        for s, st in zip(scores, states)
    )
    recovered_shared = sum(
        s.world == "shared_carrier" and st.state == "contributory_information_candidate"
        for s, st in zip(scores, states)
    )
    decisions = {
        "complete_80": len(scores) == 80,
        "positive_recovery": primary["true_positive_calls"] >= gates["positive_recovery_min"],
        "false_call_control": primary["false_positive_calls"] <= gates["false_positive_max"],
        "observation_unresolved": unresolved_selection >= gates["unresolved_observation_selection_min"],
        "omitted_driver_unavailable": unavailable_missing >= gates["omitted_driver_unavailable_min"],
        "shared_carrier_recovered": recovered_shared >= gates["shared_carrier_recovery_min"],
        "no_empirical_or_causal_promotions": all(
            not st.empirical_promotion_authorized and not st.causal_process_identified
            for st in states
        ),
    }
    status = "synthetic_prospective_pass" if all(decisions.values()) else (
        "synthetic_prospective_not_supported"
    )
    return {
        "schema": SCHEMA,
        "status": status,
        "gates": decisions,
        "gate_thresholds": gates,
        "n_cases": len(scores),
        "seeds": list(EXPECTED_SEEDS),
        "worlds": list(EXPECTED_WORLD_ORDER),
        "source_is_synthetic": True,
        "empirical_data_opened": False,
        "original_M5_and_Product_A_unchanged": True,
        "Product_B_unblocked": False,
        "comparators": comp,
        "observation_selection_unresolved": unresolved_selection,
        "omitted_driver_unavailable": unavailable_missing,
        "shared_carrier_recovered": recovered_shared,
        "cases": [
            {**asdict(s), "process_state": st.state, "process_reason": st.reason}
            for s, st in zip(scores, states)
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--execution", type=Path)
    p.add_argument("--activation", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--preflight-only", action="store_true")
    args = p.parse_args()
    design = json.loads(args.contract.read_text())
    verify_design(design)
    if args.preflight_only:
        print("PREOUTCOME_SCHEMA_PASS: 80 synthetic prospective cases declared, none opened")
        return
    if not all((args.execution, args.activation, args.output)):
        raise ValueError("one-shot execution, activation and output are required")
    execution = json.loads(args.execution.read_text())
    verify_one_shot_source(execution, args.activation.read_text(), args.contract)
    out = evaluate_prospective(design)
    out["source_commit"] = execution["source_commit"]
    encoded = (json.dumps(out, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)
    print("SYNTHETIC_PROSPECTIVE_TERMINAL", out["status"], "SHA256", sha256(encoded).hexdigest())
    print("GATES", json.dumps(out["gates"], sort_keys=True))
    for x in out["comparators"]:
        print(
            "COMPARATOR", x["comparator"],
            "RECOVERY", str(x["true_positive_calls"]) + "/" + str(x["true_positive_targets"]),
            "FALSE", str(x["false_positive_calls"]) + "/" + str(x["null_targets"])
        )


if __name__ == "__main__":
    main()
