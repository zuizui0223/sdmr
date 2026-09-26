import copy
import json
from pathlib import Path

import pytest

from sdmr.process_id.fresh.contract import (
    FreshContractError,
    contract_sha256,
    validate_final_freeze_contract,
    validate_prefreeze_contract,
)


CONFIG = Path("configs/sdmr_fresh_empirical_prefreeze_v1.json")


def _scaffold():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _final_contract():
    c = _scaffold()
    c["status"] = "frozen_ready_for_fresh_execution"
    c["cohort"].update(
        {
            "exact_denominator": 40,
            "eligibility_rules_frozen": True,
            "taxon_identities_frozen": True,
            "taxon_identity_manifest_sha256": "sha256:" + "1" * 64,
            "source_manifest_frozen": True,
            "source_manifest_sha256": "sha256:" + "2" * 64,
        }
    )
    c["data_boundary"].update(
        {
            "provider": "frozen-provider",
            "temporal_window": "frozen-window",
            "occurrence_qc_rule": "frozen-qc",
            "accessible_area_rule": "frozen-accessible-area",
        }
    )
    c["process_registry"].update(
        {
            "frozen": True,
            "registry_manifest_sha256": "sha256:" + "3" * 64,
        }
    )
    c["primary_metric"].update(
        {
            "prediction_guardrail": "frozen-prediction-guardrail",
            "prediction_guardrail_frozen": True,
        }
    )
    c["comparators"].update(
        {
            "primary": "matched_learner_flat_predictive_selector",
            "frozen": True,
        }
    )
    c["learner_design_panel"].update(
        {
            "routes": ["penalized_logistic", "shallow3_hgb"],
            "frozen": True,
        }
    )
    c["promotion"]["gate_vector"]["EMP-A"]["minimum_mean_gain"] = 0.0
    c["promotion"]["gate_vector"]["EMP-B"]["minimum_lower_bound"] = 0.0
    c["promotion"]["gate_vector"]["EMP-C"]["noninferiority_margin"] = 0.02
    c["promotion"]["gate_vector"]["EMP-D"]["minimum_stable_fraction"] = 0.8
    c["promotion"]["frozen"] = True
    return c


def test_prefreeze_scaffold_is_valid_but_does_not_open_fresh_outcomes():
    c = _scaffold()
    validate_prefreeze_contract(c)
    assert c["fresh_outcomes_opened"] is False
    assert c["cohort"]["exact_denominator"] is None
    assert c["promotion"]["frozen"] is False


def test_prefreeze_fails_closed_without_passed_prospective_known_truth():
    c = _scaffold()
    c["known_truth_prerequisite"]["terminal_passed"] = False
    with pytest.raises(FreshContractError, match="did not pass"):
        validate_prefreeze_contract(c)


def test_prefreeze_fails_closed_if_fresh_outcomes_were_opened():
    c = _scaffold()
    c["fresh_outcomes_opened"] = True
    with pytest.raises(FreshContractError, match="must remain unopened"):
        validate_prefreeze_contract(c)


def test_prefreeze_forbids_historical_taxon_reuse_and_postoutcome_replacement():
    c = _scaffold()
    c["cohort"]["historical_product_a_taxa_excluded"] = False
    with pytest.raises(FreshContractError, match="historical Product-A taxa"):
        validate_prefreeze_contract(c)

    c = _scaffold()
    c["cohort"]["replacement_after_outcome_access"] = True
    with pytest.raises(FreshContractError, match="replacement after outcome"):
        validate_prefreeze_contract(c)


def test_prefreeze_keeps_exact_process_taxonomy_and_strict_emp_conjunction():
    c = _scaffold()
    c["process_registry"]["processes"] = c["process_registry"]["processes"][:-1]
    with pytest.raises(FreshContractError, match="taxonomy drifted"):
        validate_prefreeze_contract(c)

    c = _scaffold()
    c["promotion"]["strict_conjunction"] = ["EMP-A", "EMP-B"]
    with pytest.raises(FreshContractError, match="exact EMP-A through EMP-F"):
        validate_prefreeze_contract(c)


def test_final_freeze_rejects_unresolved_design_fields():
    c = _scaffold()
    c["status"] = "frozen_ready_for_fresh_execution"
    with pytest.raises(FreshContractError, match="exact taxon denominator"):
        validate_final_freeze_contract(c)


def test_complete_final_freeze_contract_passes():
    c = _final_contract()
    validate_final_freeze_contract(c)


def test_final_freeze_requires_all_empirical_thresholds_before_outcome_access():
    c = _final_contract()
    c["promotion"]["gate_vector"]["EMP-D"]["minimum_stable_fraction"] = None
    with pytest.raises(FreshContractError, match="EMP-D.minimum_stable_fraction"):
        validate_final_freeze_contract(c)


def test_canonical_contract_hash_is_key_order_invariant():
    c = _scaffold()
    reordered = {key: c[key] for key in reversed(list(c))}
    assert contract_sha256(c) == contract_sha256(reordered)


def test_manifest_hash_cannot_appear_before_manifest_is_frozen():
    c = _scaffold()
    c["cohort"]["taxon_identity_manifest_sha256"] = "sha256:" + "a" * 64
    with pytest.raises(FreshContractError, match="cannot be populated"):
        validate_prefreeze_contract(c)
