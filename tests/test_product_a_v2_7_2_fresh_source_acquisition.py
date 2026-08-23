import json
from pathlib import Path

CONTRACT = Path('configs/product_a_v2_7_2_fresh_source_acquisition_contract.json')
WORKFLOW = Path('.github/workflows/product-a-v2-7-2-fresh-source-acquisition.yml')


def test_rank2_source_acquisition_is_source_only_and_not_yet_executable():
    c=json.loads(CONTRACT.read_text())
    assert c['purpose']=='product_a_v2_7_2_fresh_taxon_holdout_raw_source_acquisition_contract'
    assert c['predeclared_before_new_rank2_raw_source_outcome'] is True
    assert c['execution_source_pinned'] is False
    assert c['execution_allowed_before_exact_source_pin'] is False
    assert c['fresh_taxon_panel']['predeclared_rank']==2
    assert c['fresh_taxon_panel']['sha256']=='918ea2d3e94f93c26616ab30aa055a5dd72b4550d75dbbeb6a675e7a4e950f44'
    assert c['parallel_transport']['chunk_count']==16
    assert c['focal_source']['v2_7_1_rank1_focal_artifact_reused'] is False
    assert c['target_group_source']['v2_7_1_rank1_target_artifact_reused'] is False
    barrier=c['information_barrier']
    assert all(value is False for value in barrier.values())


def test_rank2_source_workflow_uses_only_new_panel_and_new_artifact_names():
    text=WORKFLOW.read_text()
    assert 'configs/product_a_v2_7_2_fresh_confirmation_taxa.csv' in text
    assert 'product-a-v2-7-2-fresh-focal-source-2026-08-01' in text
    assert 'product-a-v2-7-2-fresh-target-source-2026-08-01' in text
    assert 'product-a-v2-7-2-fresh-raw-source-receipt' in text
    assert 'product_a_v2_7_1_fresh_confirmation_taxa.csv' not in text
    assert 'product-a-v2-7-1-fresh-focal-source-2026-08-01' not in text
    assert 'product-a-v2-7-1-fresh-target-source-2026-08-01' not in text
    assert 'workflow_dispatch:' in text
    assert 'pull_request:' not in text
