import numpy as np
import pandas as pd

from sdmr.method import MODEL_ROLE, OUTER_BLOCK_COL, OUTER_ROLE_COL, SEALED_ROLE
from sdmr.model import ModelSpec
from sdmr.robust_protocol import benchmark_product_a_method_across_sensitivity_specs


def _synthetic_specifications():
    rng = np.random.default_rng(73)
    species_names = ["Plant a", "Plant b", "Plant c", "Plant d"]
    occurrence_parts = []
    background_by_spec = {"buffer_150km": [], "buffer_500km": []}

    for s_idx, species in enumerate(species_names):
        n_model_p = 12
        n_sealed_p = 4
        n_model_b = 24
        n_sealed_b = 8

        p_n = n_model_p + n_sealed_p
        p_lon = np.linspace(-2, 2, p_n) + s_idx * 8
        p_lat = np.linspace(-1, 1, p_n) + s_idx * 2
        occurrence_parts.append(
            pd.DataFrame(
                {
                    "species": species,
                    "longitude": p_lon,
                    "latitude": p_lat,
                    "signal": rng.normal(1.4 + 0.05 * s_idx, 0.25, p_n),
                    "noise": rng.normal(0, 1, p_n),
                    OUTER_ROLE_COL: [MODEL_ROLE] * n_model_p + [SEALED_ROLE] * n_sealed_p,
                    OUTER_BLOCK_COL: list(np.arange(n_model_p) % 6) + [6, 6, 7, 7],
                }
            )
        )

        for spec_idx, spec_name in enumerate(background_by_spec):
            b_n = n_model_b + n_sealed_b
            background_by_spec[spec_name].append(
                pd.DataFrame(
                    {
                        "species": species,
                        "longitude": np.linspace(-2.5, 2.5, b_n) + s_idx * 8 + 0.15 * spec_idx,
                        "latitude": np.linspace(-1.2, 1.2, b_n) + s_idx * 2,
                        "signal": rng.normal(-1.2 + 0.05 * spec_idx, 0.3, b_n),
                        "noise": rng.normal(0, 1, b_n),
                        OUTER_ROLE_COL: [MODEL_ROLE] * n_model_b + [SEALED_ROLE] * n_sealed_b,
                        OUTER_BLOCK_COL: list(np.arange(n_model_b) % 6) + [6, 6, 6, 6, 7, 7, 7, 7],
                    }
                )
            )

    occurrences = pd.concat(occurrence_parts, ignore_index=True)
    return {
        name: (occurrences.copy(), pd.concat(parts, ignore_index=True))
        for name, parts in background_by_spec.items()
    }


def test_parallel_robust_product_a_is_exactly_equivalent_to_sequential():
    specifications = _synthetic_specifications()
    universes = {"core": ["signal"], "expanded": ["signal", "noise"]}
    kwargs = dict(
        taxon_validation_fraction=0.25,
        random_state=19,
        model_specs=[ModelSpec(C=1.0, degree=1, penalty="l2")],
        inner_folds=2,
        max_predictors=2,
        random_repeats=0,
        compute_drop_one=False,
    )

    sequential = benchmark_product_a_method_across_sensitivity_specs(
        specifications, universes, n_jobs=1, **kwargs
    )
    parallel = benchmark_product_a_method_across_sensitivity_specs(
        specifications, universes, n_jobs=2, **kwargs
    )

    assert parallel.winning_universe == sequential.winning_universe
    assert parallel.winning_strategy == sequential.winning_strategy
    assert parallel.winning_predictors == sequential.winning_predictors
    assert parallel.discovery_species == sequential.discovery_species
    assert parallel.validation_species == sequential.validation_species
    assert parallel.occurrence_sha256 == sequential.occurrence_sha256
    assert parallel.occurrence_feature_sha256 == sequential.occurrence_feature_sha256

    pd.testing.assert_frame_equal(parallel.discovery_metrics, sequential.discovery_metrics)
    pd.testing.assert_frame_equal(parallel.discovery_summary, sequential.discovery_summary)
    pd.testing.assert_frame_equal(parallel.validation_metrics, sequential.validation_metrics)
    pd.testing.assert_frame_equal(parallel.validation_summary, sequential.validation_summary)
    pd.testing.assert_frame_equal(parallel.paired_validation_deltas, sequential.paired_validation_deltas)
