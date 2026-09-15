from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from sdmr.odds_standardization_v26 import standardized_probabilities, score_routes


class ExactOdds:
    def predict_proba(self, values):
        odds = values[:, 0] * (values[:, 1] if values.shape[1] > 1 else 1)
        probability = odds / (1 + odds)
        return np.column_stack([1 - probability, probability])


def reference():
    return pd.DataFrame([(r, w) for r in (.25, .75, 2) for w in (.2, 1.8)], columns=['x', 'z'])


def test_exact_factorized_odds_recover_ecological_balanced_probability():
    evaluation = pd.DataFrame({'x': [.25, .75, 2]})
    result = standardized_probabilities(ExactOdds(), evaluation, reference(), ['x', 'z'], ['z'])
    np.testing.assert_allclose(result, [.2, 3/7, 2/3], atol=1e-14)


def test_normalizer_is_training_only_and_inputs_are_not_mutated():
    evaluation = pd.DataFrame({'x': [.75], 'z': [999.]})
    ref = reference()
    saved_eval, saved_ref = evaluation.copy(deep=True), ref.copy(deep=True)
    first = standardized_probabilities(ExactOdds(), evaluation, ref, ['x', 'z'], ['z'])
    extended = pd.concat([evaluation, pd.DataFrame({'x': [100.], 'z': [-999.]})], ignore_index=True)
    second = standardized_probabilities(ExactOdds(), extended, ref, ['x', 'z'], ['z'])
    np.testing.assert_array_equal(first, second[:1])
    pd.testing.assert_frame_equal(evaluation, saved_eval)
    pd.testing.assert_frame_equal(ref, saved_ref)


def test_no_observation_still_normalizes_training_odds():
    result = standardized_probabilities(ExactOdds(), pd.DataFrame({'x': [1., 2.]}),
                                        pd.DataFrame({'x': [1., 3.]}), ['x'])
    np.testing.assert_allclose(result, [1/3, .5])


@pytest.mark.parametrize('columns,observation', [([], []), (['x', 'x'], []), (['x'], ['z'])])
def test_invalid_roles_fail_closed(columns, observation):
    with pytest.raises(ValueError):
        standardized_probabilities(ExactOdds(), reference(), reference(), columns, observation)


@pytest.mark.parametrize('kwargs', [{'epsilon': 0}, {'epsilon': .5}, {'max_reference_rows': 0}])
def test_invalid_settings_fail_closed(kwargs):
    with pytest.raises(ValueError):
        standardized_probabilities(ExactOdds(), reference(), reference(), ['x', 'z'], ['z'], **kwargs)


def test_empty_reference_and_nonfinite_ecology_fail_closed():
    with pytest.raises(ValueError):
        standardized_probabilities(ExactOdds(), reference(), reference().iloc[:0], ['x', 'z'], ['z'])
    with pytest.raises(ValueError):
        standardized_probabilities(ExactOdds(), pd.DataFrame({'x': [np.nan]}), reference(), ['x', 'z'], ['z'])


def test_score_routes_returns_finite_weighted_scores():
    presence = pd.DataFrame({'x': [2., .75], 'z': [.2, 1.8]})
    scores = score_routes(ExactOdds(), presence, reference(), reference(), ['x', 'z'], ['z'],
                          SimpleNamespace(weights=np.array([1., 2.])), 1e-6)
    assert set(scores) == {'prediction_rank', 'ecological_rank', 'ecological_density'}
    assert all(np.isfinite(value) for value in scores.values())
