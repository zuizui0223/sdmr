import pandas as pd
import pytest

from sdmr.sealed_answer_superiority_v26 import classify_sealed_answer_superiority


KEY = {
    "family": "gaussian",
    "seed": 20001,
    "target_block": -1,
    "target_process": "noise",
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
    out = classify_sealed_answer_superiority(
        frame,
        required_model_labels=("m1", "m2"),
        sem_multiplier=1.96,
        minimum_complete_occurrences=10,
        minimum_sealed_blocks=2,
    )
    assert len(out) == 1
    return out.iloc[0]


def test_all_models_must_have_positive_196_sem_lower_bound():
    row = _state(_rows({"m1": [0.040, 0.060], "m2": [0.050, 0.070]}))
    assert row.evidence_state == "exclude"
    assert row.n_superior_models == 2
    assert row.n_complete_models == 2


def test_one_uncertain_model_prevents_exclusion():
    row = _state(_rows({"m1": [0.040, 0.060], "m2": [-0.010, 0.030]}))
    assert row.evidence_state == "indeterminate"
    assert row.n_superior_models == 1


def test_nonpositive_upper_bound_is_compatible():
    row = _state(_rows({"m1": [-0.040, -0.020], "m2": [0.040, 0.060]}))
    assert row.evidence_state == "compatible"
    assert row.n_nonsuperior_models == 1


def test_zero_lower_bound_is_not_exclusion():
    # Identical positive deltas produce SEM=0.  A zero lower bound must remain
    # indeterminate because v26 freezes a strict > 0 superiority requirement.
    row = _state(_rows({"m1": [0.000, 0.000], "m2": [0.050, 0.050]}))
    assert row.evidence_state == "indeterminate"


def test_missing_required_model_or_coverage_is_unavailable():
    assert _state(_rows({"m1": [0.050, 0.060]})).evidence_state == "unavailable"
    assert _state(
        _rows({"m1": [0.050, 0.060], "m2": [0.050, 0.060]}, n_answer=4)
    ).evidence_state == "unavailable"


def test_incomplete_route_is_unavailable():
    frame = _rows({"m1": [0.050, 0.060], "m2": [0.050, 0.060]})
    frame.loc[(frame.model_label == "m2") & (frame.fold == 1), "excluded_complete"] = False
    assert _state(frame).evidence_state == "unavailable"


def test_reused_or_unfrozen_evidence_fails_closed():
    reused = _rows({"m1": [0.050, 0.060], "m2": [0.050, 0.060]})
    reused.loc[0, "sealed_answer_source_disjoint"] = False
    with pytest.raises(ValueError, match="source-disjoint"):
        _state(reused)

    unfrozen = _rows({"m1": [0.050, 0.060], "m2": [0.050, 0.060]})
    unfrozen.loc[0, "prediction_frozen_before_answer_open"] = False
    with pytest.raises(ValueError, match="frozen"):
        _state(unfrozen)


def test_duplicate_context_model_fold_keys_fail_closed():
    frame = _rows({"m1": [0.050, 0.060], "m2": [0.050, 0.060]})
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        _state(frame)
