from pathlib import Path

import pandas as pd
import pytest

from sdmr.v2_6_empirical_model_contract import load_v2_6_empirical_model_contract
from sdmr.v2_6_empirical_model_pool_worker import _partition_contract, _procedure_library
from sdmr.v2_6_empirical_pretruth_aggregate import _route_adequacy
from sdmr.v2_6_empirical_sealed_audit import _dominates

CONFIG = Path("configs/product_a_v2_6_empirical_confirmation_contract.json")
PARTITION = Path("configs/product_a_v2_6_empirical_partition_contract.json")


def test_empirical_model_pool_algorithm_is_frozen_before_sealed_audit():
    c = load_v2_6_empirical_model_contract(CONFIG)
    p = _partition_contract(PARTITION)
    procedures = _procedure_library(c)
    assert len(procedures) == 8
    assert {x.strategy for x in procedures} == {"all", "vif", "predictive_forward", "niche_forward"}
    assert c["fixed_design"]["minimum_model_pool_predictor_coverage"] == 0.95
    assert p["n_spatial_blocks"] == 5
    assert p["partition_holdout_fraction"] == 0.20


def test_knockout_route_requires_complete_three_M_by_four_fold_evidence():
    rows = []
    for M in ("buffer_150km", "buffer_300km", "buffer_500km"):
        for fold in range(4):
            rows.append({"M": M, "fold": fold, "presence_rank": 0.60})
    complete, adequate, mean, sem = _route_adequacy(
        pd.DataFrame(rows), chance=0.50, margin=0.01, sem_multiplier=1.0
    )
    assert complete and adequate
    assert mean == pytest.approx(0.60)
    assert sem == pytest.approx(0.0)

    incomplete = pd.DataFrame(rows[:-1])
    complete, adequate, _, _ = _route_adequacy(
        incomplete, chance=0.50, margin=0.01, sem_multiplier=1.0
    )
    assert not complete
    assert not adequate


def test_ecological_pareto_comparison_has_correct_directions():
    better = pd.Series({
        "niche_overlap_schoener_d_pc12": 0.8,
        "centroid_distance": 0.2,
        "breadth_log_sd_error": 0.2,
        "quantile_profile_error": 0.2,
    })
    worse = pd.Series({
        "niche_overlap_schoener_d_pc12": 0.7,
        "centroid_distance": 0.3,
        "breadth_log_sd_error": 0.3,
        "quantile_profile_error": 0.3,
    })
    tradeoff = pd.Series({
        "niche_overlap_schoener_d_pc12": 0.9,
        "centroid_distance": 0.4,
        "breadth_log_sd_error": 0.1,
        "quantile_profile_error": 0.4,
    })
    assert _dominates(better, worse)
    assert not _dominates(worse, better)
    assert not _dominates(better, tradeoff)
    assert not _dominates(tradeoff, better)
