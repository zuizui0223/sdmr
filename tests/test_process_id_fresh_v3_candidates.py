from pathlib import Path
import pandas as pd

from sdmr.process_id.fresh.cohort_v3_candidates import (
    deterministic_rank,
    select_candidate_roster,
)

def _summary(n=140):
    return pd.DataFrame({
      "scientific_name":[f"Taxon {i}" for i in range(n)],
      "family":[f"Fam {i//2}" for i in range(n)],
      "genus":[f"Gen {i}" for i in range(n)],
      "n_occurrences":[600+i for i in range(n)],
      "n_unique_1_degree_cells":[25+(i%5) for i in range(n)],
    })

def test_v3_roster_is_exact_80_and_deterministic():
    s=_summary()
    a,r=select_candidate_roster(s,excluded_names={"Taxon 0","Taxon 1"})
    assert len(r)==80
    assert r["scientific_name"].nunique()==80
    assert r["candidate_rank"].tolist()==list(range(1,81))
    r2=select_candidate_roster(s.sample(frac=1,random_state=7),excluded_names={"Taxon 0","Taxon 1"})[1]
    assert r["scientific_name"].tolist()==r2["scientific_name"].tolist()

def test_predecessor_exclusion_is_absolute():
    s=_summary()
    excluded={f"Taxon {i}" for i in range(50)}
    _,r=select_candidate_roster(s,excluded_names=excluded)
    assert not set(r["scientific_name"]) & excluded

def test_hash_seed_is_stable():
    assert deterministic_rank("Poa annua")==deterministic_rank("Poa annua")
    assert deterministic_rank("Poa annua")!=deterministic_rank("Poa trivialis")
