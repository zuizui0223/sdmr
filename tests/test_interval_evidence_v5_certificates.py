"""Deterministic certificate/logic checks; no new known-truth cases or fits."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from itertools import combinations
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_v5_certificates", ROOT / "scripts" / "audit_interval_evidence_v5_certificates.py")
assert SPEC is not None and SPEC.loader is not None
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


@pytest.fixture
def tables():
    return MOD.AUDIT.read_bundle(MOD.AUDIT.DEFAULT_ARCHIVE)[0]


@pytest.fixture(scope="module")
def env():
    return MOD.load_decision_functions()


@pytest.fixture(scope="module")
def saved():
    return json.loads((MOD.AUDIT.DEFAULT_ARCHIVE.parent / "certificate_audit.json").read_text())


def test_readout_reproduces_without_mutation(tables, saved):
    before = deepcopy(tables)
    assert MOD.summarize(tables) == {k: v for k, v in saved.items() if k != "logic_audit"}
    assert tables == before


def test_actual_source_finite_state_checks(env, saved):
    result = MOD.check_logic(env)
    assert result == saved["logic_audit"]
    assert result["metric_state_patterns"] == 256
    assert result["process_state_multisets"] == result["nested_state_edges"] == 923
    assert result["nested_numeric_interval_pairs"] == 420
    assert result["strict_boundary_checks"] == 6
    assert "fit_interval_evidence_process_challenge" not in env


@pytest.mark.parametrize("costs", [[], [1], [3, 1, 2], [5, 3, 3, 2, 1, 3, 2, 1]])
def test_prefix_frontier_equals_bruteforce_subset_optimum(costs):
    before = costs[:]
    prefix = MOD.prefix_frontier(costs)
    for k in range(len(costs) + 1):
        assert prefix[k] == min(sum(subset) for subset in combinations(costs, k))
    assert costs == before


@pytest.mark.parametrize("costs", [[0], [-1], [1.0], [True], ["2"], [None]])
def test_invalid_certificate_units_rejected(costs):
    with pytest.raises(ValueError, match="positive integers"):
        MOD.prefix_frontier(costs)


def test_truth_and_case_burden(tables):
    result = MOD.summarize(tables)
    true, false = (result["truth_profiles"][label] for label in ("true", "false"))
    assert true["inferior_certificate_cost_histogram"] == {"1": 2, "2": 7, "3": 32, "5": 2}
    assert false["inferior_certificate_cost_histogram"] == {"2": 1, "3": 11, "5": 1}
    assert true["all_unresolved_to_contributory_route_cell_certificates"] == 122
    assert false["all_unresolved_to_contributory_route_cell_certificates"] == 40
    assert true["all_unresolved_to_replaceable_route_cell_certificates"] == 43
    assert false["all_unresolved_to_replaceable_route_cell_certificates"] == 13
    prefix = true["minimum_inferior_certificates_by_additional_challenges"]
    assert [prefix[k] for k in (0, 10, 20, 30, 40, 43)] == [0, 19, 49, 79, 109, 122]
    case = result["case_coverage"]
    assert case["currently_all_true_processes_challenged"] == 10
    assert case["blocked_by_at_least_one_true_replaceable"] == 30
    assert case["conditional_all_true_coverage_upper_count"] == 30
    assert case["potential_additional_complete_cases"] == 20
    assert case["inferior_certificates_for_all_potential_complete_cases"] == 78
    assert result["frontier_is_attainability_or_prospective_claim"] is False
    assert result["truth_used_only_for_retrospective_reporting"] is True
    assert result["new_simulation_or_fit_performed"] is False
    assert result["product_a_reopened"] is False


@pytest.mark.parametrize("symbols,status", [
    (("I", "U"), MOD.AUDIT.UNRESOLVED),
    (("N", "U"), MOD.AUDIT.REPLACEABLE),
    (("N", "E"), MOD.AUDIT.REPLACEABLE),
    (("N", "A"), MOD.AUDIT.UNRESOLVED),
    (("I", "I"), MOD.AUDIT.CONTRIBUTORY),
    (("X", "X"), MOD.AUDIT.REQUIRED),
])
def test_quantifier_precedence(env, symbols, status):
    assert MOD._actual_status(symbols, env) == status


def test_source_change_rejected_before_execution(tmp_path):
    source = tmp_path / "modified.py"
    source.write_bytes(MOD.SOURCE.read_bytes() + b"\nraise RuntimeError('must not execute')\n")
    with pytest.raises(ValueError, match="source blob mismatch"):
        MOD.load_decision_functions(source)


@pytest.mark.parametrize("mutation", ["duplicate", "seed", "truth", "boundary", "route"])
def test_no_bypass_of_original_artifact_contract(tables, mutation):
    if mutation == "duplicate":
        tables["process_evaluation.csv"][-1] = tables["process_evaluation.csv"][0].copy()
    elif mutation == "seed":
        tables["case_summary.csv"][0]["seed"] = "14001"
    elif mutation == "truth":
        r = tables["process_evaluation.csv"][0]
        r["expected_true_process"] = "False" if r["expected_true_process"] == "True" else "True"
    elif mutation == "boundary":
        tables["case_summary.csv"][0]["answer_check_used_in_fit"] = "True"
    else:
        tables["process_evaluation.csv"][0]["n_indeterminate_viable_routes"] = "99"
    with pytest.raises(ValueError):
        MOD.summarize(tables)


def test_cli_reproduces_saved_snapshot(tmp_path, saved):
    output = tmp_path / "certificate.json"
    assert MOD.main(["--output", str(output)]) == 0
    assert json.loads(output.read_text()) == saved
