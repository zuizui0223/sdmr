import numpy as np
import pandas as pd


def test_probability_quality_metrics_separate_discrimination_and_calibration():
    from sdmr.process_id.known_truth.probability_audit import probability_quality_metrics

    y = np.array([1, 1, 0, 0])
    p = np.array([0.90, 0.60, 0.40, 0.10])
    metrics = probability_quality_metrics(y, p)

    assert metrics["roc_auc"] == 1.0
    assert 0.0 <= metrics["balanced_brier"] < 0.25
    assert metrics["mean_p_positive"] > metrics["mean_p_negative"]
    assert metrics["extreme_fraction"] == 0.0
    assert metrics["q01"] <= metrics["q50"] <= metrics["q99"]


def test_probability_quality_metrics_fail_closed_without_both_classes():
    import pytest
    from sdmr.process_id.known_truth.probability_audit import probability_quality_metrics

    with pytest.raises(ValueError, match="both classes"):
        probability_quality_metrics(np.ones(10, dtype=int), np.full(10, 0.5))


def test_fitted_probability_helper_preserves_existing_score():
    from sdmr.process_id.evidence import _fit_probabilities, _fit_score

    rng = np.random.default_rng(811)
    train = pd.DataFrame({
        "x1": rng.normal(size=500),
        "x2": rng.normal(size=500),
    })
    train["label"] = (train["x1"] + 0.3 * train["x2"] > 0).astype(int)
    test = pd.DataFrame({
        "x1": rng.normal(size=250),
        "x2": rng.normal(size=250),
    })
    test["label"] = (test["x1"] + 0.3 * test["x2"] > 0).astype(int)

    _, test_p = _fit_probabilities(
        train, test, ("x1", "x2"), C=1.0, learner="linear"
    )
    score = _fit_score(train, test, ("x1", "x2"), C=1.0, learner="linear")
    y = test["label"].to_numpy(int)
    expected = 0.5 * np.log(test_p[y == 1]).mean() + 0.5 * np.log1p(-test_p[y == 0]).mean()
    assert score == expected


def test_probability_audit_is_deterministic_and_keeps_full_model_only():
    from sdmr.process_id.known_truth.probability_audit import run_probability_quality_audit

    kwargs = dict(
        seeds=(812,),
        worlds=("unique_process",),
        learners=("linear", "hgb"),
        split_modes=("spatial", "random_cell"),
        n_cells=800,
        n_occurrences=80,
        n_background=260,
        n_splits=2,
    )
    first = run_probability_quality_audit(**kwargs)
    second = run_probability_quality_audit(**kwargs)

    pd.testing.assert_frame_equal(first, second)
    assert set(first["learner"]) == {"linear", "hgb"}
    assert set(first["split_mode"]) == {"spatial", "random_cell"}
    assert set(first["dataset"]) == {"train", "test"}
    assert set(first["world"]) == {"unique_process"}
    assert "process" not in first.columns
