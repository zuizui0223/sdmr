import pandas as pd

from sdmr.separator_pair_decision import (
    COMPETITOR_FAVORED,
    TARGET_FAVORED,
    UNRESOLVED,
    classify_separator_pair,
)


def _frame(target_rank, competitor_rank, target_density, competitor_density):
    return pd.DataFrame({
        "complete": [True, True, True],
        "target_rank_loss": target_rank,
        "competitor_rank_loss": competitor_rank,
        "target_density_loss": target_density,
        "competitor_density_loss": competitor_density,
    })


def test_target_favored_requires_both_evidence_axes():
    result = classify_separator_pair(_frame([0.08,0.09,0.10],[0.01,0.02,0.01],[0.05,0.06,0.05],[0.00,0.01,0.00]))
    assert result["state"] == TARGET_FAVORED


def test_competitor_favored_is_symmetric():
    result = classify_separator_pair(_frame([0.01,0.02,0.01],[0.08,0.09,0.10],[0.00,0.01,0.00],[0.05,0.06,0.05]))
    assert result["state"] == COMPETITOR_FAVORED


def test_single_axis_advantage_remains_unresolved():
    result = classify_separator_pair(_frame([0.10,0.10,0.10],[0.01,0.01,0.01],[0.02,0.02,0.02],[0.02,0.02,0.02]))
    assert result["state"] == UNRESOLVED
