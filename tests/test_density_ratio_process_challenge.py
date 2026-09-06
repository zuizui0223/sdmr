import numpy as np
import pandas as pd
import pytest

from sdmr.density_ratio_process_challenge import (
    _classify_processes,
    _paired_density_delta_summary,
    balanced_density_ratio_log_score,
)
from sdmr.process_challenge_learner import CONTRIBUTORY, REPLACEABLE, REQUIRED, UNRESOLVED


def test_balanced_density_log_score_detects_probability_quality_with_same_ranking() -> None:
    # Both predictions rank every presence above every background. Rank/AUC is
    # therefore identical, but the first predictor is far more decisive.
    p_strong = np.array([0.90, 0.85, 0.80])
    b_strong = np.array([0.20, 0.15, 0.10])
    p_weak = np.array([0.56, 0.55, 0.54])
    b_weak = np.array([0.46, 0.45, 0.44])

    strong = balanced_density_ratio_log_score(p_strong, b_strong)
    weak = balanced_density_ratio_log_score(p_weak, b_weak)
    assert strong > weak
    assert np.isfinite(strong)
    assert np.isfinite(weak)


def test_weighted_density_log_score_uses_normalized_presence_weights() -> None:
    p = np.array([0.9, 0.6])
    b = np.array([0.2, 0.3])
    equal = balanced_density_ratio_log_score(p, b, presence_weights=np.array([1.0, 1.0]))
    emphasize_first = balanced_density_ratio_log_score(p, b, presence_weights=np.array([9.0, 1.0]))
    assert emphasize_first > equal


def test_density_pairing_is_model_route_fold_specific() -> None:
    evidence = pd.DataFrame(
        [
            {"model_label": "m1", "route": "baseline::m1", "fold": 0, "complete": True, "score": -0.20},
            {"model_label": "m1", "route": "baseline::m1", "fold": 1, "complete": True, "score": -0.22},
            {"model_label": "m1", "route": "shared-route", "fold": 0, "complete": True, "score": -0.21},
            {"model_label": "m1", "route": "shared-route", "fold": 1, "complete": True, "score": -0.23},
            # Deliberately reuse the route label under another model. These rows
            # must never enter m1's paired comparison.
            {"model_label": "m2", "route": "baseline::m2", "fold": 0, "complete": True, "score": -0.50},
            {"model_label": "m2", "route": "baseline::m2", "fold": 1, "complete": True, "score": -0.52},
            {"model_label": "m2", "route": "shared-route", "fold": 0, "complete": True, "score": -0.80},
            {"model_label": "m2", "route": "shared-route", "fold": 1, "complete": True, "score": -0.82},
        ]
    )
    out = _paired_density_delta_summary(
        evidence,
        model_label="m1",
        knockout_route="shared-route",
        metric="score",
        margin=0.02,
        sem_multiplier=1.0,
    )
    assert out["complete"] is True
    assert out["n_folds"] == 2
    assert out["mean_delta"] == pytest.approx(-0.01)
    assert out["noninferior"] is True


def test_v4_classification_requires_rank_and_density_noninferiority_for_replaceability() -> None:
    routes = pd.DataFrame(
        [
            # p has a v3 rank witness, but density score rejects it -> contributory.
            {
                "model_label": "m1",
                "route": "p-route",
                "excluded_process": "p",
                "density_complete": True,
                "multicriterion_noninferior": False,
                "route_adequate": True,
            },
            # q passes all criteria -> replaceable.
            {
                "model_label": "m1",
                "route": "q-route",
                "excluded_process": "q",
                "density_complete": True,
                "multicriterion_noninferior": True,
                "route_adequate": True,
            },
            # r has no absolutely adequate process-free route -> required.
            {
                "model_label": "m1",
                "route": "r-route",
                "excluded_process": "r",
                "density_complete": True,
                "multicriterion_noninferior": False,
                "route_adequate": False,
            },
            # s is incomplete -> unresolved rather than required.
            {
                "model_label": "m1",
                "route": "s-route",
                "excluded_process": "s",
                "density_complete": False,
                "multicriterion_noninferior": False,
                "route_adequate": False,
            },
        ]
    )
    result = _classify_processes(
        routes,
        ("p", "q", "r", "s"),
        expected_model_labels=("m1",),
    ).set_index("process")
    assert result.loc["p", "status"] == CONTRIBUTORY
    assert result.loc["q", "status"] == REPLACEABLE
    assert result.loc["r", "status"] == REQUIRED
    assert result.loc["s", "status"] == UNRESOLVED


def test_v4_missing_expected_model_route_is_unresolved() -> None:
    routes = pd.DataFrame(
        [
            {
                "model_label": "m1",
                "route": "p-m1",
                "excluded_process": "p",
                "density_complete": True,
                "multicriterion_noninferior": False,
                "route_adequate": False,
            }
        ]
    )
    result = _classify_processes(
        routes,
        ("p",),
        expected_model_labels=("m1", "m2"),
    )
    assert result.iloc[0]["status"] == UNRESOLVED
    assert result.iloc[0]["n_process_baseline_models"] == 2
    assert result.iloc[0]["n_complete_density_routes"] == 1


def test_v4_duplicate_model_process_route_fails_closed() -> None:
    routes = pd.DataFrame(
        [
            {
                "model_label": "m1",
                "route": "p-a",
                "excluded_process": "p",
                "density_complete": True,
                "multicriterion_noninferior": False,
                "route_adequate": True,
            },
            {
                "model_label": "m1",
                "route": "p-b",
                "excluded_process": "p",
                "density_complete": True,
                "multicriterion_noninferior": False,
                "route_adequate": True,
            },
        ]
    )
    with pytest.raises(ValueError, match="duplicate model-process"):
        _classify_processes(routes, ("p",), expected_model_labels=("m1",))
