"""Integrity regression tests; no new simulation denominator or model fits."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_interval_evidence_v5_readout", ROOT / "scripts" / "audit_interval_evidence_v5_readout.py"
)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


@pytest.fixture
def bundle():
    tables, _ = AUDIT.read_bundle(AUDIT.DEFAULT_ARCHIVE)
    return deepcopy(tables)


def test_pinned_bundle_and_readout_reproduce(bundle):
    result = AUDIT.validate_tables(bundle)
    _, hashes = AUDIT.read_bundle(AUDIT.DEFAULT_ARCHIVE)
    result["checks_passed"].insert(0, "archive_integrity")
    result["member_sha256"] = hashes
    saved = json.loads((AUDIT.DEFAULT_ARCHIVE.parent / "readout_audit.json").read_text())
    assert result == saved
    m = result["overall_metrics"]
    assert [m[k] for k in ("n_contributory", "n_replaceable", "n_unresolved", "n_required")] == [49, 195, 56, 0]
    assert m["n_challenge_detected_true_processes"] == 49
    assert m["n_challenge_detected_false_processes"] == 0
    assert result["truth_status_counts"]["true"][AUDIT.UNRESOLVED] == 43
    assert result["truth_status_counts"]["false"][AUDIT.UNRESOLVED] == 13


@pytest.mark.parametrize("member", ["case_summary.csv", "process_evaluation.csv", "family_metrics.csv"])
def test_reject_duplicate_and_missing_denominators(bundle, member):
    bundle[member][-1] = bundle[member][0].copy()
    with pytest.raises(ValueError, match="denominator"):
        AUDIT.validate_tables(bundle)


@pytest.mark.parametrize("member", ["case_summary.csv", "process_evaluation.csv"])
def test_reject_missing_row(bundle, member):
    bundle[member].pop()
    with pytest.raises(ValueError, match="denominator"):
        AUDIT.validate_tables(bundle)


@pytest.mark.parametrize("value", ["", "false", "0", "NaN", "null"])
def test_reject_noncanonical_boundary_boolean(bundle, value):
    bundle["case_summary.csv"][0]["answer_check_used_in_fit"] = value
    with pytest.raises(ValueError, match="boolean"):
        AUDIT.validate_tables(bundle)


@pytest.mark.parametrize("field", ["answer_check_used_in_fit", "proxy_audit_used_outcome", "proxy_audit_modified_registry"])
def test_reject_boundary_violation(bundle, field):
    bundle["case_summary.csv"][0][field] = "True"
    with pytest.raises(ValueError, match="boundary"):
        AUDIT.validate_tables(bundle)


@pytest.mark.parametrize("member,field,value,message", [
    ("case_summary.csv", "seed", "14001", "denominator"),
    ("process_evaluation.csv", "process", "unknown", "denominator"),
    ("process_evaluation.csv", "expected_true_process", "True", "truth"),
    ("case_summary.csv", "selection_receipt", "", "receipt"),
    ("case_summary.csv", "n_model_pool_occurrences", "500", "partition"),
    ("case_summary.csv", "prediction_model_label", "other", "grid"),
    ("process_evaluation.csv", "n_expected_routes", "7", "route denominator"),
    ("process_evaluation.csv", "n_incomplete_routes", "1", "incomplete"),
    ("process_evaluation.csv", "n_noninferior_routes", "0", "partition"),
    ("process_evaluation.csv", "status", "unresolved", "status"),
    ("process_evaluation.csv", "process_detected", "True", "challenge"),
    ("process_evaluation.csv", "shared_information_contested", "True", "contested"),
    ("process_evaluation.csv", "unique_process_evidence", "True", "attribution"),
    ("process_evaluation.csv", "v5_changed_from_v4", "True", "change"),
    ("family_metrics.csv", "n_contributory", "99", "metric"),
])
def test_reject_corrupt_record(bundle, member, field, value, message):
    bundle[member][0][field] = value
    with pytest.raises(ValueError, match=message):
        AUDIT.validate_tables(bundle)


def test_reject_decision_metric_corruption(bundle):
    bundle["development_decision.json"]["overall_metrics"]["n_contributory"] = 50
    with pytest.raises(ValueError, match="metric"):
        AUDIT.validate_tables(bundle)


@pytest.mark.parametrize("field,value", [
    ("development_only", False), ("eligible_for_prospective_performance_claim", True),
    ("product_a_reopened", True), ("rank_margin", 0.03), ("density_margin_nats", 0.02),
])
def test_reject_decision_boundary_changes(bundle, field, value):
    bundle["development_decision.json"][field] = value
    with pytest.raises(ValueError):
        AUDIT.validate_tables(bundle)


def test_reject_archive_byte_change(tmp_path):
    path = tmp_path / "modified.zip"
    path.write_bytes(AUDIT.DEFAULT_ARCHIVE.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="SHA256"):
        AUDIT.read_bundle(path)
