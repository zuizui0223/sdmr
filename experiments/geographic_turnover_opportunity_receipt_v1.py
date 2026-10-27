"""Recompute factual 25-km source-window climate support, NOT species niches."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

PAIRS = {"Quercus robur": ("quercus_DE_central", "quercus_SE_south"),
         "Pinus sylvestris": ("pinus_ES_central", "pinus_FI_central")}


def summarize(frame: pd.DataFrame, *, source_sha: str):
    required={"region","cell_id","temperature","moisture"}
    if required - set(frame):raise ValueError(f"missing required columns: {required-set(frame)}")
    if frame.duplicated(["region","cell_id"]).any():raise ValueError('duplicated environmental cell')
    if not np.isfinite(frame[["temperature","moisture"]].to_numpy(float)).all():
        raise ValueError('not all climate cells are finite')
    output=[]
    for taxon, (name_a,name_b) in PAIRS.items():
        a=frame[frame.region==name_a].copy();b=frame[frame.region==name_b].copy()
        if a.empty or b.empty:raise ValueError(f'no climate evidence for {taxon}')
        def desc(g):
            return {'n_25km_cells':len(g),
                    'temperature_c_min':float(g.temperature.min()),'temperature_c_median':float(g.temperature.median()),'temperature_c_max':float(g.temperature.max()),
                    'bio12_mm_per_year_min':float(g.moisture.min()),'bio12_mm_per_year_median':float(g.moisture.median()),'bio12_mm_per_year_max':float(g.moisture.max())}
        # 6x6 pooled-quantile climate-bin overlap: coarse descriptive statistic.
        edges=[np.unique(np.quantile(np.r_[a[k],b[k]],np.linspace(0,1,7)[1:-1])) for k in ('temperature','moisture')]
        def hist(g):
            x=np.searchsorted(edges[0],g.temperature,side='right')
            y=np.searchsorted(edges[1],g.moisture,side='right')
            v=np.bincount(x*6+y,minlength=36).astype(float)
            return v/v.sum()
        output.append({'taxon':taxon,'source_windows':[name_a,name_b], 'areas':{name_a:desc(a),name_b:desc(b)},
                       'temperature_raw_range_overlap_c':float(max(0,min(a.temperature.max(),b.temperature.max())-max(a.temperature.min(),b.temperature.min()))),
                       'bio12_raw_range_overlap_mm_year':float(max(0,min(a.moisture.max(),b.moisture.max())-max(a.moisture.min(),b.moisture.min()))),
                       'coarse_joint_climate_overlap_6x6':float(np.minimum(hist(a),hist(b)).sum())})
    return {'status':'source_environmental_opportunity_only',
            'source_climate_cells_sha256':source_sha,
            'n_25km_climate_cells':int(len(frame)),
            'no_native_population_presence_or_effort_inference':True,
            'not_species_accessible_areas_M':True,
            'no_biological_niche_shift_inference':True,
            'pairs':output}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cells',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    arg=ap.parse_args()
    raw=arg.cells.read_bytes()
    out=summarize(pd.read_csv(arg.cells),source_sha=hashlib.sha256(raw).hexdigest())
    arg.output.parent.mkdir(parents=True,exist_ok=True)
    arg.output.write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print([(x['taxon'],x['temperature_raw_range_overlap_c']) for x in out['pairs']])

if __name__=='__main__':main()
