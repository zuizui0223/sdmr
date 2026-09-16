import pandas as pd

from sdmr.separating_evidence_refinement_v24 import (
    refine_context_sets,
    score_known_truth_refinement,
)


def _base() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "family": "gaussian",
            "seed": 17001,
            "target_block": 0,
            "supported_set": "temperature+water+seasonality",
            "supported_set_size": 3,
        }
    ])


def _evidence() -> pd.DataFrame:
    rows = []
    for process in ("temperature", "water", "seasonality"):
        for separator_id in ("sep_a", "sep_b"):
            rows.append({
                "family": "gaussian",
                "seed": 17001,
                "target_block": 0,
                "target_process": process,
                "separator_id": separator_id,
                "evidence_state": "exclude" if process == "seasonality" else "compatible",
                "qualified": True,
                "source_disjoint_from_v21_support_inputs": True,
                "decision_rule_frozen_before_separator_outcomes": True,
            })
    return pd.DataFrame(rows)


def _truth(native: bool) -> pd.DataFrame:
    rows = []
    for process in ("temperature", "water", "seasonality", "noise"):
        value = process in {"temperature", "water"}
        rows.append({
            "family": "gaussian",
            "seed": 17001,
            "target_block": 0,
            "target_process": process,
            "generating_process_true": value if native else ("True" if value else "False"),
        })
    return pd.DataFrame(rows)


def test_known_truth_string_booleans_score_identically_to_native_booleans():
    refined, _ = refine_context_sets(
        _base(),
        _evidence(),
        required_separator_ids=("sep_a", "sep_b"),
    )
    native_score = score_known_truth_refinement(refined, _truth(native=True))
    string_score = score_known_truth_refinement(refined, _truth(native=False))
    assert string_score == native_score
    assert string_score["n_removed_true_members"] == 0
    assert string_score["n_removed_false_members"] == 1
