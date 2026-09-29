"""Metadata-only 80-candidate roster for SDMR fresh empirical v3."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

PROGRAM="sdmr-fresh-empirical-v3-candidate-roster"
EXACT_CANDIDATES=80
MIN_OCCURRENCES=500
MIN_UNIQUE_CELLS=20
MAX_PER_GENUS=1
MAX_PER_FAMILY=2
HASH_SEED="sdmr-fresh-empirical-v3-candidate-roster|2026-09-29"

def deterministic_rank(scientific_name: str) -> str:
    return hashlib.sha256(f"{HASH_SEED}\n{str(scientific_name).strip()}\n".encode()).hexdigest()

def select_candidate_roster(
    summary: pd.DataFrame,
    *,
    excluded_names: Iterable[str],
) -> tuple[pd.DataFrame,pd.DataFrame]:
    required={"scientific_name","family","genus","n_occurrences","n_unique_1_degree_cells"}
    missing=required-set(summary.columns)
    if missing:
        raise ValueError(f"candidate summary missing columns: {sorted(missing)}")
    excluded={str(x).strip() for x in excluded_names if str(x).strip()}
    audit=summary.copy()
    audit["scientific_name"]=audit["scientific_name"].astype(str).str.strip()
    audit["historically_or_predecessor_excluded"]=audit["scientific_name"].isin(excluded)
    audit["eligible"]=(
        ~audit["historically_or_predecessor_excluded"]
        & (pd.to_numeric(audit["n_occurrences"],errors="raise")>=MIN_OCCURRENCES)
        & (pd.to_numeric(audit["n_unique_1_degree_cells"],errors="raise")>=MIN_UNIQUE_CELLS)
        & audit["family"].astype(str).str.strip().ne("")
        & audit["genus"].astype(str).str.strip().ne("")
    )
    audit["selection_hash"]=audit["scientific_name"].map(deterministic_rank)
    audit=audit.sort_values(["selection_hash","scientific_name"],kind="mergesort").reset_index(drop=True)

    selected=[]
    genus_count={}
    family_count={}
    for row in audit.loc[audit["eligible"]].itertuples(index=False):
        genus=str(row.genus); family=str(row.family)
        if genus_count.get(genus,0)>=MAX_PER_GENUS: continue
        if family_count.get(family,0)>=MAX_PER_FAMILY: continue
        rec=row._asdict()
        selected.append(rec)
        genus_count[genus]=genus_count.get(genus,0)+1
        family_count[family]=family_count.get(family,0)+1
        if len(selected)==EXACT_CANDIDATES: break
    if len(selected)!=EXACT_CANDIDATES:
        raise RuntimeError(f"v3 candidate roster unavailable: selected {len(selected)} of {EXACT_CANDIDATES}")
    roster=pd.DataFrame(selected)
    roster.insert(0,"candidate_rank",range(1,EXACT_CANDIDATES+1))
    keep=["candidate_rank","scientific_name","family","genus","n_occurrences","n_unique_1_degree_cells","selection_hash"]
    roster=roster[keep]
    if roster["scientific_name"].isin(excluded).any():
        raise RuntimeError("excluded taxon entered v3 candidate roster")
    if roster["genus"].value_counts().max()>MAX_PER_GENUS:
        raise RuntimeError("candidate genus cap violated")
    if roster["family"].value_counts().max()>MAX_PER_FAMILY:
        raise RuntimeError("candidate family cap violated")
    return audit,roster

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--summary",required=True)
    p.add_argument("--exclusions",required=True)
    p.add_argument("--predecessor50",required=True)
    p.add_argument("--output-dir",required=True)
    a=p.parse_args()
    summary=pd.read_csv(a.summary)
    hist=pd.read_csv(a.exclusions)
    pred=pd.read_csv(a.predecessor50)
    names=set(hist["scientific_name"].astype(str))|set(pred["scientific_name"].astype(str))
    audit,roster=select_candidate_roster(summary,excluded_names=names)
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    audit.to_csv(out/"candidate_selection_audit.csv",index=False)
    roster.to_csv(out/"candidate_roster_v3.csv",index=False)
    result={
      "program":PROGRAM,
      "status":"candidate_roster_frozen_outcomes_unopened",
      "candidate_count":len(roster),
      "predecessor_taxa_excluded":int(len(set(pred["scientific_name"].astype(str)))),
      "environmental_values_read":False,
      "soil_support_opened":False,
      "answer_check_accessed":False,
      "model_fitting_performed":False,
    }
    (out/"candidate_roster_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
