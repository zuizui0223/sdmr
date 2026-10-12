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
