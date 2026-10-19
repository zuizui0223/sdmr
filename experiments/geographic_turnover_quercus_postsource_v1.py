"""Post-source demonstration on fixed Quercus rectangles; NOT confirmatory.

Run after a complete 25km climate cell source archive exists. Sentinel plant
counts are NOT verified observation-effort probabilities. This is only a
labelled calibration diagnostic, not a macroecological or biological inference.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import pandas as pd


def diagnostic(frame: pd.DataFrame, *, source_sha: str, seed: int = 20261019, replicates: int = 99):
    allowed = ['quercus_DE_central','quercus_SE_south']
    subset = frame.loc[frame['region'].isin(allowed)].copy()
    if sorted(subset.region.unique()) != allowed:
        raise ValueError('Both predeclared Quercus windows are required')
    cols = ['n_focal_records_diagnostic','n_independent_target_group_records_diagnostic']
    if subset[cols].isna().any().any():
        raise ValueError('Incomplete focal or independent target-group source archive')
    if (subset.n_independent_target_group_records_diagnostic <= 0).any():
        raise ValueError('Cell lacks sentinel support; no zero effort is imputed')
    subset['n_occ'] = subset['n_focal_records_diagnostic'].astype(int)
    subset['effort'] = subset['n_independent_target_group_records_diagnostic'].astype(float)
    subset['taxon'] = 'Quercus robur'
    if subset.duplicated(['region','cell_id']).any():
        raise ValueError('duplicate climate cell')
    path = Path(__file__).with_name('geographic_driver_turnover_v0.py')
    spec = importlib.util.spec_from_file_location('turnover_v0_exploratory',path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    colnames=['taxon','region','cell_id','spatial_block','temperature','moisture','effort','n_occ']
    result=mod.analyze_taxon(subset[colnames],replicates=replicates,seed=seed)
    return {
      'status':'post_source_diagnostic_not_scientific_promotion',
      'taxon':'Quercus robur',
      'source_climate_cells_sha256':source_sha,
      'fixed_source_windows':allowed,
      'strict_no_biological_inference': True,
      'risk_ledger': [
         'rectangles_not_taxon_accessible_M',
         'sentinel_record_density_not_calibrated_effort',
         'planted_individuals_not_screened',
         'unmatched_detection_and_spatial_dependence',
         'limited_joint_environmental_support',
         'outcome_assessed_post_source_without_prospective_effect_gates'
      ],
      'result':result
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cells',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seed',type=int,default=20261019)
    parser.add_argument('--replicates',type=int,default=99)
    args=parser.parse_args()
    raw=args.cells.read_bytes()
    result=diagnostic(pd.read_csv(args.cells),source_sha=hashlib.sha256(raw).hexdigest(),seed=args.seed,replicates=args.replicates)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print('post-source demo: region-reversal=',result['result']['observed']['direction_reversal'],
          'uncalibrated-bootstrap-tail=',result['result']['one_sided_bootstrap_p'])

if __name__=='__main__':
    main()
