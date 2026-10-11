#!/usr/bin/env python3
"""Diagnose BLAS-thread sensitivity of the ORIGINAL frozen v5 logistic replay.

Only frozen model-pool artifacts are allowed; never read sealed answer checks.
Thread counts are diagnostic variants, not a tuneable v5 hyperparameter.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits, threadpool_info

PATH=Path(__file__).with_name("v5_standardization_probe.py")
spec=importlib.util.spec_from_file_location("v5_standardization_probe",PATH)
probe=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(probe)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--feature-zip",type=Path,required=True)
    p.add_argument("--occurrence-zip",type=Path,required=True)
    p.add_argument("--pool-zip",type=Path,required=True)
    p.add_argument("--registry",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--taxon-limit",type=int,default=4)
    p.add_argument("--blas-threads",type=int,nargs="+",default=[1,2,4,8])
    a=p.parse_args()
    if sorted(set(a.blas_threads))!=[1,2,4,8]:
        raise ValueError("predeclared diagnostic only supports four BLAS thread levels")
    a.output_dir.mkdir(parents=True,exist_ok=True)
    by_thread={}
    for n in a.blas_threads:
        output=a.output_dir/f"replay_blas_{n}.json"
        with threadpool_limits(limits=n,user_api="blas"):
            library_info=threadpool_info()
            probe.run(feature_zip=a.feature_zip,occurrence_zip=a.occurrence_zip,
                      pool_zip=a.pool_zip,registry_path=a.registry,
                      taxon_limit=a.taxon_limit,output=output)
        data=json.loads(output.read_text(encoding="utf-8"))
        by_thread[str(n)]={"blas_info":library_info,"matched_taxa":data["baseline_replay"]["matched_taxa_within_1e-3"],
            "max_original_score_error":data["baseline_replay"]["maximum_absolute_score_error"],
            "canonical_manual_max_difference":data["baseline_replay"]["canonical_helper_minus_handwritten_maximum_abs"],
            "taxa":[{
                 "taxon":r["scientific_name"],
                 "frozen_score":r["frozen_raw_score"],
                 "canonical_score":r["verbatim_frozen_fit_helper_replay"]["observed_mean_score"],
                 "absolute_error":r["canonical_helper_replay_absolute_error"],
                 "raw_hit_limit_folds":r["raw_logistic_v5_replay"]["solver_hit_iteration_ceiling_folds"],
                 "standardized_hit_limit_folds":r["standardized_logistic_exploratory"]["solver_hit_iteration_ceiling_folds"],
              } for r in data["rows"]]}
    result={
       "schema":"sdmr.v5.postterminal_blas_thread_probe.v1",
       "status":"diagnostic_only_no_v5_rescue",
       "taxon_limit":a.taxon_limit,"frozen_taxon_denominator":50,
       "blas_threads":a.blas_threads,"original_v5_emp_d":"failed_closed",
       "sealed_answer_check_read":False,
       "causal_standardization_effect_established":False,
       "runs":by_thread,
    }
    f=a.output_dir/"thread_diagnosis.json"
    f.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("THREAD DIAGNOSIS",json.dumps({
      n:{k:v for k,v in d.items() if k not in ("taxa","blas_info")}
      for n,d in by_thread.items()},indent=2))

if __name__=="__main__":
    main()
