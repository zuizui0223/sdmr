"""Pinned v5 decision-logic and certificate-burden audit; no fitting or tuning.

Uses the already-burned artifact. A certificate unit is one indeterminate
route-cell becoming inferior, NOT a sample, job, model fit, or intervention.
Frontiers are exact only in a relaxed, independently resolvable state algebra.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import importlib.util
from itertools import combinations_with_replacement, product
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "sdmr" / "interval_evidence_process_challenge.py"
SOURCE_BLOB = "969e335e10595f2cd818553e1be290bce530360c"
SPEC = importlib.util.spec_from_file_location(
    "_certificate_readout_audit", Path(__file__).with_name("audit_interval_evidence_v5_readout.py")
)
if SPEC is None or SPEC.loader is None:
    raise ImportError("cannot load the pinned-artifact audit")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
require = AUDIT.require


STATE_NAMES = {"N": "noninferior", "I": "inferior", "U": "indeterminate", "E": "incomplete"}
METRICS = (
    ("mean_prediction_delta_vs_baseline", "prediction_delta_sem", "prediction_interval_state", 0.02),
    ("mean_ecological_delta_vs_baseline", "ecological_delta_sem", "ecological_rank_interval_state", 0.02),
    ("mean_density_delta_vs_baseline", "density_delta_sem", "density_interval_state", 0.01),
    ("mean_ecological_density_delta_vs_baseline", "ecological_density_delta_sem", "ecological_density_interval_state", 0.01),
)


def load_decision_functions(source: Path = SOURCE) -> dict:
    """Execute only three hash-pinned function ASTs, never module-level fits.

The ASTs are copied without edits from the actual versioned source. This keeps
module imports, fitting entrypoints and simulation code out of this audit.
"""
    import numpy as np
    import pandas as pd

    raw = source.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    require(blob == SOURCE_BLOB, "v5 decision source blob mismatch")
    tree = ast.parse(raw.decode("utf-8"), filename=str(source))
    names = {"interval_evidence_state", "_enrich_routes", "_classify_processes"}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    require({node.name for node in functions} == names and len(functions) == 3, "missing decision functions")
    future = ast.parse("from __future__ import annotations").body[0]
    isolated = ast.Module(body=[future, *functions], type_ignores=[])
    env = {"np": np, "pd": pd, "CONTRIBUTORY": AUDIT.CONTRIBUTORY,
           "REPLACEABLE": AUDIT.REPLACEABLE, "REQUIRED": AUDIT.REQUIRED,
           "UNRESOLVED": AUDIT.UNRESOLVED,
           "NONINFERIOR_EVIDENCE": STATE_NAMES["N"], "INFERIOR_EVIDENCE": STATE_NAMES["I"],
           "INDETERMINATE_EVIDENCE": STATE_NAMES["U"], "INCOMPLETE_EVIDENCE": STATE_NAMES["E"]}
    exec(compile(ast.fix_missing_locations(isolated), str(source), "exec"), env)
    require("fit_interval_evidence_process_challenge" not in env, "fit entrypoint loaded")
    return env


def _frame(symbols: tuple[str, ...], env: dict):
    # X: complete and absolutely inadequate; A: absolute evidence incomplete.
    return env["pd"].DataFrame([
        {"model_label": f"route_{i}", "excluded_process": "p",
         "complete": symbol != "A", "route_adequate": symbol not in ("X", "A"),
         "relative_evidence_state": STATE_NAMES.get(symbol, STATE_NAMES["E"])}
        for i, symbol in enumerate(symbols)
    ])


def _actual_status(symbols: tuple[str, ...], env: dict, *, reverse: bool = False) -> str:
    frame = _frame(symbols, env)
    if reverse:
        frame = frame.iloc[::-1]
    result = env["_classify_processes"](frame, ("p",), expected_model_labels=tuple(frame["model_label"]))
    return str(result.iloc[0]["status"])


def _oracle_status(symbols: tuple[str, ...]) -> str:
    if "A" in symbols:
        return AUDIT.UNRESOLVED
    viable = [s for s in symbols if s != "X"]
    if not viable:
        return AUDIT.REQUIRED
    if "N" in viable:
        return AUDIT.REPLACEABLE
    return AUDIT.CONTRIBUTORY if all(s == "I" for s in viable) else AUDIT.UNRESOLVED


def _metric_rows(patterns):
    rows = []
    for pattern in patterns:
        row = {"relative_complete": True, "density_complete": True}
        for state, (mean_key, sem_key, _, margin) in zip(pattern, METRICS):
            row[mean_key] = -margin + {"N": 0.04, "I": -0.04, "U": 0.0, "E": 0.0}[state]
            row[sem_key] = float("nan") if state == "E" else 0.005
        rows.append(row)
    return rows


def check_logic(env: dict) -> dict:
    """Finite-state conformance checks plus deterministic interval fixtures.

