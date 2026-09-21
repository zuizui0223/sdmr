import pytest
import pandas as pd


def test_occurrence_evidence_is_paired_by_process_and_fold():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("unique_process", seed=201, n_cells=1200, n_occurrences=120, n_background=420)
    result = evaluate_occurrence_processes(world, n_splits=3)
    expected = len(world.process_universe) * 3
    assert len(result.evidence) == expected
    assert result.evidence[["process", "fold"]].drop_duplicates().shape[0] == expected
    assert set(result.evidence["route"]) == {"logistic"}
    assert result.evidence["complete"].dtype == bool
    assert {"full_log_score", "knockout_log_score", "delta"}.issubset(result.evidence.columns)


def test_occurrence_evidence_uses_declared_process_closure():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("unique_process", seed=202, n_cells=1200, n_occurrences=120, n_background=420)
    result = evaluate_occurrence_processes(world, n_splits=3)
    thermal = result.evidence.loc[result.evidence["process"].eq("thermal")]
    assert thermal["excluded_predictors"].nunique() == 1
    excluded = set(thermal["excluded_predictors"].iloc[0].split(","))
    assert {"temperature", "elevation_proxy", "pet_shared"}.issubset(excluded)
    assert "sampling_effort" not in excluded


def test_observation_confounded_process_is_forced_unresolved():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("observation_confounded", seed=203, n_cells=1200, n_occurrences=120, n_background=420)
    result = evaluate_occurrence_processes(world, n_splits=3)
    row = result.states.loc[result.states["process"].eq("thermal")].iloc[0]
    assert row["state"] == "unresolved"
    assert row["reason"] == "observation_process_not_separable"


def test_occurrence_state_table_has_one_row_per_process():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world("null_correlated", seed=204, n_cells=1200, n_occurrences=120, n_background=420)
    result = evaluate_occurrence_processes(world, n_splits=3)
    assert tuple(result.states["process"]) == world.process_universe
    assert result.states["state"].isin({"replaceable", "contributory", "required", "unresolved", "unavailable"}).all()


def test_identical_shared_carrier_closure_abstains_in_occurrence_states():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "shared_carrier",
        seed=205,
        n_cells=1400,
        n_occurrences=160,
        n_background=520,
    )
    result = evaluate_occurrence_processes(world, n_splits=3, adequacy_floor=-2.0)
    pair = result.states.loc[result.states["process"].isin(["thermal", "water"])]
    assert set(pair["state"]) == {"unresolved"}
    assert set(pair["reason"]).issubset({"interval_process_challenge", "identical_shared_carrier_closure"})


def test_equal_prior_score_fit_is_calibrated_under_imbalanced_null_training_sample():
    import math
    import numpy as np
    import pandas as pd
    from sdmr.process_id.evidence import _fit_score

    train = pd.DataFrame({
        "x": np.zeros(780),
        "label": np.r_[np.ones(180, dtype=int), np.zeros(600, dtype=int)],
    })
    test = pd.DataFrame({
        "x": np.zeros(200),
        "label": np.r_[np.ones(100, dtype=int), np.zeros(100, dtype=int)],
    })
    score = _fit_score(train, test, ("x",), C=1.0)
    assert abs(score + math.log(2.0)) < 0.01


def test_quadratic_occurrence_learner_represents_pure_interaction_signal():
    import numpy as np
    import pandas as pd
    from sdmr.process_id.evidence import _fit_score

    rng = np.random.default_rng(991)
    train = pd.DataFrame({
        "x1": rng.normal(size=1200),
        "x2": rng.normal(size=1200),
    })
    train["label"] = (train["x1"] * train["x2"] > 0).astype(int)

    test = pd.DataFrame({
        "x1": rng.normal(size=800),
        "x2": rng.normal(size=800),
    })
    test["label"] = (test["x1"] * test["x2"] > 0).astype(int)

    linear = _fit_score(train, test, ("x1", "x2"), C=1.0, learner="linear")
    quadratic = _fit_score(train, test, ("x1", "x2"), C=1.0, learner="quadratic")

    assert quadratic > linear + 0.20


def test_hgb_occurrence_learner_is_equal_prior_calibrated_and_deterministic():
    import math
    import numpy as np
    import pandas as pd
    from sdmr.process_id.evidence import _fit_score

    rng = np.random.default_rng(992)
    train = pd.DataFrame({
        "x": rng.normal(size=780),
        "label": np.r_[np.ones(180, dtype=int), np.zeros(600, dtype=int)],
    })
    train["x"] = 0.0
    test = pd.DataFrame({
        "x": np.zeros(200),
        "label": np.r_[np.ones(100, dtype=int), np.zeros(100, dtype=int)],
    })
    first = _fit_score(train, test, ("x",), C=1.0, learner="hgb")
    second = _fit_score(train, test, ("x",), C=1.0, learner="hgb")
    assert abs(first + math.log(2.0)) < 0.01
    assert first == second


