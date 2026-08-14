import numpy as np
import pandas as pd

from sdmr import ModelSpec
from sdmr.universe import (
    benchmark_method_universe_taxon_split,
    candidate_universes_from_manifest,
)


def test_manifest_builds_nested_candidate_universes():
    manifest = pd.DataFrame({
        "predictor": ["bio1", "bio12", "gdd5", "vpd"],
        "source": ["CHELSA-bioclim", "CHELSA-bioclim", "CHELSA-bioclim", "CHELSA-BIOCLIM+-archive"],
        "version": ["2.1"] * 4,
        "candidate_class": ["core_climate", "core_climate", "extended_climate", "extended_climate"],
        "process": ["temperature", "water", "thermal_energy", "drought"],
        "mechanism": ["mean", "annual", "gdd", "vpd"],
    })
    universes = candidate_universes_from_manifest(manifest)
    assert universes["bioclim19"].predictors == ("bio1", "bio12")
    assert universes["chelsa_bioclim"].predictors == ("bio1", "bio12", "gdd5")
    assert universes["active_all"].predictors == ("bio1", "bio12", "gdd5", "vpd")
    assert len(universes["active_all"].fingerprint) == 64


def _species(species, seed):
    rng = np.random.default_rng(seed)
    n_p, n_b = 120, 320
    occurrence = pd.DataFrame({
        "species": species,
        "longitude": rng.uniform(-20, 20, n_p),
        "latitude": rng.uniform(-15, 15, n_p),
        "weak": rng.normal(0, 1, n_p),
        "signal": rng.normal(4.0, 0.6, n_p),
    })
    background = pd.DataFrame({
        "species": species,
        "longitude": rng.uniform(-20, 20, n_b),
        "latitude": rng.uniform(-15, 15, n_b),
        "weak": rng.normal(0, 1, n_b),
        "signal": rng.normal(0.0, 1.0, n_b),
    })
    return occurrence, background


def test_candidate_universe_is_chosen_on_discovery_taxa_and_transfers():
    occs, bgs = [], []
    for i, species in enumerate(list("abcdef")):
        occ, bg = _species(species, 900 + i)
        occs.append(occ)
        bgs.append(bg)
    result = benchmark_method_universe_taxon_split(
        pd.concat(occs, ignore_index=True),
        pd.concat(bgs, ignore_index=True),
        {"small": ["weak"], "large": ["weak", "signal"]},
        taxon_validation_fraction=0.34,
        model_specs=[ModelSpec(C=1, degree=1)],
        max_predictors=2,
        random_repeats=0,
        compute_drop_one=False,
        random_state=21,
    )
    assert result.winning_universe == "large"
    assert set(result.discovery_species).isdisjoint(result.validation_species)
    assert result.validation_metrics["presence_rank"].mean() > 0.80
    assert set(result.validation_metrics["universe"]) == {"large"}
    counts = result.discovery_metrics.groupby("species")["n_test_presence"].nunique()
    assert counts.max() == 1
