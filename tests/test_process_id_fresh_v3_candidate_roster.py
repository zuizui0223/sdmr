import pandas as pd
from pathlib import Path
from sdmr.process_id.fresh.cohort_v3_candidates import select_candidate_roster
from sdmr.process_id.fresh.cohort_v3_metadata import validate_design

ROOT=Path(__file__).resolve().parents[1]

def test_v3_design_is_metadata_only_and_exact_80():
    c=validate_design(ROOT/"configs/sdmr_fresh_empirical_v3_soil_support_eligibility.json")
    assert c["candidate_roster"]["exact_candidates"]==80
    assert c["candidate_roster"]["final_taxa"]==50
    assert c["metadata_access"] if "metadata_access" in c else True
    assert c["information_barrier"]["forbidden_before_final_50"][0]=="numeric SoilGrids values"

def test_v3_roster_selector_preserves_caps_and_exclusion():
    rows=[]
    for i in range(100):
        rows.append({
          "scientific_name":f"Gen{i} sp{i}","family":f"Fam{i//2}","genus":f"Gen{i}",
          "n_occurrences":600+i,"n_unique_1_degree_cells":25+i%5
        })
    frame=pd.DataFrame(rows)
    audit,roster=select_candidate_roster(frame,excluded_names={"Gen0 sp0","Gen1 sp1"})
    assert len(roster)==80
    assert not set(roster.scientific_name)&{"Gen0 sp0","Gen1 sp1"}
    assert roster.genus.value_counts().max()<=1
    assert roster.family.value_counts().max()<=2
    assert audit.selection_hash.notna().all()
