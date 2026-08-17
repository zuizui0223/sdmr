import numpy as np
import pandas as pd

from sdmr.known_truth import simulate_gaussian_plant_niche
from sdmr.model import ModelSpec
from sdmr.niche_recovery_procedure import (
    RecoveryProcedure,
    RecoveryProcedureBenchmark,
)
from sdmr.procedure_surface_stability import (
    _deterministic_model_pool_reference,
    cross_validated_recovery_procedure_with_surface_stability,
    select_stable_recovery_procedure,
)
from sdmr.validation import make_spatial_partition


STABILITY_COLUMNS = (
    "ecological_surface_stability_rank_mean",
    "ecological_surface_stability_rank_min",
    "ecological_surface_stability_nrmse_mean",
    "ecological_surface_stability_nrmse_max",
)


def _small_simulation():
    return simulate_gaussian_plant_niche(
        seed=137,
        n_cells=900,
        n_occurrences=130,
        n_target_group=450,
        sampling_bias_strength=0.8,
    )


def test_procedure_outer_refits_emit_finite_common_surface_stability():
    simulation = _small_simulation()
    presence = simulation.occurrences.reset_index(drop=True)
    background = simulation.target_group.reset_index(drop=True)
    partition = make_spatial_partition(
        presence["longitude"].to_numpy(float),
        presence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        n_blocks=4,
        holdout_fraction=0.25,
        random_state=137,
    )
    procedure = RecoveryProcedure(
        "all",
        ModelSpec(C=1.0, degree=2, penalty="l2"),
        inner_folds=2,
        max_predictors=3,
    )

    result = cross_validated_recovery_procedure_with_surface_stability(
        presence,
        background,
        partition.presence_blocks,
        partition.background_blocks,
        ("temperature", "water", "seasonality"),
        simulation.audit_predictors,
        procedure,
        outer_folds=2,
        max_stability_reference_rows=128,
    )

    metrics = result.fold_metrics
    assert len(metrics) == 2
    assert metrics["n_surface_stability_pairs"].eq(1).all()
    assert np.isfinite(metrics[list(STABILITY_COLUMNS)].to_numpy(float)).all()
    assert metrics["stability_reference_rows"].eq(128).all()
    assert not any(
        str(column).startswith("sealed_")
        or str(column).startswith("n_sealed_")
        for column in metrics.columns
    )
    assert {
        "n_outer_heldout_presence",
        "n_outer_heldout_background",
        "n_outer_heldout_occurrences",
        "heldout_pc12_envelope_coverage90",
    } <= set(metrics.columns)


def test_common_reference_is_deterministic_and_response_free():
    frame = pd.DataFrame(
        {
            "environment": np.arange(100, dtype=float),
            "arbitrary_response": np.arange(100, dtype=float)[::-1],
        }
    )
    first = _deterministic_model_pool_reference(frame, max_rows=17)
    altered = frame.copy()
    altered["arbitrary_response"] = 9999.0
    second = _deterministic_model_pool_reference(altered, max_rows=17)

    assert len(first) == 17
    assert first["environment"].tolist() == second["environment"].tolist()


def test_stable_flat_surface_cannot_bypass_recovery_front():
    rows = []
    for fold in (0, 1):
        rows.extend(
            [
                {
                    "candidate": "informative",
                    "fold": fold,
                    "presence_rank": 0.70,
                    "continuous_boyce": 0.50,
                    "or10": 0.10,
                    "n_predictors": 2,
                    "niche_overlap_schoener_d_pc12": 0.85,
                    "centroid_distance": 0.10,
                    "breadth_log_sd_error": 0.10,
                    "quantile_profile_error": 0.10,
                    "ecological_surface_stability_rank_mean": 0.80,
                    "ecological_surface_stability_rank_min": 0.70,
                    "ecological_surface_stability_nrmse_mean": 0.20,
                    "ecological_surface_stability_nrmse_max": 0.30,
                },
                {
                    "candidate": "stable_flat",
                    "fold": fold,
                    "presence_rank": 0.70,
                    "continuous_boyce": 0.50,
                    "or10": 0.10,
                    "n_predictors": 1,
                    "niche_overlap_schoener_d_pc12": 0.10,
                    "centroid_distance": 1.00,
                    "breadth_log_sd_error": 1.00,
                    "quantile_profile_error": 1.00,
                    "ecological_surface_stability_rank_mean": 1.00,
                    "ecological_surface_stability_rank_min": 1.00,
                    "ecological_surface_stability_nrmse_mean": 0.00,
                    "ecological_surface_stability_nrmse_max": 0.00,
                },
            ]
        )

    selection = select_stable_recovery_procedure(
        RecoveryProcedureBenchmark(pd.DataFrame(rows), pd.DataFrame())
    )

    assert selection.candidate == "informative"
    assert selection.stable_selection.recovery_pareto_front == ("informative",)
    assert "stable_flat" not in selection.stable_selection.stability_pareto_front
