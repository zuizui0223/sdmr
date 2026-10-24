"""Source-hash-pinned, no-refit synthesis of a NEW FIA measured-year × stand-age audit.

Only the archived three-state aggregate is read. Statistical analyses must not
interpret 13 taxa, shared strata, plots, or trees as independent experiments.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_INPUT_SHA256='60de80f5b41a8eed94d13032a8176b857bc509017ace99ffa3ba4815cc2c8016'
STATES=('RI','VA','WI')
EXPECTED_CODES=('68','129','261','316','318','371','531','541','743','762','802','833','837')
EXPECTED_SOURCE_PLOT_COND_SHA='a0750b945cab7db53238827ffecce0d499d84ed9415a139561df35079eacb666'


def _m(r,st,year='measyear'):
    v=r['by_state'][st][year]
    return None if v is None else float(v)


def stratum_summary(states,codes,names,min_n):
    index={s['state']:{x['spcd']:x for x in s['species']} for s in states}
    summaries=[];nstrata=0;npos=0
    for sp in codes:
        bars=[]
        c=index['RI'][sp]['size_age_strata']
        for k in c:
            rr=[index[st][sp]['size_age_strata'][k] for st in STATES]
            if min(x['n'] for x in rr)<min_n:continue
            bars.append((k,sum(x['n'] for x in rr),[x['mean_measyear_normalized'] for x in rr],
                         [x['mean_invyr_normalized_same_pairs'] for x in rr]))
        nstrata+=len(bars)
        npos+=sum(vals[2]>vals[0] for _,_,vals,_ in bars)
        den=sum(w for _,w,_,_ in bars)
        data={}
        for ix,st in enumerate(STATES):
            data[st]={
                'measyear':sum(w*vv[ix] for _,w,vv,_ in bars)/den if den else None,
                'invyr_same_pairs':sum(w*vv[ix] for _,w,_,vv in bars)/den if den else None
            }
        observed=(data['RI']['measyear'] is not None)
        signed= bool(data['WI']['measyear']>data['RI']['measyear']) if observed else None
        previously=bool(data['WI']['invyr_same_pairs']>data['RI']['invyr_same_pairs']) if observed else None
        summaries.append({'species_code':sp,'species':names[sp],
                          'common_strata':len(bars),'matched_pair_count_in_pool':den,
                          'all_strata_WI_above_RI':all(vals[2]>vals[0] for _,_,vals,_ in bars) if observed else None,
                          'n_strata_WI_above_RI':sum(vals[2]>vals[0] for _,_,vals,_ in bars),
                          'measured_rate_WI_above_RI':signed,
                          'inventory_year_rate_WI_above_RI':previously,
                          'size_age_standardized_rates':data})
    eligible=[x for x in summaries if x['common_strata']>0]
    return {'min_n_per_species_stratum_each_state':min_n,
            'n_estimable_species':len(eligible),
            'n_species_WI_growth_higher':sum(x['measured_rate_WI_above_RI'] for x in eligible),
            'n_species_with_RI_lt_VA_lt_WI':sum(x['size_age_standardized_rates']['RI']['measyear']<x['size_age_standardized_rates']['VA']['measyear']<x['size_age_standardized_rates']['WI']['measyear'] for x in eligible),
            'n_species_all_matched_strata_WI_higher':sum(x['all_strata_WI_above_RI'] for x in eligible),
            'n_matched_strata':nstrata,'n_matched_strata_WI_higher':npos,
            'n_species_direction_switch_after_real_measyear':sum(x['measured_rate_WI_above_RI']!=x['inventory_year_rate_WI_above_RI'] for x in eligible),
            'species':summaries}


def inspect(source_json:dict, *, byte_sha:str):
    if byte_sha!=EXPECTED_INPUT_SHA256:
        raise ValueError('archived first-open source aggregate fingerprint mismatch')
    if source_json.get('study')!='fia_new_source_measyear_stand_context_v1':raise ValueError('invalid science lineage')
    if source_json.get('plot_cond_source_receipt_sha256')!=EXPECTED_SOURCE_PLOT_COND_SHA:raise ValueError('PLOT/COND source drift')
    if not source_json.get('not_equivalent_to_prior_308181_survivor_growth_pairs'):raise ValueError('historical-data conflation')
    state_rows=source_json['states']
    if [s['state'] for s in state_rows]!=list(STATES):raise ValueError('state panel altered')
    names=source_json['names']
    if set(names)!=set(EXPECTED_CODES):raise ValueError('species cohort altered')
    for st in state_rows:
        if set(x['spcd'] for x in st['species'])!=set(EXPECTED_CODES):raise ValueError('missing or extra taxon')
        if len(st['species'])!=13:raise ValueError('duplicate species')
        if st['tree_new_source']['status']!='ready':raise ValueError('source tree missing')
        if len(st['tree_new_source']['sha256'])!=64:raise ValueError('tree source hash missing')
    summ={str(q):stratum_summary(state_rows,EXPECTED_CODES,names,q) for q in (10,20,30,50,100)}
    orig=source_json['cross_state_size_stand_age_standardization']
    for row in orig:
        mine=next(x for x in summ['10']['species'] if x['species_code']==row['spcd'])
        if mine['common_strata']!=row['n_shared_size_age_strata'] or mine['matched_pair_count_in_pool']!=row['n_observed_pairs_in_common_strata']:
            raise ValueError('first-open shared-stratum denominator mismatch')
        for st in STATES:
            for k in ('measyear','invyr_same_pairs'):
                new=mine['size_age_standardized_rates'][st][k]
                old=row['by_state'][st][k]
                if (new is None) != (old is None) or (new is not None and abs(new-old)>1e-12):
                    raise ValueError('source-rate reproducibility mismatch')
    n_by={x['state']:sum(z['n_growth_pairs'] for z in x['species']) for x in state_rows}
    natural={x['state']:sum(z['n_natural_stand_age_pairs'] for z in x['species']) for x in state_rows}
    mismatch={x['state']:sum(z['counters'].get('inventory_vs_measurement_interval_different',0) for z in x['species']) for x in state_rows}
    return {'study':'fia_stand_context_archived_recalculation_v1','source_aggregate_sha256':byte_sha,
            'states':list(STATES),'n_species':13,'measurement_pairs_by_state':n_by,
            'n_total_measurement_pairs':sum(n_by.values()),
            'n_natural_stand_age_pairs_by_state':natural,'n_total_natural_stand_age_pairs':sum(natural.values()),
            'source_tree_sha_by_state':{s['state']:s['tree_new_source']['sha256'] for s in state_rows},
            'difference_gt_0p01_year_between_inventory_and_measurement_pair_intervals':mismatch,
            'contrast_primary_min_n10':summ['10'],
            'post_result_threshold_sensitivity':{s:{k:v for k,v in z.items() if k!='species'} for s,z in summ.items() if s!='10'},
            'no_plot_cluster_standard_errors':True,
            'no_population_sampling_weights':True,
            'no_species_physiological_climate_or_niche_evolution_inference':True,
            'outcome_opened_exploratory':True,
            'scientific_interpretation':'A size-and-stand-age conditional regional increment pattern in repeat-observed surviving trees, not climatic niche adaptation'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    data=a.input.read_bytes()
    result=inspect(json.loads(data),byte_sha=hashlib.sha256(data).hexdigest())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    primary=result['contrast_primary_min_n10']
    print('new source same-tree pairs',result['n_total_measurement_pairs'],
          'growth WI>RI',primary['n_species_WI_growth_higher'],'/',primary['n_estimable_species'],
          'common strata positive',primary['n_matched_strata_WI_higher'],'/',primary['n_matched_strata'])

if __name__=='__main__':main()
