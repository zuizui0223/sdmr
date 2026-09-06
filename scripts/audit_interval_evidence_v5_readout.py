"""Read-only audit of the completed, burned v5 development artifact.

No sdmr imports, model fits, simulations, RNG, answer-check opening, threshold
changes, dispatches or prospective decisions. This audits one historical run;
it is not a new scientific acceptance rule or a generic validation runner.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import zipfile

HEAD_SHA = "f3b95c7aa5ea0f559b54dc797ec46fda141582c8"
RUN_ID = 34037107229
ARTIFACT_ID = 9990648093
ARCHIVE_SHA256 = "1135dde2260a22e54d963b0cad6fd7210b98a362b983eddf2a6750e5d542b3b1"
FAMILIES = ("gaussian", "asymmetric", "soft_threshold", "interaction",
            "omitted_driver", "observation_confounded")
SEEDS = tuple(range(13001, 13011))
PROCESSES = ("temperature", "water", "soil", "seasonality", "noise")
CONTRIBUTORY = "contributory_under_evidence_contract"
REPLACEABLE = "replaceable_under_evidence_contract"
REQUIRED = "required_by_evidence_contract"
UNRESOLVED = "unresolved"
STATUSES = (CONTRIBUTORY, REPLACEABLE, UNRESOLVED, REQUIRED)
MEMBERS = {"case_summary.csv", "process_evaluation.csv", "family_metrics.csv",
           "development_decision.json"}
DEFAULT_ARCHIVE = (Path(__file__).resolve().parents[1] / "evidence" /
                   "interval_evidence_v5_development" / f"run_{RUN_ID}.zip")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def boolean(value: str) -> bool:
    require(value in ("True", "False"), f"invalid CSV boolean: {value!r}")
    return value == "True"


def integer(value: str) -> int:
    require(bool(re.fullmatch(r"0|[1-9][0-9]*", value)),
            f"invalid nonnegative CSV integer: {value!r}")
    return int(value)


def read_bundle(path: Path) -> tuple[dict, dict[str, str]]:
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA256,
            "archive SHA256 differs from the completed GitHub artifact")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        require(set(archive.namelist()) == MEMBERS and len(archive.namelist()) == 4,
                "unexpected or duplicate archive member")
        files = {name: archive.read(name) for name in sorted(MEMBERS)}
    tables = {}
    for name, content in files.items():
        text = content.decode("utf-8")
        if name.endswith(".json"):
            tables[name] = json.loads(text)
        else:
            reader = csv.DictReader(io.StringIO(text))
            require(bool(reader.fieldnames) and
                    len(reader.fieldnames) == len(set(reader.fieldnames)),
                    f"invalid CSV header: {name}")
            rows = list(reader)
            require(all(None not in row and None not in row.values() for row in rows),
                    f"malformed CSV row: {name}")
            tables[name] = rows
    return tables, {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}


def metrics(rows: list[dict[str, str]]) -> dict[str, int | float]:
    truth = [boolean(row["expected_true_process"]) for row in rows]
    challenge = [boolean(row["challenge_signal_detected"]) for row in rows]
    unique = [boolean(row["unique_process_evidence"]) for row in rows]
    contested = [boolean(row["shared_information_contested"]) for row in rows]
    ntrue = sum(truth)
    nfalse = len(rows) - ntrue
    require(ntrue > 0 and nfalse > 0, "empty truth denominator")
    tp = sum(t and d for t, d in zip(truth, challenge))
    fp = sum(not t and d for t, d in zip(truth, challenge))
    utp = sum(t and d for t, d in zip(truth, unique))
    ufp = sum(not t and d for t, d in zip(truth, unique))
    freq = sum(not t and r["attribution_status"] == REQUIRED for t, r in zip(truth, rows))
    tc = sum(t and c for t, c in zip(truth, contested))
    fc = sum(not t and c for t, c in zip(truth, contested))
    counts = Counter(row["attribution_status"] for row in rows)
    return {
        "true_process_detection_recall": tp / ntrue,
        "false_process_detection_rate": fp / nfalse,
        "true_process_challenge_recall": tp / ntrue,
        "false_process_challenge_rate": fp / nfalse,
        "true_process_unique_attribution_recall": utp / ntrue,
        "false_process_unique_attribution_rate": ufp / nfalse,
        "false_required_rate": freq / nfalse,
        "true_process_contested_rate": tc / ntrue,
        "false_process_contested_rate": fc / nfalse,
        "n_true_processes": ntrue, "n_false_processes": nfalse,
        "n_challenge_detected_true_processes": tp,
        "n_challenge_detected_false_processes": fp,
        "n_unique_true_processes": utp, "n_unique_false_processes": ufp,
        "n_false_required": freq, "n_true_contested": tc, "n_false_contested": fc,
        "n_replaceable": counts[REPLACEABLE], "n_contributory": counts[CONTRIBUTORY],
        "n_required": counts[REQUIRED], "n_contested_shared": tc + fc,
        "n_unresolved": counts[UNRESOLVED],
    }


def equal_metrics(actual: dict, expected: dict) -> None:
    require(set(actual) == set(expected), "metric schema mismatch")
    for key, value in expected.items():
        if isinstance(value, int):
            require(not isinstance(actual[key], bool) and float(actual[key]) == value,
                    f"metric mismatch: {key}")
        else:
            # Serialization comparison only; not a scientific threshold.
            require(not isinstance(actual[key], bool) and
                    math.isclose(float(actual[key]), value, rel_tol=0, abs_tol=1e-12),
                    f"metric mismatch: {key}")


def validate_tables(tables: dict) -> dict:
    cases = tables["case_summary.csv"]
    process = tables["process_evaluation.csv"]
    family_metrics = tables["family_metrics.csv"]
    decision = tables["development_decision.json"]
    expected_pairs = {(f, s) for f in FAMILIES for s in SEEDS}
    case_keys = [(r["family"], integer(r["seed"])) for r in cases]
    require(len(case_keys) == len(set(case_keys)) == 60 and set(case_keys) == expected_pairs,
            "case denominator mismatch or duplicate")
    expected_cells = {(f, s, p) for f, s in expected_pairs for p in PROCESSES}
    keys = [(r["family"], integer(r["seed"]), r["process"]) for r in process]
    require(len(keys) == len(set(keys)) == 300 and set(keys) == expected_cells,
            "process denominator mismatch or duplicate")
    model_labels = {f"logit_l2_C{c}_degree{d}_rs0" for c in ("0.1", "1", "10") for d in (1, 2)}
    for row in cases:
        for field in ("answer_check_used_in_fit", "proxy_audit_used_outcome",
                      "proxy_audit_modified_registry"):
            require(not boolean(row[field]), f"boundary flag failed: {field}")
        for field in ("selection_receipt", "attribution_receipt"):
            require(bool(re.fullmatch(r"[0-9a-f]{64}", row[field])), f"invalid receipt: {field}")
        pool = integer(row["n_model_pool_occurrences"])
        holdout = integer(row["n_answer_check_occurrences"])
        require(pool > 0 and holdout > 0 and pool + holdout == 500, "occurrence partition mismatch")
        require(row["prediction_model_label"] in model_labels, "model label outside frozen grid")
    for row in process:
        truth = row["process"] in {"temperature", "water"} or (
            row["family"] == "omitted_driver" and row["process"] == "soil")
        require(boolean(row["expected_true_process"]) == truth, "known-truth label mismatch")
        adequate, noninferior, inferior, indeterminate, incomplete = [integer(row[k]) for k in (
            "n_absolute_adequate_routes", "n_noninferior_routes", "n_inferior_viable_routes",
            "n_indeterminate_viable_routes", "n_incomplete_routes")]
        expected_routes = integer(row["n_expected_routes"])
        require(1 <= expected_routes <= 6 and adequate <= expected_routes, "route denominator mismatch")
        require(incomplete == 0, "unexpected incomplete route in this historical bundle")
        require(noninferior + inferior + indeterminate == adequate, "route evidence partition mismatch")
        expected_status = (REQUIRED if adequate == 0 else REPLACEABLE if noninferior > 0
                           else CONTRIBUTORY if inferior == adequate else UNRESOLVED)
        require(row["status"] == expected_status, "process status disagrees with route counters")
        require(row["challenge_status"] == row["status"], "challenge status mismatch")
        detected = row["status"] in (CONTRIBUTORY, REQUIRED)
        require(boolean(row["process_detected"]) == detected and
                boolean(row["challenge_signal_detected"]) == detected, "challenge flag mismatch")
        require(not boolean(row["shared_information_contested"]) and
                (not detected or integer(row["n_attribution_relevant_shared_carriers"]) == 0),
                "unexpected contested attribution in this historical bundle")
        require(row["attribution_status"] == row["status"] and
                boolean(row["unique_process_evidence"]) == detected, "attribution mismatch")
        for version in ("v3", "v4"):
            require(row[f"{version}_status"] in STATUSES, "unknown previous process status")
            require(boolean(row[f"v5_changed_from_{version}"]) ==
                    (row["status"] != row[f"{version}_status"]), "status-change flag mismatch")
    for family, seed in expected_pairs:
        expected_counts = {r["n_expected_routes"] for r in process
                           if r["family"] == family and integer(r["seed"]) == seed}
        require(len(expected_counts) == 1, "inconsistent within-case baseline route denominator")
    require(decision["purpose"] == "interval_evidence_process_challenge_v5_development_decision",
            "wrong development decision")
    require(decision["development_only"] is True and
            decision["eligible_for_prospective_performance_claim"] is False and
            decision["product_a_reopened"] is False, "development boundary changed")
    require(decision["n_cases"] == 60 and decision["rank_margin"] == 0.02 and
            decision["density_margin_nats"] == 0.01, "decision denominator or margin mismatch")
    overall = metrics(process)
    equal_metrics(decision["overall_metrics"], overall)
    changes = sum(boolean(r["v5_changed_from_v4"]) for r in process)
    require(decision["n_v5_status_changes_from_v4"] == changes and
            decision["n_unresolved"] == overall["n_unresolved"], "decision count mismatch")
    require(len(family_metrics) == 6 and {r["family"] for r in family_metrics} == set(FAMILIES),
            "family metric denominator mismatch")
    for row in family_metrics:
        group = [r for r in process if r["family"] == row["family"]]
        expected = metrics(group)
        expected["n_v5_status_changes_from_v4"] = sum(boolean(r["v5_changed_from_v4"]) for r in group)
        equal_metrics({k: v for k, v in row.items() if k != "family"}, expected)
    transitions = Counter((boolean(r["expected_true_process"]), r["v4_status"], r["status"])
                          for r in process)
    return {
        "purpose": "completed_v5_development_artifact_readout_audit",
        "development_only": True, "eligible_for_prospective_performance_claim": False,
        "product_a_reopened": False, "new_simulation_or_fit_performed": False,
        "source_head_sha": HEAD_SHA, "source_run_id": RUN_ID, "source_artifact_id": ARTIFACT_ID,
        "archive_sha256": ARCHIVE_SHA256, "n_cases": len(cases), "n_process_cells": len(process),
        "overall_metrics": overall,
        "truth_status_counts": {
            label: {s: sum(boolean(r["expected_true_process"]) == truth and r["attribution_status"] == s
                            for r in process) for s in STATUSES}
            for label, truth in (("true", True), ("false", False))},
        "raw_v4_to_v5_transitions": [
            {"expected_true_process": t, "v4_status": old, "v5_status": new, "n": n}
            for (t, old, new), n in sorted(transitions.items())],
        "n_incomplete_routes": sum(integer(r["n_incomplete_routes"]) for r in process),
        "checks_passed": ["exact_case_and_process_denominators",
                          "strict_booleans_and_boundary_flags", "receipt_format",
                          "occurrence_partition_counts", "prediction_label_membership",
                          "truth_labels", "route_counter_status_consistency",
                          "attribution_consistency", "all_overall_and_family_metrics"],
        "scope_limit": "Artifact and summary consistency, not independent refitting or proof of no leakage. "
                       "Raw route intervals and occurrence-ID manifests are not in this bundle. "
                       "v4_status is pre-attribution; do not equate it with historical v4 unique attribution."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    tables, hashes = read_bundle(args.archive)
    result = validate_tables(tables)
    result["checks_passed"].insert(0, "archive_integrity")
    result["member_sha256"] = hashes
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
