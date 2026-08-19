import numpy as np
import pandas as pd

from sdmr import ModelSpec, correlation_equivalence_groups, drop_group_importance, drop_one_importance


def _data(seed=8):
    rng = np.random.default_rng(seed)
    n_p, n_b = 180, 500
    p_signal = rng.normal(2.0, 0.7, n_p)
    b_signal = rng.normal(0.0, 1.0, n_b)
    presence = pd.DataFrame(
        {
            "signal_a": p_signal,
            "signal_b": p_signal + rng.normal(0, 0.02, n_p),
            "noise": rng.normal(size=n_p),
        }
    )
    background = pd.DataFrame(
        {
            "signal_a": b_signal,
            "signal_b": b_signal + rng.normal(0, 0.02, n_b),
            "noise": rng.normal(size=n_b),
        }
    )
    return presence.iloc[:120], background.iloc[:350], presence.iloc[120:], background.iloc[350:]


def test_equivalence_groups_correlated_substitutes_without_deleting_them():
    train_p, train_b, _, _ = _data()
    env = pd.concat([train_p, train_b], ignore_index=True)
    groups = correlation_equivalence_groups(env, ["signal_a", "signal_b", "noise"], threshold=0.9)
    lookup = groups.set_index("predictor")["equivalence_group"].to_dict()
    assert lookup["signal_a"] == lookup["signal_b"]
    assert lookup["noise"] != lookup["signal_a"]


def test_group_drop_recovers_shared_signal_hidden_by_individual_substitution():
    train_p, train_b, test_p, test_b = _data()
    predictors = ["signal_a", "signal_b", "noise"]
    groups = correlation_equivalence_groups(pd.concat([train_p, train_b]), predictors, threshold=0.9)
    spec = ModelSpec(C=1, degree=1)
    one = drop_one_importance(train_p, train_b, test_p, test_b, predictors, model_spec=spec)
    grouped = drop_group_importance(train_p, train_b, test_p, test_b, predictors, groups, model_spec=spec)
    signal_group = groups.loc[groups.predictor == "signal_a", "equivalence_group"].iloc[0]
    group_loss = grouped.loc[grouped.equivalence_group == signal_group, "loss"].iloc[0]
    max_individual_signal_loss = one.loc[one.predictor.isin(["signal_a", "signal_b"]), "loss"].max()
    assert group_loss > max_individual_signal_loss + 0.10
