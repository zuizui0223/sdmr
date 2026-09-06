import json
from pathlib import Path

from sdmr.known_truth_scenarios import KNOWN_TRUTH_FAMILIES


CONFIG = Path("configs/process_challenge_v3_development.json")


def test_v3_development_denominator_is_fixed_and_not_prospective_evidence() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["purpose"] == "process_challenge_v3_development_only"
    assert payload["development_only"] is True
    assert payload["eligible_for_prospective_performance_claim"] is False
    assert tuple(payload["families"]) == tuple(KNOWN_TRUTH_FAMILIES)
    assert tuple(payload["seeds"]) == tuple(range(13001, 13011))
    assert payload["n_cases"] == 60
    assert payload["relative_noninferiority_margin"] == 0.02
    assert payload["fit_must_use_model_pool_occurrences_only"] is True
    assert payload["answer_check_occurrences_must_not_affect_fit_or_process_status"] is True
    assert payload["future_prospective_validation_must_use_new_unused_seeds"] is True


def test_v32_shared_carrier_rules_are_explicitly_development_only() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    attribution = payload["shared_carrier_attribution"]
    assert attribution["minimum_univariate_cv_r2"] == 0.25
    assert attribution["minimum_abs_spearman"] == 0.50
    assert attribution["proxy_audit_n_splits"] == 5
    assert attribution["proxy_audit_degree"] == 2
    assert attribution["require_other_process_challenge_signal"] is True
    assert attribution["threshold_status"] == (
        "post_outcome_development_heuristic_not_prospectively_validated"
    )
    assert payload["proxy_audit_must_use_predictors_only"] is True
    assert payload["proxy_audit_must_not_modify_registry"] is True


def test_v3_development_seeds_do_not_reuse_closed_validation_denominators() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    development = set(payload["seeds"])
    assert development.isdisjoint(range(4101, 4121))
    assert development.isdisjoint(range(12001, 12021))
