import json
from pathlib import Path

import pytest

from sdmr.process_id.fresh.contract import validate_planning_freeze_contract
from sdmr.process_id.fresh.power import (
    paired_gain_power,
    select_minimum_denominator,
    stable_fraction_power,
)


POWER = Path("configs/sdmr_fresh_empirical_power_v1.json")
PLANNING = Path("configs/sdmr_fresh_empirical_planning_freeze_v1.json")


def _power_plan():
    return json.loads(POWER.read_text(encoding="utf-8"))


def _planning_contract():
    return json.loads(PLANNING.read_text(encoding="utf-8"))


def test_worst_case_paired_gain_planning_selects_exactly_50_taxa():
    p = _power_plan()["paired_gain"]
    result = select_minimum_denominator(
        planning_min=30,
        planning_max=50,
        target_power=p["target_power"],
        true_mean_gain=p["true_mean_gain"],
        taxon_sd=p["taxon_sd_upper"],
        minimum_mean_gain=p["minimum_mean_gain"],
        minimum_lower_bound=p["minimum_lower_bound"],
        alpha=p["alpha_two_sided"],
    )
    assert result.n_taxa == 50
    assert result.power == pytest.approx(p["achieved_power"], abs=1e-12)
    assert result.critical_mean == pytest.approx(p["selected_critical_mean"], abs=1e-12)


def test_n49_remains_below_the_frozen_power_target():
    p = _power_plan()["paired_gain"]
    result = paired_gain_power(
        n_taxa=49,
        true_mean_gain=p["true_mean_gain"],
        taxon_sd=p["taxon_sd_upper"],
        minimum_mean_gain=p["minimum_mean_gain"],
        minimum_lower_bound=p["minimum_lower_bound"],
        alpha=p["alpha_two_sided"],
    )
    assert result.power == pytest.approx(p["n49_power"], abs=1e-12)
    assert result.power < p["target_power"]


def test_emp_d_planning_power_is_high_at_the_frozen_denominator():
    p = _power_plan()["stability"]
    power = stable_fraction_power(
        n_taxa=p["selected_denominator"],
        true_stable_fraction=p["planning_true_stable_fraction"],
        minimum_stable_fraction=p["minimum_stable_fraction"],
    )
    assert p["required_stable_taxa"] == 40
    assert power == pytest.approx(p["power_at_planning_fraction"], abs=1e-12)
    assert power > 0.99


def test_planning_freeze_contract_passes_without_opening_or_manifest_selection():
    c = _planning_contract()
    validate_planning_freeze_contract(c)
    assert c["fresh_outcomes_opened"] is False
    assert c["cohort"]["exact_denominator"] == 50
    assert c["cohort"]["taxon_identities_frozen"] is False
    assert c["cohort"]["source_manifest_frozen"] is False
    assert c["process_registry"]["frozen"] is False


def test_planning_freeze_fails_if_thresholds_are_unfrozen():
    c = _planning_contract()
    c["promotion"]["frozen"] = False
    with pytest.raises(Exception, match="frozen EMP thresholds"):
        validate_planning_freeze_contract(c)


def test_planning_freeze_separates_primary_ecological_metric_from_auc_guardrail():
    c = _planning_contract()
    assert c["primary_metric"]["name"] == "balanced_presence_background_log_score"
    assert "AUC" in c["primary_metric"]["prediction_guardrail"]
    assert c["promotion"]["gate_vector"]["EMP-C"]["guardrail_metric"] == "answer_check_auc"
