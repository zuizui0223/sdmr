"""Retrospective information bounds for the pinned v5 route-counter summary.

No promotions are applied, no evidence is acquired, and no rule is selected.
Enumerated count pairs describe all deterministic signature-only postprocessors
on this burned artifact. Truth is used for scoring a mathematical envelope,
not as a classifier input. This is neither a fitted learner nor a new gate.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path

AUDIT_PATH = Path(__file__).with_name("audit_interval_evidence_v5_readout.py")
AUDIT_BLOB = "e7c8081bdb6a6be394a234018f910261d9ce9b82"
_raw = AUDIT_PATH.read_bytes()
_blob = hashlib.sha1(b"blob " + str(len(_raw)).encode() + b"\0" + _raw).hexdigest()
if _blob != AUDIT_BLOB:
    raise ValueError("pinned readout audit source changed")
_SPEC = importlib.util.spec_from_file_location("_collision_readout_audit", AUDIT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("cannot load the pinned readout audit")
AUDIT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(AUDIT)

# Explicit projection, fixed for this retrospective diagnostic. Identity,
# truth, historical status, proxy details and continuous scores are NOT inputs.
SIGNATURE_FIELDS = (
    "n_expected_routes",
    "n_absolute_adequate_routes",
    "n_noninferior_routes",
    "n_inferior_viable_routes",
    "n_indeterminate_viable_routes",
    "n_incomplete_routes",
)


def signature(row: dict[str, str]) -> tuple[int, ...]:
    """Return only the six recorded route counters, never an identity or truth."""
    return tuple(AUDIT.integer(row[field]) for field in SIGNATURE_FIELDS)


def attainable_count_pairs(counts: list[tuple[int, int]]) -> set[tuple[int, int]]:
    """Exact (true, false) promotion counts, not policies or altered statuses.

