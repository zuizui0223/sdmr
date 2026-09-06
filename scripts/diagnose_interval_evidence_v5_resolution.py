"""Post-outcome diagnosis of the pinned v5 aggregate; never fits or retunes.

Read only the already-burned development summaries. Nested-refinement bounds
are conditional algebra, not a proposed intervention, confidence interval,
prospective gate, or performance forecast. No RNG or sdmr learner imports.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_v5_readout_audit", Path(__file__).with_name("audit_interval_evidence_v5_readout.py")
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("cannot load the sibling pinned-artifact audit")
AUDIT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(AUDIT)


BOUND_ASSUMPTIONS = (
    "same cases, processes, expected route labels and reference comparisons",
    "absolute adequacy and completeness remain fixed",
    "every relative metric band is a nonempty subset of its original band",
    "rank/density margins, SEM settings and numerical comparators remain fixed",
    "bound concerns raw process challenge, not stability of unique attribution",
)


def _profile(rows: list[dict[str, str]]) -> dict:
    counts = Counter(row["status"] for row in rows)
    n = len(rows)
    if not n:
        raise ValueError("empty diagnostic stratum")
    detected = counts[AUDIT.CONTRIBUTORY] + counts[AUDIT.REQUIRED]
    unresolved = [row for row in rows if row["status"] == AUDIT.UNRESOLVED]
    mixed = sum(AUDIT.integer(row["n_inferior_viable_routes"]) > 0 for row in unresolved)
    return {
        "n_cells": n,
        "contributory": counts[AUDIT.CONTRIBUTORY],
        "replaceable": counts[AUDIT.REPLACEABLE],
        "unresolved": counts[AUDIT.UNRESOLVED],
        "required": counts[AUDIT.REQUIRED],
        "challenge_detected": detected,
        "challenge_rate": detected / n,
        "unresolved_mixed_inferior_and_indeterminate": mixed,
        "unresolved_all_viable_routes_indeterminate": len(unresolved) - mixed,
        "conditional_nested_refinement_challenge_upper_count": detected + len(unresolved),
        "conditional_nested_refinement_challenge_upper_rate": (detected + len(unresolved)) / n,
    }


def diagnose(tables: dict) -> dict:
    """Validate first; summarize without mutating tables or scientific outputs."""
    audit = AUDIT.validate_tables(tables)
    rows = tables["process_evaluation.csv"]
    profiles = []
    for process in AUDIT.PROCESSES:
        for truth in (True, False):
            group = [row for row in rows if row["process"] == process
                     and AUDIT.boolean(row["expected_true_process"]) == truth]
            if group:
                profiles.append({"process": process, "expected_true_process": truth,
                                 **_profile(group)})
    truth_profiles = {
        label: _profile([row for row in rows
                         if AUDIT.boolean(row["expected_true_process"]) == truth])
        for label, truth in (("true", True), ("false", False))
    }
    case_counts: Counter[str] = Counter()
    for case in tables["case_summary.csv"]:
        group = [row for row in rows if row["family"] == case["family"]
                 and row["seed"] == case["seed"]
                 and AUDIT.boolean(row["expected_true_process"])]
        n = sum(AUDIT.boolean(row["challenge_signal_detected"]) for row in group)
        category = "none" if n == 0 else "all" if n == len(group) else "partial"
        case_counts[category] += 1
    patterns = Counter(
        (AUDIT.boolean(row["expected_true_process"]),
         AUDIT.integer(row["n_absolute_adequate_routes"]),
         AUDIT.integer(row["n_inferior_viable_routes"]),
         AUDIT.integer(row["n_indeterminate_viable_routes"]))
        for row in rows if row["status"] == AUDIT.UNRESOLVED
    )
    return {
        "purpose": "post_outcome_v5_resolution_diagnosis",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "product_a_reopened": False,
        "new_simulation_or_fit_performed": False,
        "source_head_sha": audit["source_head_sha"],
        "source_run_id": audit["source_run_id"],
        "archive_sha256": audit["archive_sha256"],
        "n_cases": audit["n_cases"],
        "n_process_cells": audit["n_process_cells"],
        "bound_assumptions": list(BOUND_ASSUMPTIONS),
        "bound_is_attainability_or_future_performance_claim": False,
        "truth_profiles": truth_profiles,
        "process_profiles": profiles,
        "case_true_challenge_coverage": {key: case_counts[key] for key in ("all", "partial", "none")},
        "unresolved_route_counter_patterns": [
            {"expected_true_process": truth, "adequate": adequate,
             "inferior": inferior, "indeterminate": indeterminate, "n_cells": n}
            for (truth, adequate, inferior, indeterminate), n in sorted(patterns.items())
        ],
        "unavailable_from_aggregate": [
            "which model labels supply each relative evidence state",
            "which rank/density metric or spatial fold binds each route",
            "actual interval endpoints or joint feasibility of interval refinements",
            "independent refitting, receipt recomputation or leakage proof",
        ],
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
