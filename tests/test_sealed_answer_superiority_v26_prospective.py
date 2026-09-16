import json

import pandas as pd
import pytest

from sdmr.sealed_answer_superiority_v26_prospective import (
    assemble_truth_blind_v21_contexts,
    build_truth_blind_v23_sets,
    freeze_truth_blind_context_stage,
    load_contract,
    validate_context_set_provenance,
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
    frame["generating_process_true"] = [False, False, True]
    sets = build_truth_blind_v23_sets(frame)
    assert len(sets) == 1
    row = sets.iloc[0]
    assert row.supported_set == "temperature+water"
    assert row.high_confidence_subset == "temperature"
    assert int(row.supported_set_size) == 2
    assert "generating_process_true" not in sets.columns


def test_context_set_provenance_rejects_tampered_sets():
    decisions = assemble_truth_blind_v21_contexts(_geometry(), _activity())
    sets = build_truth_blind_v23_sets(decisions)
    validate_context_set_provenance(decisions, sets)

    tampered = sets.copy()
    tampered.loc[0, "supported_set"] = "temperature"
    tampered.loc[0, "supported_set_size"] = 1
    with pytest.raises(ValueError, match="build_context_sets"):
        validate_context_set_provenance(decisions, tampered)


def test_preterminal_context_receipt_contains_no_truth_and_pins_constructor(tmp_path):
    receipt = freeze_truth_blind_context_stage(_geometry(), _activity(), tmp_path)
    assert receipt["truth_opened"] is False
    assert receipt["context_set_constructor"] == "set_valued_attribution_v23.build_context_sets"
    assert receipt["n_contexts"] == 1
    assert receipt["n_context_decision_rows"] == 3
    assert len(receipt["context_decisions_sha256"]) == 64
    assert len(receipt["context_sets_sha256"]) == 64

    decisions = pd.read_csv(tmp_path / "context_decisions.csv")
    sets = pd.read_csv(tmp_path / "context_sets.csv")
    assert "generating_process_true" not in decisions.columns
    assert "generating_process_true" not in sets.columns
    saved = json.loads((tmp_path / "preterminal_context_receipt.json").read_text())
    assert saved == receipt
