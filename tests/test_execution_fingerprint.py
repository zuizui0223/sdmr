from pathlib import Path

from sdmr.execution_fingerprint import (
    FROZEN_SCIENCE_FILES,
    scientific_execution_fingerprint,
    scientific_execution_manifest,
)


def test_scientific_execution_fingerprint_covers_code_rules_runtime_and_workflows():
    manifest=scientific_execution_manifest('.')
    paths={row['path'] for row in manifest}
    assert 'src/sdmr/model.py' in paths
    assert 'src/sdmr/v2_7_1_fresh_model_pool_shard.py' in paths
    assert 'src/sdmr/v2_7_1_fresh_sealed_audit.py' in paths
    assert 'configs/product_a_v2_7_1_fresh_confirmation_contract.json' in paths
    assert 'configs/product_a_v2_7_2_deterministic_execution_contract.json' in paths
    assert 'configs/product_a_v2_7_2_fresh_promotion_contract.json' in paths
    assert 'configs/product_a_v2_7_2_runtime_constraints.txt' in paths
    assert '.github/workflows/product-a-v2-7-2-determinism-probe.yml' in paths
    assert '.github/workflows/product-a-v2-7-2-presealed-shard-build.yml' in paths
    assert '.github/workflows/product-a-v2-7-2-post-shard-continuation.yml' in paths
    fp=scientific_execution_fingerprint('.')
    assert fp['purpose']=='product_a_v2_7_2_scientific_execution_fingerprint'
    assert len(fp['sha256'])==64
    assert fp['n_files']==len(manifest)


def test_execution_gate_files_are_excluded_from_science_fingerprint():
    assert 'configs/product_a_v2_7_2_determinism_probe_execution.json' not in FROZEN_SCIENCE_FILES
    assert 'configs/product_a_v2_7_2_shard_build_execution.json' not in FROZEN_SCIENCE_FILES
    assert 'configs/product_a_v2_7_2_post_shard_continuation_execution.json' not in FROZEN_SCIENCE_FILES
