from sdmr.model import ModelSpec
from sdmr.niche_recovery_cv import RecoveryCandidate
from sdmr.observation_admissibility import observation_model_admissibility


def _candidates():
    return {
        "ecology_only": RecoveryCandidate(
            "ecology_only",
            ("temperature", "water"),
            ModelSpec(C=1.0, degree=2, penalty="l2"),
        ),
        "nuisance_column_but_not_declared": RecoveryCandidate(
            "nuisance_column_but_not_declared",
            ("temperature", "water", "recording_bias"),
            ModelSpec(C=1.0, degree=2, penalty="l2"),
        ),
        "ecology_plus_nuisance": RecoveryCandidate(
            "ecology_plus_nuisance",
            ("temperature", "water", "recording_bias"),
            ModelSpec(C=1.0, degree=2, penalty="l2"),
            observation_predictors=("recording_bias",),
        ),
        "nuisance_only": RecoveryCandidate(
            "nuisance_only",
            ("recording_bias",),
            ModelSpec(C=1.0, degree=1, penalty="l2"),
            observation_predictors=("recording_bias",),
        ),
    }


def test_inactive_observation_gate_restricts_no_candidates():
    result = observation_model_admissibility(
        _candidates(),
        ("recording_bias",),
        correction_active=False,
    )
    assert set(result.admissible_candidates) == set(_candidates())
    assert result.inadmissible_candidates == ()


def test_active_gate_requires_nuisance_to_be_declared_as_observation_process():
    result = observation_model_admissibility(
        _candidates(),
        ("recording_bias",),
        correction_active=True,
    )
    assert set(result.admissible_candidates) == {"ecology_plus_nuisance", "nuisance_only"}
    assert set(result.inadmissible_candidates) == {
        "ecology_only",
        "nuisance_column_but_not_declared",
    }


def test_merely_fitting_nuisance_as_ecological_predictor_is_not_admissible():
    result = observation_model_admissibility(
        _candidates(),
        ("recording_bias",),
        correction_active=True,
    )
    assert "nuisance_column_but_not_declared" not in result.admissible_candidates
