import numpy as np
import pandas as pd

from sdmr import benchmark_species, benchmark_taxon_split


def _make_species(species: str, shift: float, seed: int):
    rng = np.random.default_rng(seed)
    n_p, n_b = 120, 360
    lon_b = rng.uniform(-10 + shift, 10 + shift, n_b)
    lat_b = rng.uniform(-10, 10, n_b)
    lon_p = rng.uniform(-10 + shift, 10 + shift, n_p)
    lat_p = rng.uniform(5, 10, n_p)

    bg = pd.DataFrame(
        {
            "species": species,
            "longitude": lon_b,
            "latitude": lat_b,
            "signal": lat_b + rng.normal(0, 0.5, n_b),
            "noise": rng.normal(0, 1, n_b),
        }
    )
    occ = pd.DataFrame(
        {
            "species": species,
            "longitude": lon_p,
            "latitude": lat_p,
            "signal": lat_p + rng.normal(0, 0.5, n_p),
            "noise": rng.normal(0, 1, n_p),
        }
    )
    return occ, bg


def test_species_benchmark_selects_transferable_signal():
    occ, bg = _make_species("a", 0, 11)
    result = benchmark_species(
        occ,
        bg,
        ["signal", "noise"],
        species="a",
        max_predictors=2,
        random_state=11,
    )
    assert result.selected_predictors[0] == "signal"
    selected_score = result.outer_metrics.loc[result.outer_metrics.model == "selected", "presence_rank"].iloc[0]
    assert selected_score > 0.7


def test_taxon_split_discovers_common_signal():
    occs, bgs = [], []
    for i, sp in enumerate("abcdef"):
        occ, bg = _make_species(sp, i * 25, 100 + i)
        occs.append(occ)
        bgs.append(bg)
    result = benchmark_taxon_split(
        pd.concat(occs, ignore_index=True),
        pd.concat(bgs, ignore_index=True),
        ["signal", "noise"],
        max_predictors=2,
        common_top_k=1,
        random_state=22,
    )
    assert result.common_predictors == ["signal"]
    common = result.validation_outer[result.validation_outer.model == "common"]
    assert common["presence_rank"].mean() > 0.7
