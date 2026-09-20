import pandas as pd


def test_occurrence_oracle_audit_metrics_use_distribution_positive_denominator():
    from sdmr.process_id.known_truth.occurrence_oracle_audit import (
        summarize_occurrence_oracle_crosswalk,
    )

    crosswalk = pd.DataFrame([
        {
            "world": "unique_process",
            "seed": 1,
            "process": "thermal",
            "learner": "linear",
            "truth_state": "contributory",
            "distribution_state": "replaceable",
            "finite_state": "replaceable",
            "truth_positive": True,
            "distribution_positive": False,
            "finite_positive": False,
            "truth_positive_but_distribution_not_positive": True,
            "finite_false_negative_given_distribution_positive": False,
            "finite_false_positive_given_distribution_not_positive": False,
        },
        {
            "world": "interaction",
            "seed": 1,
            "process": "water",
            "learner": "linear",
            "truth_state": "contributory",
            "distribution_state": "contributory",
            "finite_state": "unresolved",
            "truth_positive": True,
            "distribution_positive": True,
            "finite_positive": False,
            "truth_positive_but_distribution_not_positive": False,
            "finite_false_negative_given_distribution_positive": True,
            "finite_false_positive_given_distribution_not_positive": False,
        },
        {
            "world": "interaction",
            "seed": 1,
            "process": "water",
            "learner": "quadratic",
            "truth_state": "contributory",
            "distribution_state": "contributory",
            "finite_state": "contributory",
            "truth_positive": True,
            "distribution_positive": True,
            "finite_positive": True,
            "truth_positive_but_distribution_not_positive": False,
            "finite_false_negative_given_distribution_positive": False,
            "finite_false_positive_given_distribution_not_positive": False,
        },
        {
            "world": "shared_carrier",
            "seed": 1,
            "process": "thermal",
            "learner": "linear",
            "truth_state": "unresolved",
            "distribution_state": "unresolved",
            "finite_state": "replaceable",
            "truth_positive": False,
            "distribution_positive": False,
            "finite_positive": False,
            "truth_positive_but_distribution_not_positive": False,
            "finite_false_negative_given_distribution_positive": False,
            "finite_false_positive_given_distribution_not_positive": False,
        },
    ])
    oracle_states = pd.DataFrame([
        {
            "world": "unique_process",
            "seed": 1,
            "process": "thermal",
            "state": "replaceable",
            "full_numerically_adequate": True,
        },
        {
            "world": "interaction",
            "seed": 1,
            "process": "water",
            "state": "contributory",
            "full_numerically_adequate": True,
        },
        {
            "world": "shared_carrier",
            "seed": 1,
            "process": "thermal",
            "state": "unresolved",
            "full_numerically_adequate": True,
        },
    ])

    metrics, by_world, by_process = summarize_occurrence_oracle_crosswalk(
        crosswalk, oracle_states
    )
    assert metrics["truth_positive_cells"] == 2
    assert metrics["truth_positive_distribution_positive_cells"] == 1
    assert metrics["truth_positive_distribution_positive_fraction"] == 0.5
    assert metrics["finite_positive_recovery"]["linear"] == 0.0
    assert metrics["finite_positive_recovery"]["quadratic"] == 1.0
    assert metrics["finite_false_positive_rate_on_replaceable"]["linear"] == 0.0
    assert metrics["finite_overresolution_rate_on_unresolved"]["linear"] == 1.0
    assert metrics["occurrence_oracle_unavailable_cells"] == 0
    assert {"world", "truth_positive", "distribution_positive"}.issubset(by_world.columns)
    assert {"process", "truth_positive", "distribution_positive"}.issubset(by_process.columns)


def test_run_occurrence_oracle_audit_keeps_complete_three_level_keys():
    from sdmr.process_id.known_truth.occurrence_oracle_audit import (
        run_occurrence_oracle_audit,
    )

    result = run_occurrence_oracle_audit(
        seeds=(701,),
        worlds=("unique_process", "null_correlated"),
        n_cells=800,
        n_occurrences=80,
        n_background=260,
        n_splits=2,
        truth_baseline_r2_floor=0.65,
        occurrence_oracle_approximation_tolerance=0.05,
        finite_adequacy_floor=-2.0,
    )
    assert set(result.crosswalk["learner"]) == {"linear", "quadratic"}
    assert set(result.crosswalk["world"]) == {"unique_process", "null_correlated"}
    assert result.crosswalk[["world", "seed", "process", "learner"]].duplicated().sum() == 0
    assert result.occurrence_oracle_states[["world", "seed", "process"]].duplicated().sum() == 0
    assert result.truth_states[["world", "seed", "process"]].duplicated().sum() == 0
    assert len(result.truth_states) == 2 * 6
