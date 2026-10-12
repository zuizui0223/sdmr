from pathlib import Path
import sys,json,hashlib
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'))
from matched_kt_aggregate_v1 import summarize


def test_aggregate_refuses_to_open_reference_without_finite_receipt(tmp_path):
    c={'seeds':[9],'worlds':['toy'],
       'finite':{'split_modes':['random_cell','spatial'],'learners':['standardized_isotropic_l2','shallow3_hgb']},
       'denominators':{'world_seed_cases':1,'oracle_targets':2,
                       'consensus_cells_per_split':2,'processes_per_case':2,'finite_fits':84}}
    folder=tmp_path/'parts'/'toy-9';folder.mkdir(parents=True)
    (folder/'case.json').write_text(json.dumps({'seed':9,'world':'toy','finite_receipt_sha256':'incorrect'}))
    (folder/'finite_frozen_before_oracle.json').write_text(json.dumps({'seed':9,'world':'toy'}))
    with pytest.raises(ValueError,match='receipt digest mismatch'):
        summarize(tmp_path/'parts',c,tmp_path/'out.json')


def test_finite_receipt_cannot_be_relabelled_as_prospective(tmp_path):
    """A case file cannot turn burned finite fits into a claimed sealed run."""
    folder=tmp_path/'parts'/'toy-9';folder.mkdir(parents=True)
    processes=['thermal','water','seasonality','radiation_energy','soil_substrate','productivity']
    finite={'seed':9,'world':'toy','status':'finite_frozen_before_reference_opening',
            'reference_truth_read_by_learner':False,'prospective':False,
            'finite':{mode:{learner:{'states':[{'process':p} for p in processes],
                                       'all_fold_records':21}
                           for learner in ['standardized_isotropic_l2','shallow3_hgb']}
                       for mode in ['random_cell','spatial']}}
    receipt=folder/'finite_frozen_before_oracle.json'
    receipt.write_text(json.dumps(finite))
    case={'seed':9,'world':'toy','status':'completed_all_declared_states',
          'prospective':True,'original_v5_promotion':'failed_closed',
          'M5_original_evidence_changed':False,
          'finite_receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),
          'oracle':{p:'replaceable' for p in processes},
          'consensus':{mode:{p:'replaceable' for p in processes} for mode in ['random_cell','spatial']},
          'authorization':{mode:True for mode in ['random_cell','spatial']},
          'per_learner_authorization':{mode:{learner:True for learner in ['standardized_isotropic_l2','shallow3_hgb']} for mode in ['random_cell','spatial']}}
    (folder/'case.json').write_text(json.dumps(case))
    cfg={'seeds':[9],'worlds':['toy'],
         'finite':{'split_modes':['random_cell','spatial'],'learners':['standardized_isotropic_l2','shallow3_hgb']},
         'denominators':{'world_seed_cases':1,'oracle_targets':6,
                         'consensus_cells_per_split':6,'processes_per_case':6,'finite_fits':84}}
    with pytest.raises(ValueError,match='prospective flag'):
        summarize(tmp_path/'parts',cfg,tmp_path/'out.json')
    # A fully consistent fixture, with an independently hashed finite receipt,
    # must follow the successful aggregation path without changing any states.
    finite['prospective']=True
    receipt.write_text(json.dumps(finite))
    case['finite_receipt_sha256']=hashlib.sha256(receipt.read_bytes()).hexdigest()
    (folder/'case.json').write_text(json.dumps(case))
    out=summarize(tmp_path/'parts',cfg,tmp_path/'out.json')
    assert out['summary']['paired_world_seed_cases']==1
    assert out['summary']['random_cell']['stable_sharp']==6
    assert out['declared_fit_count']==84
