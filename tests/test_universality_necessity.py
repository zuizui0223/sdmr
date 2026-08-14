import numpy as np
import pandas as pd

from sdmr import ModelSpec
from sdmr.universality import benchmark_process_core_taxon_split, benchmark_repeated_process_core_splits


def _corpus():
    occs, bgs = [], []
    for i, species in enumerate("abcdef"):
        rng = np.random.default_rng(1200 + i)
        n_p, n_b = 96, 240
        lon_p = rng.uniform(i * 10, i * 10 + 7, n_p)
        lat_p = rng.uniform(5, 10, n_p)
        lon_b = rng.uniform(i * 10, i * 10 + 7, n_b)
        lat_b = rng.uniform(-8, 10, n_b)
        signal_p = lat_p + rng.normal(0, 0.2, n_p)
        signal_b = lat_b + rng.normal(0, 0.2, n_b)
        occs.append(
            pd.DataFrame(
                {
                    "species": species,
                    "longitude": lon_p,
                    "latitude": lat_p,
                    "signal": signal_p,
                    "signal_copy": signal_p + rng.normal(0, 0.02, n_p),
                    "noise": rng.normal(size=n_p),
                }
            )
        )
        bgs.append(
            pd.DataFrame(
                {
                    "species": species,
                    "longitude": lon_b,
                    "latitude": lat_b,
                    "signal": signal_b,
                    "signal_copy": signal_b + rng.normal(0, 0.02, n_b),
                    "noise": rng.normal(size=n_b),
                }
            )
        )
    return pd.concat(occs, ignore_index=True), pd.concat(bgs, ignore_index=True)


def _manifest():
    return pd.DataFrame(
        {
            "predictor": ["signal", "signal_copy", "noise"],
            "source": ["synthetic"] * 3,
            "version": ["1"] * 3,
            "candidate_class": ["core"] * 3,
            "process": ["climate_signal", "climate_signal", "noise_process"],
            "mechanism": ["signal", "substitute", "noise"],
        }
    )


def test_unseen_taxa_process_drop_and_matched_random_core_are_recorded():
    occ, bg = _corpus()
    result = benchmark_process_core_taxon_split(
        occ,
        bg,
        ["signal", "signal_copy", "noise"],
        _manifest(),
        strategy="predictive",
        taxon_validation_fraction=0.34,
        min_process_selection_fraction=0.5,
        process_top_k=1,
        random_process_repeats=2,
        model_specs=[ModelSpec(C=1.0, degree=1)],
        max_predictors=2,
        random_state=14,
    )
    assert result.core_processes == ["climate_signal"]
    assert set(result.validation_process_drop["process"]) == {"climate_signal"}
    assert result.validation_process_drop["process_drop_loss"].mean() > 0.1
    assert set(result.validation_process_drop["comparison_baseline"]) == {"uninformative_rank_0.5"}
    assert result.random_core_metrics["repeat"].nunique() == 2
    assert len(result.core_vs_random) > 0
    assert "core_minus_random_presence_rank" in result.core_vs_random


def test_repeated_process_stability_includes_unseen_taxon_necessity():
    occ, bg = _corpus()
    result = benchmark_repeated_process_core_splits(
        occ,
        bg,
        ["signal", "signal_copy", "noise"],
        _manifest(),
        strategy="predictive",
        seeds=(5, 6),
        taxon_validation_fraction=0.34,
        min_process_selection_fraction=0.5,
        process_top_k=1,
        random_process_repeats=1,
        model_specs=[ModelSpec(C=1.0, degree=1)],
        max_predictors=2,
    )
    row = result.process_stability.set_index("process").loc["climate_signal"]
    assert row["core_stability"] == 1.0
    assert row["mean_validation_process_drop"] > 0.1
    assert row["positive_validation_drop_fraction"] == 1.0
    assert result.validation_process_drop["split_id"].nunique() == 2
    assert result.core_vs_random["split_id"].nunique() == 2
