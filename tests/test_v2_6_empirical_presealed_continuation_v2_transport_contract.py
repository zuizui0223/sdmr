from pathlib import Path
import json

CONFIG = Path('configs/product_a_v2_6_empirical_presealed_continuation_v2_transport_contract.json')


def test_transport_successor_changes_no_science_and_preserves_information_barrier():
    c = json.loads(CONFIG.read_text())
    assert c['purpose'] == 'product_a_v2_6_empirical_presealed_continuation_v2_transport_contract'
    assert c['scientific_contract_unchanged'] is True
    assert c['source_presealed_run']['run_id'] == 32323931807
    assert c['source_presealed_run']['required_M_shard_count'] == 216
    assert c['source_presealed_run']['sealed_environment_opened'] is False
    p = c['failed_predecessor_continuation']
    assert p['run_id'] == 32434610154
    assert p['pretruth_artifact_count'] == 0
    assert p['sealed_audit_artifact_count'] == 0
    assert p['sealed_environment_opened'] is False
    t = c['transport_change_only']
    assert t['new_transport'] == 'gh run download with exact artifact name for each of m0,m1,m2'
    assert t['source_artifact_names_selected_by_scientific_outcome'] is False
    assert t['all_216_predeclared_M_shards_remain_required'] is True
    assert t['subset_repair_forbidden'] is True
    assert c['continuation_stages_unchanged'] == [
        '72_exact_three_M_worker_merges',
        '6_pretruth_freezes',
        '72_final_fits',
        '6_sealed_audits',
        'unchanged_six_part_empirical_decision',
    ]
    assert not any(c['scientific_changes'].values())
    assert c['information_barrier']['pretruth_must_precede_sealed_environment_read'] is True
    assert c['information_barrier']['all_final_models_must_be_serialized_before_sealed_audit'] is True
    assert c['information_barrier']['sealed_audit_is_first_authorized_sealed_environment_read'] is True
