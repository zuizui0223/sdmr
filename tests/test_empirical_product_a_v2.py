import numpy as np
import pytest

from sdmr.empirical_product_a_v2 import (
    EmpiricalNichePerturbation,
    benchmark_empirical_product_a_v2,
)
from sdmr.known_truth_scenarios import simulate_known_truth_plant_niche, standard_known_truth_candidates


def _groups(frame):
    return np.digitize(frame["longitude"].to_numpy(float), [-1.0, 0.0, 1.0])


def _perturbation(name, family, seed, *, recording_bias=3.0):
    simulation = simulate_known_truth_plant_niche(
        family,
        seed=seed,
        n_cells=1600,
        n_occurrences=200,
        n_target_group=600,
        focal_recording_bias_strength=recording_bias,
    )
    return EmpiricalNichePerturbation(
        name=name,
        perturbation_type="sampling_or_background",
        presence=simulation.occurrences,
        background=simulation.target_group,
        presence_groups=_groups(simulation.occurrences),
        background_groups=_groups(simulation.target_group),
    )


def test_empirical_orchestrator_returns_prediction_ecology_and_interpretation_separately():
    candidates_all = standard_known_truth_candidates()
    candidates = {
        name: candidates_all[name]
        for name in ("tw_linear", "tw_quadratic", "proxy_water_quadratic")
    }
    perturbations = (
        _perturbation("canonical", "gaussian", 31),
        _perturbation("sampling_alt", "gaussian", 32),
    )
    result = benchmark_empirical_product_a_v2(
        perturbations,
        candidates,
        ("temperature", "water", "temp_proxy"),
        canonical_perturbation="canonical",
        process_groups={
            "temperature": "temperature",
            "temp_proxy": "temperature",
            "water": "water",
        },
        n_splits=2,
    )
    assert result.canonical_auc_candidate in candidates
    assert result.canonical_ecological_candidate in candidates
    assert result.robust_ecological_candidate in candidates
    assert result.robustness_error is None
    assert not result.observation_correction_active
    assert result.interpretation is not None
    assert result.certificate.status in {
        "model_consensus",
        "process_consensus_model_uncertainty",
        "partial_process_consensus",
        "process_contested",
    }
    # The empirical evidence table reports diagnostics/recovery, never generating truth.
    forbidden = {"true_suitability", "truth_surface_rank", "driver_process_f1"}
    assert not forbidden.intersection(result.candidate_fold_metrics.columns)


def test_replicated_observation_signal_restricts_ecological_candidates_not_auc_comparator():
    candidates_all = standard_known_truth_candidates()
    candidates = {
        name: candidates_all[name]
        for name in ("tw_quadratic", "niche_plus_observer", "observer_only")
    }
    base = _perturbation(
        "canonical",
        "observation_confounded",
        41,
        recording_bias=6.0,
    )
    # Duplicate the same observation world under a second predeclared sensitivity
    # label so this test isolates global observation-gate plumbing rather than
    # stochastic differences between simulations.
    alternate = EmpiricalNichePerturbation(
        name="background_alt",
        perturbation_type="sampling_or_background",
        presence=base.presence.copy(),
        background=base.background.copy(),
        presence_groups=base.presence_groups.copy(),
        background_groups=base.background_groups.copy(),
    )
    result = benchmark_empirical_product_a_v2(
        (base, alternate),
        candidates,
        ("temperature", "water"),
        canonical_perturbation="canonical",
        observation_predictors=("recording_bias",),
        process_groups={
            "temperature": "temperature",
            "water": "water",
        },
        n_splits=2,
    )
    assert result.observation_correction_active
    assert set(result.observation_admissibility.admissible_candidates) == {
        "niche_plus_observer",
        "observer_only",
    }
    assert result.canonical_ecological_candidate in {
        "niche_plus_observer",
        "observer_only",
    }
    assert result.robust_ecological_candidate in {
        "niche_plus_observer",
        "observer_only",
    }
    # Conventional AUC remains free to choose any record-prediction candidate.
    assert result.canonical_auc_candidate in candidates
    assert result.observation_signal_by_perturbation["correction_active"].all()


def test_empirical_orchestrator_rejects_observation_variable_in_ecological_audit_space():
    candidates = {
        "niche_plus_observer": standard_known_truth_candidates()["niche_plus_observer"]
    }
    perturbations = (
        _perturbation("canonical", "observation_confounded", 51, recording_bias=6.0),
        _perturbation("alt", "observation_confounded", 52, recording_bias=6.0),
    )
    with pytest.raises(ValueError, match="exclude observation-process variables"):
        benchmark_empirical_product_a_v2(
            perturbations,
            candidates,
            ("temperature", "recording_bias"),
            canonical_perturbation="canonical",
            observation_predictors=("recording_bias",),
            n_splits=2,
        )
