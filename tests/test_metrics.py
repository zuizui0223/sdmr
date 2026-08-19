import math

from sdmr.metrics import presence_rank_score


def test_presence_rank_perfect_and_randomish():
    assert presence_rank_score([0.8, 0.9], [0.1, 0.2, 0.3]) == 1.0
    assert presence_rank_score([0.5], [0.5]) == 0.5
    assert math.isnan(presence_rank_score([], [0.1]))