State representatives exhaust the declared reduced domains, not all possible
floating-point inputs or all upstream fitting behavior. See the written proof.
"""
    interval = env["interval_evidence_state"]
    boundary_checks = 0
    nested_pairs = 0
    grid = (-0.125, -0.0625, -0.03125, -0.015625, 0.0, 0.03125, 0.0625)
    for margin in (0.02, 0.01):
        boundary = -margin - 1e-12
        for mean, expected in ((env["np"].nextafter(boundary, -float("inf")), "inferior"),
                               (boundary, "noninferior"),
                               (env["np"].nextafter(boundary, float("inf")), "noninferior")):
            require(interval(mean, 0.0, margin=margin, sem_multiplier=1.0)["state"] == expected,
                    "strict boundary convention mismatch")
            boundary_checks += 1
        bands = [interval((lo + hi) / 2, (hi - lo) / 2, margin=margin, sem_multiplier=1.0)
                 for lo, hi in combinations_with_replacement(grid, 2)]
        require({b["state"] for b in bands} == {"noninferior", "inferior", "indeterminate"},
                "interval fixtures lack state coverage")
        for parent in bands:
            for child in bands:
                if parent["lower"] <= child["lower"] and child["upper"] <= parent["upper"]:
                    if parent["state"] != "indeterminate":
                        require(parent["state"] == child["state"], "nested refinement changed decided metric")
                    nested_pairs += 1

    patterns = list(product("NIUE", repeat=4))
    enriched = env["_enrich_routes"](
        SimpleNamespace(route_summary=env["pd"].DataFrame(_metric_rows(patterns))),
        rank_margin=0.02, rank_sem_multiplier=1.0, density_margin=0.01, density_sem_multiplier=1.0)
    for pattern, row in zip(patterns, enriched.to_dict("records")):
        expected = "E" if "E" in pattern else "N" if all(s == "N" for s in pattern) else "I" if "I" in pattern else "U"
        require(row["relative_evidence_state"] == STATE_NAMES[expected], "route logic mismatch")
        require(tuple(row[m[2]] for m in METRICS) == tuple(STATE_NAMES[s] for s in pattern),
                "individual metric state mismatch")

    statuses = {}
    for n in range(1, 7):
        for symbols in combinations_with_replacement("XNIUEA", n):
            actual = _actual_status(symbols, env)
            require(actual == _oracle_status(symbols), "process quantifier mismatch")
            require(_actual_status(symbols, env, reverse=True) == actual, "route order changed status")
            statuses[tuple(sorted(symbols))] = actual
    edges = 0
    for n in range(1, 7):
        for symbols in combinations_with_replacement("XNIU", n):
            old = statuses[tuple(sorted(symbols))]
            u = symbols.count("U")
            fixed = tuple(s for s in symbols if s != "U")
            for nn in range(u + 1):
                for ni in range(u - nn + 1):
                    refined = fixed + ("N",) * nn + ("I",) * ni + ("U",) * (u - nn - ni)
                    new = statuses[tuple(sorted(refined))]
                    if old != AUDIT.UNRESOLVED:
                        require(new == old, "refinement changed decided process")
                    else:
                        require(new != AUDIT.REQUIRED, "relative refinement created necessity")
                    edges += 1

    # Every route may have a DIFFERENT inferior metric: forall route exists metric.
    crossed = (("I", "N", "N", "N"), ("N", "N", "I", "N"))
    require(not any(all(row[j] == "I" for row in crossed) for j in range(4)), "bad quantifier fixture")
    require(all(any(s == "I" for s in row) for row in crossed), "bad crossed-inferiority fixture")
    require(_actual_status(("I", "I"), env) == AUDIT.CONTRIBUTORY, "quantifier swap")

    invalid_checks = 0
    normal = _frame(("I", "I"), env)
    for altered in (normal.iloc[:1], normal.assign(model_label=["route_0", "alien"]),
                    normal.iloc[:0]):
        result = env["_classify_processes"](altered, ("p",), expected_model_labels=("route_0", "route_1"))
        require(result.iloc[0]["status"] == AUDIT.UNRESOLVED, "incomplete route set did not abstain")
        invalid_checks += 1
    duplicated = env["pd"].concat([normal, normal.iloc[:1]], ignore_index=True)
    try:
        env["_classify_processes"](duplicated, ("p",), expected_model_labels=("route_0", "route_1"))
    except ValueError:
        invalid_checks += 1
    else:
        raise ValueError("duplicate routes not rejected")
    return {"source_git_blob": SOURCE_BLOB, "actual_source_functions_checked": 3,
            "metric_state_patterns": len(patterns), "process_state_multisets": len(statuses),
            "reverse_order_checks": len(statuses), "nested_state_edges": edges,
            "nested_numeric_interval_pairs": nested_pairs, "strict_boundary_checks": boundary_checks,
            "missing_extra_duplicate_route_checks": invalid_checks, "crossed_metric_quantifiers_checked": True,
            "scope": "Reduced finite-state conformance and deterministic numeric fixtures; not full floating-point verification or refitting."}


def prefix_frontier(costs: list[int]) -> list[int]:
    """Minimum route-cell certificates for each additional count, in the relaxation."""
    require(all(type(c) is int and c > 0 for c in costs), "certificate costs must be positive integers")
    result = [0]
    for cost in sorted(costs):
        result.append(result[-1] + cost)
    return result


def summarize(tables: dict) -> dict:
    audit = AUDIT.validate_tables(tables)
    rows = tables["process_evaluation.csv"]
    profiles = {}
    for label, truth in (("true", True), ("false", False)):
        group = [r for r in rows if AUDIT.boolean(r["expected_true_process"]) == truth]
        unresolved = [r for r in group if r["status"] == AUDIT.UNRESOLVED]
        costs = [AUDIT.integer(r["n_indeterminate_viable_routes"]) for r in unresolved]
        profiles[label] = {
            "n_cells": len(group),
            "current_challenges": sum(AUDIT.boolean(r["challenge_signal_detected"]) for r in group),
            "unresolved_cells": len(unresolved),
            "inferior_certificate_cost_histogram": {str(k): v for k, v in sorted(Counter(costs).items())},
            "all_unresolved_to_contributory_route_cell_certificates": sum(costs),
            "all_unresolved_to_replaceable_route_cell_certificates": len(unresolved),
            "minimum_inferior_certificates_by_additional_challenges": prefix_frontier(costs),
        }
    current_all = 0
    blocked = 0
    case_costs = []
    for case in tables["case_summary.csv"]:
        group = [r for r in rows if r["family"] == case["family"] and r["seed"] == case["seed"]
                 and AUDIT.boolean(r["expected_true_process"])]
        if any(r["status"] == AUDIT.REPLACEABLE for r in group):
            blocked += 1
        else:
            cost = sum(AUDIT.integer(r["n_indeterminate_viable_routes"]) for r in group
                       if r["status"] == AUDIT.UNRESOLVED)
            if cost:
                case_costs.append(cost)
            else:
                current_all += 1
    return {
        "purpose": "post_outcome_v5_certificate_burden_and_case_coverage",
        "development_only": True, "eligible_for_prospective_performance_claim": False,
        "product_a_reopened": False, "new_simulation_or_fit_performed": False,
        "source_run_id": audit["source_run_id"], "source_head_sha": audit["source_head_sha"],
        "archive_sha256": audit["archive_sha256"], "overall_metrics_unchanged": audit["overall_metrics"],
        "certificate_unit": "one indeterminate route-cell becoming inferior (not sample, job, fit, or intervention)",
        "assumptions": ["fixed route sets, absolute adequacy, completeness, margins and comparator",
                        "nonempty nested metric bands preserving already decided metric states",
                        "route-cell outcomes counted separately; shared data may couple their changes"],
        "frontier_exact_only_in_independent_state_relaxation": True,
        "frontier_is_attainability_or_prospective_claim": False,
        "truth_used_only_for_retrospective_reporting": True,
        "truth_profiles": profiles,
        "case_coverage": {"n_cases": len(tables["case_summary.csv"]),
                          "currently_all_true_processes_challenged": current_all,
                          "blocked_by_at_least_one_true_replaceable": blocked,
                          "conditional_all_true_coverage_upper_count": current_all + len(case_costs),
                          "potential_additional_complete_cases": len(case_costs),
                          "inferior_certificates_for_all_potential_complete_cases": sum(case_costs),
                          "minimum_inferior_certificates_by_additional_complete_cases": prefix_frontier(case_costs)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=AUDIT.DEFAULT_ARCHIVE)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    tables, _ = AUDIT.read_bundle(args.archive)
    result = summarize(tables)
    result["logic_audit"] = check_logic(load_decision_functions(args.source))
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
