import json

import pandas as pd
import pytest

from sdmr.set_valued_attribution_v23_development import (
    BLOCKS,
    FAMILIES,
    PROCESSES,
    SEEDS,
    build_from_v21,
    score_after_freeze,
    summarize_context_sets,
    validate_v21_denominator,
)


def _full_v21_like_frame() -> pd.DataFrame:
    rows = []
    for family in FAMILIES:
        for seed in SEEDS:
            for block in BLOCKS:
                for process in PROCESSES:
                    rows.append({
                        "family": family,
                        "seed": seed,
                        "target_block": block,
                        "target_process": process,
                        "supported": process == "temperature",
                        "high_confidence_supported": process == "temperature",
                        "generating_process_true": process in {"temperature", "water"},
                    })
    return pd.DataFrame(rows)


def test_validate_v21_denominator_is_exact_and_truth_blind():
    frame = _full_v21_like_frame()
    blind = validate_v21_denominator(frame)
    assert len(blind) == 1920
    assert "generating_process_true" not in blind.columns
    bad = frame.iloc[:-1].copy()
    with pytest.raises(ValueError, match="1920"):
        validate_v21_denominator(bad)


def test_build_readout_does_not_change_when_truth_column_changes(tmp_path):
    frame = _full_v21_like_frame()
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    frame.to_csv(first, index=False)
    altered = frame.copy()
    altered["generating_process_true"] = ~altered["generating_process_true"]
    altered.to_csv(second, index=False)

    summary_a = build_from_v21(first, tmp_path / "a")
    summary_b = build_from_v21(second, tmp_path / "b")
    assert summary_a == summary_b
    assert summary_a["truth_columns_used"] is False
    assert summary_a["n_contexts"] == 480
    assert summary_a["n_singleton_contexts"] == 480
    assert summary_a["supported_member_counts"]["temperature"] == 480


def test_truth_blind_summary_counts_partial_identification_and_pairs():
    sets = pd.DataFrame([
        {
            "supported_set": "temperature+water+seasonality",
            "high_confidence_subset": "temperature+water",
            "supported_set_size": 3,
            "high_confidence_subset_size": 2,
            "attribution_state": "partial_identification_set",
        },
        {
            "supported_set": "temperature",
            "high_confidence_subset": "temperature",
            "supported_set_size": 1,
            "high_confidence_subset_size": 1,
            "attribution_state": "singleton",
        },
        {
            "supported_set": "",
            "high_confidence_subset": "",
            "supported_set_size": 0,
            "high_confidence_subset_size": 0,
            "attribution_state": "empty",
        },
    ])
    got = summarize_context_sets(sets)
    assert got["n_contexts"] == 3
    assert got["n_multi_member_contexts"] == 1
    assert got["n_singleton_contexts"] == 1
    assert got["n_empty_contexts"] == 1
    assert got["n_co_support_pair_instances"] == 3
    assert got["co_support_pair_counts"]["temperature+water"] == 1
    assert got["co_support_pair_counts"]["water+seasonality"] == 1


def test_known_truth_score_is_separate_and_preserves_member_metrics(tmp_path):
    frame = _full_v21_like_frame()
    decisions = tmp_path / "decisions.csv"
    frame.to_csv(decisions, index=False)
    build_from_v21(decisions, tmp_path / "sets")
    output = tmp_path / "score.json"
    score = score_after_freeze(tmp_path / "sets" / "context_sets.csv", decisions, output)
    assert score["set_construction_used_truth"] is False
    assert score["true_member_recall"] == pytest.approx(0.5)
    assert score["false_member_positive_rate"] == 0.0
    assert score["positive_member_precision"] == 1.0
    assert json.loads(output.read_text())["fresh_empirical_claim"] is False
