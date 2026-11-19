"""Synthetic method-only test for physical site and sample-effort ledger."""
from copy import deepcopy

import pytest

from sdmr.forest_sampling_opportunity_v1 import evaluate_survey_frame


def _frame(n_blocks=8, sites_per=3, trap_replicates=1):
    rows = []
    for block in range(n_blocks):
        for site in range(sites_per):
            for trap in range(trap_replicates):
                rows.append({
                    "record_id": f"src-{block}-{site}-{trap}",
                    "physical_site_id": f"physical-{block}-{site}",
                    "source_unit_id": f"trap-{block}-{site}-{trap}",
                    "block_id": f"block-{block}",
                    "occasion_id": "year-2023",
                    "survey_date": "2023-06-21",
                    "method_id": "pitfall_original",
                    "survey_status": "surveyed",
                    "effort": 7.0,
                })
    return {
        "schema": "sdmr.forest_sampling_opportunity.v1",
        "metadata_only": True,
        "source_file_sha256": "b" * 64,
        "unit_kind": "trap",
        "expected_block_ids": [f"block-{b}" for b in range(n_blocks)],
        "rows": rows,
    }


def test_eight_independent_blocks_three_physical_sites_apiece():
    a = evaluate_survey_frame(_frame())
    assert a.status == "survey_opportunity_ready_for_separate_observation_audit"
    assert a.n_holdout_blocks == 8
    assert a.n_surveyed_blocks == 8
    assert a.min_eligible_sites_per_block == 3
    assert a.n_physical_sites == 24
    assert a.n_event_records == 24
    assert not a.true_zero_catch_inferred
    assert not a.observation_selection_resolved
    assert not a.response_opening_authorized


def test_more_traps_do_not_increase_physical_sites_or_blocks():
    a = evaluate_survey_frame(_frame(trap_replicates=8))
    assert a.n_event_records == 192
    assert a.n_physical_sites == 24
    assert a.n_holdout_blocks == 8
    assert a.min_eligible_sites_per_block == 3


def test_eight_blocks_with_one_site_each_not_eight_independent_forests():
    a = evaluate_survey_frame(_frame(sites_per=1, trap_replicates=10))
    assert a.n_event_records == 80
    assert a.n_physical_sites == 8
    assert a.min_eligible_sites_per_block == 1
    assert a.status == "not_estimable_insufficient_independent_sites"


def test_wholly_unsurveyed_block_is_not_silently_removed():
    x = _frame()
    for row in x["rows"]:
        if row["block_id"] == "block-7":
            row["survey_status"] = "not_surveyed"
            row["effort"] = 0.0
    a = evaluate_survey_frame(x)
    assert a.n_holdout_blocks == 8
    assert a.n_surveyed_blocks == 7
    assert a.n_not_surveyed == 3
    assert a.status == "not_estimable_wholly_unsurveyed_source_block"


def test_missing_declared_source_block_is_schema_failure():
    x = _frame()
    x["rows"] = [r for r in x["rows"] if r["block_id"] != "block-7"]
    with pytest.raises(ValueError, match="every declared block"):
        evaluate_survey_frame(x)


def test_unknown_opportunity_is_not_certified_zero_or_surveyed():
    x = _frame()
    x["rows"][0]["survey_status"] = "unknown"
    x["rows"][0]["effort"] = None
    a = evaluate_survey_frame(x)
    assert a.n_unknown == 1
    assert a.n_surveyed_events == 23
    assert not a.true_zero_catch_inferred
    bad = deepcopy(x)
    bad["rows"][0]["effort"] = 0.0
    with pytest.raises(ValueError, match="unknown effort"):
        evaluate_survey_frame(bad)


def test_no_fabricated_sampled_zero_or_nonpositive_surveyed_effort():
    x = _frame()
    x["rows"][0]["survey_status"] = "sampled_zero"
    with pytest.raises(ValueError, match="survey status not declared"):
        evaluate_survey_frame(x)
    x["rows"][0]["survey_status"] = "surveyed"
    x["rows"][0]["effort"] = 0.0
    with pytest.raises(ValueError, match="positive effort"):
        evaluate_survey_frame(x)


def test_duplicate_sample_ids_and_cross_block_physical_sites_refused():
    x = _frame()
    x["rows"][0]["record_id"] = x["rows"][1]["record_id"]
    with pytest.raises(ValueError, match="duplicate original survey record"):
        evaluate_survey_frame(x)
    x = _frame()
    x["rows"][0]["physical_site_id"] = x["rows"][-1]["physical_site_id"]
    with pytest.raises(ValueError, match="multiple holdout blocks"):
        evaluate_survey_frame(x)


def test_response_leakage_schema_rejected():
    x = _frame()
    x["rows"][0]["beetle_count"] = 999
    with pytest.raises(ValueError, match="no biological response columns"):
        evaluate_survey_frame(x)
    x = _frame()
    x["response_array"] = [0, 1]
    with pytest.raises(ValueError, match="response values forbidden"):
        evaluate_survey_frame(x)


def test_identity_receipt_deterministic_independent_of_sample_row_order():
    x = _frame()
    before = evaluate_survey_frame(x)
    x["rows"].reverse()
    after = evaluate_survey_frame(x)
    assert before.identity_sha256 == after.identity_sha256
    assert before.sampling_event_sha256 == after.sampling_event_sha256


def test_invalid_dates_and_minimum_blocks_refused():
    x = _frame()
    x["rows"][0]["survey_date"] = "2023-02-31"
    with pytest.raises(ValueError, match="ISO-8601"):
        evaluate_survey_frame(x)
    x = _frame()
    a = evaluate_survey_frame(x, minimum_blocks=9)
    assert a.status == "not_estimable_insufficient_source_blocks"
