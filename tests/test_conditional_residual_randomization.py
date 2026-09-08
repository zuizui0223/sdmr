import numpy as np
import pandas as pd

from sdmr.conditional_residual_randomization import (
    fit_conditional_residual_randomizer,
    verify_non_target_predictors_unchanged,
)


def test_conditional_residual_randomization_preserves_non_target_columns_and_variance():
    rng = np.random.default_rng(8)
    n = 160
    q1 = rng.normal(size=n)
    q2 = rng.normal(size=n)
    residual = rng.normal(scale=0.6, size=n)
    p = 0.8 * q1 - 0.4 * q2 + residual
    frame = pd.DataFrame({"p": p, "q1": q1, "q2": q2, "other": rng.normal(size=n)})
    fit = fit_conditional_residual_randomizer(
        frame,
        process="p",
        process_predictors=("p",),
        conditioning_predictors=("q1", "q2"),
        degree=1,
        random_state=17,
    )
    out = fit.transform(frame)
    assert verify_non_target_predictors_unchanged(frame, out, target_predictors=("p",))
    assert np.allclose(out[["q1", "q2", "other"]], frame[["q1", "q2", "other"]])
    assert not np.allclose(out["p"], frame["p"])
    # The intervention keeps a non-degenerate residual distribution rather than
    # collapsing P to the deterministic conditional mean used by v8.
    predicted = np.asarray(fit.conditional_model.predict(frame[["q1", "q2"]].to_numpy(float))).reshape(-1)
    randomized_residual = out["p"].to_numpy(float) - predicted
    assert np.std(randomized_residual) > 0.4 * np.std(fit.residual_bank[:, 0])


def test_conditional_residual_randomization_is_deterministic_for_fixed_seed():
    rng = np.random.default_rng(13)
    frame = pd.DataFrame({"p": rng.normal(size=80), "q": rng.normal(size=80)})
    a = fit_conditional_residual_randomizer(frame, process="p", process_predictors=("p",), conditioning_predictors=("q",), random_state=33)
    b = fit_conditional_residual_randomizer(frame, process="p", process_predictors=("p",), conditioning_predictors=("q",), random_state=33)
    assert np.allclose(a.transform(frame)["p"], b.transform(frame)["p"])
