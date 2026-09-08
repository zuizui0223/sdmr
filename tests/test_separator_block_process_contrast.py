import numpy as np
import pandas as pd

from sdmr.model import ModelSpec
from sdmr.separator_block_process_contrast import separator_block_process_contrast


def test_separator_block_contrast_returns_finite_evidence():
    rng = np.random.default_rng(7)
    n = 240
    blocks = np.repeat(np.arange(4), n // 4)
    q = rng.normal(size=n)
    p = 1.5 * q + rng.normal(scale=0.25, size=n)
    x = rng.normal(size=n)
    background = pd.DataFrame({"p": p, "q": q, "x": x})

    score = 1.2 * p + 0.2 * x
    prob = 1 / (1 + np.exp(-score))
    idx = rng.choice(np.arange(n), size=120, replace=True, p=prob / prob.sum())
    presence = background.iloc[idx].reset_index(drop=True)
    pblocks = blocks[idx]

    result = separator_block_process_contrast(
        presence,
        background,
        pblocks,
        blocks,
        separator_blocks=(3,),
        target_process="temperature",
        competitor_process="water",
        target_predictors=("p",),
        competitor_predictors=("q",),
        ecological_predictors=("p", "q", "x"),
        model_spec=ModelSpec(C=1.0, degree=1, penalty="l2", random_state=0),
        knockout_degree=1,
        minimum_test_presence=3,
        minimum_test_background=10,
    )
    assert len(result) == 1
    row = result.iloc[0]
    assert bool(row["complete"])
    assert np.isfinite(float(row["target_rank_loss"]))
    assert np.isfinite(float(row["competitor_rank_loss"]))
    assert np.isfinite(float(row["target_density_loss"]))
    assert np.isfinite(float(row["competitor_density_loss"]))
