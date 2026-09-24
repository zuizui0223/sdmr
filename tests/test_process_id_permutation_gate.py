import math

import numpy as np
import pandas as pd
import pytest


def _synthetic_oof(perfect: bool = True):
    rows=[]
    for fold in (0,1,2):
        labels=np.array([1,1,1,0,0,0],dtype=int)
        if perfect:
            probs=np.array([0.9,0.8,0.7,0.3,0.2,0.1],dtype=float)
        else:
            probs=np.full(6,0.5,dtype=float)
        for y,p in zip(labels,probs,strict=True):
            rows.append({"fold":fold,"label":int(y),"probability":float(p)})
    return pd.DataFrame(rows)


def test_within_fold_permutation_preserves_class_counts():
    from sdmr.process_id.known_truth.permutation_gate import (
        permute_labels_within_folds,
    )

    frame=_synthetic_oof(perfect=True)
    permuted=permute_labels_within_folds(frame,rng=np.random.default_rng(7))

    assert len(permuted)==len(frame)
    for fold in sorted(frame["fold"].unique()):
        original=frame.loc[frame["fold"].eq(fold),"label"]
        changed=permuted.loc[permuted["fold"].eq(fold),"label"]
        assert int(original.sum())==int(changed.sum())
        assert len(original)==len(changed)


def test_permutation_gate_is_deterministic_and_resolves_to_one_over_1000():
    from sdmr.process_id.known_truth.permutation_gate import (
        evaluate_permutation_statistic,
    )

    frame=_synthetic_oof(perfect=True)
    first=evaluate_permutation_statistic(
        frame,
        n_permutations=999,
        permutation_seed=0,
    )
    second=evaluate_permutation_statistic(
        frame,
        n_permutations=999,
        permutation_seed=0,
    )

    assert first == second
    assert first["p_value"] == pytest.approx(0.001)
    assert first["exceedance_count"] == 0
    assert first["observed_mean_score"] > -math.log(2.0)


def test_constant_predictions_never_authorize():
    from sdmr.process_id.known_truth.permutation_gate import (
        evaluate_permutation_statistic,
        classify_full_system_permutation_gate,
    )

    frame=_synthetic_oof(perfect=False)
    stat=evaluate_permutation_statistic(
        frame,
        n_permutations=999,
        permutation_seed=0,
    )
    assert stat["observed_mean_score"] == pytest.approx(-math.log(2.0))
    assert stat["mean_gain_over_null"] == pytest.approx(0.0)
    assert stat["p_value"] == pytest.approx(1.0)

    decision=classify_full_system_permutation_gate(
        stat,
        adequacy_floor=-0.75,
        alpha=0.001,
    )
    assert not decision["authorized"]
    assert decision["reason"] == "full_system_not_informative"


def test_gate_requires_score_gain_and_significant_permutation_pvalue():
    from sdmr.process_id.known_truth.permutation_gate import (
        classify_full_system_permutation_gate,
    )

    base={
        "observed_mean_score":-0.68,
        "mean_gain_over_null":0.0131471805599453,
        "p_value":0.001,
    }
    assert classify_full_system_permutation_gate(
        base,adequacy_floor=-0.75,alpha=0.001
    )["authorized"]

    no_gain=dict(base,mean_gain_over_null=0.0)
    assert not classify_full_system_permutation_gate(
        no_gain,adequacy_floor=-0.75,alpha=0.001
    )["authorized"]

    weak_p=dict(base,p_value=0.002)
    assert not classify_full_system_permutation_gate(
        weak_p,adequacy_floor=-0.75,alpha=0.001
    )["authorized"]

    inadequate=dict(base,observed_mean_score=-0.80)
    assert not classify_full_system_permutation_gate(
        inadequate,adequacy_floor=-0.75,alpha=0.001
    )["authorized"]


def test_full_system_permutation_evaluation_is_deterministic():
    from sdmr.process_id.known_truth.permutation_gate import (
        evaluate_full_system_permutation_gate,
    )
    from sdmr.process_id.known_truth.worlds import simulate_process_world

    world=simulate_process_world(
        "unique_process",
        seed=60101,
        n_cells=800,
        n_occurrences=80,
        n_background=260,
    )
    kwargs=dict(
        n_splits=2,
        learner="hgb",
        hgb_profile="shallow3",
        split_mode="random_cell",
        n_permutations=99,
        alpha=0.01,
        permutation_seed=0,
        adequacy_floor=-0.75,
    )
    first=evaluate_full_system_permutation_gate(world,**kwargs)
    second=evaluate_full_system_permutation_gate(world,**kwargs)

    pd.testing.assert_frame_equal(first.oof_predictions,second.oof_predictions)
    pd.testing.assert_frame_equal(first.fold_scores,second.fold_scores)
    assert first.summary==second.summary
    assert first.summary["p_value"] in {
        (i+1)/100 for i in range(100)
    }


def test_permutation_gate_rejects_invalid_alpha_and_permutation_count():
    from sdmr.process_id.known_truth.permutation_gate import (
        evaluate_permutation_statistic,
        classify_full_system_permutation_gate,
    )

    frame=_synthetic_oof(perfect=True)
    with pytest.raises(ValueError,match="n_permutations"):
        evaluate_permutation_statistic(frame,n_permutations=0,permutation_seed=0)
    with pytest.raises(ValueError,match="alpha"):
        classify_full_system_permutation_gate(
            {
                "observed_mean_score":-0.68,
                "mean_gain_over_null":0.01,
                "p_value":0.001,
            },
            adequacy_floor=-0.75,
            alpha=0.0,
        )
