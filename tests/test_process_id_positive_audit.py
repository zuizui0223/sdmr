import math

import pandas as pd


def _targets():
    return pd.DataFrame([
        {"process": "thermal", "expected_state": "contributory"},
        {"process": "water", "expected_state": "replaceable"},
    ])


def _states(reason="interval_process_challenge", full=-0.68, knockout=-0.70, delta=0.02, sem=0.005):
    return pd.DataFrame([
        {
            "process": "thermal",
            "state": "unresolved",
            "reason": reason,
            "complete": True,
            "full_log_score": full,
            "knockout_log_score": knockout,
            "delta_mean": delta,
            "delta_sem": sem,
        },
        {
            "process": "water",
            "state": "replaceable",
            "reason": "interval_process_challenge",
            "complete": True,
            "full_log_score": -0.68,
            "knockout_log_score": -0.68,
            "delta_mean": 0.0,
            "delta_sem": 0.001,
        },
    ])


def _folds(route):
    return pd.DataFrame([
        {
            "process": "thermal",
            "fold": 0,
            "route": route,
            "complete": True,
            "full_log_score": -0.67,
            "knockout_log_score": -0.70,
            "delta": 0.03,
        },
        {
            "process": "thermal",
            "fold": 1,
            "route": route,
            "complete": True,
            "full_log_score": -0.69,
            "knockout_log_score": -0.70,
            "delta": 0.01,
        },
        {
            "process": "water",
            "fold": 0,
            "route": route,
            "complete": True,
            "full_log_score": -0.67,
            "knockout_log_score": -0.67,
            "delta": 0.0,
        },
    ])


def test_boundary_full_inadequate_precedes_relative_evidence():
    from sdmr.process_id.known_truth.positive_audit import classify_positive_boundary

    row = _states(full=-0.80, knockout=-0.90, delta=0.10, sem=0.001).iloc[0]
    assert classify_positive_boundary(
        row, margin=0.01, adequacy_floor=-0.75, sem_multiplier=1.0
    ) == "full_inadequate"


def test_boundary_detects_process_free_noninferiority():
    from sdmr.process_id.known_truth.positive_audit import classify_positive_boundary

    row = _states(full=-0.68, knockout=-0.685, delta=0.005, sem=0.002).iloc[0]
    assert classify_positive_boundary(
        row, margin=0.01, adequacy_floor=-0.75, sem_multiplier=1.0
    ) == "process_free_noninferior_witness"


def test_boundary_detects_interval_indeterminacy():
    from sdmr.process_id.known_truth.positive_audit import classify_positive_boundary

    row = _states(full=-0.68, knockout=-0.695, delta=0.015, sem=0.010).iloc[0]
    assert classify_positive_boundary(
        row, margin=0.01, adequacy_floor=-0.75, sem_multiplier=1.0
    ) == "interval_indeterminate"


def test_boundary_detects_positive_contribution_evidence():
    from sdmr.process_id.known_truth.positive_audit import classify_positive_boundary

    row = _states(full=-0.65, knockout=-0.69, delta=0.04, sem=0.005).iloc[0]
    assert classify_positive_boundary(
        row, margin=0.01, adequacy_floor=-0.75, sem_multiplier=1.0
    ) == "positive_contribution_evidence"


def test_boundary_detects_positive_required_evidence():
    from sdmr.process_id.known_truth.positive_audit import classify_positive_boundary

    row = _states(full=-0.65, knockout=-0.80, delta=0.15, sem=0.005).iloc[0]
    assert classify_positive_boundary(
        row, margin=0.01, adequacy_floor=-0.75, sem_multiplier=1.0
    ) == "positive_required_evidence"


def test_explicit_refusal_reason_is_preserved():
    from sdmr.process_id.known_truth.positive_audit import classify_positive_boundary

    row = _states(reason="observation_process_not_separable").iloc[0]
    assert classify_positive_boundary(
        row, margin=0.01, adequacy_floor=-0.75, sem_multiplier=1.0
    ) == "observation_process_not_separable"


def test_build_audit_keeps_only_positive_targets_and_both_learners():
    from sdmr.process_id.known_truth.positive_audit import build_positive_evidence_audit

    states = {
        "linear": _states(),
        "quadratic": _states(delta=0.03, sem=0.02),
    }
    evidence = {
        "linear": _folds("logistic"),
        "quadratic": _folds("logistic_quadratic"),
    }
    summary, folds = build_positive_evidence_audit(
        _targets(),
        states,
        evidence,
        margin=0.01,
        adequacy_floor=-0.75,
        sem_multiplier=1.0,
    )

    assert set(summary["process"]) == {"thermal"}
    assert set(summary["learner"]) == {"linear", "quadratic"}
    assert set(folds["process"]) == {"thermal"}
    assert set(folds["learner"]) == {"linear", "quadratic"}
    assert {"lower_delta", "upper_delta", "diagnostic_boundary"}.issubset(summary.columns)
    assert len(folds) == 4
