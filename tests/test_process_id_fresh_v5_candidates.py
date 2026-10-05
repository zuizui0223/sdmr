import pandas as pd

from sdmr.process_id.fresh.cohort_v5_candidates import select_candidate_roster
from sdmr.process_id.fresh.cohort_v5_metadata import validate_design


def _summary(n=220):
    return pd.DataFrame({
      "scientific_name":[f"Taxon {i}" for i in range(n)],
      "family":[f"Fam {i//2}" for i in range(n)],
      "genus":[f"Gen {i}" for i in range(n)],
      "n_occurrences":[600+i for i in range(n)],
      "n_unique_1_degree_cells":[25+(i%5) for i in range(n)],
    })


def test_v5_design_freezes_joint_preeligibility_before_selection():
    c=validate_design("configs/sdmr_fresh_empirical_v5_preeligibility.json")
    assert c["independence"]["prior_taxa"]==304
    assert c["candidate_roster"]["exact_candidates"]==120
    assert c["geometry_eligibility"]["whole_program_failure_on_one_geometry_ineligible"] is False
    assert c["all46_support_eligibility"]["predictor_count"]==46
    assert c["final_selection"]["eligible_definition"]=="geometry_eligible AND all46_support_eligible"
    assert c["final_selection"]["final_taxa"]==50


def test_v5_roster_is_exact_120_order_invariant_and_excludes_prior():
    s=_summary()
    excluded={"Taxon 0","Taxon 1","Taxon 2"}
    _,a=select_candidate_roster(s,excluded_names=excluded)
    _,b=select_candidate_roster(s.sample(frac=1,random_state=11),excluded_names=excluded)
    assert len(a)==120
    assert a["candidate_rank"].tolist()==list(range(1,121))
    assert a["scientific_name"].tolist()==b["scientific_name"].tolist()
    assert not set(a["scientific_name"]) & excluded
    assert a["genus"].value_counts().max()==1
    assert a["family"].value_counts().max()<=2


def test_v5_candidate_selection_uses_no_geometry_or_support_columns():
    _,r=select_candidate_roster(_summary(),excluded_names=[])
    assert "geometry_eligible" not in r.columns
    assert "all46_support_eligible" not in r.columns
