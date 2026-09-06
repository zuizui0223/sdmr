import json
from pathlib import Path


RECEIPT = Path("configs/ecological_identification_successor_v2_terminal_decision_receipt.json")


def test_successor_v2_terminal_receipt_is_closed_negative_result() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert payload["purpose"] == "ecological_identification_successor_v2_terminal_decision_receipt"
    assert payload["workflow_run_id"] == 34008495338
    assert payload["decision_artifact"]["artifact_id"] == 9981839123
    assert payload["decision_artifact"]["digest"] == "sha256:d675dc0bec735b536cd2b503b5795f8555d7ed1f4e99b9ecdeb757b0802c8524"
    assert payload["fresh_denominator"]["n_cases"] == 120
    assert payload["determinism"]["passed"] is True
    learner = payload["new_identification_learner"]
    assert learner["false_required_rate"] == 0.0
    assert learner["true_process_recall"] == 0.0
    assert learner["process_status_counts"] == {
        "refuted_as_necessary": 600,
        "required_by_evidence_contract": 0,
        "unresolved": 0,
    }
    assert payload["known_truth_supported"] is False
    assert payload["nature_family_promotion_allowed_now"] is False
    assert payload["product_a_reopened"] is False
    assert payload["post_outcome_changes_allowed"] is False


def test_successor_v2_terminal_receipt_preserves_prediction_failure() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    prediction = payload["prediction"]
    assert prediction["mean_learner_minus_canonical_presence_rank"] < -0.02
    assert prediction["mean_delta_guardrail_passed"] is False
    assert prediction["family_delta_guardrail_passed"] is False
