import pandas as pd
import pytest

from sdmr.relative_attribution_v22 import (
    COESSENTIAL,
    DIRECTIONAL_NEGATIVE,
    DIRECTIONAL_POSITIVE,
    DIRECTIONAL_UNRESOLVED,
    EXCHANGEABLE,
    P_FAVORED,
    Q_FAVORED,
    UNRESOLVED,
    build_supported_pair_manifest,
    classify_symmetric_pair,
    extract_symmetric_pairwise_evidence,
)


def test_build_supported_pair_manifest_is_truth_blind_and_complete_for_three_supported_processes():
    frame = pd.DataFrame([
        {"family": "gaussian", "seed": 17001, "target_block": 2, "target_process": "temperature", "supported": True, "high_confidence_supported": True, "generating_process_true": True},
        {"family": "gaussian", "seed": 17001, "target_block": 2, "target_process": "water", "supported": True, "high_confidence_supported": False, "generating_process_true": True},
        {"family": "gaussian", "seed": 17001, "target_block": 2, "target_process": "seasonality", "supported": True, "high_confidence_supported": True, "generating_process_true": False},
        {"family": "gaussian", "seed": 17001, "target_block": 2, "target_process": "noise", "supported": False, "high_confidence_supported": False, "generating_process_true": False},
    ])
    got = build_supported_pair_manifest(frame)
    assert list(got[["process_a", "process_b"]].itertuples(index=False, name=None)) == [
        ("temperature", "water"),
        ("temperature", "seasonality"),
        ("water", "seasonality"),
    ]
    assert "generating_process_true" not in got.columns


def test_symmetric_classifier_maps_all_resolved_states_and_fails_closed():
    assert classify_symmetric_pair(DIRECTIONAL_POSITIVE, DIRECTIONAL_NEGATIVE) == P_FAVORED
    assert classify_symmetric_pair(DIRECTIONAL_NEGATIVE, DIRECTIONAL_POSITIVE) == Q_FAVORED
    assert classify_symmetric_pair(DIRECTIONAL_POSITIVE, DIRECTIONAL_POSITIVE) == COESSENTIAL
    assert classify_symmetric_pair(DIRECTIONAL_NEGATIVE, DIRECTIONAL_NEGATIVE) == EXCHANGEABLE
    assert classify_symmetric_pair(DIRECTIONAL_UNRESOLVED, DIRECTIONAL_POSITIVE) == UNRESOLVED
    assert classify_symmetric_pair(DIRECTIONAL_NEGATIVE, DIRECTIONAL_UNRESOLVED) == UNRESOLVED


def test_extractor_requires_both_directions_and_is_swap_symmetric():
    manifest = pd.DataFrame([{
        "family": "interaction",
        "seed": 17003,
        "target_block": 4,
        "process_a": "temperature",
        "process_b": "seasonality",
        "a_high_confidence_supported": True,
        "b_high_confidence_supported": True,
    }])
    evidence = pd.DataFrame([
        {"family": "interaction", "seed": 17003, "target_block": 4, "target_process": "temperature", "conditioned_on_process": "seasonality", "state": DIRECTIONAL_POSITIVE},
        {"family": "interaction", "seed": 17003, "target_block": 4, "target_process": "seasonality", "conditioned_on_process": "temperature", "state": DIRECTIONAL_NEGATIVE},
    ])
    got = extract_symmetric_pairwise_evidence(manifest, evidence)
    assert got.loc[0, "pair_status"] == P_FAVORED

    swapped_manifest = manifest.rename(columns={
        "process_a": "process_b",
        "process_b": "process_a",
        "a_high_confidence_supported": "b_high_confidence_supported",
        "b_high_confidence_supported": "a_high_confidence_supported",
    })
    swapped = extract_symmetric_pairwise_evidence(swapped_manifest, evidence)
    assert swapped.loc[0, "pair_status"] == Q_FAVORED


def test_extractor_rejects_one_sided_pair():
    manifest = pd.DataFrame([{
        "family": "gaussian",
        "seed": 17001,
        "target_block": 1,
        "process_a": "temperature",
        "process_b": "water",
    }])
    evidence = pd.DataFrame([{
        "family": "gaussian",
        "seed": 17001,
        "target_block": 1,
        "target_process": "temperature",
        "conditioned_on_process": "water",
        "state": DIRECTIONAL_POSITIVE,
    }])
    with pytest.raises(ValueError, match="missing mirrored directional evidence"):
        extract_symmetric_pairwise_evidence(manifest, evidence)
