import math

import pytest

from sdmr.metrics import omission_rate_at_training_quantile, presence_rank_score


def test_presence_rank_perfect_and_randomish():
    assert presence_rank_score([0.8, 0.9], [0.1, 0.2, 0.3]) == 1.0
    assert presence_rank_score([0.5], [0.5]) == 0.5
    assert math.isnan(presence_rank_score([], [0.1]))


def test_or10_uses_training_presence_threshold_and_independent_test_omission():
    train = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    # NumPy's linear 10th percentile is 0.19, so only the first two test scores
    # below 0.19 are omitted.
    test = [0.05, 0.18, 0.20, 0.80]
    assert omission_rate_at_training_quantile(train, test) == 0.5


def test_or10_is_diagnostic_not_silent_bad_input():
    assert math.isnan(omission_rate_at_training_quantile([], [0.2]))
    with pytest.raises(ValueError):
        omission_rate_at_training_quantile([0.2], [0.2], quantile=1.1)
