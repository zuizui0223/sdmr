import numpy as np
import pandas as pd

from sdmr.interval_evidence_process_challenge import (
    INCOMPLETE_EVIDENCE,
    INDETERMINATE_EVIDENCE,
    INFERIOR_EVIDENCE,
    NONINFERIOR_EVIDENCE,
)
from sdmr.model import ModelSpec
from sdmr.proxy_closed_route_process_challenge import (
    fit_proxy_closed_route_process_challenge,
)


def _proxy_supported_tables(seed=41):
    rng = np.random.default_rng(seed)
    n = 240
    groups = np.tile(np.arange(8), n // 8)

    background_water = rng.normal(0.0, 1.0, n)
    background_proxy = 1.3 * background_water + rng.normal(0.0, 0.18, n)
    presence_water = rng.normal(1.35, 0.75, n)
    presence_proxy = 1.3 * presence_water + rng.normal(0.0, 0.18, n)

    background = pd.DataFrame(
        {
            "water_direct": background_water,
            "water_proxy": background_proxy,
            "noise": rng.normal(0.0, 1.0, n),
        }
    )
    presence = pd.DataFrame(
        {
            "water_direct": presence_water,
            "water_proxy": presence_proxy,
            "noise": rng.normal(0.0, 1.0, n),
        }
    )
    # Deliberately incomplete declared closure: the proxy is registered under a
    # different information family. v6 must diagnose and purge its water content
    # without changing the registry after seeing an ecological outcome.
    registry = pd.DataFrame(
        [
            {"predictor": "water_direct", "process": "water", "role": "direct"},
            {"predictor": "water_proxy", "process": "proxy_family", "role": "direct"},
            {"predictor": "noise", "process": "noise", "role": "direct"},
        ]
    )
    return presence, background, groups.copy(), groups.copy(), registry


def test_v6_exports_route_level_purge_and_leakage_evidence():
    p, b, pg, bg, registry = _proxy_supported_tables()
    fit = fit_proxy_closed_route_process_challenge(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("water_direct", "water_proxy", "noise"),
        process_registry=registry,
        process_universe=("water", "proxy_family", "noise"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
        minimum_margin=0.01,
        relative_noninferiority_margin=0.02,
        density_noninferiority_margin=0.01,
        purge_degree=2,
        purge_ridge_alpha=1.0,
    )

    assert len(fit.purged_route_summary) == 3
    assert len(fit.purged_fold_evidence) == 12
    assert set(fit.process_summary["process"]) == {"water", "proxy_family", "noise"}
    assert {"v5_status", "status_changed_from_v5"}.issubset(fit.process_summary.columns)
    assert {
        "prediction_interval_state",
        "ecological_rank_interval_state",
        "density_interval_state",
        "ecological_density_interval_state",
        "relative_evidence_state",
        "closure_predictors",
        "retained_ecological_predictors",
    }.issubset(fit.purged_route_summary.columns)
    assert set(fit.purged_route_summary["relative_evidence_state"]).issubset(
        {
            NONINFERIOR_EVIDENCE,
            INFERIOR_EVIDENCE,
            INDETERMINATE_EVIDENCE,
            INCOMPLETE_EVIDENCE,
        }
    )

    water_leak = fit.leakage_diagnostic.loc[
        fit.leakage_diagnostic["process"].eq("water")
        & fit.leakage_diagnostic["process_predictor"].eq("water_direct")
    ].iloc[0]
    assert bool(water_leak["diagnostic_complete"])
    assert water_leak["pre_purge_r2"] > 0.8
    assert water_leak["post_purge_r2"] < water_leak["pre_purge_r2"]
    assert fit.selection_receipt != fit.v5_fit.selection_receipt


def test_v6_prediction_output_is_inherited_not_retuned_by_purge():
    p, b, pg, bg, registry = _proxy_supported_tables(seed=52)
    fit = fit_proxy_closed_route_process_challenge(
        p,
        b,
        pg,
        bg,
        ecological_predictors=("water_direct", "water_proxy", "noise"),
        process_registry=registry,
        process_universe=("water", "proxy_family", "noise"),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        n_splits=4,
    )
    a = fit.predict_relative_suitability(p.iloc[:20])
    b_scores = fit.v5_fit.predict_relative_suitability(p.iloc[:20])
    assert np.allclose(a, b_scores, equal_nan=True)
