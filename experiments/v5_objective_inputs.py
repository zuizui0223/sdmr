#!/usr/bin/env python3
"""Export byte-verified first10 model-pool matrices; no model fitting/holdout read."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from v5_exact_input_parity import manual_inputs,FROZEN_HASHES
from v5_standardization_probe import bg_nearest_spatial_block

def digest(a):return hashlib.sha256(np.asarray(a).tobytes(order='C')).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();root=a.root;a.output.mkdir(parents=True,exist_ok=True)
    feature=root/'feature';pool=root/'pool/model_pool_freeze';occpath=root/'occurrence/model_pool_occurrences_v5.csv'
    paths={n:feature/n for n in ('location_features_v5.parquet','model_pool_feature_index_v5.csv','background_300km_feature_index_v5.csv')}
    paths['model_pool_occurrences_v5.csv']=occpath
    for name,path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==FROZEN_HASHES[name],name
    loc=pd.read_parquet(paths['location_features_v5.parquet'])
    mi=pd.read_csv(paths['model_pool_feature_index_v5.csv']);bi=pd.read_csv(paths['background_300km_feature_index_v5.csv'])
    occ=pd.read_csv(occpath);summary=pd.read_csv(pool/'taxon_model_freeze_summary.csv')
    spec=json.loads((root/'pool/taxon_parts/sdmr-fresh-v5-model-pool-taxon-1/taxon_model_freeze.json').read_text())
    cols=spec['predictor_sets']['full_46_flat_hgb']['predictors']
    reference=json.loads((root/'parity/exact_input_path_parity_first10.json').read_text())
    refs={r['scientific_name']:r for r in reference['rows']}
    taxa=summary.sort_values('selection_rank').scientific_name.astype(str).tolist()
    assert len(taxa)==50 and len(set(taxa))==50 and len(cols)==46
    manifest={'schema':'sdmr.v5.checked_objective_inputs.v1','original_v5_promotion':'failed_closed','sealed_answer_check_read':False,'model_fitting_performed':False,'reference_taxa':50,'exported_taxa':10,'rows':[]}
    for rank,taxon in enumerate(taxa[:10],1):
        x,y,g,_,_=manual_inputs(taxon,mi,bi,occ,loc,cols,bg_nearest_spatial_block)
        r=refs[taxon]
        for arr,key in ((x,'matrix'),(y,'labels'),(g,'groups')):
            assert digest(arr)==r[key]['a_sha256'],(taxon,key)
        splits=list(GroupKFold(n_splits=3).split(x,y,g));extra={}
        for fold,(tr,te) in enumerate(splits):
            for arr,key in ((x[tr],'train'),(x[te],'validation')):
                assert digest(arr)==r['fold_matrices'][fold][key]['a_sha256'],(taxon,fold,key)
            extra[f'train_{fold}']=tr;extra[f'test_{fold}']=te
        path=a.output/f'taxon_{rank:02d}.npz'
        np.savez_compressed(path,x=x,y=y,groups=g,predictors=np.asarray(cols),scientific_name=np.asarray(taxon),**extra)
        manifest['rows'].append({'selection_rank':rank,'scientific_name':taxon,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'x_sha256':digest(x),'y_sha256':digest(y),'groups_sha256':digest(g),'reference':r})
        print(rank,taxon,'exact feature/label/group/fold hashes match',flush=True)
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
