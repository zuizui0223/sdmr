import pandas as pd
import pytest

from sdmr.set_valued_attribution_v23 import build_context_sets, score_known_truth_sets


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


def test_truth_scoring_is_separate_from_set_construction():
    frame = _frame(); sets = build_context_sets(frame)
    scored = score_known_truth_sets(sets, frame)
    assert scored["all_true_processes_covered_rate"] == 1.0
    assert scored["n_singleton_contexts"] == 1
    assert scored["singleton_precision"] == 1.0
    assert scored["false_member_fraction"] == pytest.approx(1/3)


def test_high_confidence_must_be_subset_of_supported():
    frame = _frame()
    frame.loc[frame.target_process.eq("water") & frame.target_block.eq(0), "high_confidence_supported"] = True
    with pytest.raises(ValueError, match="contained"):
        build_context_sets(frame)
