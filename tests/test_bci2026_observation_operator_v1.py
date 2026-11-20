"""Synthetic BCI observation-state logic. Never opens any Dryad file."""
import pytest
from sdmr.bci2026_observation_operator_v1 import (
    TreeKey,classify_tree_transition,inspect_original_census_visit_date,
    prior_exposure_admission,
)

def test_plot_tag_identity_never_tag_alone_or_unstable_stem_rows():
    assert TreeKey("AVA","0019").unique_id=="AVA-0019"
    assert TreeKey("Pearson","0019").unique_id=="Pearson-0019"
    assert TreeKey("AVA","0019")!=TreeKey("Pearson","0019")
    for plot,tag in (("unknown","19"),("AVA","A19"),("AVA",19),
                     ("AVA"," 0019")):
        with pytest.raises(ValueError):
            TreeKey(plot,tag)

def test_missing_is_unknown_not_dead_nor_alive():
    x=classify_tree_transition(
        first_year=2004,next_year=2014,first_status="alive",
        next_status="missing")
    assert x.baseline_alive_at_risk
    assert x.strict_binary_Y is None and not x.strict_observed_dead
    assert x.missing_is_not_observed_dead
    assert not x.new_ecological_effect_estimated

def test_author_dead_mixes_direct_and_inferred_death():
    x=classify_tree_transition(
        first_year=2014,next_year=2025,first_status="alive",
        next_status="dead")
    assert x.author_coded_dead
    assert x.strict_observed_dead is False
    assert x.strict_binary_Y is None
    assert x.status=="unknown_direct_vs_inferred_death"
    assert x.sampling_effort_audited is False

def test_future_recruit_is_not_surveyed_zero():
    x=classify_tree_transition(
        first_year=2004,next_year=2014,first_status="future recruit",
        next_status="alive")
    assert not x.baseline_alive_at_risk
    assert x.strict_binary_Y is None
    assert x.future_recruit_is_not_zero
    y=classify_tree_transition(
        first_year=2014,next_year=2025,first_status="alive",
        next_status="future recruit")
    assert y.status.startswith("ontology_conflict")
    assert y.strict_binary_Y is None

def test_aliveness_is_source_coded_not_complete_effort_claim():
    x=classify_tree_transition(
        first_year=2014,next_year=2025,first_status="alive",
        next_status="alive")
    assert x.strict_binary_Y==0
    assert x.status=="source_coded_next_alive"
    assert not x.sampling_effort_audited

def test_malformed_temporal_sequence_and_status_ontology_fail():
    for first,next_ in ((2004,2025),(2025,2014),(2014,2014)):
        with pytest.raises(ValueError,match="adjacent"):
            classify_tree_transition(
                first_year=first,next_year=next_,first_status="alive",
                next_status="alive")
    with pytest.raises(ValueError,match="unrecognized"):
        classify_tree_transition(
            first_year=2014,next_year=2025,first_status="alive",
            next_status="D")

def test_original_2004_label_mostly_2005_no_automatic_10y_annualization():
    d=inspect_original_census_visit_date(census=2004,date_text="20050719")
    assert d["visit_year"]==2005
    assert not d["annual_rate_identified"]
    d2=inspect_original_census_visit_date(census=2004,date_text=None)
    assert d2["visit_year"] is None
    assert not d2["annual_rate_identified"]
    with pytest.raises(ValueError,match="conflict"):
        inspect_original_census_visit_date(census=2014,date_text="20250101")

def test_2025_crown_exposure_is_never_baseline_predictor_before_outcome():
    for year in (2004,2014,2025):
        x=prior_exposure_admission(baseline_year=year)
        assert not x["admitted_as_baseline_mortality_predictor"]
        assert x["measured_only_on_recorded_2025_alive"]
        assert not x["causal_exposure_effect_identified"]
    with pytest.raises(ValueError,match="only_2025"):
        prior_exposure_admission(baseline_year=2014,measured_year=2014)
