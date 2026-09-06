import json
from pathlib import Path


CONFIG = Path("configs/process_identification_gap_development.json")


def test_gap_development_sources_are_frozen() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["purpose"] == "process_identification_gap_development_only"
    assert payload["development_only"] is True
    assert payload["eligible_for_prospective_performance_claim"] is False
    assert payload["expected_rows"] == 300
    assert payload["expected_cases"] == 60
    assert tuple(payload["development_seeds"]) == tuple(range(13001, 13011))
    assert payload["future_prospective_validation_must_use_new_unused_seeds"] is True

    learner = payload["learner_source"]
    assert learner["workflow_run_id"] == 34015456711
    assert learner["artifact_id"] == 9983793398
    assert learner["artifact_sha256"] == "9bc217f2b9fd0f1b1995e76e466befa05ff7f13f62400f5bff05e537544ee1d3"

    oracle = payload["oracle_source"]
    assert oracle["workflow_run_id"] == 34022478135
    assert oracle["artifact_id"] == 9986006226
    assert oracle["artifact_sha256"] == "59caa5482bd5ae3dc695e53a7dc7dcde0ffb980d061c7d155cefe8b6ce7584bb"
