import hashlib,sys,json
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'experiments'))
from nonlinear_effort_aggregate_v2 import verify_pair_consensus, verify_receipt_hash


def test_pair_consensus_detects_tampered_case_after_hash():
    finite={'spatial':{'unavailable':{
        'shallow3_hgb':{'states':[{'process':'thermal','state':'contributory'},
                                    {'process':'water','state':'replaceable'}],
                        'authorization':{'authorized':True}},
        'random_forest_leaf7':{'states':[{'process':'thermal','state':'contributory'},
                                         {'process':'water','state':'required'}],
                               'authorization':{'authorized':True}},
    }}}
    case={'consensus':{'spatial':{'unavailable':{'nonlinear_pair':{'thermal':'contributory','water':'unresolved'}}}},
          'authorizations':{'spatial':{'unavailable':{'nonlinear_pair':True}}}}
    verify_pair_consensus(finite,case,{'nonlinear_pair':['shallow3_hgb','random_forest_leaf7']},
         ('thermal','water'))
    case['consensus']['spatial']['unavailable']['nonlinear_pair']['water']='required'
    with pytest.raises(ValueError,match='consensus'):
        verify_pair_consensus(finite,case,{'nonlinear_pair':['shallow3_hgb','random_forest_leaf7']},
             ('thermal','water'))


def test_sha256_receipt_is_verified_before_case_use(tmp_path):
    f=tmp_path/'preoracle.json'
    f.write_bytes(b'{"seed":1}\n')
    correct=hashlib.sha256(f.read_bytes()).hexdigest()
    verify_receipt_hash(f,correct)
    with pytest.raises(ValueError,match='receipt'):
        verify_receipt_hash(f,'0'*64)
