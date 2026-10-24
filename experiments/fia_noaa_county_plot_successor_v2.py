"""Source-only successor after USDA FIA PLOT ZIP drift, no old-tree-data rescue.

The original source-identity mismatch is preserved as a hard, auditable STOP.
The newly encountered PLOT archive hashes constitute a separately named NEW
source cohort; never transplant those plot records into the historical growth
or size/age/density result. NOAA nClimDiv source remains the same frozen vintage.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fia_noaa_plot_original',HERE/'fia_noaa_county_plot_source_v1.py')
original=importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
STATES=('RI','VA','WI')


def validate_previous_stop(old: dict) -> dict:
    if (old.get('study') != 'fia_noaa_county_plot_chain_coverage_v1'
        or old.get('n_states_join_complete') != 0
        or old.get('n_tree_growth_observations_opened') != 0
        or not old.get('no_climate_density_effect_or_causal_inference')):
        raise ValueError('original source-drift stop is missing or invalid')
    states=old.get('states',[])
    if tuple(x.get('state') for x in states)!=STATES:
        raise ValueError('declared three-state original stop changed')
    out={}
    for item in states:
        oldsha=item.get('source_expected_sha256')
        observed=item.get('actual_sha256')
        if (item.get('status')!='source_unavailable_or_changed' or
            not isinstance(observed,str) or len(observed)!=64 or
            not isinstance(oldsha,str) or len(oldsha)!=64 or oldsha==observed):
            raise ValueError('original frozen source mismatch is not independently recorded')
        out[item['state']]=observed
    return out


def run(old_receipt,climate_csv,climate_receipt,outpath,*,getter=None):
    oldpath=Path(old_receipt)
    prev=json.loads(oldpath.read_bytes())
    new_shas=validate_previous_stop(prev)
    climate, _ = original.load_climate(Path(climate_csv),Path(climate_receipt))
    if prev['original_noaa_climate_source_sha256']!=hashlib.sha256(Path(climate_receipt).read_bytes()).hexdigest():
        raise ValueError('NOAA climate receipt differs from original stop')
    out=[]
    for state in STATES:
        with tempfile.TemporaryDirectory(prefix='fia_noaa_new_plot_v2_'+state+'_') as tmp:
            meta,zippath=original.plot_gate._fetch(state,'PLOT',Path(tmp),fetcher=getter)
            if meta.get('status')!='ready' or meta.get('zip_sha256')!=new_shas[state]:
                out.append({'state':state,'status':'new_plot_source_changed_again_stop',
                            'expected_successor_sha256':new_shas[state],
                            'actual_sha256':meta.get('zip_sha256')})
                continue
            plots,info=original.parse_plots(zippath,meta['csv_member'],state)
            audit=original.summarize_plot_chain(plots,climate,state)
            out.append({'state':state,'status':'successor_new_plot_climate_ready',
                        'new_plot_source_sha256':new_shas[state],
                        'plot_source':info,'climate_linkage':audit})
    report={'study':'fia_noaa_new_plot_version_successor_v2',
            'predecessor_stop_sha256':hashlib.sha256(oldpath.read_bytes()).hexdigest(),
            'source_history_changed':True,
            'original_frozen_FIA_plot_not_relabelled_or_recovered':True,
            'original_frozen_TREE_growth_not_reanalysed':True,
            'NOAA_climate_source_sha256':hashlib.sha256(Path(climate_receipt).read_bytes()).hexdigest(),
            'states':out,
            'n_new_source_complete_states':sum(z['status']=='successor_new_plot_climate_ready' for z in out),
            'claim':'FIA new-source PLOT-to-county-climate metadata coverage only; no tree growth, niche, competition, causal or mortality effect'}
    path=Path(outpath);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print('NOAA + successor FIA PLOT only: '+str([(z['state'],z['status'],z.get('climate_linkage',{}).get('n_county_climate_eligible_plot_links')) for z in out]))
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--original-stop',type=Path,default=Path('results/fia_noaa_county_climate_v1/original_plot_source_stop.json'))
    ap.add_argument('--climate-csv',type=Path,default=Path('results/fia_noaa_county_climate_v1/noaa_county_growing_months_1991_2025.csv'))
    ap.add_argument('--climate-receipt',type=Path,default=Path('results/fia_noaa_county_climate_v1/source_receipt.json'))
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    run(a.original_stop,a.climate_csv,a.climate_receipt,a.output)

if __name__=='__main__':main()
