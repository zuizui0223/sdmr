from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.cross_taxon_target_footprint_parallel import _read_groups, _read_taxa

ROOT = Path(__file__).resolve().parents[1]
TAXA = ROOT / "configs/product_a_real_positive_control_nonplant_taxa_v1.csv"
GROUPS = ROOT / "configs/product_a_real_positive_control_nonplant_target_groups_v1.csv"
CONTRACT = ROOT / "configs/product_a_real_positive_control_nonplant_contract_v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_cross_taxon_positive_controls_are_frozen_and_balanced():
    contract = json.loads(CONTRACT.read_text())
    taxa = pd.read_csv(TAXA)
    groups = pd.read_csv(GROUPS)
    assert contract["purpose"] == "product_a_real_positive_control_process_membership_v1"
    assert contract["scope"] == "cross_taxon_nonplant_v1"
    assert contract["frozen_before_sdm_outcome"] is True
    assert contract["external_truth_role"] == "positive_control_only_no_negative_process_truth"
    assert _sha(TAXA) == contract["source"]["taxa_sha256"]
    assert _sha(GROUPS) == contract["source"]["target_groups_sha256"]
    assert len(taxa) == 4
    assert taxa["scientific_name"].nunique() == 4
    assert taxa["target_group"].nunique() == 4
    assert taxa["expected_process"].value_counts().to_dict() == {"temperature": 2, "water": 2}
    assert set(taxa["target_group"]) == {"Insecta", "Mammalia", "Amphibia", "Gastropoda"}
    assert set(groups["taxon_rank"]) == {"class"}
    assert set(groups["target_group"]) == set(taxa["target_group"])
    assert not taxa["scientific_name"].str.contains("Quercus|Silene|Plantago", regex=True).any()


def test_cross_taxon_source_readers_lock_four_classes_and_four_species():
    groups, group_sha = _read_groups(GROUPS)
    names, taxa_sha = _read_taxa(TAXA)
    contract = json.loads(CONTRACT.read_text())
    assert len(groups) == 4
    assert len(names) == 4
    assert group_sha == contract["source"]["target_groups_sha256"]
    assert taxa_sha == contract["source"]["taxa_sha256"]


def test_cross_taxon_recovery_rule_matches_plant_positive_control_logic():
    contract = json.loads(CONTRACT.read_text())
    rule = contract["positive_control_recovery_rule"]
    assert rule["expected_process_mean_score_must_be_positive"] is True
    assert rule["expected_process_positive_m_count_min"] == 2
    assert rule["primary_overall_recovery_min"] == 0.75
    assert rule["minimum_recovered_per_process_group"] == 1
    assert rule["eligible_taxa_denominator_is_frozen_four"] is True
    assert rule["unavailable_taxon_counts_as_not_recovered"] is True
    assert rule["competing_process_score_is_descriptive_only"] is True


def test_cross_taxon_governance_prevents_post_outcome_taxonomic_rescue():
    contract = json.loads(CONTRACT.read_text())
    governance = contract["governance"]
    assert governance["no_taxon_drop_after_outcome"] is True
    assert governance["no_external_process_label_change"] is True
    assert governance["no_target_group_change_after_outcome"] is True
    assert governance["no_predictor_group_change_after_outcome"] is True
    assert governance["no_threshold_or_recovery_rule_change_after_outcome"] is True
    assert governance["no_favorable_m_subset"] is True
