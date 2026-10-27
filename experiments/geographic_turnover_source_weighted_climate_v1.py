"""Descriptive source-assemblage climate comparison: availability/focal/sentinels.

All source rows must be complete before any reported mean. Three sampled distributions
are NOT causal estimands and sentinel plant occurrence is NOT verified recorder effort.
No positive niche-selection, local adaptation or range-limit conclusion is allowed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

AXES=('temperature','moisture')

def study(frame: pd.DataFrame, *, source_sha256: str)->dict:
    needed={'region','cell_id','temperature','moisture','n_focal_records_diagnostic',
            'n_independent_target_group_records_diagnostic'}
    if needed-set(frame.columns):raise ValueError(f'missing columns: {needed-set(frame.columns)}')
    if frame.duplicated(['region','cell_id']).any():raise ValueError('duplicate source cell')
    rows=[]
    for region,df in frame.groupby('region',sort=True):
        out={'region':region,'n_climate_cells':len(df),'status':'diagnostic_only'}
        src_cols=['n_focal_records_diagnostic','n_independent_target_group_records_diagnostic']
        if df[src_cols].isna().any().any():
            out.update({'source_complete':False,'reason':'missing focal/independent sentinel archive; do not convert unavailable to zero'})
            rows.append(out);continue
        if not np.isfinite(df[['temperature','moisture']].to_numpy(float)).all():
            raise ValueError('nonfinite climate values')
        counts=df[src_cols].to_numpy(float)
        if (counts<0).any() or not np.all(counts==np.floor(counts)):
            raise ValueError('invalid source record counts')
        weights={'equal_area_available_cells':np.ones(len(df)),
                 'focal_record_weighted':counts[:,0],
                 'independent_sentinel_record_weighted':counts[:,1]}
        if any(v.sum()<=0 for v in weights.values()):
            out.update({'source_complete':False,'reason':'zero positive focal or independent sentinel records'})
            rows.append(out);continue
        means={mode:{axis:float(np.average(df[axis],weights=q)) for axis in AXES}
               for mode,q in weights.items()}
        out.update({
            'source_complete':True,
            'n_focal_records':int(counts[:,0].sum()),
            'n_sentinel_records':int(counts[:,1].sum()),
            'n_cells_focal_positive':int((counts[:,0]>0).sum()),
            'n_cells_sentinel_positive':int((counts[:,1]>0).sum()),
            'source_climate_means':means,
            'focal_minus_equal_area':{v:float(means['focal_record_weighted'][v]-means['equal_area_available_cells'][v]) for v in AXES},
            'focal_minus_sentinel':{v:float(means['focal_record_weighted'][v]-means['independent_sentinel_record_weighted'][v]) for v in AXES}
        })
        rows.append(out)
    return {'type':'source_photographic_analogue_climate_assemblage_not_niche',
            'climate_source_sha256':source_sha256,
            'n_climate_regions':int(len(rows)),
            'n_regions_with_both_record_sources':sum(x.get('source_complete',False) for x in rows),
            'inferential_status':'exploratory source support only; not species population, causal habitat selection, or process identification',
            'cautions':['region rectangles are not accessible M','GBIF record density is not population density',
                        'sentinel-record density is not calibrated observation effort','native-country does not imply each record is wild',
                        'long-term climate normals do not represent observation-year exposure'],
            'windows':rows}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cells',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    raw=args.cells.read_bytes()
    r=study(pd.read_csv(args.cells),source_sha256=hashlib.sha256(raw).hexdigest())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(r,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
    print('complete paired source windows',r['n_regions_with_both_record_sources'],'/',r['n_climate_regions'])

if __name__=='__main__':main()
