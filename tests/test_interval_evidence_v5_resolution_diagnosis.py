"""Regression checks on retrospective summaries, not new scientific gates."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "diagnose_v5_resolution", ROOT / "scripts" / "diagnose_interval_evidence_v5_resolution.py"
)
assert SPEC is not None and SPEC.loader is not None
DIAG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAG)


@pytest.fixture
def tables():
    return DIAG.AUDIT.read_bundle(DIAG.AUDIT.DEFAULT_ARCHIVE)[0]


def test_saved_diagnosis_reproduces_and_inputs_unchanged(tables):
    before = deepcopy(tables)
    result = DIAG.diagnose(tables)
    saved = json.loads((DIAG.AUDIT.DEFAULT_ARCHIVE.parent / "resolution_diagnosis.json").read_text())
    assert result == saved
    assert tables == before


@pytest.mark.parametrize("process,truth,expected", [
    ("temperature", True, (60, 14, 23, 23, 37)),
    ("water", True, (60, 32, 8, 20, 52)),
    ("soil", True, (10, 3, 7, 0, 3)),
    ("soil", False, (50, 0, 49, 1, 1)),
    ("seasonality", False, (60, 0, 48, 12, 12)),
    ("noise", False, (60, 0, 60, 0, 0)),
])
def test_process_profiles(tables, process, truth, expected):
    row = next(r for r in DIAG.diagnose(tables)["process_profiles"]
               if r["process"] == process and r["expected_true_process"] == truth)
    fields = ("n_cells", "contributory", "replaceable", "unresolved",
              "conditional_nested_refinement_challenge_upper_count")
    assert tuple(row[key] for key in fields) == expected
    assert row["required"] == 0


def test_conditional_bound_and_abstention_partition(tables):
    result = DIAG.diagnose(tables)
    true = result["truth_profiles"]["true"]
    false = result["truth_profiles"]["false"]
    assert true["conditional_nested_refinement_challenge_upper_count"] == 92
    assert true["conditional_nested_refinement_challenge_upper_rate"] == 92 / 130
    assert false["conditional_nested_refinement_challenge_upper_count"] == 13
    assert false["conditional_nested_refinement_challenge_upper_rate"] == 13 / 170
    assert true["unresolved_mixed_inferior_and_indeterminate"] == 41
    assert true["unresolved_all_viable_routes_indeterminate"] == 2
    assert false["unresolved_mixed_inferior_and_indeterminate"] == 2
    assert false["unresolved_all_viable_routes_indeterminate"] == 11
    assert result["case_true_challenge_coverage"] == {"all": 10, "partial": 28, "none": 22}
    assert sum(r["n_cells"] for r in result["unresolved_route_counter_patterns"]) == 56
    assert result["bound_is_attainability_or_future_performance_claim"] is False
    assert len(result["bound_assumptions"]) == 5
    assert result["eligible_for_prospective_performance_claim"] is False
    assert result["product_a_reopened"] is False
    assert result["new_simulation_or_fit_performed"] is False


@pytest.mark.parametrize("mutation", ["duplicate", "truth", "route", "sealed"])
def test_diagnosis_does_not_bypass_audit(tables, mutation):
    if mutation == "duplicate":
        tables["process_evaluation.csv"][-1] = tables["process_evaluation.csv"][0].copy()
    elif mutation == "truth":
        row = tables["process_evaluation.csv"][0]
        row["expected_true_process"] = "False" if row["expected_true_process"] == "True" else "True"
    elif mutation == "route":
        tables["process_evaluation.csv"][0]["n_incomplete_routes"] = "1"
    else:
        tables["case_summary.csv"][0]["answer_check_used_in_fit"] = "True"
    with pytest.raises(ValueError):
        DIAG.diagnose(tables)


def test_cli_reproduces_json(tmp_path, tables):
    output = tmp_path / "diagnosis.json"
    assert DIAG.main(["--output", str(output)]) == 0
    assert json.loads(output.read_text()) == DIAG.diagnose(tables)


def test_empty_profile_fails():
    with pytest.raises(ValueError, match="empty"):
        DIAG._profile([])
