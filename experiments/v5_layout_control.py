#!/usr/bin/env python3
"""Controlled array-layout audit, not an empirical promotion or tuning run."""
from __future__ import annotations
import argparse
import hashlib
import json
import warnings
from pathlib import Path
import numpy as np

def layout_scores(x, y, splits):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.exceptions import ConvergenceWarning
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=int)
    if not np.isfinite(x).all(): raise ValueError('finite inputs required')
    result={route:{order:{'fold_scores':[],'iterations':[],'warning_folds':0,
             'training_c_contiguous':[],'address_mod64':[]} for order in ('C','F')}
             for route in ('raw','scaled')}
    largest={'raw':0.,'scaled':0.};same=True
    for train,test in splits:
        tx=np.array(x[train],order='C',copy=True)
        vx=np.array(x[test],order='C',copy=True)
        ty=np.array(y[train],copy=True);vy=np.array(y[test],copy=True)
        scaler=StandardScaler().fit(tx)
        variants={'raw':(tx,vx),'scaled':(scaler.transform(tx),scaler.transform(vx))}
        for route,(training,validation) in variants.items():
            predictions={}
            left=np.array(training,order='C',copy=True)
            right=np.array(training,order='F',copy=True)
            same=same and np.array_equal(left,right)
            for order,features in (('C',left),('F',right)):
                model=LogisticRegression(C=1.,penalty='l2',solver='lbfgs',max_iter=1000,
                                         random_state=0,class_weight='balanced')
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always',ConvergenceWarning)
                    model.fit(features,ty)
                p=model.predict_proba(np.array(validation,order='C',copy=True))[:,1]
                predictions[order]=p
                p=np.clip(p,1e-9,1.-1e-9)
                score=.5*(np.log(p[vy==1]).mean()+np.log1p(-p[vy==0]).mean())
                out=result[route][order]
                out['fold_scores'].append(float(score))
                out['iterations'].append(int(model.n_iter_[0]))
                out['warning_folds']+=sum(issubclass(w.category,ConvergenceWarning) for w in caught)
                out['training_c_contiguous'].append(bool(features.flags.c_contiguous))
                out['address_mod64'].append(int(features.ctypes.data%64))
            largest[route]=max(largest[route],float(np.max(np.abs(predictions['C']-predictions['F']))))
    for route in ('raw','scaled'):
        for order in ('C','F'):
            result[route][order]['mean_score']=float(np.mean(result[route][order]['fold_scores']))
    result.update(same_training_values_all_folds=bool(same),
                  maximum_raw_probability_difference=largest['raw'],
                  maximum_scaled_probability_difference=largest['scaled'],
                  scaler_fitted_once_per_training_fold=True)
    return result

def main():
    from sklearn.model_selection import GroupKFold
    from sdmr.process_id.known_truth.permutation_gate import _sample_and_groups
    import pandas as pd
    import v5_exact_input_parity as audit
    p=argparse.ArgumentParser()
    p.add_argument('--feature-root',type=Path,required=True)
    p.add_argument('--occurrence',type=Path,required=True)
    p.add_argument('--pool-root',type=Path,required=True)
    p.add_argument('--selected',type=Path,required=True)
    p.add_argument('--registry',type=Path,required=True)
    p.add_argument('--original-source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    paths={n:a.feature_root/n for n in ('location_features_v5.parquet','model_pool_feature_index_v5.csv','background_300km_feature_index_v5.csv')}
    paths.update({'model_pool_occurrences_v5.csv':a.occurrence,'selected_fresh_taxa_v5.csv':a.selected,
                  'full_system_authorization_all_taxa.csv':a.pool_root/'full_system_authorization_all_taxa.csv'})
    for name,path in paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=audit.FROZEN_HASHES[name]:
            raise ValueError('frozen input hash mismatch: '+name)
    original=audit.load_original_module(a.original_source)
    selected,loc,mi,bi,predictors,registry=original._load_feature_bundle(
        feature_root=a.feature_root,selected_path=a.selected,process_registry_path=a.registry)
    mi=original.attach_occurrence_spatial_blocks(mi,occurrence_model_pool_path=a.occurrence)
    taxa=selected.sort_values('selection_rank').scientific_name.astype(str).tolist()
    report={'schema':'sdmr.v5.controlled_array_layout.v1','status':'postterminal_diagnostic_only',
            'original_v5_promotion':'failed_closed','sealed_answer_check_read':False,
            'taxon_limit':10,'original_taxon_denominator':50,
            'causal_scaling_effect_established':False,'rows':[]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    for taxon in taxa[:10]:
        model,bg=original._taxon_training_tables(taxon=taxon,locations=loc,
            model_index=mi,background_index=bi,predictors=predictors)
        world=original._empirical_world(taxon=taxon,model=model,background=bg,
            predictors=predictors,registry=registry)
        sample,groups=_sample_and_groups(world)
        x=sample[list(predictors)].apply(pd.to_numeric,errors='coerce').to_numpy(float)
        y=sample.label.to_numpy(int)
        splits=list(GroupKFold(n_splits=3).split(x,y,groups))
        row=layout_scores(x,y,splits);row['scientific_name']=taxon
        report['rows'].append(row)
        a.output.write_text(json.dumps(report,indent=2)+'\n')
        print(taxon,'raw C-F prob difference',row['maximum_raw_probability_difference'],
              'scaled C-F prob difference',row['maximum_scaled_probability_difference'],flush=True)
    report['summary']={
        'all_training_values_identical':all(r['same_training_values_all_folds'] for r in report['rows']),
        'raw_layout_sensitive_taxa_above_1e_8':sum(r['maximum_raw_probability_difference']>1e-8 for r in report['rows']),
        'scaled_layout_sensitive_taxa_above_1e_8':sum(r['maximum_scaled_probability_difference']>1e-8 for r in report['rows']),
        'maximum_raw_probability_difference':max(r['maximum_raw_probability_difference'] for r in report['rows']),
        'maximum_scaled_probability_difference':max(r['maximum_scaled_probability_difference'] for r in report['rows']),
    }
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2))
if __name__=='__main__':main()
