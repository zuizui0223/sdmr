import math

import pandas as pd
import pytest


def test_full_system_information_evaluator_is_deterministic():
    from sdmr.process_id.known_truth.full_system_calibration import (
        evaluate_full_system_information,
    )
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process",
        seed=50101,
        n_cells=900,
        n_occurrences=120,
        n_background=360,
    )
    first = evaluate_full_system_information(
        world,
        n_splits=3,
        split_mode="random_cell",
        learner="hgb",
        hgb_profile="shallow3",
    )
    second = evaluate_full_system_information(
        world,
        n_splits=3,
        split_mode="random_cell",
        learner="hgb",
        hgb_profile="shallow3",
    )
    pd.testing.assert_frame_equal(first.fold_scores, second.fold_scores)
    pd.testing.assert_frame_equal(first.summary, second.summary)


def test_full_system_information_summary_matches_null_gain_definition():
    from sdmr.process_id.known_truth.full_system_calibration import (
        summarize_information_folds,
    )

    fold_scores = pd.DataFrame(
        {
            "fold": [0, 1, 2],
            "full_log_score": [
                -math.log(2.0) + 0.01,
                -math.log(2.0) + 0.02,
                -math.log(2.0) + 0.03,
            ],
        }
    )
    summary = summarize_information_folds(
        fold_scores,
        adequacy_floor=-0.75,
    ).iloc[0]

    assert summary["mean_full_score"] == pytest.approx(-math.log(2.0) + 0.02)
    assert summary["mean_gain_over_null"] == pytest.approx(0.02)
    assert summary["gain_sem"] == pytest.approx(0.005773502691896258)
    assert bool(summary["absolute_adequate"])


def test_candidate_table_uses_frozen_multiplier_grid():
    from sdmr.process_id.known_truth.full_system_calibration import (
        evaluate_information_candidates,
    )

    summary = pd.DataFrame(
        [
            {
                "mean_full_score": -0.68,
                "mean_gain_over_null": 0.02,
                "gain_sem": 0.005,
                "absolute_adequate": True,
            }
        ]
    )
    grid = (1.0, 1.645, 1.96)
    out = evaluate_information_candidates(summary, multipliers=grid)

    assert tuple(out["multiplier"]) == grid
    assert out.loc[out["multiplier"].eq(1.0), "lower_gain"].iloc[0] == pytest.approx(0.015)
    assert out["authorized"].all()


def test_candidate_selector_chooses_smallest_qualifying_multiplier():
    from sdmr.process_id.known_truth.full_system_calibration import (
        select_information_multiplier,
    )

    rows = []
    worlds = [
        "unique_process",
        "redundant_representation",
        "shared_carrier",
        "null_correlated",
        "interaction",
        "geographic_shift",
        "observation_confounded",
        "omitted_driver",
    ]
    for multiplier in (1.0, 1.645, 1.96):
        for world in worlds:
            if world == "omitted_driver":
                rate = {1.0: 0.03, 1.645: 0.01, 1.96: 0.0}[multiplier]
            elif world == "observation_confounded":
                rate = 0.50
            else:
                rate = {1.0: 0.99, 1.645: 0.97, 1.96: 0.96}[multiplier]
            rows.append(
                {
                    "multiplier": multiplier,
                    "world": world,
                    "authorization_rate": rate,
                }
            )
    summary = pd.DataFrame(rows)
    decision = select_information_multiplier(
        summary,
        candidate_order=(1.0, 1.645, 1.96),
        max_w7_false_authorization=0.01,
        min_informative_world_authorization=0.95,
    )

    assert decision.selected_multiplier == pytest.approx(1.645)
    assert decision.passed
    assert decision.eligible_multipliers == (1.645, 1.96)


def test_candidate_selector_ignores_w6_for_selection_but_requires_all_six_controls():
    from sdmr.process_id.known_truth.full_system_calibration import (
        select_information_multiplier,
    )

    controls = [
        "unique_process",
        "redundant_representation",
        "shared_carrier",
        "null_correlated",
        "interaction",
        "geographic_shift",
    ]
    rows = []
    for world in controls:
        rows.append({"multiplier": 2.0, "world": world, "authorization_rate": 0.96})
    rows.append({"multiplier": 2.0, "world": "observation_confounded", "authorization_rate": 0.0})
    rows.append({"multiplier": 2.0, "world": "omitted_driver", "authorization_rate": 0.0})

    decision = select_information_multiplier(
        pd.DataFrame(rows),
        candidate_order=(2.0,),
        max_w7_false_authorization=0.01,
        min_informative_world_authorization=0.95,
    )
    assert decision.passed
    assert decision.selected_multiplier == 2.0

    broken = pd.DataFrame(rows)
    broken.loc[broken["world"].eq("geographic_shift"), "authorization_rate"] = 0.94
    failed = select_information_multiplier(
        broken,
        candidate_order=(2.0,),
        max_w7_false_authorization=0.01,
        min_informative_world_authorization=0.95,
    )
    assert not failed.passed
    assert failed.selected_multiplier is None


def test_candidate_selector_fails_closed_on_missing_worlds():
    from sdmr.process_id.known_truth.full_system_calibration import (
        select_information_multiplier,
    )

    with pytest.raises(ValueError, match="required calibration worlds"):
        select_information_multiplier(
            pd.DataFrame(
                [
                    {
                        "multiplier": 1.0,
                        "world": "omitted_driver",
                        "authorization_rate": 0.0,
                    }
                ]
            ),
            candidate_order=(1.0,),
            max_w7_false_authorization=0.01,
            min_informative_world_authorization=0.95,
        )


import pandas as pd


def test_confirmation_passes_only_with_zero_w7_and_48_of_50_controls():
    from sdmr.process_id.known_truth.full_system_calibration import (
        evaluate_confirmation_panel,
    )

    rows=[]
    controls=[
        "unique_process",
        "redundant_representation",
        "shared_carrier",
        "null_correlated",
        "interaction",
        "geographic_shift",
    ]
    for world in controls:
        rows.append({"world":world,"authorized_count":48,"denominator":50})
    rows.append({"world":"observation_confounded","authorized_count":20,"denominator":50})
    rows.append({"world":"omitted_driver","authorized_count":0,"denominator":50})

    decision=evaluate_confirmation_panel(pd.DataFrame(rows))
    assert decision.passed
    assert decision.w7_authorized_count==0
    assert decision.minimum_control_authorized_count==48


def test_confirmation_fails_without_reselection():
    from sdmr.process_id.known_truth.full_system_calibration import (
        evaluate_confirmation_panel,
    )

    rows=[
        {"world":"unique_process","authorized_count":50,"denominator":50},
        {"world":"redundant_representation","authorized_count":50,"denominator":50},
        {"world":"shared_carrier","authorized_count":50,"denominator":50},
        {"world":"null_correlated","authorized_count":50,"denominator":50},
        {"world":"interaction","authorized_count":50,"denominator":50},
        {"world":"geographic_shift","authorized_count":47,"denominator":50},
        {"world":"observation_confounded","authorized_count":50,"denominator":50},
        {"world":"omitted_driver","authorized_count":0,"denominator":50},
    ]
    decision=evaluate_confirmation_panel(pd.DataFrame(rows))
    assert not decision.passed
    assert "geographic_shift" in decision.failed_controls

    rows[-1]["authorized_count"]=1
    rows[5]["authorized_count"]=48
    decision2=evaluate_confirmation_panel(pd.DataFrame(rows))
    assert not decision2.passed
    assert decision2.w7_authorized_count==1
