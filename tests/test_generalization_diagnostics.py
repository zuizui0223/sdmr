import pandas as pd

from sdmr.generalization_diagnostics import discovery_generalization_diagnostics


def test_generalization_diagnostics_detect_inner_outer_reversal():
    metrics = pd.DataFrame([
        # case 1: inner winner A fails outer; B becomes oracle
        {"data_specification":"m1","species":"sp1","universe":"u","strategy":"A","inner_presence_rank":0.90,"presence_rank":0.30,"boyce":-0.2,"continuous_boyce":-0.4,"n_predictors":2},
        {"data_specification":"m1","species":"sp1","universe":"u","strategy":"B","inner_presence_rank":0.70,"presence_rank":0.80,"boyce":0.8,"continuous_boyce":0.9,"n_predictors":2},
        {"data_specification":"m1","species":"sp1","universe":"u","strategy":"C","inner_presence_rank":0.60,"presence_rank":0.60,"boyce":0.4,"continuous_boyce":0.5,"n_predictors":2},
        # case 2: same reversal
        {"data_specification":"m2","species":"sp2","universe":"u","strategy":"A","inner_presence_rank":0.85,"presence_rank":0.40,"boyce":0.0,"continuous_boyce":-0.1,"n_predictors":2},
        {"data_specification":"m2","species":"sp2","universe":"u","strategy":"B","inner_presence_rank":0.65,"presence_rank":0.75,"boyce":0.7,"continuous_boyce":0.8,"n_predictors":2},
        {"data_specification":"m2","species":"sp2","universe":"u","strategy":"C","inner_presence_rank":0.55,"presence_rank":0.55,"boyce":0.3,"continuous_boyce":0.4,"n_predictors":2},
    ])
    cases, summary = discovery_generalization_diagnostics(metrics)
    assert len(cases) == 2
    assert not cases["winner_match"].any()
    assert (cases["outer_regret"] > 0).all()
    assert (cases["within_case_inner_outer_spearman"] < 0).all()
    row = summary.iloc[0]
    assert row["inner_winner_matches_outer_winner_fraction"] == 0.0
    assert row["mean_outer_regret"] > 0.3
    assert row["row_level_outer_auc_boyce_spearman"] > 0.8
    assert row["row_level_outer_auc_cbi_spearman"] > 0.8


def test_generalization_diagnostics_detect_stable_inner_ranking():
    metrics = pd.DataFrame([
        {"data_specification":"m","species":"sp","universe":"u","strategy":"A","inner_presence_rank":0.8,"presence_rank":0.82,"boyce":0.8,"n_predictors":2},
        {"data_specification":"m","species":"sp","universe":"u","strategy":"B","inner_presence_rank":0.6,"presence_rank":0.61,"boyce":0.5,"n_predictors":2},
        {"data_specification":"m","species":"sp","universe":"u","strategy":"C","inner_presence_rank":0.4,"presence_rank":0.39,"boyce":0.2,"n_predictors":2},
    ])
    cases, summary = discovery_generalization_diagnostics(metrics)
    assert bool(cases.iloc[0]["winner_match"])
    assert cases.iloc[0]["outer_regret"] == 0.0
    assert cases.iloc[0]["within_case_inner_outer_spearman"] == 1.0
    assert summary.iloc[0]["inner_winner_matches_outer_winner_fraction"] == 1.0
