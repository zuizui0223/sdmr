import json
from pathlib import Path

from sdmr.known_truth_scenarios import KNOWN_TRUTH_FAMILIES, standard_known_truth_candidates
from sdmr.v2_7_2_deterministic_procedure_library import seed_recovery_candidates
from sdmr.v2_7_2_known_truth_confirmation import load_contract

CONTRACT = Path("configs/product_a_v2_7_2_deterministic_successor_contract.json")
WORKFLOW = Path(".github/workflows/product-a-v2-7-2-known-truth-determinism.yml")


def test_v272_contract_freezes_determinism_before_new_truth():
    c = load_contract(CONTRACT)
    assert c["frozen_before_v2_7_2_known_truth_outcome"] is True
    assert c["implementation_change"]["historical_modelspec_default_random_state"] is None
    assert c["implementation_change"]["successor_model_random_state"] == 0
    assert c["known_truth_confirmation"]["families"] == list(KNOWN_TRUTH_FAMILIES)
    assert c["known_truth_confirmation"]["seeds"] == list(range(3101, 3111))
    assert c["known_truth_confirmation"]["n_cases"] == 60
    assert c["determinism_gate"]["fail_closed_on_any_discrete_difference"] is True
    assert c["determinism_gate"]["tolerance_may_not_be_changed_after_outcome"] is True
    assert c["scientific_nonregression_gate"]["post_outcome_threshold_tuning_allowed"] is False


def test_v271_failed_fresh_lane_cannot_be_relabelled_or_opened():
    c = json.loads(CONTRACT.read_text())
    stop = c["v2_7_1_stop_rule"]
    assert stop["widen_parity_tolerance_allowed"] is False
    assert stop["ignore_discrete_selection_difference_allowed"] is False
    assert stop["launch_216_shard_recovery_as_semantics_preserving_allowed"] is False
    assert stop["open_current_fresh_sealed_outcomes_under_modified_estimator_allowed"] is False
    successor = c["empirical_successor_requirement"]
    assert successor["current_v2_7_1_fresh_model_pool_may_be_relabelled_as_v2_7_2_confirmation"] is False
    assert successor["new_disjoint_taxon_panel_or_later_occurrence_snapshot_required"] is True
    assert successor["old_v2_7_1_sealed_rows_may_be_opened_for_v2_7_2"] is False


def test_seeded_known_truth_candidate_library_preserves_names_and_predictors():
    original = standard_known_truth_candidates()
    seeded = seed_recovery_candidates(original, random_state=0)
    assert set(seeded) == set(original)
    for name in original:
        assert seeded[name].predictors == original[name].predictors
        assert seeded[name].observation_predictors == original[name].observation_predictors
        assert seeded[name].model_spec.random_state == 0
        assert seeded[name].model_spec.label.endswith("_rs0")


def test_known_truth_workflow_is_dispatch_only_and_runs_two_replicates():
    text = WORKFLOW.read_text()
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "replicate: [a, b]" in text
    assert "v2_7_2_known_truth_confirmation run" in text
    assert "v2_7_2_known_truth_confirmation compare" in text
