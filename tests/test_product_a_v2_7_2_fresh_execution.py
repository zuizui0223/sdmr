import json
from pathlib import Path

EXECUTION = Path('configs/product_a_v2_7_2_fresh_execution_contract.json')
GATE = Path('configs/product_a_v2_7_2_fresh_empirical_source_gate.json')
LAUNCHER = Path('.github/workflows/product-a-v2-7-2-fresh-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_7_2_fresh_pr_trigger.txt')


def test_exact_rank2_empirical_execution_identity_is_frozen():
    c = json.loads(EXECUTION.read_text())
    assert c['purpose'] == 'product_a_v2_7_2_fresh_empirical_execution_contract'
    assert c['execution_source_frozen_before_rank2_empirical_outcome'] is True
    assert c['implementation_sha'] == '5073d6c701f36fdae0bf5df9a1d42f1863d994a8'
    assert c['frozen_ref'] == 'frozen/product-a-v2-7-2-fresh-confirmation-5073d6c7'
    assert c['workflow_file'] == 'product-a-v2-7-2-fresh-confirmation.yml'
    assert c['workflow_blob_sha'] == 'a03e72d2e04f1866108fdda344251e2c90cc0902'
    assert c['requires_single_workflow_dispatch_run_for_frozen_identity'] is True
    superseded = c['supersedes_failed_runtime']
    assert superseded['implementation_sha'] == 'a5c2b4bb3b00581f7eea67327ac9f89074e914bb'
    assert superseded['workflow_run_id'] == 32637052553
    assert superseded['failed_stage'] == 'preflight'
    assert superseded['raw_source_job_started'] is False
    assert superseded['sealed_environment_read'] is False
    assert superseded['scientific_decision_created'] is False
    frozen = c['frozen_inputs']
    assert frozen['scientific_contract_blob_sha'] == '04ec0d9519b8ea5ed7720f04cffb79ec0cdf4291'
    assert frozen['runtime_design_blob_sha'] == 'aed6c3c2db4abe495753712433aaaf0b066b74c4'
    assert frozen['source_gate_blob_sha_at_runtime_freeze'] == '1ad8efc9032ece86d7a174737cb9c8b8a06d5903'
    assert frozen['source_receipt_blob_sha'] == 'ff5b712124d84b81749e75b248bb817b81574999'
    assert frozen['source_run_id'] == 32631351934
    assert frozen['source_receipt_artifact_id'] == 9491375010
    assert frozen['source_receipt_artifact_digest'] == 'sha256:61f81acd96d8a3f5aad3a2e15599503d754e40607355722eaf6062e8edf91887'
    graph = c['execution_graph']
    assert graph == {
        'materialization_parts': 6,
        'primary_M_shards': 216,
        'aggregated_workers': 72,
        'pretruth_parts': 6,
        'final_fit_jobs': 72,
        'sealed_audit_parts': 6,
        'decision_artifacts': 1,
    }
    assert c['scientific_invariants']['weighted_super_score_allowed'] is False
    assert c['scientific_invariants']['selective_shard_repair_or_substitution_allowed'] is False
    assert c['claim_boundary']['decision_itself_promotes_Product_A'] is False
    assert c['claim_boundary']['product_b_unblocked'] is False


def test_authorization_gate_points_only_to_frozen_runtime():
    c = json.loads(EXECUTION.read_text())
    gate = json.loads(GATE.read_text())
    req = gate['required_before_execution']
    assert gate['gate_state'] == 'ready_for_one_shot_rank2_empirical_confirmation'
    assert gate['execution_allowed'] is True
    assert req['empirical_runtime_implementation_sha'] == c['implementation_sha']
    assert req['empirical_runtime_frozen_ref'] == c['frozen_ref']
    assert req['workflow_file'] == c['workflow_file']
    assert req['raw_source_receipt_artifact_id'] == c['frozen_inputs']['source_receipt_artifact_id']
    assert req['raw_source_receipt_artifact_digest'] == c['frozen_inputs']['source_receipt_artifact_digest']


def test_launcher_is_one_shot_and_trigger_is_not_committed():
    text = LAUNCHER.read_text()
    assert 'product_a_v2_7_2_fresh_pr_trigger.txt' in text
    assert 'multiple frozen v2.7.2 empirical runs exist' in text
    assert "payload={'ref':c['frozen_ref']}" in text
    assert "'scientific_promotion_allowed':False" in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()
