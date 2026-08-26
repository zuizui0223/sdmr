import hashlib
import json
from pathlib import Path

import pandas as pd


SOURCE = Path('configs/product_a_v2_8_geometry_calibration_source_contract.json')
EXECUTION = Path('configs/product_a_v2_8_geometry_calibration_source_execution.json')
DESIGN = Path('configs/product_a_v2_8_geometry_only_validation_calibration_contract.json')
REGISTRY = Path('configs/product_a_v2_7_1_fresh_taxon_candidates.csv')
WORKFLOW = Path('.github/workflows/product-a-v2-8-geometry-calibration-source.yml')
LAUNCHER = Path('.github/workflows/product-a-v2-8-geometry-calibration-source-pr-launch.yml')
TRIGGER = Path('configs/product_a_v2_8_geometry_calibration_source_pr_trigger.txt')


def test_v28_geometry_source_contract_is_exact_36_taxon_raw_only():
    c = json.loads(SOURCE.read_text())
    d = json.loads(DESIGN.read_text())
    r = pd.read_csv(REGISTRY)
    assert c['purpose'] == 'product_a_v2_8_geometry_calibration_raw_source_acquisition_contract'
    assert c['issue'] == 133
    assert c['predeclared_before_any_v2_8_geometry_source_outcome'] is True
    assert c['design_freeze']['merge_sha'] == 'c2d0b50dcd2ed88889491f23c1018f4d0c957a60'
    assert c['design_freeze']['contract_blob_sha'] == '6c3b74da06ac225ff6ef153761fd334ec1eb9d1c'
    assert c['design_freeze']['candidate_registry_blob_sha'] == 'ee43c9731eb8ad3673d2fa9271e0c3a8503bd0e0'
    assert hashlib.sha256(REGISTRY.read_bytes()).hexdigest() == c['design_freeze']['candidate_registry_sha256']
    assert len(r) == 36 and r['validation_stratum'].nunique() == 12
    assert c['snapshot']['date'] == '2026-08-01'
    assert c['snapshot']['doi'] == '10.15468/dl.fs3btq'
    assert c['parallel_transport']['chunk_count'] == 16
    assert c['calibration_corpus']['future_scientific_confirmation_reuse_allowed'] is False
    assert d['claim_boundary']['post_outcome_rescue_of_consumed_rank1_rank2_rank3_taxa'] is False
    for value in c['information_barrier'].values():
        assert value is False


def test_v28_geometry_source_execution_pins_exact_frozen_runtime():
    e = json.loads(EXECUTION.read_text())
    assert e['purpose'] == 'product_a_v2_8_geometry_calibration_raw_source_execution_authorization'
    assert e['implementation_sha'] == 'e33a883ff0829b2c6b621b77ac295151de647a58'
    assert e['frozen_ref'] == 'frozen/product-a-v2-8-geometry-source-e33a883f'
    assert e['workflow_blob_sha'] == 'ee221fa4efefd581def497b5fbc3becf936ea7e2'
    assert e['source_contract_blob_sha'] == 'd11b11567afa8899db53361365268d847cdf7108'
    assert e['design_contract_blob_sha'] == '6c3b74da06ac225ff6ef153761fd334ec1eb9d1c'
    assert e['candidate_registry_blob_sha'] == 'ee43c9731eb8ad3673d2fa9271e0c3a8503bd0e0'
    assert e['source_acquisition_only'] is True
    assert e['chunk_count'] == 16
    for key in ('geometry_calibration_execution_allowed', 'environmental_values_allowed', 'candidate_model_fitting_allowed', 'sealed_ecological_outcomes_allowed', 'scientific_confirmation_allowed', 'scientific_promotion_allowed', 'product_b_unblocked'):
        assert e[key] is False
    assert e['one_shot'] is True
    assert e['execution_allowed'] is True


def test_v28_geometry_source_workflow_stays_raw_only():
    text = WORKFLOW.read_text()
    assert 'authorization_commit_sha:' in text
    assert 'authorization_blob_sha:' in text
    assert '--taxa configs/product_a_v2_7_1_fresh_taxon_candidates.csv' in text
    assert '--exclude-taxa configs/product_a_v2_7_1_fresh_taxon_candidates.csv' in text
    assert 'product-a-v2-8-geometry-calibration-focal-source-2026-08-01' in text
    assert 'product-a-v2-8-geometry-calibration-target-source-2026-08-01' in text
    assert 'product-a-v2-8-geometry-calibration-raw-source-receipt' in text
    assert 'configs/chelsa_v2_1_plant_candidates.csv' not in text
    assert 'benchmark_recovery_procedures' not in text
    assert "'geometry_calibration_executed':False" in text
    assert "'scientific_confirmation_allowed':False" in text


def test_v28_geometry_source_launcher_is_one_shot_and_trigger_absent():
    text = LAUNCHER.read_text()
    assert "authorization_commit_sha=str(event['pull_request']['base']['sha'])" in text
    assert "if json.loads(base64.b64decode(base_auth['content']).decode())!=auth" in text
    assert "auth.get('execution_allowed') is not True" in text
    assert "verify_blob('.github/workflows/product-a-v2-8-geometry-calibration-source.yml',auth['workflow_blob_sha'])" in text
    assert "verify_blob('configs/product_a_v2_7_1_fresh_taxon_candidates.csv',auth['candidate_registry_blob_sha'])" in text
    assert 'multiple exact v2.8 source runs exist' in text
    assert "'geometry_calibration_execution_allowed':False" in text
    assert "'scientific_confirmation_allowed':False" in text
    assert not TRIGGER.exists()
