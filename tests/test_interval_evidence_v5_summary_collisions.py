"""Artifact-only collision and finite-partition theorem regression tests."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from itertools import product
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "summary_collision_audit", ROOT / "scripts" / "audit_interval_evidence_v5_summary_collisions.py"
)
assert SPEC is not None and SPEC.loader is not None
COLLISION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLISION)


@pytest.fixture
def tables():
    return COLLISION.AUDIT.read_bundle(COLLISION.AUDIT.DEFAULT_ARCHIVE)[0]


def _exhaustive(counts):
    return {(sum(t * use for (t, _), use in zip(counts, flags)),
             sum(f * use for (_, f), use in zip(counts, flags)))
            for flags in product((0, 1), repeat=len(counts))}


def test_saved_audit_reproduces_without_mutation(tables):
    original = deepcopy(tables)
    result = COLLISION.diagnose(tables)
    saved = json.loads((COLLISION.AUDIT.DEFAULT_ARCHIVE.parent / "summary_collision_audit.json").read_text())
    assert result == saved
    assert tables == original
    assert result["observed_metrics_unchanged"] == COLLISION.AUDIT.validate_tables(tables)["overall_metrics"]


def test_all_actual_512_signature_subsets_match_dynamic_program(tables):
    result = COLLISION.diagnose(tables)
    counts = [(r["true_cells"], r["false_cells"]) for r in result["signature_groups"]]
    assert len(counts) == 9
    actual = COLLISION.attainable_count_pairs(counts)
    assert actual == _exhaustive(counts)
    assert len(actual) == 216
    assert result["n_signature_subsets"] == 512
    assert COLLISION.nondominated_pairs(actual) == [(37, 0), (39, 1), (41, 2), (43, 9)]
    assert result["total_true_ceiling_with_zero_extra_false"] == 86
    assert result["total_true_recall_ceiling_with_zero_extra_false"] == 86 / 130
    assert result["extra_false_floor_when_all_true_unresolved_promoted"] == 9


def test_collision_counts_and_traceable_witnesses(tables):
    result = COLLISION.diagnose(tables)
    assert result["n_mixed_truth_signatures"] == 3
    assert result["true_cells_in_mixed_signatures"] == 6
    assert result["false_cells_in_mixed_signatures"] == 9
    for witness in result["mixed_signature_witnesses"]:
        for field, truth in (("true_example", True), ("false_example", False)):
            identity = witness[field]
            row = next(r for r in tables["process_evaluation.csv"]
                       if r["family"] == identity["family"] and int(r["seed"]) == identity["seed"]
                       and r["process"] == identity["process"])
            assert COLLISION.AUDIT.boolean(row["expected_true_process"]) is truth
            assert row["status"] == COLLISION.AUDIT.UNRESOLVED
            assert dict(zip(COLLISION.SIGNATURE_FIELDS, COLLISION.signature(row))) == witness["signature"]
    mixed = [g for g in result["signature_groups"] if g["true_cells"] and g["false_cells"]]
    assert [(g["true_cells"], g["false_cells"]) for g in mixed] == [(2, 7), (2, 1), (2, 1)]


@pytest.mark.parametrize("field", ["family", "seed", "process", "expected_true_process",
                                   "v3_status", "v4_status", "max_shared_univariate_cv_r2",
                                   "qualifying_shared_carrier_predictors"])
def test_signature_cannot_read_truth_identity_or_proxy_details(tables, field):
    row = tables["process_evaluation.csv"][0]
    modified = dict(row, **{field: "intentionally-unusable-as-a-predictor"})
    assert COLLISION.signature(modified) == COLLISION.signature(row)


def test_exact_feature_projection(tables):
    row = tables["process_evaluation.csv"][0]
    assert len(COLLISION.SIGNATURE_FIELDS) == 6
    for field in COLLISION.SIGNATURE_FIELDS:
        altered = dict(row, **{field: str(int(row[field]) + 1)})
        assert COLLISION.signature(altered) != COLLISION.signature(row)


@pytest.mark.parametrize("counts", [[], [(3, 0)], [(0, 4)], [(2, 7)],
                                    [(2, 1), (2, 1)], [(1, 2), (4, 3), (2, 0)],
                                    [(0, 2), (3, 1), (2, 4), (1, 0)]])
def test_partition_endpoint_formulas_and_pareto_by_brute_force(counts):
    pairs = COLLISION.attainable_count_pairs(counts)
    assert pairs == _exhaustive(counts)
    total_true = sum(t for t, _ in counts)
    assert max(t for t, f in pairs if f == 0) == sum(t for t, f in counts if f == 0)
    assert min(f for t, f in pairs if t == total_true) == sum(f for t, f in counts if t > 0)
    brute = sorted((p for p in pairs if not any(
        q != p and q[0] >= p[0] and q[1] <= p[1] for q in pairs)), key=lambda p: p[1])
    assert COLLISION.nondominated_pairs(pairs) == brute
    assert COLLISION.attainable_count_pairs(list(reversed(counts))) == pairs


@pytest.mark.parametrize("counts", [[(True, 1)], [(1, False)], [(1.0, 2)],
                                     [(1, -1)], [(0, 0)], [("1", 0)]])
def test_invalid_bucket_counts_rejected(counts):
    with pytest.raises(ValueError, match="bucket counts"):
        COLLISION.attainable_count_pairs(counts)


@pytest.mark.parametrize("pairs", [set(), {(-1, 0)}, {(0, -1)}, {(True, 0)}, {(1, 1.0)}])
def test_invalid_frontier_domain_rejected(pairs):
    with pytest.raises(ValueError):
        COLLISION.nondominated_pairs(pairs)


@pytest.mark.parametrize("fault", ["duplicate_case", "duplicate_process", "truth", "route", "sealed", "metric"])
def test_invalid_artifact_cannot_reach_collision_readout(tables, fault):
    if fault.startswith("duplicate"):
        name = "case_summary.csv" if fault == "duplicate_case" else "process_evaluation.csv"
        tables[name][-1] = tables[name][0].copy()
    elif fault == "truth":
        row = tables["process_evaluation.csv"][0]
        row["expected_true_process"] = "False" if row["expected_true_process"] == "True" else "True"
    elif fault == "route":
        tables["process_evaluation.csv"][0]["n_incomplete_routes"] = "1"
    elif fault == "sealed":
        tables["case_summary.csv"][0]["answer_check_used_in_fit"] = "True"
    else:
        tables["development_decision.json"]["overall_metrics"]["n_unresolved"] = 55
    with pytest.raises(ValueError):
        COLLISION.diagnose(tables)


def test_order_independence_and_no_policy_or_science_change(tables):
    original = COLLISION.diagnose(tables)
    for name in ("case_summary.csv", "process_evaluation.csv", "family_metrics.csv"):
        tables[name].reverse()
    assert COLLISION.diagnose(tables) == original
    for field in ("eligible_for_prospective_performance_claim", "product_a_reopened",
                  "new_simulation_or_fit_performed", "new_route_evidence_acquired",
                  "original_statuses_modified", "postprocessing_policy_selected_or_exported"):
        assert original[field] is False
    assert original["n_cases"] == 60 and original["n_process_cells"] == 300


def test_cli_reproduces_and_rejects_changed_archive(tmp_path, tables):
    output = tmp_path / "collision.json"
    archive = COLLISION.AUDIT.DEFAULT_ARCHIVE
    before = archive.read_bytes()
    assert COLLISION.main(["--output", str(output)]) == 0
    assert json.loads(output.read_text()) == COLLISION.diagnose(tables)
    assert archive.read_bytes() == before
    invalid = tmp_path / "corrupt.zip"
    invalid.write_bytes(before + b"changed")
    with pytest.raises(ValueError, match="SHA256"):
        COLLISION.main(["--archive", str(invalid), "--output", str(output)])
