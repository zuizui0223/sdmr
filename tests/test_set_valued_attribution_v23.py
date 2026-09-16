import pandas as pd
import pandas.testing as pdt
import pytest

from sdmr.set_valued_attribution_v23 import (
    build_context_sets,
    score_known_truth_sets,
    summarize_set_geometry,
)


def _frame():
    return pd.DataFrame([
        {"family":"gaussian","seed":17001,"target_block":0,"target_process":"temperature","supported":True,"high_confidence_supported":True,"generating_process_true":True},
        {"family":"gaussian","seed":17001,"target_block":0,"target_process":"water","supported":False,"high_confidence_supported":False,"generating_process_true":False},
        {"family":"gaussian","seed":17001,"target_block":0,"target_process":"seasonality","supported":True,"high_confidence_supported":False,"generating_process_true":False},
        {"family":"gaussian","seed":17001,"target_block":0,"target_process":"noise","supported":False,"high_confidence_supported":False,"generating_process_true":False},
        {"family":"gaussian","seed":17001,"target_block":1,"target_process":"temperature","supported":True,"high_confidence_supported":True,"generating_process_true":True},
        {"family":"gaussian","seed":17001,"target_block":1,"target_process":"water","supported":False,"high_confidence_supported":False,"generating_process_true":False},
        {"family":"gaussian","seed":17001,"target_block":1,"target_process":"seasonality","supported":False,"high_confidence_supported":False,"generating_process_true":False},
        {"family":"gaussian","seed":17001,"target_block":1,"target_process":"noise","supported":False,"high_confidence_supported":False,"generating_process_true":False},
        {"family":"gaussian","seed":17001,"target_block":2,"target_process":"temperature","supported":False,"high_confidence_supported":False,"generating_process_true":False},
        {"family":"gaussian","seed":17001,"target_block":2,"target_process":"water","supported":False,"high_confidence_supported":False,"generating_process_true":False},
        {"family":"gaussian","seed":17001,"target_block":2,"target_process":"seasonality","supported":False,"high_confidence_supported":False,"generating_process_true":False},
        {"family":"gaussian","seed":17001,"target_block":2,"target_process":"noise","supported":False,"high_confidence_supported":False,"generating_process_true":False},
    ])


def test_sets_preserve_all_supported_members_without_truth_based_deletion():
    got = build_context_sets(_frame())
    first = got.loc[got.target_block.eq(0)].iloc[0]
    assert first.supported_set == "temperature+seasonality"
    assert first.high_confidence_subset == "temperature"
    assert first.attribution_state == "partial_identification_set"
    second = got.loc[got.target_block.eq(1)].iloc[0]
    assert second.supported_set == "temperature"
    assert second.attribution_state == "singleton"
    third = got.loc[got.target_block.eq(2)].iloc[0]
    assert third.supported_set == ""
    assert third.attribution_state == "empty"


def test_set_construction_is_identical_after_truth_columns_are_removed():
    frame = _frame()
    with_truth = build_context_sets(frame)
    support_only = build_context_sets(frame.drop(columns=["generating_process_true"]))
    pdt.assert_frame_equal(with_truth, support_only)


def test_truth_free_geometry_quantifies_partial_identification():
    sets = build_context_sets(_frame())
    summary = summarize_set_geometry(sets)
    assert summary["truth_labels_used"] is False
    assert summary["n_contexts"] == 3
    assert summary["n_empty_contexts"] == 1
    assert summary["n_positive_contexts"] == 2
    assert summary["n_singleton_contexts"] == 1
    assert summary["n_partial_identification_contexts"] == 1
    assert summary["singleton_rate_among_positive"] == 0.5
    assert summary["partial_identification_rate_among_positive"] == 0.5
    assert summary["mean_supported_set_size_among_positive"] == 1.5
    assert summary["median_supported_set_size_among_positive"] == 1.5
    assert summary["maximum_supported_set_size"] == 2
    assert summary["supported_set_size_distribution"] == {"0": 1, "1": 1, "2": 1}
    assert summary["n_contexts_with_high_confidence_member"] == 2


def test_truth_scoring_is_separate_from_set_construction():
    frame = _frame()
    sets = build_context_sets(frame)
    scored = score_known_truth_sets(sets, frame)
    assert scored["all_true_processes_covered_rate"] == pytest.approx(2 / 3)
    assert scored["n_singleton_contexts"] == 1
    assert scored["singleton_precision"] == 1.0
    assert scored["false_member_fraction"] == pytest.approx(1 / 3)


def test_string_false_is_not_coerced_to_true():
    frame = _frame().drop(columns=["generating_process_true"])
    frame["supported"] = frame["supported"].map({True: "True", False: "False"})
    frame["high_confidence_supported"] = frame["high_confidence_supported"].map(
        {True: "True", False: "False"}
    )
    got = build_context_sets(frame)
    assert got.loc[got.target_block.eq(2), "supported_set_size"].iloc[0] == 0


def test_high_confidence_must_be_subset_of_supported():
    frame = _frame()
    frame.loc[
        frame.target_process.eq("water") & frame.target_block.eq(0),
        "high_confidence_supported",
    ] = True
    with pytest.raises(ValueError, match="contained"):
        build_context_sets(frame)


def test_geometry_rejects_inconsistent_state_labels():
    sets = build_context_sets(_frame())
    sets.loc[sets.target_block.eq(0), "attribution_state"] = "singleton"
    with pytest.raises(ValueError, match="inconsistent"):
        summarize_set_geometry(sets)
