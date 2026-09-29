import pandas as pd
import pytest

from sdmr.process_id.known_truth.worlds import KNOWN_TRUTH_WORLDS


def _oracle_rows():
    return pd.DataFrame([
        {"world": "unique_process", "seed": 1, "process": "thermal", "state": "contributory", "expected_state": "contributory", "unique_attribution_forbidden": False},
        {"world": "redundant_representation", "seed": 1, "process": "thermal", "state": "replaceable", "expected_state": "replaceable", "unique_attribution_forbidden": False},
        {"world": "shared_carrier", "seed": 1, "process": "thermal", "state": "unresolved", "expected_state": "unresolved", "unique_attribution_forbidden": True},
        {"world": "shared_carrier", "seed": 1, "process": "water", "state": "unresolved", "expected_state": "unresolved", "unique_attribution_forbidden": True},
        {"world": "null_correlated", "seed": 1, "process": "seasonality", "state": "replaceable", "expected_state": "replaceable", "unique_attribution_forbidden": False},
        {"world": "interaction", "seed": 1, "process": "thermal", "state": "contributory", "expected_state": "contributory", "unique_attribution_forbidden": True},
        {"world": "interaction", "seed": 1, "process": "water", "state": "contributory", "expected_state": "contributory", "unique_attribution_forbidden": True},
        {"world": "observation_confounded", "seed": 1, "process": "thermal", "state": "contributory", "expected_state": "unresolved", "unique_attribution_forbidden": False},
        {"world": "omitted_driver", "seed": 1, "process": "thermal", "state": "unavailable", "expected_state": "unavailable", "unique_attribution_forbidden": False},
        {"world": "geographic_shift", "seed": 1, "process": "thermal", "state": "contributory", "expected_state": "contributory", "unique_attribution_forbidden": False},
    ])


def _occurrence_rows(shared=("unresolved", "unresolved")):
    return pd.DataFrame([
        {"world": "unique_process", "seed": 1, "process": "thermal", "state": "contributory"},
        {"world": "redundant_representation", "seed": 1, "process": "thermal", "state": "replaceable"},
        {"world": "shared_carrier", "seed": 1, "process": "thermal", "state": shared[0]},
        {"world": "shared_carrier", "seed": 1, "process": "water", "state": shared[1]},
        {"world": "null_correlated", "seed": 1, "process": "seasonality", "state": "replaceable"},
        {"world": "interaction", "seed": 1, "process": "thermal", "state": "contributory"},
        {"world": "interaction", "seed": 1, "process": "water", "state": "contributory"},
        {"world": "observation_confounded", "seed": 1, "process": "thermal", "state": "unresolved"},
        {"world": "omitted_driver", "seed": 1, "process": "thermal", "state": "unavailable"},
        {"world": "geographic_shift", "seed": 1, "process": "thermal", "state": "contributory"},
    ])


def _world_summary():
    return pd.DataFrame([
        {"world": world, "seed": 1, "oracle_valid": True, "sealed_transfer_ok": True}
        for world in KNOWN_TRUTH_WORLDS
    ])


def test_comparison_uses_expected_occurrence_state_not_raw_oracle_state():
    from sdmr.process_id.known_truth.benchmark import compare_oracle_and_occurrence

    comparison = compare_oracle_and_occurrence(_oracle_rows(), _occurrence_rows())
    w6 = comparison.loc[comparison["world"].eq("observation_confounded")].iloc[0]
    assert w6["oracle_state"] == "contributory"
    assert w6["target_state"] == "unresolved"
    assert w6["occurrence_state"] == "unresolved"
    assert not bool(w6["overresolved"])


def test_shared_carrier_single_positive_call_is_false_unique_attribution():
    from sdmr.process_id.known_truth.benchmark import compare_oracle_and_occurrence
    from sdmr.process_id.known_truth.promotion import evaluate_known_truth_gate

    comparison = compare_oracle_and_occurrence(
        _oracle_rows(), _occurrence_rows(shared=("contributory", "unresolved"))
    )
    decision = evaluate_known_truth_gate(
        comparison,
        _world_summary(),
        min_positive_recovery=0.70,
        max_false_positive=0.20,
        max_overresolution=0.20,
        max_false_unique_attribution=0.0,
        min_sealed_transfer=0.80,
    )
    assert decision.metrics["false_unique_attribution_rate"] > 0.0
    assert decision.gates["KT-E"] is False
    assert not decision.passed


def test_all_known_truth_gates_pass_by_strict_conjunction():
    from sdmr.process_id.known_truth.benchmark import compare_oracle_and_occurrence
    from sdmr.process_id.known_truth.promotion import evaluate_known_truth_gate

    comparison = compare_oracle_and_occurrence(_oracle_rows(), _occurrence_rows())
    decision = evaluate_known_truth_gate(
        comparison,
        _world_summary(),
        min_positive_recovery=0.95,
        max_false_positive=0.0,
        max_overresolution=0.0,
        max_false_unique_attribution=0.0,
        min_sealed_transfer=1.0,
    )
    assert decision.passed
    assert all(decision.gates.values())


def test_one_failed_metric_cannot_be_compensated_by_other_gates():
    from sdmr.process_id.known_truth.benchmark import compare_oracle_and_occurrence
    from sdmr.process_id.known_truth.promotion import evaluate_known_truth_gate

    occurrence = _occurrence_rows().copy()
    occurrence.loc[
        occurrence["world"].eq("redundant_representation"), "state"
    ] = "contributory"
    comparison = compare_oracle_and_occurrence(_oracle_rows(), occurrence)
    decision = evaluate_known_truth_gate(
        comparison,
        _world_summary(),
        min_positive_recovery=0.80,
        max_false_positive=0.0,
        max_overresolution=0.0,
        max_false_unique_attribution=0.0,
        min_sealed_transfer=1.0,
    )
    assert decision.gates["KT-C"] is False
    assert not decision.passed


def test_gate_fails_closed_on_missing_required_world():
    from sdmr.process_id.known_truth.benchmark import compare_oracle_and_occurrence
    from sdmr.process_id.known_truth.promotion import evaluate_known_truth_gate

    comparison = compare_oracle_and_occurrence(_oracle_rows(), _occurrence_rows())
    summary = _world_summary().loc[lambda x: ~x["world"].eq("geographic_shift")]
    with pytest.raises(ValueError, match="required known-truth worlds"):
        evaluate_known_truth_gate(
            comparison,
            summary,
            min_positive_recovery=0.8,
            max_false_positive=0.1,
            max_overresolution=0.1,
            max_false_unique_attribution=0.1,
            min_sealed_transfer=0.8,
        )
