import json

import pytest

from sdmr.prospective_identification_successor_v2 import (
    EXPECTED_NUMERICAL_ENVIRONMENT,
    SUCCESSOR_SEEDS,
    load_successor_execution,
)


def test_successor_contract_preserves_science_and_uses_fresh_seeds() -> None:
    payload = load_successor_execution()
    assert tuple(payload["seeds"]) == SUCCESSOR_SEEDS == tuple(range(12001, 12021))
    assert payload["n_cases"] == 120
    assert payload["predecessor_process_truth_opened"] is False
    assert payload["predecessor_terminal"] == "determinism_gate_not_supported"
    assert tuple(payload["predecessor_seed_denominator_retired"]) == tuple(range(4101, 4121))
    assert payload["technical_change_only"] is True
    assert payload["numerical_environment"] == EXPECTED_NUMERICAL_ENVIRONMENT
    assert payload["post_outcome_changes_allowed"] is False
    assert payload["threshold_relaxation_allowed"] is False
    assert payload["seed_replacement_allowed"] is False
    assert payload["family_replacement_allowed"] is False


def test_successor_rejects_scientific_drift(tmp_path) -> None:
    payload = load_successor_execution()
    payload["learner"]["minimum_margin"] = 0.02
    path = tmp_path / "drift.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="successor scientific field differs from predecessor: learner"):
        load_successor_execution(path)


def test_successor_rejects_seed_reuse(tmp_path) -> None:
    payload = load_successor_execution()
    payload["seeds"] = list(range(4101, 4121))
    path = tmp_path / "reuse.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="successor seed denominator changed"):
        load_successor_execution(path)