def test_hgb_route_label_is_explicit():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process", seed=206, n_cells=900, n_occurrences=90, n_background=300
    )
    result = evaluate_occurrence_processes(
        world, n_splits=3, learner="hgb", adequacy_floor=-2.0
    )
    assert set(result.evidence["route"]) == {"hgb"}


def test_occurrence_learner_rejects_unknown_route():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process", seed=207, n_cells=900, n_occurrences=90, n_background=300
    )
    with pytest.raises(ValueError, match="learner"):
        evaluate_occurrence_processes(world, n_splits=3, learner="neural_magic")


def test_hgb_balanced_weights_preserve_equal_prior_and_empirical_loss_scale():
    import numpy as np
    from sdmr.process_id.evidence import _hgb_balanced_sample_weight

    y = np.r_[np.ones(180, dtype=int), np.zeros(600, dtype=int)]
    weights = _hgb_balanced_sample_weight(y)

    assert weights.sum() == pytest.approx(len(y))
    assert weights[y == 1].sum() == pytest.approx(len(y) / 2)
    assert weights[y == 0].sum() == pytest.approx(len(y) / 2)
    assert np.all(weights > 0)


def test_hgb_balanced_weights_require_both_classes():
    import numpy as np
    from sdmr.process_id.evidence import _hgb_balanced_sample_weight

    with pytest.raises(ValueError, match="both classes"):
        _hgb_balanced_sample_weight(np.ones(20, dtype=int))


def test_random_cell_split_is_deterministic_and_keeps_duplicate_cells_together():
    import numpy as np
    import pandas as pd
    from sdmr.process_id.evidence import _finite_split_indices

    sample = pd.DataFrame({
        "cell_id": [1, 1, 2, 3, 3, 4, 5, 5, 6, 7, 8, 8],
        "label":   [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    })
    spatial_groups = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])

    first = _finite_split_indices(
        sample, spatial_groups, n_splits=3, split_mode="random_cell"
    )
    second = _finite_split_indices(
        sample, spatial_groups, n_splits=3, split_mode="random_cell"
    )

    assert len(first) == len(second) == 3
    for (tr1, te1), (tr2, te2) in zip(first, second, strict=True):
        np.testing.assert_array_equal(tr1, tr2)
        np.testing.assert_array_equal(te1, te2)
        train_cells = set(sample.iloc[tr1]["cell_id"])
        test_cells = set(sample.iloc[te1]["cell_id"])
        assert train_cells.isdisjoint(test_cells)


def test_finite_process_challenge_rejects_unknown_split_mode():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process", seed=208, n_cells=900, n_occurrences=90, n_background=300
    )
    with pytest.raises(ValueError, match="split_mode"):
        evaluate_occurrence_processes(
            world, n_splits=3, learner="hgb", split_mode="checkerboard"
        )


def test_random_cell_split_runs_same_hgb_process_challenge_with_explicit_geometry():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "unique_process", seed=23002, n_cells=1000, n_occurrences=100, n_background=340
    )
    spatial = evaluate_occurrence_processes(
        world, n_splits=3, learner="hgb", split_mode="spatial"
    )
    random_cell = evaluate_occurrence_processes(
        world, n_splits=3, learner="hgb", split_mode="random_cell"
    )

    assert set(spatial.evidence["split_mode"]) == {"spatial"}
    assert set(random_cell.evidence["split_mode"]) == {"random_cell"}
    assert tuple(spatial.states["process"]) == tuple(random_cell.states["process"])
    assert spatial.evidence["complete"].all()
    assert random_cell.evidence["complete"].all()


def test_random_cell_preserves_observation_and_shared_closure_refusals():
    from sdmr.process_id.evidence import evaluate_occurrence_processes
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    confounded = simulate_process_world(
        "observation_confounded",
        seed=209,
        n_cells=1000,
        n_occurrences=100,
        n_background=340,
    )
    confounded_result = evaluate_occurrence_processes(
        confounded, n_splits=3, learner="hgb", split_mode="random_cell", adequacy_floor=-2.0
    )
    thermal = confounded_result.states.loc[
        confounded_result.states["process"].eq("thermal")
    ].iloc[0]
    assert thermal["state"] == "unresolved"
    assert thermal["reason"] == "observation_process_not_separable"

    shared = simulate_process_world(
        "shared_carrier",
        seed=210,
        n_cells=1000,
        n_occurrences=100,
        n_background=340,
    )
    shared_result = evaluate_occurrence_processes(
        shared, n_splits=3, learner="hgb", split_mode="random_cell", adequacy_floor=-2.0
    )
    pair = shared_result.states.loc[
        shared_result.states["process"].isin(["thermal", "water"])
    ]
    assert set(pair["state"]) == {"unresolved"}
