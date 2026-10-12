#!/usr/bin/env python3
"""Post-terminal audit of the original v5 input-construction path.

Identical HGB scores are not a substitute for direct input-matrix equality.
This script imports the byte-pinned original loader and compares its matrices,
spatial groups, fold indices and full-system scores with the PR-278 replay.
No sealed answer-check is read; no existing scientific endpoint is altered.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd

ORIGINAL_COMMIT='bf0d76d615d649adad4c4df6f21b5411f9ac3bfd'
ORIGINAL_BLOB='452f90508dd265c223731c2a9f5bc070cb89e6a1'
FROZEN_HASHES={
    'location_features_v5.parquet':'705f4e8d5db87eb60061258dc1e5d936be988e7b9ced45f936a866d7e8f015c5',
    'model_pool_feature_index_v5.csv':'fa33b8ccc6ded3f12ce34b58370c83b1d66857e795cebafa678789f7f317471b',
    'background_300km_feature_index_v5.csv':'6caba416d9aefc7345994eb97568b8f24d5565c7ad6fca906de58821e88049f0',
    'model_pool_occurrences_v5.csv':'5abd582c3c03b99f58263c720f76e04d08c54250daef942b06ae854fd721c624',
    'selected_fresh_taxa_v5.csv':'fb845485a1415c1fe3c2366d44834b194fe8b7a183718bd5cd69123f6ad79e27',
    'full_system_authorization_all_taxa.csv':'8ce83beaefb6aa1f9996452e0835a0e9531386e26180db4760bf3847535cd475',
}

def compare_arrays(a, b) -> dict:
    a=np.asarray(a); b=np.asarray(b)
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('matrix comparison requires finite values')
    shape=a.shape==b.shape
    result={'a_shape':list(a.shape),'b_shape':list(b.shape),'same_shape':shape,
            'a_dtype':str(a.dtype),'b_dtype':str(b.dtype),
            'a_c_contiguous':bool(a.flags.c_contiguous),'b_c_contiguous':bool(b.flags.c_contiguous),
            'a_f_contiguous':bool(a.flags.f_contiguous),'b_f_contiguous':bool(b.flags.f_contiguous),
            'a_sha256':hashlib.sha256(a.tobytes(order='C')).hexdigest(),
            'b_sha256':hashlib.sha256(b.tobytes(order='C')).hexdigest()}
    result['same_bytes']=shape and a.dtype==b.dtype and result['a_sha256']==result['b_sha256']
    result['same_values']=bool(shape and np.array_equal(a,b))
    result['changed_entries']=int(np.count_nonzero(a!=b)) if shape else None
    result['max_absolute_difference']=float(np.max(np.abs(a.astype(float)-b.astype(float)))) if shape and a.size else None
    return result

def load_original_module(path: Path):
    raw=path.read_bytes()
    digest=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()
    if digest!=ORIGINAL_BLOB:
        raise ValueError('original v5 source blob differs from frozen execution')
    spec=importlib.util.spec_from_file_location('frozen_v5_model_pool',path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def manual_inputs(taxon, mi, bi, occurrence, locations, predictors, nearest):
    o=mi.loc[(mi.scientific_name==taxon)&mi.complete_case].copy()
    all_occ=occurrence.loc[occurrence.scientific_name==taxon,
        ['occurrence_id','longitude','latitude','spatial_block']].copy()
    o=o.merge(all_occ[['occurrence_id','spatial_block']],on='occurrence_id',how='left',validate='one_to_one')
    b=bi.loc[(bi.scientific_name==taxon)&bi.complete_case&(bi.background_rank.mod(5)!=0)].copy()
    b['spatial_block']=nearest(all_occ,b)
    cols=['location_id',*predictors]
    o=o.merge(locations[cols],on='location_id',how='left',validate='many_to_one')
    b=b.merge(locations[cols],on='location_id',how='left',validate='many_to_one')
    x=np.vstack([o[list(predictors)].to_numpy(dtype=float),b[list(predictors)].to_numpy(dtype=float)])
    y=np.r_[np.ones(len(o),dtype=int),np.zeros(len(b),dtype=int)]
    groups=np.r_[o.spatial_block.to_numpy(dtype=int),b.spatial_block.to_numpy(dtype=int)]
    return x,y,groups,o,b

def run(args):
    from sklearn.model_selection import GroupKFold
    from sklearn.exceptions import ConvergenceWarning
    from sdmr.process_id.known_truth.permutation_gate import _sample_and_groups
    import v5_standardization_probe as probe
    import sklearn, scipy
    if args.taxon_limit!=10:
        raise ValueError('audit cohort must be the first ten frozen selection ranks')
    paths={n:args.feature_root/n for n in ('location_features_v5.parquet','model_pool_feature_index_v5.csv','background_300km_feature_index_v5.csv')}
    paths.update({'model_pool_occurrences_v5.csv':args.occurrence,
                  'selected_fresh_taxa_v5.csv':args.selected,
                  'full_system_authorization_all_taxa.csv':args.pool_root/'full_system_authorization_all_taxa.csv'})
    for name,path in paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=FROZEN_HASHES[name]:
            raise ValueError('frozen input hash mismatch: '+name)
    original=load_original_module(args.original_source)
    selected,loc,mi,bi,predictors,registry=original._load_feature_bundle(
        feature_root=args.feature_root,selected_path=args.selected,process_registry_path=args.registry)
    attached=original.attach_occurrence_spatial_blocks(mi,occurrence_model_pool_path=args.occurrence)
    occurrence=pd.read_csv(args.occurrence)
    auth=pd.read_csv(args.pool_root/'full_system_authorization_all_taxa.csv')
    taxa=selected.sort_values('selection_rank').scientific_name.astype(str).tolist()
    if len(taxa)!=50 or len(set(taxa))!=50: raise ValueError('invalid frozen cohort')
    report={'schema':'sdmr.v5.exact_input_path_parity.v1','status':'postterminal_diagnostic_only',
        'original_commit':ORIGINAL_COMMIT,'original_blob':ORIGINAL_BLOB,'taxon_limit':10,
        'original_taxon_denominator':50,'original_v5_promotion':'failed_closed',
        'sealed_answer_check_read':False,'causal_scaling_effect_established':False,
        'versions':{'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,
                    'scipy':scipy.__version__,'sklearn':sklearn.__version__},'rows':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for taxon in taxa[:10]:
        model,bg=original._taxon_training_tables(taxon=taxon,locations=loc,
            model_index=attached,background_index=bi,predictors=predictors)
        world=original._empirical_world(taxon=taxon,model=model,background=bg,
            predictors=predictors,registry=registry)
        sample,groups=_sample_and_groups(world)
        x=sample.loc[:,list(predictors)].apply(pd.to_numeric,errors='coerce').to_numpy(float)
        y=sample.label.to_numpy(int)
        mx,my,mg,mo,mb=manual_inputs(taxon,mi,bi,occurrence,loc,predictors,probe.bg_nearest_spatial_block)
        splits=list(GroupKFold(n_splits=3).split(x,y,groups))
        msplits=list(GroupKFold(n_splits=3).split(mx,my,mg))
        row={'scientific_name':taxon,'matrix':compare_arrays(x,mx),
             'labels':compare_arrays(y,my),'groups':compare_arrays(groups,mg),
             'same_occurrence_row_order':model.occurrence_id.astype(str).tolist()==mo.occurrence_id.astype(str).tolist(),
             'same_background_row_order':bg.background_rank.tolist()==mb.background_rank.tolist(),
             'same_folds':all(np.array_equal(a,c) and np.array_equal(b,d) for (a,b),(c,d) in zip(splits,msplits)),
             'original_column_dtypes':sample[list(predictors)].dtypes.astype(str).to_dict(),
             'fold_matrices':[]}
        for (tr,te),(mtr,mte) in zip(splits,msplits):
            tx=sample.iloc[tr].reset_index(drop=True).loc[:,list(predictors)].apply(pd.to_numeric,errors='coerce').to_numpy(float)
            vx=sample.iloc[te].reset_index(drop=True).loc[:,list(predictors)].apply(pd.to_numeric,errors='coerce').to_numpy(float)
            row['fold_matrices'].append({'train':compare_arrays(tx,mx[mtr]),'validation':compare_arrays(vx,mx[mte])})
        for learner,alias in [('linear','penalized_logistic'),('hgb','shallow3_hgb')]:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter('always',ConvergenceWarning)
                evaluation=original.evaluate_full_system_permutation_gate(world,n_splits=3,split_mode='spatial',
                    learner=learner,hgb_profile='current' if learner=='linear' else 'shallow3',C=1.,
                    adequacy_floor=-.75,n_permutations=999,alpha=.001,permutation_seed=0,minimum_gain_over_null=.01)
            archived=auth.loc[(auth.scientific_name==taxon)&(auth.learner_route==alias)]
            if len(archived)!=1: raise ValueError('missing or duplicate archived score')
            baseline=float(archived.observed_mean_score.iloc[0])
            now=float(evaluation.summary['observed_mean_score'])
            row[alias]={'archived_score':baseline,'original_pipeline_replay_score':now,
                        'absolute_error':abs(now-baseline),'authorized':bool(evaluation.summary['authorized']),
                        'convergence_warnings':sum(issubclass(w.category,ConvergenceWarning) for w in captured)}
        report['rows'].append(row)
        args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        print(taxon,'input_equal=',row['matrix']['same_values'],'raw_archive_error=',row['penalized_logistic']['absolute_error'],
              'HGB_archive_error=',row['shallow3_hgb']['absolute_error'],flush=True)
    report['summary']={
        'all_input_values_equal':all(r['matrix']['same_values'] for r in report['rows']),
        'all_labels_groups_and_folds_equal':all(r['labels']['same_values'] and r['groups']['same_values'] and r['same_folds'] for r in report['rows']),
        'logistic_original_pipeline_matched_taxa':sum(r['penalized_logistic']['absolute_error']<=.001 for r in report['rows']),
        'hgb_original_pipeline_matched_taxa':sum(r['shallow3_hgb']['absolute_error']<=.001 for r in report['rows']),
        'logistic_maximum_error':max(r['penalized_logistic']['absolute_error'] for r in report['rows']),
        'hgb_maximum_error':max(r['shallow3_hgb']['absolute_error'] for r in report['rows']),
    }
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report['summary'],indent=2))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--feature-root',type=Path,required=True)
    p.add_argument('--occurrence',type=Path,required=True)
    p.add_argument('--pool-root',type=Path,required=True)
    p.add_argument('--selected',type=Path,required=True)
    p.add_argument('--registry',type=Path,required=True)
    p.add_argument('--original-source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--taxon-limit',type=int,default=10)
    run(p.parse_args())
if __name__=='__main__':main()
