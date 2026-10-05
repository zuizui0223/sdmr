"""Metadata-only 120-candidate roster for SDMR fresh empirical v5."""
from __future__ import annotations

import hashlib
from typing import Iterable

import pandas as pd

PROGRAM="sdmr-fresh-empirical-v5-candidate-roster"
EXACT_CANDIDATES=120
MIN_OCCURRENCES=500
MIN_UNIQUE_CELLS=20
MAX_PER_GENUS=1
MAX_PER_FAMILY=2
HASH_SEED="sdmr-fresh-empirical-v5-candidate-roster|2026-10-05"

def deterministic_rank(scientific_name: str)->str:
    return hashlib.sha256(
        f"{HASH_SEED}\n{str(scientific_name).strip()}\n".encode()
    ).hexdigest()

def select_candidate_roster(
    summary: pd.DataFrame,
    *,
    excluded_names: Iterable[str],
)->tuple[pd.DataFrame,pd.DataFrame]:
    required={"scientific_name","family","genus","n_occurrences","n_unique_1_degree_cells"}
    missing=required-set(summary.columns)
    if missing:
        raise ValueError(f"v5 candidate summary missing columns: {sorted(missing)}")
    excluded={str(x).strip() for x in excluded_names if str(x).strip()}
    audit=summary.copy()
    audit["scientific_name"]=audit["scientific_name"].astype(str).str.strip()
    audit["prior_program_excluded"]=audit["scientific_name"].isin(excluded)
    audit["eligible"]=(
        ~audit["prior_program_excluded"]
        & (pd.to_numeric(audit["n_occurrences"],errors="raise")>=MIN_OCCURRENCES)
        & (pd.to_numeric(audit["n_unique_1_degree_cells"],errors="raise")>=MIN_UNIQUE_CELLS)
        & audit["family"].astype(str).str.strip().ne("")
        & audit["genus"].astype(str).str.strip().ne("")
    )
    audit["selection_hash"]=audit["scientific_name"].map(deterministic_rank)
    audit=audit.sort_values(
        ["selection_hash","scientific_name"],kind="mergesort"
    ).reset_index(drop=True)

    selected=[]
    genus_count={}
    family_count={}
    for row in audit.loc[audit["eligible"]].itertuples(index=False):
        genus=str(row.genus); family=str(row.family)
        if genus_count.get(genus,0)>=MAX_PER_GENUS:
            continue
        if family_count.get(family,0)>=MAX_PER_FAMILY:
            continue
        selected.append(row._asdict())
        genus_count[genus]=genus_count.get(genus,0)+1
        family_count[family]=family_count.get(family,0)+1
        if len(selected)==EXACT_CANDIDATES:
            break
    if len(selected)!=EXACT_CANDIDATES:
        raise RuntimeError(
            f"v5 candidate roster unavailable: selected {len(selected)} of {EXACT_CANDIDATES}"
        )
    roster=pd.DataFrame(selected)
    roster.insert(0,"candidate_rank",range(1,EXACT_CANDIDATES+1))
    roster=roster[[
        "candidate_rank","scientific_name","family","genus",
        "n_occurrences","n_unique_1_degree_cells","selection_hash"
    ]]
    if roster["scientific_name"].isin(excluded).any():
        raise RuntimeError("prior-program taxon entered v5 candidate roster")
    if roster["genus"].value_counts().max()>MAX_PER_GENUS:
        raise RuntimeError("v5 candidate genus cap violated")
    if roster["family"].value_counts().max()>MAX_PER_FAMILY:
        raise RuntimeError("v5 candidate family cap violated")
    return audit,roster
