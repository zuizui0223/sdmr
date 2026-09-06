import json
from pathlib import Path

from sdmr.known_truth_scenarios import KNOWN_TRUTH_FAMILIES


CONFIG = Path("configs/density_ratio_process_challenge_v4_development.json")


def test_v4_development_denominator_is_fixed_and_not_prospective() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["purpose"] == "density_ratio_process_challenge_v4_development_only"
    assert payload["development_only"] is True
    assert payload["eligible_for_prospective_performance_claim"] is False
    assert tuple(payload["families"]) == tuple(KNOWN_TRUTH_FAMILIES)
    assert tuple(payload["seeds"]) == tuple(range(13001, 13011))
    assert payload["n_cases"] == 60
    assert payload["product_a_reopened"] is False
    assert payload["future_prospective_validation_must_use_new_unused_seeds"] is True


def test_density_score_is_relative_distribution_not_absolute_probability() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    density = payload["density_ratio"]
    assert density["noninferiority_margin_nats"] == 0.01
    assert density["sem_multiplier"] == 1.0
    assert density["probability_epsilon"] == 0.000001
    assert density["score_interpretation"] == (
        "equal_prior_presence_background_density_ratio_not_absolute_occurrence_probability"
    )
    assert density["threshold_status"] == (
        "post_outcome_development_heuristic_not_prospectively_validated"
    )


def test_v4_preserves_sealed_and_shared_carrier_contracts() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["fit_must_use_model_pool_occurrences_only"] is True
    assert payload["answer_check_occurrences_must_not_affect_fit_or_process_status"] is True
    assert payload["proxy_audit_must_use_predictors_only"] is True
    assert payload["proxy_audit_must_not_modify_registry"] is True
    attribution = payload["shared_carrier_attribution"]
    assert attribution["minimum_univariate_cv_r2"] == 0.25
    assert attribution["minimum_abs_spearman"] == 0.50
    assert attribution["require_other_process_challenge_signal"] is True
