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


def _assert_same_product_a(left, right):
    assert left.winning_universe == right.winning_universe
    assert left.winning_strategy == right.winning_strategy
    assert left.winning_predictors == right.winning_predictors
    assert left.discovery_species == right.discovery_species
    assert left.validation_species == right.validation_species
    assert left.occurrence_sha256 == right.occurrence_sha256
    assert left.occurrence_feature_sha256 == right.occurrence_feature_sha256
    pd.testing.assert_frame_equal(left.discovery_metrics, right.discovery_metrics)
    pd.testing.assert_frame_equal(left.discovery_summary, right.discovery_summary)
    pd.testing.assert_frame_equal(left.validation_metrics, right.validation_metrics)
    pd.testing.assert_frame_equal(left.validation_summary, right.validation_summary)
    pd.testing.assert_frame_equal(left.paired_validation_deltas, right.paired_validation_deltas)


def _base_kwargs():
    return dict(
        taxon_validation_fraction=0.25,
        random_state=19,
        model_specs=[ModelSpec(C=1.0, degree=1, penalty="l2")],
        inner_folds=2,
        max_predictors=2,
        compute_drop_one=False,
    )


def test_parallel_robust_product_a_is_exactly_equivalent_to_sequential():
    specifications = _synthetic_specifications()
    universes = {"core": ["signal"], "expanded": ["signal", "noise"]}
    kwargs = _base_kwargs()

    sequential = benchmark_product_a_method_across_sensitivity_specs(
        specifications, universes, n_jobs=1, random_repeats=0, **kwargs
    )
    parallel = benchmark_product_a_method_across_sensitivity_specs(
        specifications, universes, n_jobs=2, random_repeats=0, **kwargs
    )
    _assert_same_product_a(parallel, sequential)


def test_random_baseline_repeats_do_not_change_robust_product_a_outputs():
    """Robust Product A discards SpeciesMethodBenchmarkResult.random_baseline."""
    specifications = _synthetic_specifications()
    universes = {"core": ["signal"], "expanded": ["signal", "noise"]}
    kwargs = _base_kwargs()

    no_random = benchmark_product_a_method_across_sensitivity_specs(
        specifications, universes, n_jobs=1, random_repeats=0, **kwargs
    )
    with_random = benchmark_product_a_method_across_sensitivity_specs(
        specifications, universes, n_jobs=1, random_repeats=3, **kwargs
    )
    _assert_same_product_a(with_random, no_random)
