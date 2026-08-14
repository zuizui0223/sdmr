import numpy as np
import pandas as pd

from sdmr import ModelSpec
from sdmr.protocol_stability import benchmark_repeated_product_a_protocols
from sdmr.universe import CandidateUniverse


def _corpus():
    occs, bg_a, bg_b = [], [], []
    for i, species in enumerate("abcdef"):
        rng = np.random.default_rng(900 + i)
        n_p, n_b = 78, 190
        lon_p = rng.uniform(i * 12, i * 12 + 7, n_p)
        lat_p = rng.uniform(4, 10, n_p)
        occs.append(
            pd.DataFrame(
                {
                    "gbifID": [f"{species}-{j}" for j in range(n_p)],
                    "species": species,
                    "longitude": lon_p,
                    "latitude": lat_p,
                    "signal": lat_p + rng.normal(0, 0.2, n_p),
                    "noise": rng.normal(size=n_p),
                }
            )
        )
        for target, low in ((bg_a, -9), (bg_b, -2)):
            lon_b = rng.uniform(i * 12, i * 12 + 7, n_b)
            lat_b = rng.uniform(low, 10, n_b)
            target.append(
                pd.DataFrame(
                    {
                        "species": species,
                        "longitude": lon_b,
                        "latitude": lat_b,
                        "signal": lat_b + rng.normal(0, 0.2, n_b),
                        "noise": rng.normal(size=n_b),
                    }
                )
            )
    return pd.concat(occs, ignore_index=True), pd.concat(bg_a, ignore_index=True), pd.concat(bg_b, ignore_index=True)


def test_repeated_product_a_protocol_reports_choice_and_validation_stability():
    occ, bg_a, bg_b = _corpus()
    universes = {
        "signal": CandidateUniverse("signal", ("signal",)),
        "signal_noise": CandidateUniverse("signal_noise", ("signal", "noise")),
    }
    result = benchmark_repeated_product_a_protocols(
        {"wide": (occ, bg_a), "narrow": (occ.copy(), bg_b)},
        universes,
        seeds=(3, 4),
        sealed_fractions=(0.20,),
        taxon_validation_fraction=0.34,
        model_specs=[ModelSpec(C=1.0, degree=1)],
        max_predictors=2,
        random_repeats=0,
        compute_drop_one=False,
    )
    assert len(result.runs) == 2
    assert result.choice_stability["runs_selected"].sum() == 2
    assert set(result.component_stability["component"]) == {"data_specification", "universe", "strategy"}
    assert result.component_stability.groupby("component")["runs_selected"].sum().eq(2).all()
    assert result.selected_validation_metrics["run_id"].nunique() == 2
    assert set(result.validation_delta_summary["comparator"]) <= {"all", "vif", "predictive"}
