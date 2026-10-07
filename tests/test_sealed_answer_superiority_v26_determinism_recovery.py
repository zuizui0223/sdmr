import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'configs'/'sealed_answer_superiority_v26_determinism_recovery.json'
W=ROOT/'.github'/'workflows'/'sealed-answer-superiority-v26-determinism-recovery.yml'

def test_recovery_is_truth_blind_and_scientifically_unchanged():
    c=json.loads(C.read_text())
    assert c['predecessor']['truth_opened'] is False
    assert c['scientific_contract']['thresholds_changed'] is False
    assert c['scientific_contract']['model_specs_changed'] is False
    assert c['scientific_contract']['support_logic_changed'] is False
    assert c['scientific_contract']['truth_labels_accessed'] is False
    assert c['execution']['truth_blind_only'] is True
    assert c['execution']['terminal_truth_job_present'] is False
    assert c['execution']['exact_receipt_hash_match_required'] is True

def test_recovery_changes_only_runtime_determinism_controls():
    c=json.loads(C.read_text())
    assert c['only_change']['type']=='runtime_determinism_control'
    assert c['only_change']['environment'] == {
      'OMP_NUM_THREADS':'1',
      'OPENBLAS_NUM_THREADS':'1',
      'MKL_NUM_THREADS':'1',
      'NUMEXPR_NUM_THREADS':'1',
      'VECLIB_MAXIMUM_THREADS':'1',
      'PYTHONHASHSEED':'0',
    }

def test_workflow_has_no_terminal_truth_job_and_sets_single_thread_env():
    text=W.read_text()
    assert '\n  terminal:' not in text
    assert 'sealed_answer_superiority_v26_terminal' not in text
    assert "OMP_NUM_THREADS: '1'" in text
    assert "OPENBLAS_NUM_THREADS: '1'" in text
    assert "MKL_NUM_THREADS: '1'" in text
    assert "NUMEXPR_NUM_THREADS: '1'" in text
    assert "VECLIB_MAXIMUM_THREADS: '1'" in text
    assert "PYTHONHASHSEED: '0'" in text
