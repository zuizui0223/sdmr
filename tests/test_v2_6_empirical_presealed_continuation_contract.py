from pathlib import Path
import json

CONFIG = Path('configs/product_a_v2_6_empirical_presealed_continuation_contract.json')


def test_presealed_continuation_uses_all_existing_shards_without_science_changes():
    c = json.loads(CONFIG.read_text())
    assert c['purpose'] == 'product_a_v2_6_empirical_presealed_continuation'
    source = c['source_recovery_run']
    assert source['run_id'] == 32323931807
    assert source['head_sha'] == '7f79dd10f312c42168f0d80496c7299d0e629cad'
    assert source['failure_stage'] == 'merge_worker_before_pretruth'
    assert source['pretruth_artifacts_observed'] == 0
    assert source['sealed_audit_artifacts_observed'] == 0
    assert source['decision_artifacts_observed'] == 0
    shards = c['source_shards']
    assert shards['required_count'] == 216
    assert shards['all_shards_must_be_used'] is True
    assert shards['subset_repair_forbidden'] is True
    assert shards['sealed_occurrence_environment_read'] is False
    d = shards['dimensions']
    assert len(d['part_seeds']) * len(d['sealed_fractions']) * len(d['taxon_indices']) * len(d['m_indices']) == 216
    continuation = c['continuation_semantics']
    assert continuation['recompute_model_pool_shards'] is False
    assert continuation['reconstruct_all_72_taxon_workers_with_existing_exact_merge'] is True
    assert continuation['sealed_environment_first_read_only_after_all_6_pretruth_and_72_final_fit_outputs'] is True
    assert continuation['scientific_thresholds_changed'] is False
    assert continuation['candidate_selection_rules_changed'] is False
    assert continuation['M_semantics_changed'] is False
    assert continuation['process_registry_changed'] is False
    assert c['decision_artifact_name'] == 'product-a-v2-6-independent-empirical-confirmation-decision-continuation'
