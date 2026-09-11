import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.attribution_eligibility_v19 import load_classifier, load_contract, predict_eligibility

ROOT = Path(__file__).resolve().parents[1]


def test_v19_contract_is_fresh_and_fixed():
    cfg = load_contract()
    assert tuple(cfg["fresh_seed_denominator"]) == tuple(range(16001, 16011))
    assert tuple(cfg["target_processes"]) == ("temperature", "water")
    assert tuple(cfg["negative_control_processes"]) == ("seasonality", "noise")
    assert cfg["target_selection_uses_outcomes"] is False
    assert cfg["fixed_baseline_class"] == "eligible"
    assert cfg["success_criteria"] == {
        "eligible_precision_min": 0.70,
        "eligible_recall_min": 0.50,
        "macro_f1_gain_over_fixed_baseline_min": 0.15,
        "false_process_eligible_rate_max": 0.10,
    }


def test_v19_classifier_shape_and_threshold_are_frozen():
    cfg = load_classifier()
    assert len(cfg["feature_order"]) == 5
    assert len(cfg["scaler_mean"]) == 5
    assert len(cfg["scaler_scale"]) == 5
    assert len(cfg["logistic_coef"]) == 5
    assert cfg["decision_threshold"] == 0.5
    assert cfg["source"]["n_training_contexts"] == 69
    assert cfg["source"]["v18_artifact_id"] == 10189371935


def test_v19_frozen_predictor_is_deterministic():
    clf = load_classifier()
    row = {name: mean for name, mean in zip(clf["feature_order"], clf["scaler_mean"], strict=True)}
    out = predict_eligibility(pd.DataFrame([row, row]))
    expected = 1.0 / (1.0 + np.exp(-float(clf["logistic_intercept"])))
    assert np.allclose(out["p_eligible"].to_numpy(float), expected, atol=1e-14, rtol=0.0)
    assert out["eligibility_prediction"].tolist() == ["eligible", "eligible"]


def test_v19_contract_requires_prediction_before_truth_open():
    cfg = load_contract()
    policy = cfg["truth_open_policy"]
    assert policy["geometry_and_predictions_before_labels"] is True
    assert policy["all_prediction_shards_must_complete_before_truth_open"] is True
    assert policy["generating_process_truth_opens_only_in_terminal_audit"] is True
    assert policy["fresh_labels_may_not_be_used_to_change_features_classifier_threshold_or_success_criteria"] is True
