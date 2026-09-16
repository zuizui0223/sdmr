import pandas as pd

from sdmr.sealed_answer_superiority_v26_prospective import (
    assemble_truth_blind_v21_contexts,
    build_truth_blind_v23_sets,
    load_contract,
)


def _geometry():
    return pd.DataFrame(
        [
            {"family": "gaussian", "seed": 20001, "target_process": "temperature", "target_block": 0, "eligibility_prediction": "eligible"},
            {"family": "gaussian", "seed": 20001, "target_process": "water", "target_block": 0, "eligibility_prediction": "ineligible"},
            {"family": "gaussian", "seed": 20001, "target_process": "noise", "target_block": 0, "eligibility_prediction": "eligible"},
        ]
    )


def _activity():
    return pd.DataFrame(
        [
            {"family": "gaussian", "seed": 20001, "target_process": "temperature", "target_block": 0, "context_status": "context_contributory"},
            {"family": "gaussian", "seed": 20001, "target_process": "water", "target_block": 0, "context_status": "context_contributory"},
            {"family": "gaussian", "seed": 20001, "target_process": "noise", "target_block": 0, "context_status": "context_noncontributory"},
        ]
    )


def test_v26_fresh_contract_freezes_unused_denominator_and_truth_ordering():
    cfg = load_contract()
    assert cfg["fresh_seed_denominator"] == list(range(20001, 20021))
    assert cfg["families"] == [
        "gaussian", "asymmetric", "soft_threshold", "interaction", "omitted_driver", "observation_confounded"
    ]
    assert cfg["process_universe"] == ["temperature", "water", "seasonality", "noise"]
    assert cfg["separator"]["sem_multiplier"] == 1.96
    assert cfg["separator"]["superiority_boundary"] == 0.0
    assert cfg["governance"]["truth_open_after_refinement_receipt_only"] is True
    assert cfg["governance"]["post_outcome_rule_changes_allowed"] is False


def test_truth_blind_v21_assembly_reproduces_frozen_support_rules_without_truth_column():
    frame = assemble_truth_blind_v21_contexts(_geometry(), _activity())
    assert "generating_process_true" not in frame.columns
    keyed = frame.set_index("target_process")
    assert bool(keyed.loc["temperature", "supported"]) is True
    assert bool(keyed.loc["temperature", "high_confidence_supported"]) is True
    assert bool(keyed.loc["water", "supported"]) is True
    assert bool(keyed.loc["water", "high_confidence_supported"]) is False
    assert bool(keyed.loc["noise", "supported"]) is False


def test_truth_blind_v23_sets_preserve_all_supported_members_and_ignore_extra_truth_like_columns():
    frame = assemble_truth_blind_v21_contexts(_geometry(), _activity())
    # A truth-like extra column must not be read by set construction.
    frame["generating_process_true"] = [False, False, True]
    sets = build_truth_blind_v23_sets(frame)
    assert len(sets) == 1
    row = sets.iloc[0]
    assert row.supported_set == "temperature+water"
    assert row.high_confidence_subset == "temperature"
    assert int(row.supported_set_size) == 2
    assert "generating_process_true" not in sets.columns
