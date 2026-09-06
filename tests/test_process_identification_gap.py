import pandas as pd
import pytest

from sdmr.oracle_process_identifiability import (
    ORACLE_CONTESTED,
    ORACLE_CONTRIBUTORY,
    ORACLE_REPLACEABLE,
    ORACLE_REQUIRED,
    ORACLE_UNAVAILABLE,
)
from sdmr.process_identification_gap import compare_process_identification_to_oracle


def test_identification_gap_separates_miss_overchallenge_and_unassessable() -> None:
    learner = pd.DataFrame(
        [
            {"family": "a", "seed": 1, "process": "p", "challenge_signal_detected": True, "unique_process_evidence": True},
            {"family": "a", "seed": 1, "process": "q", "challenge_signal_detected": False, "unique_process_evidence": False},
            {"family": "a", "seed": 1, "process": "r", "challenge_signal_detected": True, "unique_process_evidence": False},
            {"family": "a", "seed": 1, "process": "s", "challenge_signal_detected": True, "unique_process_evidence": True},
            {"family": "a", "seed": 1, "process": "u", "challenge_signal_detected": False, "unique_process_evidence": False},
        ]
    )
    oracle = pd.DataFrame(
        [
            {"family": "a", "seed": 1, "process": "p", "oracle_status": ORACLE_CONTRIBUTORY, "oracle_identifiable_signal": True},
            {"family": "a", "seed": 1, "process": "q", "oracle_status": ORACLE_REQUIRED, "oracle_identifiable_signal": True},
            {"family": "a", "seed": 1, "process": "r", "oracle_status": ORACLE_REPLACEABLE, "oracle_identifiable_signal": False},
            {"family": "a", "seed": 1, "process": "s", "oracle_status": ORACLE_CONTESTED, "oracle_identifiable_signal": False},
            {"family": "a", "seed": 1, "process": "u", "oracle_status": ORACLE_UNAVAILABLE, "oracle_identifiable_signal": False},
        ]
    )

    result = compare_process_identification_to_oracle(learner, oracle)
    m = result.overall_metrics
    assert m["n_oracle_assessable"] == 3
    assert m["n_oracle_identifiable"] == 2
    assert m["challenge_recovered_oracle_identifiable"] == 1
    assert m["challenge_identification_gap"] == 1
    assert m["challenge_recall_against_oracle"] == 0.5
    assert m["challenge_overchallenge"] == 1
    assert m["unique_recovered_oracle_identifiable"] == 1
    assert m["unique_identification_gap"] == 1
    assert m["unique_overattribution"] == 0

    by_process = result.comparison.set_index("process")
    assert bool(by_process.loc["q", "challenge_identification_gap"])
    assert bool(by_process.loc["r", "challenge_overchallenge"])
    assert not bool(by_process.loc["s", "oracle_assessable"])
    assert not bool(by_process.loc["u", "oracle_assessable"])


def test_identification_gap_requires_identical_key_universes() -> None:
    learner = pd.DataFrame(
        [{"family": "a", "seed": 1, "process": "p", "challenge_signal_detected": True, "unique_process_evidence": True}]
    )
    oracle = pd.DataFrame(
        [{"family": "a", "seed": 1, "process": "q", "oracle_status": ORACLE_REPLACEABLE, "oracle_identifiable_signal": False}]
    )
    with pytest.raises(ValueError, match="key universes differ"):
        compare_process_identification_to_oracle(learner, oracle)
