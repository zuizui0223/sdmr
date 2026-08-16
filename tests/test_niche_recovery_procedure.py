import numpy as np

from sdmr.known_truth_scenarios import simulate_known_truth_plant_niche
from sdmr.model import ModelSpec
from sdmr.niche_recovery_procedure import (
    RecoveryProcedure,
    benchmark_recovery_procedures,
    cross_validated_recovery_procedure,
    select_recovery_procedure,
)


def _data(seed=71):
    sim = simulate_known_truth_plant_niche(
        "gaussian",
        seed=seed,
        n_cells=1300,
        n_occurrences=180,
        n_target_group=500,
    )
    cuts = [-1.2, 0.0, 1.2]
    p_groups = np.digitize(sim.occurrences["longitude"].to_numpy(float), cuts)
    b_groups = np.digitize(sim.target_group["longitude"].to_numpy(float), cuts)
    ecological = ("temperature", "water", "temp_proxy", "soil", "noise")
    return sim.occurrences, sim.target_group, p_groups, b_groups, ecological


def test_niche_forward_is_rerun_inside_outer_spatial_folds():
    presence, background, p_groups, b_groups, predictors = _data()
    procedure = RecoveryProcedure(
        "niche_forward",
        ModelSpec(C=1.0, degree=2, penalty="l2"),
        inner_folds=2,
        max_predictors=2,
    )
    result = cross_validated_recovery_procedure(
        presence,
        background,
        p_groups,
        b_groups,
        predictors,
        predictors,
        procedure,
        outer_folds=3,
    )
    assert len(result.fold_metrics) >= 2
    assert set(result.fold_metrics["strategy"]) == {"niche_forward"}
    assert set(result.fold_metrics["candidate"]) == {procedure.label}
    assert not result.selection_trace.empty
    assert result.selection_trace["outer_fold"].nunique() >= 2
    for value in result.fold_metrics["selected_ecological_predictors"]:
        selected = {x for x in str(value).split(",") if x}
        assert selected <= set(predictors)
        assert 1 <= len(selected) <= 2

    forbidden = {"true_suitability", "truth_surface_rank", "driver_process_f1"}
    assert not forbidden.intersection(result.fold_metrics.columns)
    assert not forbidden.intersection(result.selection_trace.columns)


def test_all_and_vif_are_procedures_not_frozen_global_predictor_sets():
    presence, background, p_groups, b_groups, predictors = _data(seed=72)
    procedures = (
        RecoveryProcedure(
            "all",
            ModelSpec(C=1.0, degree=1, penalty="l2"),
            inner_folds=2,
        ),
        RecoveryProcedure(
            "vif",
            ModelSpec(C=1.0, degree=1, penalty="l2"),
            inner_folds=2,
            vif_threshold=5.0,
        ),
    )
    result = benchmark_recovery_procedures(
        presence,
        background,
        p_groups,
        b_groups,
        predictors,
        predictors,
        procedures,
        outer_folds=3,
    )
    assert set(result.fold_metrics["procedure"]) == {p.label for p in procedures}
    all_rows = result.fold_metrics.loc[result.fold_metrics["strategy"].eq("all")]
    assert all(all_rows["n_ecological_predictors"].eq(len(predictors)))
    vif_rows = result.fold_metrics.loc[result.fold_metrics["strategy"].eq("vif")]
    assert (vif_rows["n_ecological_predictors"] <= len(predictors)).all()


def test_procedure_selector_uses_ecological_recovery_after_prediction_adequacy():
    presence, background, p_groups, b_groups, predictors = _data(seed=73)
    procedures = (
        RecoveryProcedure(
            "all",
            ModelSpec(C=1.0, degree=1, penalty="l2"),
            inner_folds=2,
        ),
        RecoveryProcedure(
            "niche_forward",
            ModelSpec(C=1.0, degree=2, penalty="l2"),
            inner_folds=2,
            max_predictors=2,
        ),
    )
    benchmark = benchmark_recovery_procedures(
        presence,
        background,
        p_groups,
        b_groups,
        predictors,
        predictors,
        procedures,
        outer_folds=3,
    )
    selection = select_recovery_procedure(benchmark)
    assert selection.candidate in {p.label for p in procedures}
    assert set(selection.pareto_front) <= {p.label for p in procedures}
    assert "weighted_score" not in selection.candidate_summary.columns


def test_predictive_forward_retains_prediction_role_as_baseline():
    presence, background, p_groups, b_groups, predictors = _data(seed=74)
    procedure = RecoveryProcedure(
        "predictive_forward",
        ModelSpec(C=1.0, degree=1, penalty="l2"),
        inner_folds=2,
        max_predictors=2,
        predictive_min_gain=0.0,
    )
    result = cross_validated_recovery_procedure(
        presence,
        background,
        p_groups,
        b_groups,
        predictors,
        predictors,
        procedure,
        outer_folds=3,
    )
    assert len(result.fold_metrics) >= 2
    assert set(result.fold_metrics["strategy"]) == {"predictive_forward"}
    assert not result.selection_trace.empty
    assert "inner_presence_rank" in result.selection_trace.columns
