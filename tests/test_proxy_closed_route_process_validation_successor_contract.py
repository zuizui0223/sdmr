import json
from pathlib import Path

from sdmr.known_truth_scenarios import KNOWN_TRUTH_FAMILIES
from sdmr.proxy_closed_route_process_validation_successor import load_contract


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "configs" / "proxy_closed_route_process_challenge_v6_known_truth_validation.json"
NEW = ROOT / "configs" / "proxy_closed_route_process_challenge_v6_known_truth_validation_successor_v2.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_failed_attempt_is_retired_without_opening_truth() -> None:
    old = _read(OLD)
    new = load_contract(NEW)
    assert tuple(old["seeds"]) == tuple(range(14001, 14011))
    assert tuple(new["predecessor_seed_denominator_retired"]) == tuple(range(14001, 14011))
    assert new["technical_successor_of_run_id"] == 34103111132
    assert new["predecessor_terminal"] == "determinism_gate_not_supported"
    assert new["predecessor_generating_process_truth_opened"] is False
    assert new["technical_probe_discrete_differences"] == 0
    assert new["technical_probe_finite_mask_differences"] == 0


def test_successor_uses_fresh_frozen_denominator() -> None:
    c = load_contract(NEW)
    assert tuple(c["families"]) == tuple(KNOWN_TRUTH_FAMILIES)
    assert tuple(c["seeds"]) == tuple(range(15001, 15011))
    assert c["n_cases"] == 60
    assert c["n_process_cells"] == 300
    assert c["post_outcome_changes_allowed"] is False
    assert c["threshold_relaxation_allowed"] is False
    assert c["seed_replacement_allowed"] is False
    assert c["family_replacement_allowed"] is False
    assert c["failed_or_null_cases_must_remain_in_denominator"] is True


def test_only_transport_parity_envelope_changes() -> None:
    old = _read(OLD)
    new = load_contract(NEW)
    for key in (
        "families",
        "simulation",
        "ecological_predictors",
        "observation_predictors",
        "process_registry",
        "process_universe",
        "model_specs",
        "learner",
        "primary_process_thresholds",
        "report_only_not_promotion_gates",
        "fresh_empirical_validation_required_after_known_truth_support",
        "product_a_reopened",
    ):
        assert new[key] == old[key]
    assert new["technical_change"] == "transport_only_float_parity_envelope"
    assert new["technical_change_does_not_modify_estimator_or_scientific_thresholds"] is True
    det = new["determinism"]
    assert det["n_independent_replicates"] == 2
    assert det["discrete_identity_must_match"] is True
    assert det["numeric_absolute_tolerance"] == 1e-4
    assert det["numeric_relative_tolerance"] == 1e-6
    assert det["absolute_tolerance_fraction_of_smallest_scientific_margin"] == 0.01
    assert det["tolerance_frozen_from_retired_truth_blind_technical_probe"] is True
    assert new["technical_probe_max_absolute_float_drift"] < det["numeric_absolute_tolerance"]
