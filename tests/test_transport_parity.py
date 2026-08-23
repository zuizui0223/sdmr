import pandas as pd
import pytest

from sdmr.transport_parity import assert_transport_frame_parity


def test_transport_parity_allows_only_small_predeclared_float_drift():
    reference = pd.DataFrame({
        'candidate': ['a', 'b'],
        'fold': [0, 1],
        'presence_rank': [0.9000, 0.7500],
        'available': [True, False],
    })
    reconstructed = pd.DataFrame({
        'candidate': ['a', 'b'],
        'fold': [0, 1],
        'presence_rank': [0.9002, 0.7498],
        'available': [True, False],
    })
    summary = assert_transport_frame_parity(
        reference, reconstructed, rtol=5e-4, atol=5e-4
    )
    assert summary.rows == 2
    assert summary.columns == 4
    assert summary.floating_cells_compared == 2
    assert 0 < summary.max_absolute_difference <= 5e-4


def test_transport_parity_rejects_float_drift_outside_envelope():
    reference = pd.DataFrame({'presence_rank': [0.9000]})
    reconstructed = pd.DataFrame({'presence_rank': [0.8980]})
    with pytest.raises(AssertionError, match='floating tolerance exceeded'):
        assert_transport_frame_parity(
            reference, reconstructed, rtol=5e-4, atol=5e-4
        )


def test_transport_parity_rejects_integer_or_discrete_changes():
    reference = pd.DataFrame({
        'candidate': ['a'],
        'fold': [0],
        'presence_rank': [0.9],
    })
    changed_fold = pd.DataFrame({
        'candidate': ['a'],
        'fold': [1],
        'presence_rank': [0.9],
    })
    with pytest.raises(AssertionError):
        assert_transport_frame_parity(
            reference, changed_fold, rtol=5e-4, atol=5e-4
        )

    changed_candidate = pd.DataFrame({
        'candidate': ['b'],
        'fold': [0],
        'presence_rank': [0.9],
    })
    with pytest.raises(AssertionError):
        assert_transport_frame_parity(
            reference, changed_candidate, rtol=5e-4, atol=5e-4
        )


def test_transport_parity_requires_same_nonfinite_pattern_and_schema():
    reference = pd.DataFrame({'metric': [1.0, float('nan')]})
    changed_nan = pd.DataFrame({'metric': [1.0, 0.0]})
    with pytest.raises(AssertionError, match='finite/non-finite mask changed'):
        assert_transport_frame_parity(
            reference, changed_nan, rtol=5e-4, atol=5e-4
        )

    changed_schema = pd.DataFrame({'other': [1.0, float('nan')]})
    with pytest.raises(AssertionError, match='column order changed'):
        assert_transport_frame_parity(
            reference, changed_schema, rtol=5e-4, atol=5e-4
        )
