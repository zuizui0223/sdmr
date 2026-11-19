"""No-refit independent audit of archived structural KT prospective receipt.

Reads only saved final scores from GitHub Actions artifact, never calls the
synthetic generator, refits learners, opens original tree data, or retries
prospective seeds.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, fields
from hashlib import sha256
import json
from pathlib import Path

from sdmr.structural_known_truth_v1 import WORLDS, ForestScore
from sdmr.structural_process_benchmarks_v1 import aggregate_comparators
from sdmr.structural_process_gate_v1 import assess_forest_development

ORIGINAL_RUN = 44432358638
ORIGINAL_SOURCE_COMMIT = "9ccc3c4747b8dfd486623c756dbe5455f373a25b"
ORIGINAL_INNER_SHA256 = "e384e5270a07c4a3bbbabdbb02fd17302d34f7c0f94dbbd627ddb21ef762ea39"
ORIGINAL_ZIP_SHA256 = "6a354d3329081d5b33b4636a1b0feea5481847ccd5d034e2dd90710a9d1c563b"
SEEDS = tuple(range(96001, 96011))


def audit_saved_result(path: Path, design_path: Path) -> dict:
    source_bytes = path.read_bytes()
    exact_sha = sha256(source_bytes).hexdigest()
    if exact_sha != ORIGINAL_INNER_SHA256:
        raise ValueError("prospective original saved JSON digest mismatch")
    result = json.loads(source_bytes)
    design = json.loads(design_path.read_text())
    if result["status"] != "synthetic_prospective_pass":
        raise ValueError("original terminal state is not the recorded PASS")
    if result["source_commit"] != ORIGINAL_SOURCE_COMMIT:
        raise ValueError("original source freeze mismatch")
    if result["seeds"] != list(SEEDS) or result["worlds"] != list(WORLDS):
        raise ValueError("prospective source denominators changed")
    if result["n_cases"] != 80 or len(result["cases"]) != 80:
        raise ValueError("incomplete 80-case denominator")
    if result["gate_thresholds"] != design["gate"]:
        raise ValueError("original frozen gate changed")
    if result["empirical_data_opened"] is not False or result["Product_B_unblocked"] is not False:
        raise ValueError("forbidden empirical promotion")
    if result["original_M5_and_Product_A_unchanged"] is not True:
        raise ValueError("original program boundaries changed")

    names = {field.name for field in fields(ForestScore)}
    scores: list[ForestScore] = []
    seen: set[tuple[str, int]] = set()
    labels = {}
    for row in result["cases"]:
        if not names.issubset(row):
            raise ValueError("missing scored fields")
        score = ForestScore(**{key: row[key] for key in names})
        key = (score.world, score.seed)
        if key in seen or score.world not in WORLDS or score.seed not in SEEDS:
            raise ValueError("duplicated or unknown prospective world x seed")
        seen.add(key)
        actual = assess_forest_development(score)
        if row["process_state"] != actual.state or row["process_reason"] != actual.reason:
            raise ValueError("archived decision differs from frozen policy on saved scores")
        if row["causal_process_identified"] or row["empirical_promotion_authorized"]:
            raise ValueError("synthetic case illegally promoted to causal/empirical")
        labels[key] = actual.state
        scores.append(score)
    expected_keys = {(world, seed) for world in WORLDS for seed in SEEDS}
    if seen != expected_keys:
        raise ValueError("nonexact prospective case coverage")

    controls = [asdict(c) for c in aggregate_comparators(scores)]
    if controls != result["comparators"]:
        raise ValueError("original comparator counts do not match saved scores")
    n_obs = sum(labels[("observation_selection", seed)] == "unresolved" for seed in SEEDS)
    n_miss = sum(labels[("omitted_driver", seed)] == "unavailable" for seed in SEEDS)
    n_shared = sum(
        labels[("shared_carrier", seed)] == "contributory_information_candidate"
        for seed in SEEDS
    )
    expected_gates = {
        "complete_80": True,
        "positive_recovery": controls[-1]["true_positive_calls"] >= design["gate"]["positive_recovery_min"],
        "false_call_control": controls[-1]["false_positive_calls"] <= design["gate"]["false_positive_max"],
        "observation_unresolved": n_obs >= design["gate"]["unresolved_observation_selection_min"],
        "omitted_driver_unavailable": n_miss >= design["gate"]["omitted_driver_unavailable_min"],
        "shared_carrier_recovered": n_shared >= design["gate"]["shared_carrier_recovery_min"],
        "no_empirical_or_causal_promotions": True,
    }
    if result["gates"] != expected_gates or not all(expected_gates.values()):
        raise ValueError("original gate flags disagree with independently audited finite scores")
    return {
        "schema": "sdmr.structural_kt_prospective_saved_receipt_audit.v1",
        "audit_status": "exact_saved_score_reconciliation_pass",
        "original_run": ORIGINAL_RUN,
        "original_source_commit": ORIGINAL_SOURCE_COMMIT,
        "original_inner_result_sha256": ORIGINAL_INNER_SHA256,
        "original_artifact_zip_sha256": ORIGINAL_ZIP_SHA256,
        "not_a_new_scientific_opening": True,
        "models_refitted": 0,
        "generator_called": False,
        "n_cases": 80,
        "n_true_positive": 30,
        "n_null": 50,
        "observation_unresolved": n_obs,
        "omitted_driver_unavailable": n_miss,
        "shared_carrier_recovered": n_shared,
        "recalculated_comparators": controls,
        "gates": expected_gates,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--contract", default="configs/structural_process_kt_prospective_v1.json", type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    summary = audit_saved_result(args.source, args.contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print("EXACT_RECONCILIATION_PASS", summary["n_cases"])
    print("NO_REFITS", summary["models_refitted"])
    for x in summary["recalculated_comparators"]:
        print("SAVED_COMPARATOR", x["comparator"],
              x["true_positive_calls"], "/", x["true_positive_targets"],
              x["false_positive_calls"], "/", x["null_targets"])
    print("OBSERVATION_UNRESOLVED", summary["observation_unresolved"])
    print("OMITTED_UNAVAILABLE", summary["omitted_driver_unavailable"])
    print("SHARED_RECOVERED", summary["shared_carrier_recovered"])


if __name__ == "__main__":
    main()
