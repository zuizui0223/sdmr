"""Re-run Product-A method search on already frozen GBIF/CHELSA feature evidence.

This development CLI deliberately skips occurrence admission, M/background
construction and raster extraction. It may only consume a prepared pilot-grid
bundle that already contains ``pilot_occurrences.csv`` and one feature-complete
``specifications/<M>/background.csv`` per frozen M specification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from .model import ModelSpec
from .pilot_grid_cli import _write_protocol_outputs, read_pilot_grid
from .robust_protocol import benchmark_product_a_method_across_sensitivity_specs
from .universe import candidate_universes_from_manifest


def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _model_specs(profile: str):
    if profile == 'full':
        return None
    if profile == 'linear_l2_c1':
        return [ModelSpec(C=1.0, degree=1, penalty='l2')]
    if profile == 'linear_l2_grid':
        return [ModelSpec(C=c, degree=1, penalty='l2') for c in (0.1,1.0,10.0)]
    if profile == 'linear_regularized':
        return [ModelSpec(C=c, degree=1, penalty=p) for p in ('l1','l2') for c in (0.1,1.0,10.0)]
    raise ValueError(f'unknown model profile: {profile}')


def main(argv: list[str] | None=None) -> int:
    parser=argparse.ArgumentParser(description='Re-run Product-A tuning on frozen prepared feature tables only.')
    parser.add_argument('--prepared-dir',required=True)
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--output-dir',required=True)
    parser.add_argument('--model-profile',choices=['full','linear_l2_c1','linear_l2_grid','linear_regularized'],default='full')
    parser.add_argument('--taxon-validation-fraction',type=float,default=0.25)
    parser.add_argument('--spatial-test-fraction',type=float,default=0.20)
    parser.add_argument('--vif-threshold',type=float,default=5.0)
    parser.add_argument('--max-predictors',type=int,default=8)
    parser.add_argument('--random-baseline-repeats',type=int,default=0)
    parser.add_argument('--seed',type=int,default=20260814)
    parser.add_argument('--benchmark-jobs',type=int,default=1)
    parser.add_argument('--model-spec-jobs',type=int,default=1)
    args=parser.parse_args(argv)
    if not 0 < args.taxon_validation_fraction < 1 or not 0 < args.spatial_test_fraction < 1:
        parser.error('test fractions must be between 0 and 1')
    if args.vif_threshold <= 1 or args.max_predictors < 1 or args.random_baseline_repeats < 0:
        parser.error('invalid tuning controls')
    if args.benchmark_jobs < 1 or args.model_spec_jobs < 1:
        parser.error('parallel worker counts must be >=1')

    root=Path(args.prepared_dir)
    occurrence_path=root/'pilot_occurrences.csv'
    grid_path=root/'pilot_grid_frozen.csv'
    for path in (occurrence_path,grid_path):
        if not path.exists(): raise SystemExit(f'missing prepared evidence: {path}')
    occurrences=pd.read_csv(occurrence_path)
    grid=read_pilot_grid(str(grid_path))
    specifications={}
    for name in grid['name'].astype(str):
        background_path=root/'specifications'/name/'background.csv'
        if not background_path.exists(): raise SystemExit(f'missing prepared background: {background_path}')
        specifications[name]=(occurrences.copy(),pd.read_csv(background_path))

    manifest=pd.read_csv(args.manifest)
    universes=candidate_universes_from_manifest(manifest)
    all_predictors=sorted({p for universe in universes.values() for p in universe.predictors})
    missing_occ=[p for p in all_predictors if p not in occurrences.columns]
    missing_bg={name:[p for p in all_predictors if p not in bg.columns] for name,(_,bg) in specifications.items()}
    missing_bg={name:vals for name,vals in missing_bg.items() if vals}
    if missing_occ or missing_bg:
        raise SystemExit(f'prepared feature evidence is incomplete: occurrence_missing={missing_occ}, background_missing={missing_bg}')

    os.environ['SDMR_MODEL_SPEC_JOBS']=str(args.model_spec_jobs)
    result=benchmark_product_a_method_across_sensitivity_specs(
        specifications,
        universes,
        taxon_validation_fraction=args.taxon_validation_fraction,
        sealed_fraction=args.spatial_test_fraction,
        vif_threshold=args.vif_threshold,
        max_predictors=args.max_predictors,
        model_specs=_model_specs(args.model_profile),
        random_repeats=args.random_baseline_repeats,
        compute_drop_one=False,
        random_state=args.seed,
        n_jobs=args.benchmark_jobs,
    )

    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    run_args=SimpleNamespace(
        spatial_test_fraction=args.spatial_test_fraction,
        taxon_validation_fraction=args.taxon_validation_fraction,
        m_grid_as_sensitivity=True,
        seed=args.seed,
    )
    _write_protocol_outputs(result,out,args=run_args)
    grid.to_csv(out/'pilot_grid_frozen.csv',index=False)
    (out/'prepared_benchmark_contract.json').write_text(json.dumps({
        'prepared_dir':str(root),
        'prepared_occurrence_sha256':_sha(occurrence_path),
        'prepared_grid_sha256':_sha(grid_path),
        'manifest_sha256':_sha(Path(args.manifest)),
        'model_profile':args.model_profile,
        'taxon_validation_fraction':args.taxon_validation_fraction,
        'spatial_test_fraction':args.spatial_test_fraction,
        'vif_threshold':args.vif_threshold,
        'max_predictors':args.max_predictors,
        'random_baseline_repeats':args.random_baseline_repeats,
        'seed':args.seed,
        'benchmark_jobs':args.benchmark_jobs,
        'model_spec_jobs':args.model_spec_jobs,
        'changes_prepared_source_evidence':False,
        'purpose':'development_method_search_only',
    },indent=2,sort_keys=True),encoding='utf-8')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
