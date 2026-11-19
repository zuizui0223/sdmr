"""Synthetic-only first field outcome contract tests: no HF453 source GET."""
from __future__ import annotations

from io import StringIO
from pathlib import Path
import importlib.util
import json
import sys

import pytest

sys.path.insert(0, str(Path("scripts").resolve()))
spec = importlib.util.spec_from_file_location(
    "hf453_first_status_transition_v1",
    Path("scripts/hf453_first_status_transition_v1.py"),
)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def synthetic_csv():
    # The only four accessed original-style columns are fixed here.
    # Include irrelevant notes to confirm they don't influence the contrast.
    rows = ["StemTag,year,status,CP,Notes"]
    status = {
        "A": ("A", "DC", "DC", "DC"),
        "B": ("AU", "DN", "DN", "DN"),
        "C": ("A", "A", "AU", "AU"),
        "D": ("A", "DS", "DS", "DS"),
        "E": ("A", "NA", "NA", "NA"),
        "F": ("DC", "DC", "DC", "DC"),
    }
    first_cp = {"A":"1", "B":"2", "C":"4", "D":"3", "E":"NA", "F":"5"}
    for tag, states in status.items():
        for i, year in enumerate((2021,2022,2023,2024)):
            rows.append(f"{tag},{year},{states[i]},{first_cp[tag]},not_read_{i}")
    return "\n".join(rows)+"\n"


def test_frozen_source_contract_matches_exact_binary_target():
    config=json.loads(Path("configs/hf453_demographic_transition_first_open_v1.json").read_text())
    mod.validate_contract(config)
    config["primary_interval"]=[2022,2023]
    with pytest.raises(ValueError,match="primary_interval"):
        mod.validate_contract(config)


def test_all_tags_and_statuses_and_censored_dn_remain_separate():
    panel, frame=mod.parse_four_published_fields(
        StringIO(synthetic_csv()),expected_tags=6,expected_per_year=6,
    )
    assert frame["n_source_rows"]==24
    assert frame["per_year_record_counts"]=={
        "2021":6,"2022":6,"2023":6,"2024":6,
    }
    assert frame["status_code_counts_by_year"]["2022"]["DN"]==1
    first=mod.classify_interval(panel,2021,2022)
    assert first["n_start_observed_alive"]==5
    assert first["n_start_not_at_risk_dead"]==1
    assert first["n_end_observed_dead_DC_DS"]==2
    assert first["n_end_observed_alive_A_AU"]==1
    assert first["n_end_unknown_DN_or_missing"]==2
    assert first["canopy_low_light"]=={"p":1,"z":0,"m":1}
    assert first["canopy_greater_light"]=={"p":1,"z":1,"m":0}
    assert first["canopy_not_measured"]=={"p":0,"z":0,"m":1}
    q=first["identified_CP_contrast"]
    assert q["lower"]=="-1/2"
    assert q["upper"]=="0"
    assert q["sign"]=="unresolved_including_zero"
    assert q["causal_process_identified"] is False
    assert q["biological_result_estimated"] is False  # generic method result flag


def test_secondary_events_not_independent_or_survivor_selected_at_end():
    panel,_=mod.parse_four_published_fields(
        StringIO(synthetic_csv()),expected_tags=6,expected_per_year=6,
    )
    secondary=mod.classify_interval(panel,2022,2023)
    assert secondary["n_start_observed_alive"]==1
    assert secondary["n_end_observed_alive_A_AU"]==1
    assert secondary["n_start_not_at_risk_dead"]==3
    assert secondary["n_start_not_at_risk_DN_or_missing"]==2
    assert secondary["independent_forest_replication"] is False


def test_unregistered_status_canopy_duplicated_tag_and_incomplete_panel_refused():
    data=synthetic_csv()
    for wrong, expected in (
        (data.replace(",DC,1",",D,1"),"unregistered_original_status_code"),
        (data.replace(",AU,2",",AU,7"),"unregistered_original_canopy_code"),
        (data+"A,2021,A,1,duplicate\n","duplicate_original_tag_year"),
        (data.replace("F,2024,DC,5,not_read_3\n",""),"source_tag_or_total_frame_changed"),
    ):
        with pytest.raises(ValueError,match=expected):
            mod.parse_four_published_fields(
                StringIO(wrong),expected_tags=6,expected_per_year=6,
            )


def test_cp_unknown_never_silently_sorted_into_preferred_group():
    panel,_=mod.parse_four_published_fields(
        StringIO(synthetic_csv()),expected_tags=6,expected_per_year=6,
    )
    q=mod.classify_interval(panel,2021,2022)
    assert q["n_baseline_CP_unknown"] == 1
    assert q["CP_contrast_population_scope"] == (
        "source_published_tagged_cohort_alive_at_start_and_CP_observed"
    )
    assert q["no_claim_of_unobserved_tree_or_sampling_opportunity_completeness"]


def test_original_source_failure_never_opens_rows(monkeypatch):
    config=json.loads(Path("configs/hf453_demographic_transition_first_open_v1.json").read_text())
    def wrong_sha(_):
        return {"sha256":"0"*64,"md5":mod.PUBLISHER_MD5,
                "n_bytes":mod.EXPECTED_ORIGINAL_NBYTES}
    monkeypatch.setattr(mod,"_download_and_hash_original",wrong_sha)
    monkeypatch.setattr(
        mod,"parse_four_published_fields",
        lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError("must not parse")),
    )
    with pytest.raises(ValueError,match="original_HF453_source_digest"):
        mod.run_first_response_opening(config)


def test_preflight_is_response_free_and_lock_is_exact(monkeypatch,tmp_path):
    monkeypatch.setattr(
        mod,"run_first_response_opening",
        lambda _: (_ for _ in ()).throw(AssertionError("network and outcome forbidden")),
    )
    out=tmp_path/"preflight.json"
    monkeypatch.setattr(sys,"argv",["stage","--preflight-only","--out",str(out)])
    mod.main()
    d=json.loads(out.read_text())
    assert d["result"]["status"]=="preflight_only_no_response_opened"
    assert not d["response_original_HF453"]
    assert not d["causal_effect_estimated"]
    assert not d["Product_B_unblocked"]
    bad=tmp_path/"bad.lock"
    bad.write_text(mod.LOCK_CONTENT.replace("primary=2021_to_2022","primary=2022_to_2023"))
    monkeypatch.setattr(
        sys,"argv",["stage","--execute-lock",str(bad),
                    "--out",str(tmp_path/"bad.json")],
    )
    with pytest.raises(ValueError,match="lock_mismatch"):
        mod.main()
