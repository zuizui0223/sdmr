import json
from pathlib import Path

CONTRACT=Path('configs/product_a_v2_7_2_determinism_probe_execution.json')
WORKFLOW=Path('.github/workflows/product-a-v2-7-2-determinism-probe.yml')
LAUNCHER=Path('.github/workflows/product-a-v2-7-2-determinism-probe-pr-launch.yml')
TRIGGER=Path('configs/product_a_v2_7_2_determinism_probe_pr_trigger.txt')


def test_probe_gate_is_closed_and_reference_is_predeclared():
    c=json.loads(CONTRACT.read_text())
    assert c['execution_allowed'] is False
    assert 'implementation_sha' not in c
    assert c['frozen_ref'] is None
    assert c['sha_resolution_policy']=='resolve_frozen_ref_tip_at_dispatch'
    assert c['repository_stored_self_referential_sha_allowed'] is False
    assert c['random_state']==271
    assert c['reference_case']=={
        'primary_run_id':32552745281,
        'seed':2026082201,
        'sealed_fraction':0.30,
        'taxon_index':10,
        'M':'buffer_150km',
        'selection_basis':'continuity_with_existing_transport_reference_not_scientific_metric_outcome',
    }
    assert c['replicas']==2
    assert c['exact_artifact_identity_required'] is True
    assert c['sealed_environment_read_allowed'] is False
    assert c['product_b_unblocked'] is False


def test_probe_requires_two_independent_exact_outputs_and_fixed_seed():
    text=WORKFLOW.read_text()
    assert 'replica: [a, b]' in text
    assert "SDMR_LOGISTIC_RANDOM_STATE: '271'" in text
    assert 'v271-fresh-part-2026082201-0.30' in text
    assert '--M buffer_150km' in text
    assert "raise SystemExit(f'determinism probe mismatch: {rel}')" in text
    assert "'all_files_byte_identical':True" in text
    assert "'sealed_environment_read':False" in text


def test_probe_launcher_resolves_frozen_ref_once_and_trigger_is_absent():
    text=LAUNCHER.read_text()
    assert 'product_a_v2_7_2_determinism_probe_pr_trigger.txt' in text
    assert 'multiple exact deterministic probe runs exist' in text
    assert "quote(c['frozen_ref'],safe='')" in text
    assert "resolved_sha=str(branch.get('commit',{}).get('sha',''))" in text
    assert "'expected_sha':resolved_sha" in text
    assert "'expected_ref':c['frozen_ref']" in text
    assert "'implementation_sha':resolved_sha" in text
    assert "c['implementation_sha']" not in text
    assert "'product_b_unblocked':False" in text
    assert not TRIGGER.exists()
