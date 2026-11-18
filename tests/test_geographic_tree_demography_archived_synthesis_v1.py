"""Frozen real FIA aggregate audit and exploratory cross-taxon synthesis tests."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "experiments" / "geographic_tree_demography_archived_synthesis_v1.py"
spec = importlib.util.spec_from_file_location("geo_tree_synth", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SRC = ROOT / "evidence/geographic_tree_demography_first_response_v1/aggregate.json"
OUT = ROOT / "results/fia_archived_regional_growth_status_synthesis_v1.json"


def load_data():
    data = SRC.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def test_frozen_source_corrected_cohort_and_hash():
    data, sha = load_data()
    assert sha == mod.ARCHIVE_SHA256
    rows, std = mod.validate(data)
    assert set(rows) == set(mod.STATES)
    assert len(std) == 13
    assert len(data["state_summaries"]) == 3
    assert sum(len(s["taxa"]) for s in data["state_summaries"]) == 39
    assert "43" not in rows["RI"]  # old 22-taxon display was incorrect


def test_all_original_growth_pairs_preserved():
    data, sha = load_data()
    result = mod.synthesize(data, archived_sha256=sha)
    assert {k: v["growth_pairs"] for k, v in result["states"].items()} == {"RI": 5190, "VA": 100189, "WI": 202802}
    assert sum(v["growth_pairs"] for v in result["states"].values()) == 308181
    assert len(result["species"]) == 13
    assert result["n_species_with_shared_size_bins"] == 9


def test_regional_direction_and_minimum_size_bin_sensitivity():
    data, sha = load_data()
    result = mod.synthesize(data, archived_sha256=sha)
    comparison = next(r for r in result["state_pair_descriptive_comparisons"] if r["first_state"] == "RI" and r["second_state"] == "WI")
    assert comparison["n_taxa_with_common_size_growth"] == 9
    assert comparison["higher_growth_in_second_state"] == 7
    assert comparison["lower_growth_in_second_state"] == 2
    assert [(r["taxa"],r["growth_higher_in_second_state"]) for r in comparison["shared_size_band_sensitivity"]] == [(9, 7), (7, 6), (4, 4)]
    assert len(result["strict_increasing_growth_ri_va_wi_species"]) == 6
    assert result["n_pre_response_frozen_species"] == 13
    assert result["n_species_with_2plus_shared_size_bins"] == 7
    assert result["n_species_with_2plus_bands_all_WI_above_RI"] == 6
    assert result["n_total_common_size_bands_across_species"] == 21
    assert result["n_common_size_bands_WI_growth_higher"] == 19


def test_growth_and_observed_dead_status_are_not_conflated():
    data, sha = load_data()
    result = mod.synthesize(data, archived_sha256=sha)
    for comparison in result["state_pair_descriptive_comparisons"]:
        sub = comparison["among_growth_comparable_taxa"]
        assert sum(sub.values()) == 9
        assert sub["higher_growth_and_higher_linked_dead_fraction"] == 3
        assert sub["higher_growth_and_lower_linked_dead_fraction"] == 4
    assert result["states"]["RI"]["not_currently_tallied_excluded"] > 0
    assert result["status"] == "post_outcome_descriptive_no_confirmatory_promotion"


def test_four_species_cannot_appear_as_zero_growth():
    data, sha = load_data()
    result = mod.synthesize(data, archived_sha256=sha)
    excluded = [x for x in result["species"] if x["n_shared_size_bands"] == 0]
    assert len(excluded) == 4
    for x in excluded:
        assert x["growth_direction_in_RI_VA_WI_order"] == "not_estimable_common_size_band"
        assert all(v is None for v in x["size_standardized_log_growth_per_year"].values())
        assert all(x["growth_pairs_by_state"][s] >= 0 for s in mod.STATES)


def test_rejects_source_sha_or_fabricated_unseen_taxon():
    data, _ = load_data()
    with pytest.raises(ValueError, match="digest"):
        mod.synthesize(data, archived_sha256="tampered")
    data["state_summaries"][0]["taxa"][0]["spcd"] = "43"
    with pytest.raises(ValueError, match="non-nominated"):
        mod.validate(data)


def test_rejects_unlinked_status_or_growth_denominator_mismatch():
    data, _ = load_data()
    data["state_summaries"][0]["taxa"][0]["n_observed_live_to_dead"] += 1
    with pytest.raises(ValueError, match="decomposition"):
        mod.validate(data)
    data, _ = load_data()
    data["state_summaries"][0]["taxa"][0]["n_growth_pairs_with_diameter"] += 1
    with pytest.raises(ValueError, match="denominator"):
        mod.validate(data)


def test_rejects_posthoc_size_band_entry_or_drift():
    data, _ = load_data()
    row = data["size_standardized"]["taxa"][0]
    row["n_shared_size_bands"] += 1
    with pytest.raises(ValueError, match="common size"):
        mod.validate(data)
    data, _ = load_data()
    row = next(r for r in data["size_standardized"]["taxa"] if r["spcd"] == "316")
    row["observed_size_standardized_mean_log_diameter_change_by_state"]["RI"] += 0.01
    with pytest.raises(ValueError, match="archived standardized growth"):
        mod.validate(data)


def test_rejects_changed_state_order_and_zip_source():
    data, _ = load_data()
    data["state_summaries"].reverse()
    with pytest.raises(ValueError, match="three-state"):
        mod.validate(data)
    data, _ = load_data()
    data["sources"]["original_source_zip_sha_by_state"]["VA"] = "different"
    with pytest.raises(ValueError, match="provenance"):
        mod.validate(data)


def test_versioned_synthesis_reproduces_exactly_without_refitting():
    data, sha = load_data()
    result = mod.synthesize(data, archived_sha256=sha)
    assert result == json.loads(OUT.read_text())
    assert result["provenance"]["source_artifact_id"] == 12183086705
    assert result["status"] == "post_outcome_descriptive_no_confirmatory_promotion"
    assert not any(k in result for k in ("p_value", "climate_attribution", "physiological_driver", "evolutionary_change"))
