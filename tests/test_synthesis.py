import numpy as np
import pandas as pd

from sdmr import ModelSpec
from sdmr.synthesis import benchmark_driver_corpus_from_strategy


def _species(species, shift, seed):
    rng = np.random.default_rng(seed)
    n_p, n_b = 120, 320
    lon_b = rng.uniform(-10 + shift, 10 + shift, n_b)
    lat_b = rng.uniform(-10, 10, n_b)
    lon_p = rng.uniform(-10 + shift, 10 + shift, n_p)
    lat_p = rng.uniform(4, 10, n_p)
    bg_sig = lat_b + rng.normal(0, 0.3, n_b)
    p_sig = lat_p + rng.normal(0, 0.3, n_p)
    bg = pd.DataFrame({
        "species": species, "longitude": lon_b, "latitude": lat_b,
        "signal": bg_sig, "signal_copy": bg_sig + rng.normal(0, 0.02, n_b),
        "noise": rng.normal(size=n_b),
    })
    occ = pd.DataFrame({
        "species": species, "longitude": lon_p, "latitude": lat_p,
        "signal": p_sig, "signal_copy": p_sig + rng.normal(0, 0.02, n_p),
        "noise": rng.normal(size=n_p),
    })
    return occ, bg


def _manifest():
    return pd.DataFrame({
        "predictor": ["signal", "signal_copy", "noise"],
        "source": ["synthetic"] * 3,
        "version": ["1"] * 3,
        "candidate_class": ["core"] * 3,
        "process": ["climate_signal", "climate_signal", "noise_process"],
        "mechanism": ["a", "b", "noise"],
    })


def test_product_a_strategy_feeds_product_b_without_strategy_reselection():
    occs, bgs = [], []
    for i, sp in enumerate(["a", "b", "c"]):
        occ, bg = _species(sp, i * 30, 200 + i)
        occs.append(occ); bgs.append(bg)
    result = benchmark_driver_corpus_from_strategy(
        pd.concat(occs, ignore_index=True),
        pd.concat(bgs, ignore_index=True),
        ["signal", "signal_copy", "noise"],
        _manifest(),
        strategy="predictive",
        model_specs=[ModelSpec(C=1, degree=1)],
        max_predictors=2,
        random_state=31,
    )
    assert result.strategy == "predictive"
    assert set(result.per_species_metrics["strategy"]) == {"predictive"}
    assert result.per_species_metrics["species"].nunique() == 3
    assert set(result.selection_rows["species"]) == {"a", "b", "c"}
    assert len(result.group_drop_rows) > 0
    top_process = result.process_summary.iloc[0]["process"]
    assert top_process == "climate_signal"
