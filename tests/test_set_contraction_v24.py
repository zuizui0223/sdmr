import pandas as pd
import pandas.testing as pdt
import pytest

from sdmr.set_contraction_v24 import contract_supported_sets


def _sets():
    return pd.DataFrame([
        {
            "family": "interaction",
            "seed": 17001,
            "target_block": 0,
            "supported_set": "temperature+water+seasonality",
            "supported_set_size": 3,
        },
        {
            "family": "gaussian",
            "seed": 17002,
            "target_block": 1,
            "supported_set": "temperature",
            "supported_set_size": 1,
        },
        {
            "family": "gaussian",
            "seed": 17003,
            "target_block": 2,
            "supported_set": "",
            "supported_set_size": 0,
        },
    ])


def _evidence():
    return pd.DataFrame([
        {
            "family": "interaction",
            "seed": 17001,
            "target_block": 0,
            "target_process": "temperature",
            "action": "retain",
            "evidence_source_id": "independent_temporal_contrast_v1",
            "evidence_is_new": True,
            "evidence_is_separating": True,
        },
        {
            "family": "interaction",
            "seed": 17001,
            "target_block": 0,
            "target_process": "water",
            "action": "retain",
            "evidence_source_id": "independent_temporal_contrast_v1",
            "evidence_is_new": True,
            "evidence_is_separating": True,
        },
        {
            "family": "interaction",
            "seed": 17001,
            "target_block": 0,
            "target_process": "seasonality",
            "action": "remove",
            "evidence_source_id": "independent_temporal_contrast_v1",
            "evidence_is_new": True,
            "evidence_is_separating": True,
        },
    ])


def test_independent_separating_evidence_can_contract_a_multi_member_set():
    got = contract_supported_sets(_sets(), _evidence())
    row = got.loc[got.target_block.eq(0)].iloc[0]
    assert row.set_before == "temperature+water+seasonality"
    assert row.contracted_set == "temperature+water"
    assert row.removed_members == "seasonality"
    assert row.set_size_before == 3
    assert row.set_size_after == 2
    assert row.contraction_state == "contracted"
    assert row.evidence_source_id == "independent_temporal_contrast_v1"


def test_empty_and_singleton_sets_are_never_sharpened():
    got = contract_supported_sets(_sets(), _evidence())
    singleton = got.loc[got.target_block.eq(1)].iloc[0]
    empty = got.loc[got.target_block.eq(2)].iloc[0]
    assert singleton.contracted_set == "temperature"
    assert singleton.contraction_state == "unchanged_singleton"
    assert empty.contracted_set == ""
    assert empty.contraction_state == "unchanged_empty"


def test_abstain_explicitly_preserves_a_member():
    evidence = _evidence()
    evidence.loc[evidence.target_process.eq("seasonality"), "action"] = "abstain"
    got = contract_supported_sets(_sets(), evidence)
    row = got.loc[got.target_block.eq(0)].iloc[0]
    assert row.contracted_set == "temperature+water+seasonality"
    assert row.removed_members == ""
    assert row.contraction_state == "abstained"


def test_all_remove_proposal_fails_closed_and_preserves_original_set():
    evidence = _evidence()
    evidence["action"] = "remove"
    got = contract_supported_sets(_sets(), evidence)
    row = got.loc[got.target_block.eq(0)].iloc[0]
    assert row.contracted_set == "temperature+water+seasonality"
    assert row.removed_members == ""
    assert row.contraction_state == "fail_closed_all_remove"


def test_reused_or_nonseparating_evidence_is_rejected():
    reused = _evidence()
    reused["evidence_source_id"] = "v21_supported"
    with pytest.raises(ValueError, match="forbidden evidence source"):
        contract_supported_sets(_sets(), reused)

    not_new = _evidence()
    not_new["evidence_is_new"] = False
    with pytest.raises(ValueError, match="genuinely new"):
        contract_supported_sets(_sets(), not_new)

    not_separating = _evidence()
    not_separating["evidence_is_separating"] = False
    with pytest.raises(ValueError, match="separating"):
        contract_supported_sets(_sets(), not_separating)


def test_evidence_cannot_action_a_process_outside_v23_supported_set():
    evidence = pd.concat([
        _evidence(),
        pd.DataFrame([{
            "family": "interaction",
            "seed": 17001,
            "target_block": 0,
            "target_process": "noise",
            "action": "retain",
            "evidence_source_id": "independent_temporal_contrast_v1",
            "evidence_is_new": True,
            "evidence_is_separating": True,
        }]),
    ], ignore_index=True)
    with pytest.raises(ValueError, match="outside v23 supported set"):
        contract_supported_sets(_sets(), evidence)


def test_multi_member_context_requires_one_explicit_action_per_supported_member():
    incomplete = _evidence().loc[lambda x: ~x.target_process.eq("seasonality")].copy()
    with pytest.raises(ValueError, match="exactly one action"):
        contract_supported_sets(_sets(), incomplete)

    duplicate = pd.concat([_evidence(), _evidence().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="exactly one action"):
        contract_supported_sets(_sets(), duplicate)


def test_unknown_action_is_rejected():
    evidence = _evidence()
    evidence.loc[evidence.target_process.eq("seasonality"), "action"] = "winner"
    with pytest.raises(ValueError, match="action"):
        contract_supported_sets(_sets(), evidence)


def test_truth_like_columns_cannot_change_contraction():
    sets = _sets()
    evidence = _evidence()
    baseline = contract_supported_sets(sets, evidence)

    sets_with_truth = sets.copy()
    sets_with_truth["generating_process_true"] = [False, True, False]
    evidence_with_truth = evidence.copy()
    evidence_with_truth["generating_process_true"] = [False, False, True]
    altered = contract_supported_sets(sets_with_truth, evidence_with_truth)
    pdt.assert_frame_equal(baseline, altered)


def test_declared_supported_set_size_must_match_members():
    sets = _sets()
    sets.loc[sets.target_block.eq(0), "supported_set_size"] = 2
    with pytest.raises(ValueError, match="supported_set_size"):
        contract_supported_sets(sets, _evidence())
