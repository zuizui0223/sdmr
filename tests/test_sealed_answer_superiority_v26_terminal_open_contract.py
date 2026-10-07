import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'configs'/'sealed_answer_superiority_v26_terminal_open_contract.json'
W=ROOT/'.github'/'workflows'/'sealed-answer-superiority-v26-terminal-open.yml'

def test_terminal_contract_preserves_denominator_and_gate():
    c=json.loads(C.read_text())
    assert c['status']=='staged_unexecutable_until_truth_blind_recovery_pass_is_pinned'
    assert c['fresh_truth_denominator']['contexts']==960
    assert c['fresh_truth_denominator']['seeds']==list(range(20001,20021))
    assert c['fresh_truth_denominator']['replacement_allowed'] is False
    assert c['terminal_gate']=={
      'max_removed_true_members':0,
      'max_contexts_with_true_member_deletion':0,
      'min_removed_false_members':1,
      'all_reported_removals_must_be_qualified':True,
    }

def test_terminal_requires_exact_truth_blind_recovery_pass():
    c=json.loads(C.read_text())
    r=c['required_recovery']
    assert r['deterministic_match'] is True
    assert r['truth_open_authorized'] is True
    assert r['truth_opened'] is False
    assert r['mismatched_fields']==[]
    assert r['exact_recovery_run_must_be_pinned'] is True
    assert r['exact_artifact_ids_and_digests_must_be_pinned'] is True

def test_workflow_is_inert_without_future_lock():
    text=W.read_text()
    assert "configs/sealed_answer_superiority_v26_terminal_open_execute.lock" in text
    assert "configs/sealed_answer_superiority_v26_terminal_open_execution.json" in text
    assert 'sealed_answer_superiority_v26_terminal' in text
    assert 'workflow_dispatch:' not in text
