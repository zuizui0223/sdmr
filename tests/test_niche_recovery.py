import numpy as np
import pandas as pd

from sdmr.niche_recovery import empirical_niche_recovery_profile


def test_good_environmental_niche_reconstruction_beats_bad_reconstruction():
    rng = np.random.default_rng(4)
    n = 2500
    reference = pd.DataFrame(
        {
            "x1": rng.normal(0, 1.5, n),
            "x2": rng.normal(0, 1.5, n),
            "x3": rng.normal(0, 1.0, n),
        }
    )
    target_center = np.array([0.8, -0.7])
    sealed = pd.DataFrame(
        {
            "x1": rng.normal(target_center[0], 0.45, 250),
            "x2": rng.normal(target_center[1], 0.50, 250),
            "x3": rng.normal(0, 1.0, 250),
        }
    )

    x1 = reference["x1"].to_numpy()
    x2 = reference["x2"].to_numpy()
    good = np.exp(-0.5 * (((x1 - 0.8) / 0.45) ** 2 + ((x2 + 0.7) / 0.50) ** 2))
    bad = np.exp(-0.5 * (((x1 + 1.0) / 0.45) ** 2 + ((x2 - 1.0) / 0.50) ** 2))

    good_profile = empirical_niche_recovery_profile(reference, sealed, good, ["x1", "x2", "x3"])
    bad_profile = empirical_niche_recovery_profile(reference, sealed, bad, ["x1", "x2", "x3"])

    assert good_profile.niche_overlap_schoener_d_pc12 > bad_profile.niche_overlap_schoener_d_pc12
    assert good_profile.centroid_distance < bad_profile.centroid_distance
    assert good_profile.quantile_profile_error < bad_profile.quantile_profile_error


def test_audit_basis_ignores_missing_rows_and_returns_profile():
    reference = pd.DataFrame(
        {
            "a": [-2, -1, 0, 1, 2, np.nan, 0.5],
            "b": [0, 1, 0, -1, 0, 1, 0.5],
        }
    )
    sealed = pd.DataFrame({"a": [-0.2, 0.1, 0.4], "b": [0.0, 0.1, -0.1]})
    suitability = np.array([0.1, 0.3, 1.0, 0.4, 0.1, 0.9, 0.8])

    profile = empirical_niche_recovery_profile(reference, sealed, suitability, ["a", "b"], max_components=2)

    assert profile.n_audit_components == 2
    assert profile.n_reference == 6
    assert profile.n_sealed_occurrences == 3
    assert 0 <= profile.niche_overlap_schoener_d_pc12 <= 1
