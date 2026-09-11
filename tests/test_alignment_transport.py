import numpy as np
import pandas as pd
import pytest

from sdmr.alignment_transport import (
    fit_alignment_transport_map,
    verify_transport_retained_predictors,
)


def _frames():
    rng = np.random.default_rng(123)
    n = 60
    block = np.repeat([0, 1, 2], n // 3)
    q1 = rng.normal(size=n)
    q2 = rng.normal(size=n)
    p = 1.5 * q1 - 0.7 * q2 + rng.normal(scale=0.02, size=n)
    r = rng.normal(size=n)
    frame = pd.DataFrame({"p": p, "q1": q1, "q2": q2, "r": r})
    return frame, block


def test_fit_uses_only_declared_source_block_and_transports_to_other_block():
    frame, block = _frames()
    fitted = fit_alignment_transport_map(
        frame,
        block,
        source_block=0,
        process="P",
        process_predictors=("p",),
        conditioning_predictors=("q1", "q2"),
        degree=2,
        ridge_alpha=1.0,
        minimum_complete_rows=10,
    )
    assert fitted.source_block == 0
    assert fitted.knockout.n_fit_rows == 20
    target = frame.loc[block == 2].reset_index(drop=True)
    transformed = fitted.transform(target)
    assert np.isfinite(transformed["p"]).all()
    assert verify_transport_retained_predictors(
        target,
        transformed,
        ecological_predictors=("p", "q1", "q2", "r"),
        process_predictors=("p",),
    )
    pd.testing.assert_series_equal(target["q1"], transformed["q1"])
    pd.testing.assert_series_equal(target["q2"], transformed["q2"])
    pd.testing.assert_series_equal(target["r"], transformed["r"])


def test_source_block_failure_is_fail_closed():
    frame, block = _frames()
    with pytest.raises(ValueError, match="source block needs"):
        fit_alignment_transport_map(
            frame,
            block,
            source_block=0,
            process="P",
            process_predictors=("p",),
            conditioning_predictors=("q1", "q2"),
            minimum_complete_rows=25,
        )
