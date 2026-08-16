import numpy as np

from sdmr.known_truth_perturbation import KnownTruthPerturbationSpec
from sdmr.known_truth_scenarios import standard_known_truth_candidates
from sdmr.replicated_observation_gate import (
    evaluate_replicated_observation_gate_perturbations,
)


PERTURBATIONS = (
    KnownTruthPerturbationSpec("sampling_low", sampling_bias_strength=0.5, access_radius=0.35),
    KnownTruthPerturbationSpec("sampling_standard", sampling_bias_strength=1.15, access_radius=0.35),
    KnownTruthPerturbationSpec("sampling_high", sampling_bias_strength=2.0, access_radius=0.35),
)


def test_strong_reproducible_observation_signal_activates_global_correction():
    result = evaluate_replicated_observation_gate_perturbations(
        "observation_confounded",
        11,
        standard_known_truth_candidates(),
        perturbations=PERTURBATIONS,
        n_cells=1800,
        n_occurrences=220,
        n_target_group=700,
        n_spatial_blocks=5,
        inner_folds=2,
        min_background=30,
        focal_recording_bias_strength=6.0,
        # Selection adequacy is not the target of this unit test.
        chance_auc=0.0,
        minimum_auc_margin=0.0,
        auc_sem_multiplier=0.0,
    )
    assert result.global_correction_active
    assert result.n_signal_perturbations == len(PERTURBATIONS)
    assert result.n_active_signal_perturbations == len(PERTURBATIONS)
    assert result.signal_summary["observation_signal_correction_active"].all()
    assert result.result.fold_metrics["observation_signal_global_active"].all()
    assert result.result.fold_metrics["observation_correction_active"].all()


def test_nonreplicated_nuisance_signal_reverts_to_identity_evidence():
    result = evaluate_replicated_observation_gate_perturbations(
        "interaction",
        3,
        standard_known_truth_candidates(),
        perturbations=PERTURBATIONS,
        n_cells=1800,
        n_occurrences=220,
        n_target_group=700,
        n_spatial_blocks=5,
        inner_folds=2,
        min_background=30,
        # Selection adequacy is not the target of this unit test.
        chance_auc=0.0,
        minimum_auc_margin=0.0,
        auc_sem_multiplier=0.0,
    )
    assert not result.global_correction_active
    assert result.n_active_signal_perturbations < result.n_signal_perturbations
    effective = result.result.fold_metrics
    uncorrected = result.uncorrected_result.fold_metrics
    assert not effective["observation_signal_global_active"].any()
    assert not effective["observation_correction_active"].any()
    assert np.allclose(effective["observation_weight_max"], 1.0)
    assert np.allclose(effective["observation_weight_truncation_cap"], 1.0)

    keys = ["candidate", "perturbation", "fold"]
    ecological = [
        "niche_overlap_schoener_d_pc12",
        "centroid_distance",
        "breadth_log_sd_error",
        "quantile_profile_error",
    ]
    left = effective[keys + ecological].sort_values(keys).reset_index(drop=True)
    right = uncorrected[keys + ecological].sort_values(keys).reset_index(drop=True)
    assert left[keys].equals(right[keys])
    for column in ecological:
        assert np.allclose(left[column], right[column], equal_nan=True)
    assert result.result.selection is not None
    assert result.uncorrected_result.selection is not None
    assert result.result.selection.candidate == result.uncorrected_result.selection.candidate
