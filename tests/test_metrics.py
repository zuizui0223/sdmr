import math

import pytest

from sdmr.metrics import omission_rate_at_training_quantile, presence_rank_score


def test_presence_rank_perfect_and_randomish():
    assert presence_rank_score([0.8, 0.9], [0.1, 0.2, 0.3]) == 1.0
    assert presence_rank_score([0.5], [0.5]) == 0.5
    assert math.isnan(presence_rank_score([], [0.1]))


def test_or10_uses_training_threshold_then_scores_independent_test_occurrences():
    train = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    test = [0.05, 0.18, 0.20, 0.80]
    assert omission_rate_at_training_quantile(train, test) == 0.5


def test_or10_rejects_invalid_quantile_and_handles_empty_samples():
    assert math.isnan(omission_rate_at_training_quantile([], [0.2]))
    with pytest.raises(ValueError):
        omission_rate_at_training_quantile([0.2], [0.2], quantile=1.1)
