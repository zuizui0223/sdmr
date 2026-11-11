from sdmr.interval_evidence_process_challenge_development import _load
from sdmr.known_truth_scenarios import KNOWN_TRUTH_FAMILIES


def test_v5_development_reuses_burned_denominator_and_v4_thresholds() -> None:
    dev, v4, _ = _load()
    assert dev["development_only"] is True
    assert dev["eligible_for_prospective_performance_claim"] is False
    assert dev["product_a_reopened"] is False
    assert tuple(dev["families"]) == tuple(KNOWN_TRUTH_FAMILIES)
    assert tuple(dev["seeds"]) == tuple(range(13001, 13011))
    assert dev["n_cases"] == 60
    assert dev["no_threshold_changes_from_v4"] is True
    assert dev["shared_carrier_attribution_unchanged"] is True
    assert dev["rank_margin"] == v4["rank_relative_noninferiority_margin"]
    assert dev["rank_sem_multiplier"] == v4["rank_relative_sem_multiplier"]
    assert dev["density_margin_nats"] == v4["density_ratio"]["noninferiority_margin_nats"]
    assert dev["density_sem_multiplier"] == v4["density_ratio"]["sem_multiplier"]
