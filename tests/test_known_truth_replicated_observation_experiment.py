from sdmr.known_truth_perturbation import KnownTruthPerturbationSpec
from sdmr.known_truth_replicated_observation_experiment import (
    run_known_truth_replicated_observation_experiment,
)


PERTURBATIONS = (
    KnownTruthPerturbationSpec("sampling_low", sampling_bias_strength=0.5, access_radius=0.35),
    KnownTruthPerturbationSpec("sampling_standard", sampling_bias_strength=1.15, access_radius=0.35),
    KnownTruthPerturbationSpec("sampling_high", sampling_bias_strength=2.0, access_radius=0.35),
)


def test_replicated_observation_experiment_applies_model_admissibility_only_to_ecology():
    choices, truth, summary, metrics, signals = (
        run_known_truth_replicated_observation_experiment(
            families=("observation_confounded",),
            seeds=(11,),
            perturbations=PERTURBATIONS,
            n_cells=1800,
            n_occurrences=220,
            n_target_group=700,
            n_spatial_blocks=5,
            inner_folds=2,
            min_background=30,
            focal_recording_bias_strength=6.0,
            # Keep candidate prediction adequacy out of this plumbing test; the
            # observation-signal gate retains its production .51/.50 thresholds.
            chance_auc=0.0,
            minimum_auc_margin=0.0,
            auc_sem_multiplier=0.0,
        )
    )
    expected = {
        "canonical_auc",
        "canonical_replicated_observation_niche_recovery",
        "replicated_observation_perturbation_robust_niche_recovery",
    }
    assert set(choices["selector"]) == expected
    assert set(truth["selector"]) == expected
    assert set(summary["selector"]) == expected
    assert choices["global_observation_correction_active"].all()

    ecological = choices.loc[~choices["selector"].eq("canonical_auc")]
    assert ecological["observation_model_admissible"].all()
    assert set(ecological["candidate"]) <= {"niche_plus_observer", "observer_only"}
    assert set(signals["admissible_candidates"]) == {"niche_plus_observer,observer_only"}
    assert signals["global_correction_active"].all()

    # Candidate selection evidence remains truth-free.
    assert "true_suitability" not in metrics.columns
    assert "truth_surface_rank" not in metrics.columns
    assert "driver_process_f1" not in metrics.columns


def test_inactive_global_observation_gate_leaves_ecological_candidate_library_open():
    choices, truth, summary, metrics, signals = (
        run_known_truth_replicated_observation_experiment(
            families=("interaction",),
            seeds=(3,),
            perturbations=PERTURBATIONS,
            n_cells=1800,
            n_occurrences=220,
            n_target_group=700,
            n_spatial_blocks=5,
            inner_folds=2,
            min_background=30,
            chance_auc=0.0,
            minimum_auc_margin=0.0,
            auc_sem_multiplier=0.0,
        )
    )
    assert not choices["global_observation_correction_active"].any()
    assert signals["inadmissible_candidates"].eq("").all()
    assert metrics["observation_model_admissible"].all()
