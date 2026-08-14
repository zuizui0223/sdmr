import numpy as np
import pandas as pd
import pytest

from sdmr import ModelSpec
from sdmr.specification import (
    benchmark_matched_data_specifications,
    occurrence_table_fingerprint,
    validate_matched_occurrence_specifications,
)


def _corpus():
    occs, bg_wide, bg_narrow = [], [], []
    for i, species in enumerate("abcdef"):
        rng = np.random.default_rng(100 + i)
        n_p, n_b = 90, 220
        lon_p = rng.uniform(i * 20, i * 20 + 10, n_p)
        lat_p = rng.uniform(5, 10, n_p)
        occs.append(pd.DataFrame({
            "gbifID": [f"{species}-p-{j}" for j in range(n_p)],
            "species": species,
            "longitude": lon_p,
            "latitude": lat_p,
            "signal": lat_p + rng.normal(0, .25, n_p),
            "noise": rng.normal(size=n_p),
        }))
        for container, low in ((bg_wide, -10), (bg_narrow, -2)):
            lon_b = rng.uniform(i * 20, i * 20 + 10, n_b)
            lat_b = rng.uniform(low, 10, n_b)
            container.append(pd.DataFrame({
                "species": species,
                "longitude": lon_b,
                "latitude": lat_b,
                "signal": lat_b + rng.normal(0, .25, n_b),
                "noise": rng.normal(size=n_b),
            }))
    return (
        pd.concat(occs, ignore_index=True),
        pd.concat(bg_wide, ignore_index=True),
        pd.concat(bg_narrow, ignore_index=True),
    )


def test_occurrence_fingerprint_rejects_direct_ranking_when_test_evidence_changes():
    occ, bg1, bg2 = _corpus()
    changed = occ.iloc[:-1].copy()
    assert occurrence_table_fingerprint(occ) != occurrence_table_fingerprint(changed)
    with pytest.raises(ValueError, match="identical occurrence evidence"):
        validate_matched_occurrence_specifications({"a": (occ, bg1), "b": (changed, bg2)})


def test_background_specification_and_strategy_are_frozen_on_discovery_taxa():
    occ, bg1, bg2 = _corpus()
    result = benchmark_matched_data_specifications(
        {"wide_M": (occ, bg1), "narrow_M": (occ.copy(), bg2)},
        ["signal", "noise"],
        taxon_validation_fraction=0.34,
        model_specs=[ModelSpec(C=1.0, degree=1)],
        max_predictors=2,
        random_repeats=0,
        compute_drop_one=False,
        random_state=8,
    )
    assert set(result.discovery_species).isdisjoint(result.validation_species)
    top = result.discovery_summary.iloc[0]
    assert result.winning_specification == top["data_specification"]
    assert result.winning_strategy == top["strategy"]
    selected = result.validation_metrics.loc[result.validation_metrics["selected_by_discovery"]]
    assert selected["data_specification"].unique().tolist() == [result.winning_specification]
    assert selected["strategy"].unique().tolist() == [result.winning_strategy]
    assert selected["species"].nunique() == len(result.validation_species)
