import numpy as np
import pandas as pd
import pytest

from sdmr import ModelSpec
from sdmr.protocol import (
    benchmark_product_a_protocol_grid,
    occurrence_feature_fingerprint,
    validate_matched_protocol_specifications,
)
from sdmr.universe import CandidateUniverse


def _corpus():
    occs, backgrounds_a, backgrounds_b = [], [], []
    for i, species in enumerate("abcdef"):
        rng = np.random.default_rng(700 + i)
        n_p, n_b = 84, 210
        lon_p = rng.uniform(i * 15, i * 15 + 8, n_p)
        lat_p = rng.uniform(4, 10, n_p)
        signal_p = lat_p + rng.normal(0, 0.25, n_p)
        occs.append(
            pd.DataFrame(
                {
                    "gbifID": [f"{species}-{j}" for j in range(n_p)],
                    "species": species,
                    "longitude": lon_p,
                    "latitude": lat_p,
                    "signal": signal_p,
                    "noise": rng.normal(size=n_p),
                }
            )
        )
        for target, low in ((backgrounds_a, -10), (backgrounds_b, -3)):
            lon_b = rng.uniform(i * 15, i * 15 + 8, n_b)
            lat_b = rng.uniform(low, 10, n_b)
            target.append(
                pd.DataFrame(
                    {
                        "species": species,
                        "longitude": lon_b,
                        "latitude": lat_b,
                        "signal": lat_b + rng.normal(0, 0.25, n_b),
                        "noise": rng.normal(size=n_b),
                    }
                )
            )
    return (
        pd.concat(occs, ignore_index=True),
        pd.concat(backgrounds_a, ignore_index=True),
        pd.concat(backgrounds_b, ignore_index=True),
    )


def test_protocol_grid_rejects_occurrence_feature_mismatch_even_when_locations_match():
    occ, bg_a, bg_b = _corpus()
    altered = occ.copy()
    altered.loc[0, "signal"] += 1.0
    universes = {"signal_only": CandidateUniverse("signal_only", ("signal",))}
    assert occurrence_feature_fingerprint(occ, ["signal"]) != occurrence_feature_fingerprint(altered, ["signal"])
    with pytest.raises(ValueError, match="environmental features"):
        validate_matched_protocol_specifications(
            {"a": (occ, bg_a), "b": (altered, bg_b)},
            universes,
        )


def test_product_a_protocol_freezes_spec_universe_and_strategy_before_validation():
    occ, bg_a, bg_b = _corpus()
    universes = {
        "signal_only": CandidateUniverse("signal_only", ("signal",)),
        "signal_plus_noise": CandidateUniverse("signal_plus_noise", ("signal", "noise")),
    }
    result = benchmark_product_a_protocol_grid(
        {"wide_M": (occ, bg_a), "narrow_M": (occ.copy(), bg_b)},
        universes,
        taxon_validation_fraction=0.34,
        model_specs=[ModelSpec(C=1.0, degree=1)],
        max_predictors=2,
        random_repeats=0,
        compute_drop_one=False,
        random_state=17,
    )
    assert set(result.discovery_species).isdisjoint(result.validation_species)
    winner = result.discovery_summary.iloc[0]
    assert result.winning_data_specification == winner["data_specification"]
    assert result.winning_universe == winner["universe"]
    assert result.winning_strategy == winner["strategy"]
    assert result.validation_metrics["data_specification"].unique().tolist() == [result.winning_data_specification]
    assert result.validation_metrics["universe"].unique().tolist() == [result.winning_universe]
    selected = result.validation_metrics.loc[result.validation_metrics["selected_by_discovery"]]
    assert selected["strategy"].unique().tolist() == [result.winning_strategy]
    assert selected["species"].nunique() == len(result.validation_species)
    assert set(result.validation_summary["strategy"]) <= {"all", "vif", "predictive"}