One bucket is indivisible for a deterministic signature-only rule. Dynamic
programming enumerates including/excluding each whole bucket; it stores no
selected bucket IDs and exports no postprocessing rule.
"""
    pairs = {(0, 0)}
    for true, false in counts:
        AUDIT.require(type(true) is int and type(false) is int
                      and true >= 0 and false >= 0 and true + false > 0,
                      "bucket counts must be nonnegative integers with positive total")
        pairs |= {(tp + true, fp + false) for tp, fp in pairs}
    return pairs


def nondominated_pairs(pairs: set[tuple[int, int]]) -> list[tuple[int, int]]:
    """All points maximizing true count while minimizing false count."""
    AUDIT.require(bool(pairs), "empty count-pair domain")
    best_at_false: dict[int, int] = {}
    for true, false in pairs:
        AUDIT.require(type(true) is int and type(false) is int and true >= 0 and false >= 0,
                      "invalid count pair")
        best_at_false[false] = max(true, best_at_false.get(false, -1))
    best_true = -1
    frontier = []
    for false, true in sorted(best_at_false.items()):
        if true > best_true:
            frontier.append((true, false))
            best_true = true
    return frontier


def _identity(row: dict[str, str]) -> dict[str, str | int]:
    # Used only to trace an existing collision, never to define its signature.
    return {"family": row["family"], "seed": AUDIT.integer(row["seed"]),
            "process": row["process"]}


def diagnose(tables: dict) -> dict:
    """Audit the immutable artifact first, then score its summary projection."""
    checked = AUDIT.validate_tables(tables)
    unresolved = [row for row in tables["process_evaluation.csv"]
                  if row["status"] == AUDIT.UNRESOLVED]
    buckets: dict[tuple[int, ...], list[dict[str, str]]] = defaultdict(list)
    for row in unresolved:
        buckets[signature(row)].append(row)
    groups = []
    witnesses = []
    counts = []
    for key, rows in sorted(buckets.items()):
        ordered = sorted(rows, key=lambda r: (r["family"], AUDIT.integer(r["seed"]), r["process"]))
        true = [row for row in ordered if AUDIT.boolean(row["expected_true_process"])]
        false = [row for row in ordered if not AUDIT.boolean(row["expected_true_process"])]
        counts.append((len(true), len(false)))
        named = dict(zip(SIGNATURE_FIELDS, key))
        groups.append({"signature": named, "true_cells": len(true), "false_cells": len(false)})
        if true and false:
            witnesses.append({"signature": named, "true_example": _identity(true[0]),
                              "false_example": _identity(false[0])})
    pairs = attainable_count_pairs(counts)
    frontier = nondominated_pairs(pairs)
    pure_true = sum(t for t, f in counts if f == 0)
    mixed_true = sum(t for t, f in counts if t > 0 and f > 0)
    mixed_false = sum(f for t, f in counts if t > 0 and f > 0)
    total_true = sum(t for t, _ in counts)
    total_false = sum(f for _, f in counts)
    # Independent checks of the two analytical endpoint formulas.
    AUDIT.require(max(tp for tp, fp in pairs if fp == 0) == pure_true,
                  "zero-false endpoint disagrees with partition theorem")
    AUDIT.require(min(fp for tp, fp in pairs if tp == total_true) == mixed_false,
                  "full-true endpoint disagrees with partition theorem")
    m = checked["overall_metrics"]
    tp0 = m["n_challenge_detected_true_processes"]
    fp0 = m["n_challenge_detected_false_processes"]
    return {
        "purpose": "post_outcome_v5_summary_collision_information_bound",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "product_a_reopened": False,
        "new_simulation_or_fit_performed": False,
        "new_route_evidence_acquired": False,
        "original_statuses_modified": False,
        "postprocessing_policy_selected_or_exported": False,
        "source_head_sha": checked["source_head_sha"],
        "source_run_id": checked["source_run_id"],
        "archive_sha256": checked["archive_sha256"],
        "readout_audit_git_blob": AUDIT_BLOB,
        "n_cases": checked["n_cases"],
        "n_process_cells": checked["n_process_cells"],
        "signature_fields": list(SIGNATURE_FIELDS),
        "rule_class": "deterministic, same decision for identical six-counter signatures; "
                      "only currently unresolved cells may be promoted; decided statuses fixed",
        "excluded_rule_inputs": ["family", "seed", "process", "expected_true_process",
                                 "v3_status", "v4_status", "proxy/shared-carrier details",
                                 "continuous scores", "route labels", "row order"],
        "n_unresolved_cells": len(unresolved),
        "n_true_unresolved": total_true,
        "n_false_unresolved": total_false,
        "n_signatures": len(groups),
        "n_mixed_truth_signatures": len(witnesses),
        "true_cells_in_mixed_signatures": mixed_true,
        "false_cells_in_mixed_signatures": mixed_false,
        "extra_true_ceiling_with_zero_extra_false": pure_true,
        "total_true_ceiling_with_zero_extra_false": tp0 + pure_true,
        "total_true_recall_ceiling_with_zero_extra_false": (tp0 + pure_true) / m["n_true_processes"],
        "extra_false_floor_when_all_true_unresolved_promoted": mixed_false,
        "n_signature_subsets": 2 ** len(groups),
        "n_distinct_attainable_count_pairs": len(pairs),
        "signature_groups": groups,
        "mixed_signature_witnesses": witnesses,
        "complete_nondominated_count_frontier": [
            {"extra_true": tp, "extra_false": fp,
             "total_true": tp0 + tp, "total_false": fp0 + fp,
             "total_true_recall": (tp0 + tp) / m["n_true_processes"],
             "total_false_rate": (fp0 + fp) / m["n_false_processes"]}
            for tp, fp in frontier
        ],
        "observed_metrics_unchanged": m,
        "interpretation": "In-sample oracle envelope, not a deployable or validated rule. "
                          "A raw summary-only promotion does not supply the interval evidence "
                          "required by the unchanged v5 contract. No promotion is performed.",
        "scope_limit": "A limitation of this explicit six-counter projection on this artifact, "
                       "not all recorded information, process-aware rules, additional observations, "
                       "future performance, or ecological identifiability. Unlike the previous "
                       "nested-refinement bounds, this diagnostic acquires no new evidence.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=AUDIT.DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    tables, _ = AUDIT.read_bundle(args.archive)
    text = json.dumps(diagnose(tables), indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
