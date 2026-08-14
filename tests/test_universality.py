import numpy as np
import pandas as pd

from sdmr import ModelSpec
from sdmr.universality import benchmark_process_core_taxon_split, benchmark_repeated_process_core_splits


def _species(species, seed):
    rng = np.random.default_rng(seed)
    n_p, n_b = 110, 280
    lon_b = rng.uniform(-20, 20, n_b)
    lat_b = rng.uniform(-12, 12, n_b)
    lon_p = rng.uniform(-20, 20, n_p)
    lat_p = rng.uniform(4, 12, n_p)
    signal_b = lat_b + rng.normal(0, 0.25, n_b)
    signal_p = lat_p + rng.normal(0, 0.25, n_p)
    return (
        pd.DataFrame({
            "species": species, "longitude": lon_p, "latitude": lat_p,
            "signal": signal_p, "signal_copy": signal_p + rng.normal(0, .02, n_p),
            "noise": rng.normal(size=n_p),
        }),
        pd.DataFrame({
            "species": species, "longitude": lon_b, "latitude": lat_b,
            "signal": signal_b, "signal_copy": signal_b + rng.normal(0, .02, n_b),
            "noise": rng.normal(size=n_b),
        }),
    )


def _corpus():
    occs, bgs = [], []
    for i, sp in enumerate(list("abcdef")):
        occ, bg = _species(sp, 400 + i)
        occs.append(occ); bgs.append(bg)
    return pd.concat(occs, ignore_index=True), pd.concat(bgs, ignore_index=True)


def _manifest():
    return pd.DataFrame({
        "predictor": ["signal", "signal_copy", "noise"],
        "source": ["synthetic"] * 3,
        "version": ["1"] * 3,
        "candidate_class": ["core"] * 3,
        "process": ["climate_signal", "climate_signal", "noise_process"],
        "mechanism": ["a", "b", "noise"],
    })


def test_process_core_is_discovered_without_validation_taxa_and_transfers():
    occ, bg = _corpus()
    result = benchmark_process_core_taxon_split(
        occ, bg, ["signal", "signal_copy", "noise"], _manifest(),
        strategy="predictive", taxon_validation_fraction=0.34,
        min_process_selection_fraction=0.5, process_top_k=1,
        model_specs=[ModelSpec(C=1, degree=1)], max_predictors=2,
        random_process_repeats=0, random_state=9,
    )
    assert set(result.discovery_species).isdisjoint(result.validation_species)
    assert result.core_processes == ["climate_signal"]
    assert result.validation_comparison["core_presence_rank"].mean() > 0.65
    assert result.validation_comparison["core_minus_full_presence_rank"].mean() > -0.12


def test_repeated_taxon_splits_report_core_stability():
    occ, bg = _corpus()
    result = benchmark_repeated_process_core_splits(
        occ, bg, ["signal", "signal_copy", "noise"], _manifest(),
        strategy="predictive", seeds=(2, 3), taxon_validation_fraction=0.34,
        min_process_selection_fraction=0.5, process_top_k=1,
        model_specs=[ModelSpec(C=1, degree=1)], max_predictors=2,
        random_process_repeats=0,
    )
    stability = result.process_stability.set_index("process")
    assert stability.loc["climate_signal", "core_stability"] == 1.0
    assert result.validation_comparison["split_id"].nunique() == 2


def test_random_process_null_uses_same_sealed_occurrences_as_full_and_core():
    occ, bg = _corpus()
    result = benchmark_process_core_taxon_split(
        occ, bg, ["signal", "signal_copy", "noise"], _manifest(),
        strategy="predictive", taxon_validation_fraction=0.34,
        min_process_selection_fraction=0.5, process_top_k=1,
        model_specs=[ModelSpec(C=1, degree=1)], max_predictors=2,
        random_process_repeats=2, random_state=13,
    )
    full_counts = result.validation_full_metrics.set_index("species")["n_test_presence"].to_dict()
    assert len(result.random_core_metrics) > 0
    for row in result.random_core_metrics.itertuples(index=False):
        assert row.n_test_presence == full_counts[row.species]
