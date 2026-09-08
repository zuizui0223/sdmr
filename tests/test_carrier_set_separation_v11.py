import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.carrier_set_separation_v11 import qualify_carrier_pair, qualify_carrier_set


def _frame():
    rng = np.random.default_rng(7)
    rows = []
    blocks = []
    for block in range(4):
        q = rng.normal(size=80)
        p = (1.7 * q + rng.normal(scale=0.08, size=80)) if block < 3 else rng.normal(size=80)
        noise = rng.normal(size=80)
        rows.extend({"p": float(a), "q": float(b), "noise": float(c)} for a, b, c in zip(p, q, noise))
        blocks.extend([block] * 80)
    return pd.DataFrame(rows), np.asarray(blocks)


def test_v11_contract_is_consumed_and_outcome_blind():
    cfg = json.loads(Path("configs/carrier_set_separation_v11_development.json").read_text())
    assert cfg["purpose"] == "carrier_set_separation_v11_development_only"
    assert cfg["development_only"] is True
    assert cfg["eligible_for_prospective_performance_claim"] is False
    assert cfg["consumed_seed_denominator"] == list(range(15001, 15011))
    assert cfg["carrier_selection_uses_background_only"] is True
    assert cfg["competitor_outcome_status_used_for_carrier_selection"] is False
    assert cfg["carrier_minimum_complete_blocks"] == 3
    assert cfg["carrier_median_heldout_r2_min_exclusive"] == 0.0
    assert cfg["material_r2_drop"] == 0.10
    assert cfg["pairwise_rank_margin"] == 0.02
    assert cfg["pairwise_density_margin"] == 0.01
    assert cfg["fresh_known_truth_validation_authorized"] is False
    assert cfg["fresh_empirical_validation_authorized"] is False


def test_reproducible_background_relation_qualifies_carrier_and_keeps_separator():
    frame, blocks = _frame()
    row, audit = qualify_carrier_pair(
        frame,
        blocks,
        target_process="P",
        carrier_process="Q",
        target_predictors=("p",),
        carrier_predictors=("q",),
        degree=1,
        minimum_complete_rows_per_block=20,
    )
    assert audit is not None
    assert row["structurally_disjoint"] is True
    assert row["n_complete_blocks"] == 4
    assert row["median_heldout_r2"] > 0
    assert row["eligible_carrier"] is True
    assert row["separating_blocks"] == "3"


def test_unrelated_background_process_does_not_qualify_as_carrier():
    frame, blocks = _frame()
    row, _ = qualify_carrier_pair(
        frame,
        blocks,
        target_process="P",
        carrier_process="N",
        target_predictors=("p",),
        carrier_predictors=("noise",),
        degree=1,
        minimum_complete_rows_per_block=20,
    )
    assert row["eligible_carrier"] is False


def test_structural_overlap_fails_closed_without_carrier():
    frame, blocks = _frame()
    row, audit = qualify_carrier_pair(
        frame,
        blocks,
        target_process="P",
        carrier_process="Q",
        target_predictors=("p",),
        carrier_predictors=("p",),
        minimum_complete_rows_per_block=20,
    )
    assert audit is None
    assert row["structurally_disjoint"] is False
    assert row["eligible_carrier"] is False


def test_carrier_set_does_not_require_outcome_status_input():
    frame, blocks = _frame()
    carriers, audits = qualify_carrier_set(
        frame,
        blocks,
        target_process="P",
        process_universe=("P", "Q", "N"),
        closures={"P": ("p",), "Q": ("q",), "N": ("noise",)},
        degree=1,
        minimum_complete_rows_per_block=20,
    )
    eligible = set(carriers.loc[carriers["eligible_carrier"].astype(bool), "carrier_process"])
    assert eligible == {"Q"}
    assert set(audits) == {"Q", "N"}
