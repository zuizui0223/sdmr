import json
from pathlib import Path

DESIGN = Path('configs/product_a_v2_7_2_empirical_runtime_design.json')
REPAIR = Path('configs/product_a_v2_7_2_fresh_preflight_repair.json')


def test_preflight_repair_only_duplicates_existing_false_invariant():
    design = json.loads(DESIGN.read_text())
    assert design['primary_shard_invariants']['selective_repair_or_substitution_allowed'] is False
    assert design['failure_policy']['selective_repair_or_substitution_allowed'] is False
    repair = json.loads(REPAIR.read_text())
    assert repair['purpose'] == 'product_a_v2_7_2_fresh_preflight_only_repair'
    failed = repair['failed_runtime']
    assert failed['workflow_run_id'] == 32637052553
    assert failed['failed_stage'] == 'preflight'
    assert failed['raw_source_job_started'] is False
    assert failed['materialization_started'] is False
    assert failed['model_fitting_started'] is False
    assert failed['pretruth_started'] is False
    assert failed['sealed_environment_read'] is False
    assert failed['scientific_decision_created'] is False
    changed = repair['repair']
    assert changed['failure_policy_selective_repair_or_substitution_allowed'] is False
    for key, value in changed.items():
        if key.endswith('_changed'):
            assert value is False
    assert repair['claim_boundary']['failed_preflight_is_scientific_evidence'] is False
    assert repair['claim_boundary']['Product_A_promoted'] is False
    assert repair['claim_boundary']['product_b_unblocked'] is False
