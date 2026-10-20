"""New-source FIA competition/moisture-site context audit, exploratory ONLY.

Pin 3 TREE + 6 PLOT/COND archive hashes to independently opened stage. Using
identical 13 species and plots, compare growth in matched stand basal-area classes
and xeric/mesic physiographic classes. No causal soil-water or climate claim.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
import math
import sqlite3
import tempfile
from zipfile import ZipFile
import importlib.util

HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('join_v1',HERE/'fia_tree_plot_condition_join_v1.py')
join=importlib.util.module_from_spec(s);s.loader.exec_module(join)
STATES=join.STATES
DENSITIES=(('0-<60',0,60),('60-<120',60,120),('120+',120,float('inf')))
PHYS_CLASSES=('xeric','mesic','hydric')


def physiographic(raw):
    try:v=int(str(raw).strip())
    except (ValueError,TypeError):return None
    if 11<=v<=19:return 'xeric'
    if 21<=v<=29:return 'mesic'
    if 31<=v<=39:return 'hydric'
    return None


def parse_context(path,member):
    out={}
    with ZipFile(path) as z,z.open(member) as raw:
        rd=csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig',newline=''))
        needed={'PLT_CN','CONDID','STDAGE','STDORGCD','COND_STATUS_CD','BALIVE','PHYSCLCD'}
        missing=needed-set(rd.fieldnames or [])
        if missing:raise ValueError('Missing source COND context '+str(sorted(missing)))
        for r in rd:
            key=(str(r['PLT_CN'] or '').strip(),str(r['CONDID'] or '').strip())
            if not all(key) or key in out:raise ValueError('invalid/duplicated condition')
            value=join._flt(r.get('BALIVE'))
            if value is not None and value<0:value=None
            out[key]={'age':join.source._age(r.get('STDAGE')),
                      'origin':str(r.get('STDORGCD') or '').strip(),
                      'forest':str(r.get('COND_STATUS_CD') or '').strip()=='1',
                      'basal_area_ft2_ac':value,
                      'phys':physiographic(r.get('PHYSCLCD'))}
    return out


def _pool_index():
    return {'n':0,'total_growth':0.0}


def run_strata(db,plots,conds,codes,state):
    counts=defaultdict(Counter)
    density=defaultdict(lambda:defaultdict(_pool_index))
    phys=defaultdict(lambda:defaultdict(_pool_index))
    phys_density=defaultdict(lambda:defaultdict(_pool_index))
    sql='''SELECT c.spcd,p.plt,c.plt,p.cond,c.cond,p.invyr,c.invyr,p.sta,c.sta,p.dia,c.dia
       FROM tree c JOIN tree p ON c.prev=p.cn
       WHERE c.prev!='' AND c.spcd=p.spcd AND c.invyr>p.invyr'''
    for sp,pplt,cplt,pc,cc,y0,y1,st0,st1,d0,d1 in db.execute(sql):
        co=counts[sp];co['forward_tree_link']+=1
        a,b=plots.get(pplt),plots.get(cplt)
        if a is None or b is None or b['previous']!=pplt or a['measure'] is None or b['measure'] is None:continue
        dt=b['measure']-a['measure']
        if not 1<=dt<=20 or st0!='1' or st1!='1' or d0 is None or d1 is None or d0<1:continue
        co['eligible_measured_live_growth']+=1
        da,db=conds.get((pplt,pc)),conds.get((cplt,cc))
        if da is None or db is None:continue
        if not da['forest'] or not db['forest'] or da['origin']!='0' or db['origin']!='0':continue
        age=join._band(da['age'],join.AGES)
        dia=join._band(d0,join.BANDS)
        if age is None or dia is None:continue
        co['natural_forest_valid_age']+=1
        score=math.log(d1/d0)/dt
        densityclass=join._band(da['basal_area_ft2_ac'],DENSITIES)
        physiog=da['phys']
        if densityclass is not None:
            co['density_recorded']+=1
            key=dia+'|'+age+'|'+densityclass
            d=density[sp][key];d['n']+=1;d['total_growth']+=score
        if physiog is not None:
            co['physiography_recorded']+=1
            key=dia+'|'+age+'|'+physiog
            d=phys[sp][key];d['n']+=1;d['total_growth']+=score
        if physiog is not None and densityclass is not None:
            co['both_density_and_physiography']+=1
            key=dia+'|'+age+'|'+densityclass+'|'+physiog
            d=phys_density[sp][key];d['n']+=1;d['total_growth']+=score
    def clean(store):
        return {sp:{key:{'n':d['n'],'mean_growth':d['total_growth']/d['n'] if d['n'] else None}
                    for key,d in groups.items()}
                for sp,groups in store.items()}
    return {'state':state,'species':[{ 'spcd':sp,'counts':dict(counts[sp]),
               'size_age_density':clean(density).get(sp,{}),
               'size_age_physio':clean(phys).get(sp,{}),
               'size_age_density_physio':clean(phys_density).get(sp,{})}
              for sp in codes]}


def regional_standardize(statemetrics,codes,mode='size_age_density',min_n=10):
    lookup={s['state']:{x['spcd']:x[mode] for x in s['species']} for s in statemetrics}
    out=[]
    for sp in codes:
        all_keys=set().union(*(lookup[st][sp].keys() for st in STATES))
        keys=[]
        for k in sorted(all_keys):
            data=[lookup[st][sp].get(k,{'n':0}) for st in STATES]
            if min(z['n'] for z in data)>=min_n:
                keys.append((k,sum(z['n'] for z in data),[z['mean_growth'] for z in data]))
        total=sum(x[1] for x in keys)
        means={st:(sum(w*v[i] for _,w,v in keys)/total if total else None) for i,st in enumerate(STATES)}
        out.append({'spcd':sp,'n_common_strata':len(keys),'n_source_pairs_in_common_strata':total,
                    'state_means':means,'WI_higher_RI':(means['WI']>means['RI'] if total else None),
                    'n_strata_WI_higher_RI':sum(vals[2]>vals[0] for _,_,vals in keys)})
    return out


def moisture_site_within_state(statemetrics,codes,min_n=10):
    """Mesic–xeric within each state and species, size/age/density matched.

    This is a qualitative site moisture indicator, not measured water stress.
    """
    out=[]
    for state in statemetrics:
        for row in state['species']:
            groups=defaultdict(dict)
            for key,val in row['size_age_density_physio'].items():
                *base,category=key.split('|')
                if category in ('xeric','mesic'):
                    groups['|'.join(base)][category]=val
            kept=[]
            for key,rr in groups.items():
                if ('xeric' not in rr or 'mesic' not in rr or
                    min(rr['xeric']['n'],rr['mesic']['n'])<min_n):continue
                w=rr['xeric']['n']+rr['mesic']['n']
                kept.append((key,w,rr['mesic']['mean_growth']-rr['xeric']['mean_growth']))
            wt=sum(x[1] for x in kept)
            out.append({'state':state['state'],'spcd':row['spcd'],
                        'n_common_stand_size_density_groups':len(kept),
                        'sum_within_pairs':wt,
                        'mesic_minus_xeric_growth':sum(w*delta for _,w,delta in kept)/wt if wt else None})
    return out


def run(conf,plot_cond_source,tree_result,output,fetch_plotcond=None,fetch_tree=None):
    c=json.loads(Path(conf).read_text())
    src=json.loads(Path(plot_cond_source).read_text())
    tr=json.loads(Path(tree_result).read_text())
    if c['study_id']!='fia_habitat_structure_extension_v1' or c['states']!=list(STATES):raise ValueError('invalid extension')
    if c.get('minimum_eligible_source_pairs_per_state_stratum') != 10 or c.get('basal_area_ft2_ac_bands') != ['0-<60','60-<120','120+'] or c.get('physiographic_source_FIADB_codes') != {'xeric':'11-19','mesic':'21-29','hydric':'31-39'}:
        raise ValueError('altered ecological strata or support threshold')
    if src['n_states_complete']!=3 or [s['state'] for s in src['states']]!=list(STATES):raise ValueError('source panel')
    if [s['state'] for s in tr['states']]!=list(STATES):raise ValueError('tree panel')
    if hashlib.sha256(Path(tree_result).read_bytes()).hexdigest()!=c['tree_result_sha256']:
        raise ValueError('first-open tree result altered')
    codes=[str(x) for x in c['species_codes']]
    if len(codes)!=13 or set(codes)!=set(tr['names']):raise ValueError('different tree cohort')
    states=[]
    for i,st in enumerate(STATES):
        expected=src['states'][i]
        with tempfile.TemporaryDirectory(prefix='fia_habitat_'+st+'_') as temp:
            folder=Path(temp)
            pm,pz=join.source._fetch(st,'PLOT',folder,fetcher=fetch_plotcond)
            cm,cz=join.source._fetch(st,'COND',folder,fetcher=fetch_plotcond)
            if pm['status']!='ready' or cm['status']!='ready' or pm['zip_sha256']!=expected['plot']['zip_sha256'] or cm['zip_sha256']!=expected['cond']['zip_sha256']:
                raise RuntimeError('Source PLOT/COND ZIP drift, stop '+st)
            tm,tz=join.fetch_tree(st,folder,fetcher=fetch_tree)
            if tm['status']!='ready' or tm['sha256']!=tr['states'][i]['tree_new_source']['sha256']:
                raise RuntimeError('Source TREE ZIP drift, stop '+st)
            plots=join.parse_plot(pz,pm['csv_member'])
            conds=parse_context(cz,cm['csv_member'])
            con=sqlite3.connect(folder/'selected.sqlite')
            try:
                join.parse_selected_tree(tz,tm['member'],con,set(codes))
                out=run_strata(con,plots,conds,codes,st)
            finally:con.close()
            expected_pairs=sum(x['n_growth_pairs'] for x in tr['states'][i]['species'])
            actual_pairs=sum(x['counts'].get('eligible_measured_live_growth',0) for x in out['species'])
            if actual_pairs!=expected_pairs:
                raise RuntimeError(f'{st} tree/plot live-growth denominator changed on same source: {actual_pairs} vs {expected_pairs}')
            states.append(out)
    output_obj={'study':'fia_habitat_structure_extension_v1',
         'data_status':'exploratory same-source post-outcome extension, not independent replication',
         'raw_tree_zip_source_hashes_verified':True,
         'species_count':13,'states':states,
         'matched_size_age_density':regional_standardize(states,codes),
         'matched_size_age_physiography':regional_standardize(states,codes,mode='size_age_physio'),
         'mesic_minus_xeric_within_state_matched_density':moisture_site_within_state(states,codes),
         'no_causal_moisture_limitation_or_growth_process_claim':True,
         'sampling_note':'Presence of tree in repeated FIAS sample, live-survivor and plot selection effects not corrected',
         'experimental_status':'not_confirmatory'}
    out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(output_obj,indent=2,sort_keys=True)+'\n')
    for key in ('matched_size_age_density','matched_size_age_physiography'):
        arr=output_obj[key];valid=[x for x in arr if x['n_common_strata']>0]
        print(key,'estimable',len(valid),'WI>RI',sum(x['WI_higher_RI'] for x in valid))
    z=[x for x in output_obj['mesic_minus_xeric_within_state_matched_density'] if x['mesic_minus_xeric_growth'] is not None]
    print('XERIC vs MESIC supported same-species/state comparisons',len(z),'mesic positive',sum(x['mesic_minus_xeric_growth']>0 for x in z))
    return output_obj


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',type=Path,default=Path('configs/fia_habitat_structure_extension_v1.json'))
    p.add_argument('--plot-cond',type=Path,default=Path('evidence/fia_plot_condition_source_v1.json'))
    p.add_argument('--first-tree',type=Path,default=Path('evidence/fia_new_source_stand_context_v1/aggregate.json'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    run(a.config,a.plot_cond,a.first_tree,a.output)

if __name__=='__main__':main()
