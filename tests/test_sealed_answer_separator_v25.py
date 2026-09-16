import pandas as pd
import pytest

from sdmr.sealed_answer_separator_v25 import classify_sealed_answer_separator


KEY = {
    "family": "gaussian",
    "seed": 17001,
    "target_block": 2,
    "target_process": "seasonality",
}


def _rows(deltas_by_model, *, n_answer=6):
    rows = []
    for model_label, deltas in deltas_by_model.items():
        for fold, delta in enumerate(deltas):
            baseline = -0.60
            rows.append(
                {
                    **KEY,
                    "model_label": model_label,
                    "fold": fold,
                    "baseline_complete": True,
                    "excluded_complete": True,
                    "baseline_density_log_score": baseline,
                    "excluded_density_log_score": baseline + float(delta),
                    "n_answer_occurrences": int(n_answer),
                    "n_separator_background": 40,
                    "sealed_answer_source_disjoint": True,
                    "prediction_frozen_before_answer_open": True,
                }
            )
    return pd.DataFrame(rows)


def _state(frame):
    out = classify_sealed_answer_separator(
        frame,
        required_model_labels=("m1", "m2"),
        margin=0.01,
        sem_multiplier=1.0,
        minimum_complete_occurrences=10,
        minimum_sealed_blocks=2,
    )
    assert len(out) == 1
    return out.iloc[0]


def test_unanimous_noninferiority_emits_exclude():
    row = _state(_rows({"m1": [-0.003, -0.001], "m2": [0.002, -0.002]}))
    assert row.evidence_state == "exclude"
    assert row.n_complete_models == 2
    assert row.n_sealed_blocks == 2
    assert row.n_answer_occurrences == 12


def test_clear_exclusion_harm_emits_compatible():
    row = _state(_rows({"m1": [-0.050, -0.048], "m2": [-0.002, 0.001]}))
    assert row.evidence_state == "compatible"
    assert row.n_clearly_inferior_models == 1


def test_interval_overlap_emits_indeterminate():
    # mean=-0.01 and nonzero SEM: interval overlaps the inherited -0.01 margin.
    row = _state(_rows({"m1": [-0.020, 0.000], "m2": [-0.002, 0.001]}))
    assert row.evidence_state == "indeterminate"


def test_missing_required_model_or_coverage_emits_unavailable():
    missing_model = _rows({"m1": [-0.002, -0.001]})
    assert _state(missing_model).evidence_state == "unavailable"

    low_coverage = _rows({"m1": [-0.002, -0.001], "m2": [-0.002, -0.001]}, n_answer=4)
    assert _state(low_coverage).evidence_state == "unavailable"


def test_incomplete_route_emits_unavailable():
    frame = _rows({"m1": [-0.002, -0.001], "m2": [-0.002, -0.001]})
    frame.loc[(frame.model_label == "m2") & (frame.fold == 1), "excluded_complete"] = False
    assert _state(frame).evidence_state == "unavailable"


def test_reused_or_unfrozen_evidence_fails_closed():
    reused = _rows({"m1": [-0.002, -0.001], "m2": [-0.002, -0.001]})
    reused.loc[0, "sealed_answer_source_disjoint"] = False
    with pytest.raises(ValueError, match="source-disjoint"):
        _state(reused)

    unfrozen = _rows({"m1": [-0.002, -0.001], "m2": [-0.002, -0.001]})
    unfrozen.loc[0, "prediction_frozen_before_answer_open"] = False
    with pytest.raises(ValueError, match="frozen"):
        _state(unfrozen)


def test_duplicate_context_model_fold_keys_fail_closed():
    frame = _rows({"m1": [-0.002, -0.001], "m2": [-0.002, -0.001]})
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        _state(frame)
