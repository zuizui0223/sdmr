"""Contract and regression checks against SHA-verified GitHub Actions source snapshot."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "geographic_turnover_postsource_audit_v1_tests",
    ROOT / "experiments" / "geographic_turnover_postsource_audit_v1.py",
)
if _spec is None or _spec.loader is None:
    raise ImportError("Missing postsource audit module")
post = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(post)
SOURCE = ROOT / "evidence" / "geographic_turnover_native_source_v1"


def _source():
    rows = pd.read_csv(SOURCE / "available_climate_cells.csv")
    receipt = json.loads((SOURCE / "source_receipt.json").read_text())
    config = json.loads((ROOT / "configs/geographic_turnover_native_windows_v1.json").read_text())
    return rows, receipt, config


def test_released_source_provenance_matches_first_20261019_action():
    assert hashlib.sha256((SOURCE / "available_climate_cells.csv").read_bytes()).hexdigest() == (
        "42747f07c030a09134a08703bf20e60a73fe661468c2047ccc1c1fd7628b85aa"
    )
    assert hashlib.sha256((SOURCE / "source_receipt.json").read_bytes()).hexdigest() == (
        "c0619957ff3e30d65810cec716067891973e6d991fb68ca6cf4b7b7bce82a8e5"
    )


def test_preserve_four_windows_and_finnish_source_failure():
    a, rec, conf = _source()
    selected, s = post.source_checks(a, rec, conf, "Quercus robur")
    assert len(s) == 4
    assert len(selected) == 54
    assert selected.groupby("region").n_occ.sum().to_dict() == {
        "quercus_DE_central": 264, "quercus_SE_south": 3310,
    }
    assert s["pinus_FI_central"]["focal_source_status"] == "bulk_required_count_over_diagnostic_cap"


def test_source_cell_missing_fails_before_fitting():
    a, rec, conf = _source()
    with pytest.raises(ValueError, match="Climate cell count"):
        post.source_checks(a.iloc[1:], rec, conf, "Quercus robur")


def test_effort_is_never_imputed():
    a, rec, conf = _source()
    a.loc[a.region == "quercus_DE_central", "n_independent_target_group_records_diagnostic"] = 0
    with pytest.raises(ValueError, match="Zero sentinel count"):
        post.source_checks(a, rec, conf, "Quercus robur")


def test_input_row_permutation_does_not_change_audit():
    a, rec, conf = _source()
    aa = post.audit(a, rec, conf)
    bb = post.audit(a.sample(frac=1, random_state=2026), rec, conf)
    assert aa == bb


def test_observed_source_rank_reversal_is_effort_assumption_dependent():
    a, rec, conf = _source()
    outcome = post.audit(a, rec, conf)
    powers = outcome["effort_power_sensitivity"]
    assert [powers[k]["apparent_rank_reversal_ignoring_adequacy"] for k in ("0.0", "0.5", "1.0")] == [False, True, False]
    for k, expected_winners in {
        "0.0": ("moisture", "moisture"),
        "0.5": ("moisture", "temperature"),
        "1.0": ("temperature", "temperature"),
    }.items():
        ranks = tuple(z["rank_only_ignoring_adequacy"] for z in powers[k]["by_region"].values())
        assert ranks == expected_winners
    assert all(z["full_minus_effort_only"] < 0 for z in powers["1.0"]["by_region"].values())
    assert all(z["ecological_process_claim_allowed"] is False
               for p in powers.values() for z in p["by_region"].values())
    assert outcome["publication_claim_allowed"] is False


def test_occupied_climate_cells_nearly_saturated():
    a, rec, conf = _source()
    result = post.audit(a, rec, conf)
    regions = result["region_sources"]
    assert (regions["quercus_DE_central"]["n_recorded_cells"],
            regions["quercus_SE_south"]["n_recorded_cells"]) == (28, 24)
    assert regions["quercus_SE_south"]["fraction_cells_with_any_record"] == 1.0
    assert result["pairwise_environment_overlap_coarse"]["quercus_DE_central :: quercus_SE_south"] == pytest.approx(0.1)


def test_spatial_orientation_and_ridge_sensitivity_block_promotion():
    a, rec, conf = _source()
    outcome = post.audit(a, rec, conf)
    # Fixed-sentinel north/south: full cannot outperform effort-only under
    # any inspected postsource ridge in Germany; changing ridge is not rescue.
    assert all(v["quercus_DE_central"]["full_minus_effort_only"] < 0
               for v in outcome["postsource_ridge_sensitivity_raw_sentinel"].values())
    # East-west holdout makes Sweden slightly adequate under the same exact
    # data and raw sentinel offset. Therefore a universal inadequacy claim is
    # also disallowed, even though no biological-process claim is authorized.
    spatial = outcome["postsource_spatial_orientation_sensitivity"]
    assert spatial["north_south"]["1.0"]["quercus_SE_south"]["full_minus_effort_only"] < 0
    assert spatial["east_west"]["1.0"]["quercus_SE_south"]["full_minus_effort_only"] > 0
    assert outcome["process_turnover_test_authorized"] is False
