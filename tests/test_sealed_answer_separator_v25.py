import numpy as np
import pandas as pd
import pytest

from sdmr.model import ModelSpec
from sdmr.sealed_answer_separator_v25 import (
    build_sealed_answer_fold_evidence,
    classify_sealed_answer_separator,
)
from sdmr.sealed_occurrence_contract import freeze_occurrence_answer_check_split


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


def _outer_frames():
    rng = np.random.default_rng(5)
    centers = np.array([
        [-4.0, -2.0], [-4.0, 2.0], [-1.5, -2.0], [-1.5, 2.0],
        [1.5, -2.0], [1.5, 2.0], [4.0, -2.0], [4.0, 2.0],
    ])
    occ_xy = np.vstack([c + rng.normal(0, 0.08, (10, 2)) for c in centers])

    def features(xy):
        lon = xy[:, 0]
        lat = xy[:, 1]
        temp = 0.7 * lat + 0.2 * lon
        return pd.DataFrame({
            "longitude": lon,
            "latitude": lat,
            "temperature": temp,
            "temp_proxy": 0.9 * temp + 0.03 * lon,
            "water": -0.6 * lon + 0.2 * lat,
            "seasonality": np.sin(lon) + 0.2 * np.cos(lat),
            "noise": 0.1 * lon - 0.05 * lat,
        })

    occurrences = features(occ_xy)
    occurrences.insert(0, "occurrence_id", [f"occ-{i:03d}" for i in range(len(occurrences))])
    bg_xy = rng.uniform([-4.8, -2.8], [4.8, 2.8], size=(240, 2))
    sep_xy = rng.uniform([-4.7, -2.7], [4.7, 2.7], size=(240, 2)) + 1e-5
    return occurrences, features(bg_xy), features(sep_xy)


def _registry():
    return pd.DataFrame([
        {"predictor": "temperature", "process": "temperature", "role": "direct"},
        {"predictor": "temp_proxy", "process": "temperature", "role": "proxy"},
        {"predictor": "water", "process": "water", "role": "direct"},
        {"predictor": "seasonality", "process": "seasonality", "role": "direct"},
        {"predictor": "noise", "process": "noise", "role": "direct"},
    ])


def test_build_outer_evidence_excludes_full_process_closure_and_opens_only_after_receipt():
    occurrences, background, separator_background = _outer_frames()
    split = freeze_occurrence_answer_check_split(
        occurrences,
        n_blocks=8,
        holdout_fraction=0.25,
        random_state=19,
    )
    specs = (
        ModelSpec(C=1.0, degree=1, penalty="l2", random_state=0),
        ModelSpec(C=1.0, degree=2, penalty="l2", random_state=0),
    )
    evidence = build_sealed_answer_fold_evidence(
        occurrences,
        background,
        separator_background,
        occurrence_split=split,
        family="gaussian",
        seed=17001,
        target_block=2,
        target_process="temperature",
        process_registry=_registry(),
        ecological_predictors=("temperature", "temp_proxy", "water", "seasonality", "noise"),
        observation_predictors=(),
        model_specs=specs,
        selection_receipt="v23-support-frozen",
        outer_n_blocks=8,
        outer_holdout_fraction=0.25,
        outer_random_state=19,
    )
    assert set(evidence.model_label) == {s.label for s in specs}
    assert evidence.prediction_frozen_before_answer_open.astype(bool).all()
    assert evidence.sealed_answer_source_disjoint.astype(bool).all()
    assert evidence.prediction_receipt.astype(str).str.len().min() == 64
    assert evidence.baseline_predictors.str.contains("temperature").all()
    assert evidence.baseline_predictors.str.contains("temp_proxy").all()
    assert (~evidence.excluded_predictors.str.contains("temperature")).all()
    assert (~evidence.excluded_predictors.str.contains("temp_proxy")).all()
    assert evidence.fold.nunique() >= 2


def test_build_outer_evidence_requires_receipt_and_disjoint_reference_rows():
    occurrences, background, separator_background = _outer_frames()
    split = freeze_occurrence_answer_check_split(
        occurrences,
        n_blocks=8,
        holdout_fraction=0.25,
        random_state=19,
    )
    kwargs = dict(
        occurrence_split=split,
        family="gaussian",
        seed=17001,
        target_block=2,
        target_process="temperature",
        process_registry=_registry(),
        ecological_predictors=("temperature", "temp_proxy", "water", "seasonality", "noise"),
        observation_predictors=(),
        model_specs=(ModelSpec(C=1.0, degree=1, random_state=0),),
        outer_n_blocks=8,
        outer_holdout_fraction=0.25,
        outer_random_state=19,
    )
    with pytest.raises(ValueError, match="selection_receipt"):
        build_sealed_answer_fold_evidence(
            occurrences, background, separator_background,
            selection_receipt="", **kwargs,
        )

    overlapping = separator_background.copy()
    overlapping.loc[0, ["longitude", "latitude"]] = background.loc[0, ["longitude", "latitude"]]
    with pytest.raises(ValueError, match="source-disjoint"):
        build_sealed_answer_fold_evidence(
            occurrences, background, overlapping,
            selection_receipt="frozen", **kwargs,
        )
