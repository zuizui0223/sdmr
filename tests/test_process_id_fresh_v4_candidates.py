import pandas as pd

from sdmr.process_id.fresh.cohort_v4_candidates import (
    deterministic_rank,
    select_candidate_roster,
)


def _summary(n=170):
    return pd.DataFrame({
      "scientific_name":[f"Taxon {i}" for i in range(n)],
      "family":[f"Fam {i//2}" for i in range(n)],
      "genus":[f"Gen {i}" for i in range(n)],
      "n_occurrences":[600+i for i in range(n)],
      "n_unique_1_degree_cells":[25+(i%5) for i in range(n)],
    })


def test_v4_roster_is_exact_90_and_order_invariant():
    s=_summary()
    excluded={"Taxon 0","Taxon 1"}
    _,a=select_candidate_roster(s,excluded_names=excluded)
    _,b=select_candidate_roster(s.sample(frac=1,random_state=11),excluded_names=excluded)
    assert len(a)==90
    assert a["candidate_rank"].tolist()==list(range(1,91))
    assert a["scientific_name"].tolist()==b["scientific_name"].tolist()


def test_v4_prior_exclusion_is_absolute():
    s=_summary()
    excluded={f"Taxon {i}" for i in range(60)}
    _,r=select_candidate_roster(s,excluded_names=excluded)
    assert not set(r["scientific_name"]) & excluded


def test_v4_hash_seed_is_stable_and_distinct():
    assert deterministic_rank("Poa annua")==deterministic_rank("Poa annua")
    assert deterministic_rank("Poa annua")!=deterministic_rank("Poa trivialis")
