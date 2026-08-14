import numpy as np
import pandas as pd

from sdmr import (
    ModelSpec,
    benchmark_holdout_sensitivity,
    benchmark_method_taxon_split,
    benchmark_species_methods,
    drop_one_importance,
    vif_prune_predictors,
)


def _synthetic(seed=1, n_p=180, n_b=600):
    rng = np.random.default_rng(seed)
    lon_b = rng.uniform(-20, 20, n_b)
    lat_b = rng.uniform(-15, 15, n_b)
    lon_p = rng.uniform(-20, 20, n_p)
    lat_p = rng.uniform(5, 15, n_p)

    bg_signal = lat_b + rng.normal(0, 0.3, n_b)
    occ_signal = lat_p + rng.normal(0, 0.3, n_p)
    bg = pd.DataFrame(
        {
            "species": "plant",
            "longitude": lon_b,
            "latitude": lat_b,
            "signal": bg_signal,
            "signal_copy": bg_signal + rng.normal(0, 0.02, n_b),
            "noise": rng.normal(0, 1, n_b),
        }
    )
    occ = pd.DataFrame(
        {
            "species": "plant",
            "longitude": lon_p,
            "latitude": lat_p,
            "signal": occ_signal,
            "signal_copy": occ_signal + rng.normal(0, 0.02, n_p),
            "noise": rng.normal(0, 1, n_p),
        }
    )
    return occ, bg


def test_vif_baseline_prunes_collinear_copy():
    _, bg = _synthetic()
    kept, _ = vif_prune_predictors(bg, ["signal", "signal_copy", "noise"], threshold=5)
    assert "noise" in kept
    assert len({"signal", "signal_copy"} & set(kept)) == 1


def test_product_a_freezes_methods_before_sealed_evaluation():
    occ, bg = _synthetic(5)
    specs = [
        ModelSpec(C=0.1, degree=1),
        ModelSpec(C=1, degree=1),
        ModelSpec(C=1, degree=2),
    ]
    result = benchmark_species_methods(
        occ,
        bg,
        ["signal", "signal_copy", "noise"],
        species_name="plant",
        sealed_fraction=0.2,
        model_specs=specs,
        max_predictors=2,
        random_repeats=8,
        random_state=9,
    )
    assert {"all", "vif", "predictive"} <= set(result.sealed_metrics["strategy"])
    assert set(result.protocols["predictive"].predictors) & {"signal", "signal_copy"}
    score = result.sealed_metrics.loc[
        result.sealed_metrics.strategy == "predictive", "presence_rank"
    ].iloc[0]
    assert score > 0.68
    assert len(result.random_baseline) == 8


def test_drop_one_identifies_strong_signal_as_necessary():
    occ, bg = _synthetic(12)
    train_p, test_p = occ.iloc[:120], occ.iloc[120:]
    train_b, test_b = bg.iloc[:400], bg.iloc[400:]
    importance = drop_one_importance(
        train_p,
        train_b,
        test_p,
        test_b,
        ["signal", "noise"],
        model_spec=ModelSpec(C=1, degree=1),
    )
    losses = dict(zip(importance.predictor, importance.loss))
    assert losses["signal"] > losses["noise"] + 0.05


def test_holdout_fraction_is_sensitivity_not_fixed_rule():
    occ, bg = _synthetic(7)
    out = benchmark_holdout_sensitivity(
        occ,
        bg,
        ["signal", "noise"],
        species_name="plant",
        fractions=(0.15, 0.30),
        seeds=(3,),
        model_specs=[ModelSpec(C=1, degree=1)],
        max_predictors=2,
    )
    assert set(out["sealed_fraction"]) == {0.15, 0.30}
    assert set(out["strategy"]) == {"all", "vif", "predictive"}


def test_method_strategy_is_chosen_before_unseen_taxa():
    occs, bgs = [], []
    for i, species in enumerate(["a", "b", "c", "d", "e", "f"]):
        occ, bg = _synthetic(100 + i, n_p=150, n_b=450)
        occs.append(occ.assign(species=species))
        bgs.append(bg.assign(species=species))

    result = benchmark_method_taxon_split(
        pd.concat(occs, ignore_index=True),
        pd.concat(bgs, ignore_index=True),
        ["signal", "signal_copy", "noise"],
        taxon_validation_fraction=0.33,
        model_specs=[ModelSpec(C=1, degree=1)],
        max_predictors=2,
        random_repeats=0,
        compute_drop_one=False,
        random_state=17,
    )
    assert set(result.discovery_species).isdisjoint(result.validation_species)
    assert result.winning_strategy in {"all", "vif", "predictive"}
    chosen = result.validation_metrics[result.validation_metrics.selected_by_discovery]
    assert len(chosen) == len(result.validation_species)
