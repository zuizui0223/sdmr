import math

from sdmr.sealed_evaluation_status import classify_sealed_evaluation


def _payload(**overrides):
    base = {
        "presence_rank": 0.8,
        "niche_overlap_schoener_d_pc12": 0.5,
        "centroid_distance": 0.2,
        "breadth_log_sd_error": 0.1,
        "quantile_profile_error": 0.3,
    }
    base.update(overrides)
    return base


def test_complete_sealed_evaluation():
    assert classify_sealed_evaluation(
        _payload(), n_complete_sealed_presence=20, n_complete_sealed_background=20
    ) == "complete"


def test_zero_complete_sealed_background_is_explicit_abstention():
    assert classify_sealed_evaluation(
        _payload(presence_rank=float("nan")),
        n_complete_sealed_presence=20,
        n_complete_sealed_background=0,
    ) == "abstain_prediction_evaluation_unavailable"


def test_nonfinite_prediction_metric_is_distinct_from_row_support():
    assert classify_sealed_evaluation(
        _payload(presence_rank=float("nan")),
        n_complete_sealed_presence=20,
        n_complete_sealed_background=20,
    ) == "abstain_prediction_metric_nonfinite"


def test_prediction_can_exist_when_ecological_recovery_is_unavailable():
    assert classify_sealed_evaluation(
        _payload(centroid_distance=float("nan")),
        n_complete_sealed_presence=20,
        n_complete_sealed_background=20,
    ) == "partial_prediction_only_ecological_recovery_unavailable"
