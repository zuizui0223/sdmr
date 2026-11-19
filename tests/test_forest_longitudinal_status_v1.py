"""Published source codebook semantics only: no original tree response rows."""
import pytest

from sdmr.forest_longitudinal_status_v1 import (
    BCI, HARVARD, map_tree_status, source_tree_identity,
    classify_census_transition,
)


def test_bci_missing_is_not_death_and_future_recruit_not_absence():
    assert map_tree_status(BCI, "missing").meaning == "missing"
    assert map_tree_status(BCI, "dead").meaning == "reported_dead_mixed"
    assert map_tree_status(BCI, "future recruit").meaning == "not_yet_recruited"


def test_harvard_verified_visible_and_unfound_deaths_remain_separate():
    assert map_tree_status(HARVARD, "DC").meaning == "observed_dead"
    assert map_tree_status(HARVARD, "DS").certainty == "dead_standing"
    assert map_tree_status(HARVARD, "DN").meaning == "reported_dead_unfound"
    assert map_tree_status(HARVARD, "AU").meaning == "alive_with_health_issue"
    assert map_tree_status(HARVARD, "A").meaning == "alive"


def test_tree_identity_needs_plot_and_tag_not_stem_cross_census():
    assert source_tree_identity(BCI, "Zetek", "12345") == (
        BCI, "Zetek", "12345"
    )
    assert source_tree_identity(BCI, "Pearson", "12345") != (
        BCI, "Zetek", "12345"
    )
    with pytest.raises(ValueError, match="cannot be linked"):
        source_tree_identity(BCI, "Zetek", "12345", stem_tag="stem1")


def test_bci_missing_and_author_reported_death_are_not_strict_mortality():
    missing = classify_census_transition(BCI, 2004, 2014, "alive", "missing")
    reported = classify_census_transition(BCI, 2014, 2025, "alive", "dead")
    assert missing.status == "missing_outcome_not_automatically_death"
    assert reported.status == "reported_death_not_directly_certified"
    assert not missing.population_mortality_estimated
    assert not reported.biological_result_opening_authorized


def test_harvard_visible_death_only_a_candidate_without_effort_exposure():
    r = classify_census_transition(HARVARD, 2021, 2024, "AU", "DS")
    assert r.status == "source_observed_dead_candidate"
    assert not r.actual_exposure_time_established
    assert not r.population_mortality_estimated
    assert not r.biological_result_opening_authorized


def test_later_recruit_does_not_create_historical_zero():
    r = classify_census_transition(
        BCI, 2004, 2014, "future recruit", "alive"
    )
    assert r.status == "not_at_risk_until_recruitment"
    assert not r.population_mortality_estimated


def test_no_unregistered_status_or_drifted_date_protocol():
    with pytest.raises(ValueError, match="unregistered"):
        map_tree_status(BCI, "D")
    with pytest.raises(ValueError, match="unregistered"):
        map_tree_status(HARVARD, "dead")
    with pytest.raises(ValueError, match="chronological"):
        classify_census_transition(HARVARD, 2024, 2021, "A", "DS")
    with pytest.raises(ValueError, match="chronological"):
        classify_census_transition(BCI, 2005, 2014, "alive", "dead")


def test_mixed_source_codes_are_never_interchangeable():
    with pytest.raises(ValueError, match="unregistered"):
        map_tree_status(BCI, "DN")
    with pytest.raises(ValueError, match="unregistered"):
        map_tree_status(HARVARD, "missing")
