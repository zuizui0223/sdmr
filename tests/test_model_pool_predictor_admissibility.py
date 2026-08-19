import pandas as pd

from sdmr.model_pool_predictor_admissibility import (
    select_model_pool_admissible_predictors,
)


def test_sparse_predictor_is_rejected_across_model_pool_M_without_sealed_data():
    p = pd.DataFrame(
        {
            "dense": list(range(20)),
            "sparse": [1.0] + [None] * 19,
            "edge": list(range(19)) + [None],
        }
    )
    b150 = pd.DataFrame(
        {
            "dense": list(range(20)),
            "sparse": [1.0] + [None] * 19,
            "edge": list(range(20)),
        }
    )
    b300 = b150.copy()
    b500 = b150.copy()
    result = select_model_pool_admissible_predictors(
        {
            "buffer_150km": (p, b150),
            "buffer_300km": (p, b300),
            "buffer_500km": (p, b500),
        },
        ("dense", "sparse", "edge"),
        minimum_coverage=0.95,
    )
    assert result.predictors == ("dense", "edge")
    sparse = result.ledger.loc[result.ledger["predictor"].eq("sparse")]
    assert not sparse["eligible_all_perturbations"].any()
    assert sparse["minimum_model_pool_coverage"].iloc[0] == 0.05
    assert "presence_rank" not in result.ledger.columns
    assert "__sdmr_outer_role" not in result.ledger.columns


def test_predictor_must_pass_presence_and_background_in_every_M():
    p = pd.DataFrame({"x": [1.0] * 20, "y": [1.0] * 20})
    good = pd.DataFrame({"x": [1.0] * 20, "y": [1.0] * 20})
    bad = pd.DataFrame({"x": [1.0] * 18 + [None, None], "y": [1.0] * 20})
    result = select_model_pool_admissible_predictors(
        {
            "m1": (p, good),
            "m2": (p, bad),
        },
        ("x", "y"),
        minimum_coverage=0.95,
    )
    assert result.predictors == ("y",)
    x = result.ledger.loc[result.ledger["predictor"].eq("x")]
    assert x["n_required_perturbations"].iloc[0] == 2
    assert x["n_passing_perturbations"].iloc[0] == 1
