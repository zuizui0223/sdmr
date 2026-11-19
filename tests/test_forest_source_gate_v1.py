"""Response-blind forest admission tests; ZERO ecological model fits."""
from dataclasses import replace, asdict
import json
from pathlib import Path

import pytest

from sdmr.forest_source_gate_v1 import (
    ForestSourceProfile,
    assess_forest_source,
    source_catalog_receipt,
)

CATALOG = Path("configs/forest_source_gate_archived_sources_v1.json")


def _source(**kw):
    base = dict(
        source_id="synthetic_metadata_valid",
        study_reference="https://example.org/known-source",
        evidence_family_id="synthetic_source_not_biology",
        publisher_source="test_fixture_only",
        receipt_role="original_source",
        receipt_sha256="a" * 64,
        endpoint="recorded_tree_status",
        operator="future_demography",
        observation_mode="unconditional",
        sampling_frame="complete_including_zeros",
        effort_status="verified",
        attrition_status="accounted",
        taxon_status="verified_for_declared_response",
        block_status="verified_independent",
        process_carriers="complete",
        response_state="unopened",
        design_state="outcome_blind",
        n_source_units=60,
        n_eligible_units=60,
        n_blocks_reported=6,
        min_block_units=10,
        source_identity_verified=True,
        temporal_alignment_verified=True,
        notes="Synthetic metadata only; all validation fields are independent of Y",
    )
    return ForestSourceProfile(**(base | kw))


def test_ready_source_only_authorizes_protocol_drafting_not_response_opening():
    result = assess_forest_source(_source())
    assert result.status == "metadata_ready_for_separate_protocol_freeze"
    assert result.reasons == ()
    assert result.observation_process_adequate
    assert result.process_carriers_complete
    assert result.response_opening_authorized is False
    assert result.biological_effect_estimated is False


def test_true_zero_requires_sampled_opportunity_and_positive_effort():
    with pytest.raises(ValueError, match="audited zeros AND effort"):
        _source(sampling_frame="detected_only")
    with pytest.raises(ValueError, match="audited zeros AND effort"):
        _source(effort_status="unknown")
    assert assess_forest_source(
        _source(
            observation_mode="capture_conditional",
            sampling_frame="detected_only",
            effort_status="verified",
        )
    ).status == "observation_unresolved"


def test_survivors_are_not_an_unconditional_demographic_frame():
    conditional = _source(
        observation_mode="survivor_conditional",
        sampling_frame="survivors_only",
        attrition_status="survivor_selected",
        effort_status="conditional",
    )
    result = assess_forest_source(conditional)
    assert "observation_selection_or_zero_frame_unresolved" in result.reasons
    assert not result.observation_process_adequate
    with pytest.raises(ValueError, match="survivors_only"):
        _source(observation_mode="survivor_conditional")


def test_positive_prediction_information_cannot_bypass_source_missingness():
    # The gate has no predictions or effects in its inputs. No numeric effect
    # can turn a source stop into biological support.
    result = assess_forest_source(_source(
        n_blocks_reported=6, min_block_units=0,
        block_status="single_site_block",
        process_carriers="partial",
    ))
    assert result.status == "not_estimable_under_new_protocol"
    assert result.response_opening_authorized is False


def test_prior_opened_outcomes_are_not_fresh_evidence():
    result = assess_forest_source(_source(
        response_state="previously_opened",
        design_state="historical_outcome_exposed",
    ))
    assert result.status == "retrospective_only"
    assert "prior_response_exposed_no_fresh_confirmation" in result.reasons
    assert not result.response_opening_authorized


def test_distinct_ontology_and_grouping_holds():
    result = assess_forest_source(_source(
        taxon_status="partial_format_sensitivity",
        block_status="nested_parent_unknown",
    ))
    assert result.status == "source_or_ontology_hold"
    assert "response_ontology_partial_format_sensitivity" in result.reasons
    assert "block_design_nested_parent_unknown" in result.reasons


def test_zero_eligible_units_remain_source_stop_not_zero_ecological_effect():
    result = assess_forest_source(_source(
        n_eligible_units=0,
        min_block_units=0,
    ))
    assert result.status == "not_estimable_under_new_protocol"
    assert "zero_eligible_observation_units" in result.reasons
    assert result.biological_effect_estimated is False


def test_source_manifest_preserves_all_five_original_research_lineages():
    source = json.loads(CATALOG.read_text())
    output = source_catalog_receipt(source)
    assert output["n_source_profiles"] == 5
    assert output["n_protocol_ready"] == 0
    assert output["n_biological_outcomes_opened"] == 0
    assert output["n_new_models_fit"] == 0
    assert output["no_existing_result_reclassified"] is True
    by_source = {r["source_id"]: r for r in output["decisions"]}
    assert by_source["structural_finland_deadwood_guild_142"]["status"] == "not_estimable_under_new_protocol"
    assert by_source["structural_carpathian_weiss170_116"]["status"] == "source_or_ontology_hold"
    assert by_source["structural_england_nfi2026_canopy_malaise"]["status"] == "not_estimable_under_new_protocol"
    assert by_source["sdmr_fia_va_wi_selected_survivor_growth"]["status"] == "source_or_ontology_hold"
    assert by_source["structural_neon_2014_2018_vst_forest_link"]["status"] == "not_estimable_under_new_protocol"
    assert all(not r["response_opening_authorized"] for r in output["decisions"])
    assert all(not r["biological_effect_estimated"] for r in output["decisions"])


def test_no_source_response_or_loss_columns_can_enter_metadata_gate():
    source = json.loads(CATALOG.read_text())
    source["sources"][0]["growth"] = +2.75
    with pytest.raises(ValueError, match="no biological outcome columns"):
        source_catalog_receipt(source)
    source = json.loads(CATALOG.read_text())
    source["sources"][0]["response_loss"] = 0.001
    with pytest.raises(ValueError, match="no biological outcome columns"):
        source_catalog_receipt(source)


def test_typed_profile_validation_refuses_contradictory_metadata():
    with pytest.raises(ValueError, match="eligible units exceed"):
        _source(n_eligible_units=100)
    with pytest.raises(ValueError, match="paired"):
        _source(n_blocks_reported=6, min_block_units=None)
    with pytest.raises(ValueError, match="lowercase"):
        _source(receipt_sha256="X"*64)
    with pytest.raises(ValueError, match="outcome-exposed"):
        _source(response_state="unopened", design_state="historical_outcome_exposed")



def test_metadata_catalog_rejects_top_level_outcomes_and_threshold_changes():
    c = json.loads(CATALOG.read_text())
    c["unopened_growth_responses"] = [100.0]
    with pytest.raises(ValueError, match="top-level schema mismatch"):
        source_catalog_receipt(c)
    c = json.loads(CATALOG.read_text())
    c["minimum_per_block"] = 1
    with pytest.raises(ValueError, match="thresholds differ"):
        source_catalog_receipt(c)


def test_source_only_catalog_rejects_duplicate_groups_and_unknown_schemas():
    c = json.loads(CATALOG.read_text())
    c["sources"].append(c["sources"][0])
    with pytest.raises(ValueError, match="duplicate source ID"):
        source_catalog_receipt(c)
    c = json.loads(CATALOG.read_text())
    c["schema"] = "other_schema"
    with pytest.raises(ValueError, match="schema"):
        source_catalog_receipt(c)
