import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "configs/product_a_v2_8_2_fresh_confirmation_taxa.csv"
PILOT = ROOT / "configs/product_a_pilot_taxa_v1.csv"
CONSUMED = ROOT / "configs/product_a_v2_7_1_fresh_taxon_candidates.csv"
CONTRACT = ROOT / "configs/product_a_v2_8_2_fresh_source_acquisition_contract.json"
EXECUTION = ROOT / "configs/product_a_v2_8_2_fresh_source_execution.json"
WORKFLOW = ROOT / ".github/workflows/product-a-v2-8-2-fresh-source-acquisition.yml"

EXPECTED_PANEL_SHA = "835059c9ca4328253ea306f7b4027615007d558f6999a1049677d8903ce4a3c1"
EXPECTED_CITATION_SHA = "022a524b59c4c037b28f252c08294e0f22c5eb7b3bce5c52a0a5fc6016f17050"
EXPECTED_STRATA = {
    "arid_shrub",
    "boreal_conifer",
    "boreal_temperate_conifer",
    "fern",
    "montane_tree",
    "southern_temperate_tree",
    "temperate_annual_herb",
    "temperate_deciduous_tree",
    "temperate_shrub",
    "tropical_mangrove",
    "wetland_emergent",
    "wetland_grass",
}


def test_v282_source_panel_is_exact_eligibility_artifact_and_fresh():
    panel = pd.read_csv(PANEL)
    pilot = pd.read_csv(PILOT)
    consumed = pd.read_csv(CONSUMED)

    assert hashlib.sha256(PANEL.read_bytes()).hexdigest() == EXPECTED_PANEL_SHA
    assert len(panel) == 12
    assert panel["scientific_name"].is_unique
    assert panel["validation_stratum"].is_unique
    assert set(panel["validation_stratum"]) == EXPECTED_STRATA
    assert set(panel["candidate_rank"].astype(int)) == {1}
    assert (panel["n_occurrences"].astype(int) >= 80).all()
    assert (panel["n_unique_0_05_degree_cells"].astype(int) >= 50).all()
    assert set(panel["scientific_name"]).isdisjoint(set(pilot["scientific_name"]))
    assert set(panel["scientific_name"]).isdisjoint(set(consumed["scientific_name"]))


def test_v282_source_contract_is_source_only_and_inherits_exact_transport():
    contract = json.loads(CONTRACT.read_text())
    assert contract["purpose"] == "product_a_v2_8_2_fresh_raw_source_acquisition_contract"
    assert contract["tracks_issue"] == 148
    assert contract["predeclared_before_v2_8_2_raw_source_outcome"] is True
    assert contract["execution_source_pinned"] is False
    assert contract["execution_allowed_before_exact_source_pin"] is False

    endpoint = contract["eligibility_endpoint"]
    assert endpoint["workflow_run_id"] == 32988143625
    assert endpoint["artifact_id"] == 9613925063
    assert endpoint["artifact_digest"] == "sha256:9a97889c0b69048df8142f2e59d4d860682670f13e2781440520c03fa8401dab"
    assert endpoint["status"] == "available"
    assert endpoint["selected_panel_sha256"] == EXPECTED_PANEL_SHA
    assert endpoint["selected_global_sealed_fraction"] == 0.25
    assert endpoint["unavailable_strata"] == []

    snapshot = contract["snapshot"]
    assert snapshot == {
        "date": "2026-08-01",
        "doi": "10.15468/dl.fs3btq",
        "citation_sha256": EXPECTED_CITATION_SHA,
        "region": "us-east-1",
        "temporal_independence_claim_allowed": False,
    }

    panel = contract["fresh_taxon_panel"]
    assert panel["path"] == "configs/product_a_v2_8_2_fresh_confirmation_taxa.csv"
    assert panel["sha256"] == EXPECTED_PANEL_SHA
    assert panel["n_taxa"] == 12
    assert panel["selected_candidate_rank"] == 1
    assert panel["post_selection_replacement_allowed"] is False

    transport = contract["parallel_transport"]
    assert transport["chunk_count"] == 16
    assert transport["snapshot_shards_partitioned_exactly_once"] is True
    assert transport["chunking_changes_scientific_query"] is False
    assert transport["aggregate_requires_complete_chunk_indices"] is True
    assert transport["aggregate_requires_common_snapshot_catalog_sha256"] is True

    focal = contract["focal_source"]
    assert focal["thinning_at_source_acquisition"] is False
    assert focal["thinning_occurs_later_before_outer_split"] is True
    assert focal["historical_focal_artifact_reused"] is False

    target = contract["target_group_source"]
    assert target["kingdom"] == "Plantae"
    assert target["exclude_taxa_sha256"] == EXPECTED_PANEL_SHA
    assert target["one_per_grid_cell_degrees"] == 0.05
    assert target["source_independent_of_focal_occurrence_geography"] is True
    assert target["historical_target_artifact_reused"] is False

    assert all(value is False for value in contract["information_barrier"].values())


def test_v282_execution_is_closed_or_exactly_pinned_but_never_crosses_scope():
    execution = json.loads(EXECUTION.read_text())
    assert execution["purpose"] == "product_a_v2_8_2_fresh_raw_source_execution_authorization"
    assert execution["tracks_issue"] == 148
    assert execution["one_shot"] is True
    assert execution["selected_panel_sha256"] == EXPECTED_PANEL_SHA
    assert execution["selected_global_sealed_fraction"] == 0.25

    barrier_keys = (
        "environmental_values_allowed",
        "candidate_model_fitting_allowed",
        "candidate_scores_allowed",
        "sealed_ecological_outcomes_allowed",
        "scientific_confirmation_allowed",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    )
    for key in barrier_keys:
        assert execution[key] is False

    pin_keys = (
        "workflow_blob_sha",
        "contract_blob_sha",
        "panel_blob_sha",
        "focal_module_blob_sha",
        "target_parallel_module_blob_sha",
        "target_core_module_blob_sha",
    )
    if execution["execution_allowed"] is False:
        assert execution["implementation_sha"] is None
        assert execution["frozen_ref"] is None
        assert all(execution[key] is None for key in pin_keys)
    else:
        assert execution["execution_allowed"] is True
        assert isinstance(execution["implementation_sha"], str)
        assert len(execution["implementation_sha"]) == 40
        assert execution["frozen_ref"].startswith("frozen/product-a-v2-8-2-fresh-source-")
        for key in pin_keys:
            assert isinstance(execution[key], str)
            assert len(execution[key]) == 40


def test_v282_source_workflow_is_manual_external_authorization_only():
    text = WORKFLOW.read_text()
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "authorization_commit_sha" in text
    assert "authorization_blob_sha" in text
    assert "expected_runtime_sha" in text
    assert "expected_frozen_ref" in text
    assert "python -m sdmr.fresh_focal_parallel chunk" in text
    assert "python -m sdmr.fresh_focal_parallel aggregate" in text
    assert "sdmr-gbif-target-footprint-parallel chunk" in text
    assert "sdmr-gbif-target-footprint-parallel aggregate" in text
    assert "--chunk-count 16" in text
    assert "--grid-cell-degrees 0.05" in text
    assert "product-a-v2-8-2-fresh-focal-source-2026-08-01" in text
    assert "product-a-v2-8-2-fresh-target-source-2026-08-01" in text
    assert "product-a-v2-8-2-fresh-raw-source-receipt" in text
    assert "scientific_confirmation_allowed': False" in text
    assert "scientific_promotion_allowed': False" in text
    assert "product_b_unblocked': False" in text
