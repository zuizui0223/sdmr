import math

import pandas as pd


def test_expected_targets_override_observation_confounded_process():
    from sdmr.process_id.known_truth.development import expected_occurrence_targets
    from sdmr.process_id.known_truth.oracle import evaluate_oracle_states
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world = simulate_process_world(
        "observation_confounded", seed=301, n_cells=900, n_occurrences=90, n_background=300
    )
    oracle = evaluate_oracle_states(world, n_splits=3, baseline_r2_floor=0.70)
    target = expected_occurrence_targets(world, oracle)
    thermal = target.loc[target["process"].eq("thermal")].iloc[0]
    assert thermal["expected_state"] == "unresolved"


def test_expected_targets_mark_shared_carrier_and_interaction_boundaries():
    from sdmr.process_id.known_truth.development import expected_occurrence_targets
    from sdmr.process_id.known_truth.oracle import evaluate_oracle_states
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    shared = simulate_process_world(
        "shared_carrier", seed=302, n_cells=900, n_occurrences=90, n_background=300
    )
    shared_target = expected_occurrence_targets(
        shared, evaluate_oracle_states(shared, n_splits=3, baseline_r2_floor=0.70)
    )
    assert shared_target.loc[
        shared_target["process"].isin(["thermal", "water"]), "unique_attribution_forbidden"
    ].all()

    interaction = simulate_process_world(
        "interaction", seed=303, n_cells=900, n_occurrences=90, n_background=300
    )
    interaction_target = expected_occurrence_targets(
        interaction, evaluate_oracle_states(interaction, n_splits=3, baseline_r2_floor=0.70)
    )
    assert interaction_target.loc[
        interaction_target["process"].isin(["thermal", "water"]), "unique_attribution_forbidden"
    ].all()


def test_development_panel_keeps_complete_world_seed_process_denominator():
    from sdmr.process_id.known_truth.development import run_development_panel

    result = run_development_panel(
        seeds=(401,),
        worlds=("unique_process", "observation_confounded"),
        n_cells=800,
        n_occurrences=80,
        n_background=260,
        n_splits=2,
        oracle_baseline_r2_floor=0.65,
        occurrence_adequacy_floor=-2.0,
    )
    assert len(result.comparison) == 2 * 6
    assert result.comparison[["world", "seed", "process"]].drop_duplicates().shape[0] == 12
    assert len(result.world_summary) == 2
    assert set(result.world_summary["world"]) == {"unique_process", "observation_confounded"}


def test_development_panel_is_deterministic_for_same_seed():
    from sdmr.process_id.known_truth.development import run_development_panel

    kwargs = dict(
        seeds=(402,),
        worlds=("unique_process",),
        n_cells=700,
        n_occurrences=70,
        n_background=220,
        n_splits=2,
        oracle_baseline_r2_floor=0.65,
        occurrence_adequacy_floor=-2.0,
    )
    first = run_development_panel(**kwargs)
    second = run_development_panel(**kwargs)
    pd.testing.assert_frame_equal(first.comparison, second.comparison)
    pd.testing.assert_frame_equal(first.world_summary, second.world_summary)
    assert first.metrics.keys() == second.metrics.keys()
    for key in first.metrics:
        left = first.metrics[key]
        right = second.metrics[key]
        if isinstance(left, float) and math.isnan(left):
            assert isinstance(right, float) and math.isnan(right)
        else:
            assert left == right


def test_development_metrics_include_required_diagnostics():
    from sdmr.process_id.known_truth.development import summarize_development_comparison

    comparison = pd.DataFrame([
        {"world": "a", "seed": 1, "process": "p1", "target_state": "contributory", "occurrence_state": "contributory", "unique_attribution_forbidden": False},
        {"world": "a", "seed": 1, "process": "p2", "target_state": "replaceable", "occurrence_state": "replaceable", "unique_attribution_forbidden": False},
        {"world": "b", "seed": 1, "process": "p1", "target_state": "unresolved", "occurrence_state": "unresolved", "unique_attribution_forbidden": True},
        {"world": "b", "seed": 1, "process": "p2", "target_state": "unresolved", "occurrence_state": "unresolved", "unique_attribution_forbidden": True},
        {"world": "c", "seed": 1, "process": "p1", "target_state": "unavailable", "occurrence_state": "unavailable", "unique_attribution_forbidden": False},
    ])
    metrics, confusion, process_summary, world_summary = summarize_development_comparison(comparison)
    assert metrics["positive_recovery"] == 1.0
    assert metrics["false_positive_rate"] == 0.0
    assert metrics["overresolution_rate"] == 0.0
    assert metrics["exact_state_agreement"] == 1.0
    assert metrics["unavailable_cell_count"] == 1
    assert metrics["false_unique_attribution_rate"] == 0.0
    assert set(confusion.columns) == {"target_state", "occurrence_state", "count"}
    assert {"process", "positive_recovery", "false_positive_rate"}.issubset(process_summary.columns)
    assert {"world", "exact_state_agreement"}.issubset(world_summary.columns)
