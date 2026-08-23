import json
from pathlib import Path

CONTRACT=Path('configs/product_a_v2_7_2_shard_build_execution.json')
WORKFLOW=Path('.github/workflows/product-a-v2-7-2-presealed-shard-build.yml')
LAUNCHER=Path('.github/workflows/product-a-v2-7-2-presealed-shard-build-pr-launch.yml')
TRIGGER=Path('configs/product_a_v2_7_2_shard_build_pr_trigger.txt')


def test_deterministic_shard_build_gate_is_closed_until_probe_passes():
    c=json.loads(CONTRACT.read_text())
    assert c['execution_allowed'] is False
    assert c['implementation_sha'] is None
    assert c['frozen_ref'] is None
    assert c['random_state']==271
    assert c['probe_run_id'] is None
    assert c['probe_artifact_id'] is None
    assert c['probe_artifact_digest'] is None
    assert c['probe_passed'] is None
    assert c['total_M_shards']==216
    assert c['reuse_old_worker_outputs'] is False
    assert c['selective_repair_allowed'] is False
    assert c['product_b_unblocked'] is False


def test_deterministic_shard_build_reruns_full_denominator_with_seed():
    text=WORKFLOW.read_text()
    assert "SDMR_LOGISTIC_RANDOM_STATE: '271'" in text
    assert "seed: [2026082201, 2026082202, 2026082203]" in text
    assert "sealed_fraction: ['0.20', '0.30']" in text
    assert 'taxon_index: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]' in text
    assert 'M: [buffer_150km, buffer_300km, buffer_500km]' in text
    assert 'v272-fresh-M-' in text
    assert "'old_worker_outputs_reused':False" in text
    assert "'sealed_environment_read':False" in text
    assert 'product-a-v2-7-2-determinism-probe' in text


def test_deterministic_shard_build_launcher_is_one_shot_and_trigger_absent():
    text=LAUNCHER.read_text()
    assert 'product_a_v2_7_2_shard_build_pr_trigger.txt' in text
    assert 'multiple exact deterministic shard-build runs exist' in text
    assert "'probe_artifact_digest':c['probe_artifact_digest']" in text
    assert "'sealed_environment_read_allowed':False" in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()
