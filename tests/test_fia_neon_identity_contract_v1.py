"""NEON 2026 normalized identity/source-only contract: NO measured outcomes."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_neon_identity_contract_v1 as g


def fixtures():
    plots=[
      {"site":"HARV","plotID":"HARV_001","eventID":"E2014","surveyYear":"2014",
       "samplingImpractical":"ok","totalSampledAreaTrees":"400"},
      {"site":"HARV","plotID":"HARV_001","eventID":"E2024","surveyYear":"2024",
       "samplingImpractical":"ok","totalSampledAreaTrees":"400"},
    ]
    mapping=[
      {"site":"HARV","plotID":"HARV_001","individualID":"NEON1",
       "date":"2014-09-01","taxonID":"PIRU"},
      {"site":"HARV","plotID":"HARV_001","individualID":"NEON1",
       "date":"2024-09-01","taxonID":"PIRU"},
      {"site":"HARV","plotID":"HARV_001","individualID":"NEON2",
       "date":"2014-09-01","taxonID":"ACRU"},
      {"site":"HARV","plotID":"HARV_001","individualID":"TEMP001",
       "date":"2014-09-01","taxonID":"QURU"},
    ]
    stems=[]
    for event in ("E2014","E2024"):
        stems.extend([
          {"site":"HARV","plotID":"HARV_001","eventID":event,
           "individualID":"NEON1","tempStemID":"1"},
          {"site":"HARV","plotID":"HARV_001","eventID":event,
           "individualID":"TEMP001","tempStemID":"1"},
          {"site":"HARV","plotID":"HARV_001","eventID":event,
           "individualID":"NEON2","tempStemID":"1"},
          {"site":"HARV","plotID":"HARV_001","eventID":event,
           "individualID":"NEON2","tempStemID":"2"},
        ])
    return plots,mapping,stems


def test_one_stable_tag_source_candidate_neither_tree_growth_nor_death():
    p,m,s=fixtures()
    x=g.audit_identity_source(p,m,s)
    assert x["n_source_identity_candidates_with_4_years_or_longer"]==1
    assert x["n_candidate_IDs_by_site"]=={"HARV":1,"SCBI":0}
    assert x["n_plots_with_candidate_IDs_by_site"]["HARV"]==1
    assert x["failure_and_exclusion_counts"]["multi_stem_or_nonstable_tempStemID"]==1
    assert x["failure_and_exclusion_counts"]["TEMP_ID_event_rows_not_longitudinal"]==2
    assert x["failure_and_exclusion_counts"]["historical_mapping_correction_rows"]==1
    assert x["verified_same_tree_growth_or_death_status"] is None
    assert not x["raw_tree_diameter_status_values_evaluated"]
    assert not x["biological_outcome_estimated"]


def test_neon_2026_mapping_has_no_eventID():
    p,m,s=fixtures()
    m[0]["eventID"]="E2014"
    with pytest.raises(ValueError,match="normalized source column mismatch"):
        g.audit_identity_source(p,m,s)


def test_extra_biological_measurements_forbidden_in_normalized_source_gate():
    p,m,s=fixtures()
    s[0]["plantStatus"]="dead"
    with pytest.raises(ValueError,match="source column mismatch"):
        g.audit_identity_source(p,m,s)
    p,m,s=fixtures()
    s[0]["stemDiameter"]=9.0
    with pytest.raises(ValueError,match="source column mismatch"):
        g.audit_identity_source(p,m,s)


def test_invalid_tree_area_does_not_create_mortality_or_repeat():
    p,m,s=fixtures()
    p[1]["totalSampledAreaTrees"]="0"
    x=g.audit_identity_source(p,m,s)
    assert x["n_source_identity_candidates_with_4_years_or_longer"]==0
    assert x["failure_and_exclusion_counts"]["plot_event_without_complete_tree_sampled_area_or_effort"]==1
    assert x["failure_and_exclusion_counts"]["individual_event_area_or_effort_invalid"]>=1


def test_temporary_ids_excluded_even_if_apparently_repeated():
    p,m,s=fixtures()
    m=[x for x in m if x["individualID"]=="TEMP001"]
    s=[x for x in s if x["individualID"]=="TEMP001"]
    x=g.audit_identity_source(p,m,s)
    assert x["n_source_identity_candidates_with_4_years_or_longer"]==0
    assert x["failure_and_exclusion_counts"]["TEMP_ID_event_rows_not_longitudinal"]==2


def test_repeats_less_than_four_years_not_longitudinal_design_candidates():
    p,m,s=fixtures()
    p[1]["surveyYear"]="2017"
    x=g.audit_identity_source(p,m,s)
    assert x["n_source_identity_candidates_with_4_years_or_longer"]==0
    assert x["failure_and_exclusion_counts"]["repeat_ID_time_span_under_four_years"]==1


def test_duplicate_event_plot_and_stem_are_hard_stops():
    p,m,s=fixtures()
    with pytest.raises(ValueError,match="duplicate NEON plotID x eventID"):
        g.audit_identity_source(p+[p[0].copy()],m,s)
    with pytest.raises(ValueError,match="duplicate NEON eventID"):
        g.audit_identity_source(p,m,s+[s[0].copy()])


def test_cross_plot_reused_individualID_not_proven_same_tree():
    p,m,s=fixtures()
    more=[
     {"site":"HARV","plotID":"HARV_002","eventID":"F2014","surveyYear":"2014",
      "samplingImpractical":"ok","totalSampledAreaTrees":"400"},
     {"site":"HARV","plotID":"HARV_002","eventID":"F2024","surveyYear":"2024",
      "samplingImpractical":"ok","totalSampledAreaTrees":"400"}]
    m=m+[{"site":"HARV","plotID":"HARV_002","individualID":"NEON1","date":"2014-01-01","taxonID":"PIRU"}]
    s=s+[{"site":"HARV","plotID":"HARV_002","eventID":e,"individualID":"NEON1","tempStemID":"1"} for e in ("F2014","F2024")]
    x=g.audit_identity_source(p+more,m,s)
    assert x["n_source_identity_candidates_with_4_years_or_longer"]==0
    assert x["failure_and_exclusion_counts"]["same_individualID_appears_in_multiple_plots"]==2


def test_latest_mapping_correction_2026_schema_without_eventID():
    p,m,s=fixtures()
    m[1]["taxonID"]="NEW-TAXON-ID"
    x=g.audit_identity_source(p,m,s)
    assert x["n_unverified_NEON_taxonIDs_by_site"]["HARV"]==1
    assert x["n_source_identity_candidates_with_4_years_or_longer"]==1


def test_fixed_panel_not_five_FIA_species_claim():
    assert g.SITES==("HARV","SCBI")
    assert g.FIA_CODES==("129","316","802","833","837")
    assert g.BLOCKED_RESULT=="source_only_tagged_individual_candidates_not_demographic_effect"
    assert g.MIN_GAP_YEARS==4
