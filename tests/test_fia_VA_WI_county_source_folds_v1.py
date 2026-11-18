"""No outcome use: county-block source readiness for VA/WI response design."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import fia_VA_WI_county_source_folds_v1 as mod


def conf():
    return json.loads((ROOT / "configs/fia_joint_climate_support_gate_v1.json").read_text())


def source_rows(taxa=("129",), n_counties=60):
    samples = []
    for sp in taxa:
        for state, prefix in (("VA", "51"), ("WI", "55")):
            for county in range(1, n_counties + 1):
                fips = f"{prefix}{county:03d}"
                for plot in range(5):
                    samples.append({
                        "species_code": sp,
                        "state": state,
                        "county_fips": fips,
                        "plot_chain_id": f"{state}-{county}-{plot}",
                        "interval_id": "source-1",
                        "interval_end_year": 2010,
                        "temperature_anomaly_c": 0.5 + 2*(county % 2),
                        "precipitation_anomaly_mm": 40.0 + 200*(county % 2),
                    })
    return samples


def test_county_split_matches_original_geographic_hash_and_no_leakage():
    for county in ("51001", "51049", "55001", "55023"):
        expected = int.from_bytes(hashlib.sha256(county.encode()).digest()[:4], "big") % 5
        assert mod.county_fold(county) == expected
    with pytest.raises(ValueError, match="five-digit"):
        mod.county_fold("51")
    cfg = conf()
    output = mod.evaluate(source_rows(), cfg)
    assert len(output["folds"]) == 13*5
    assert output["n_taxa_declared"] == 13
    assert output["VA_WI_train_only_no_heldout_environment_used_for_bin_discovery"] is True
    assert all(x["withheld_counties_fully_excluded_from_train"] for x in output["folds"])


def test_denominator_retains_all_missing_taxa_as_not_ready():
    output = mod.evaluate(source_rows(), conf())
    r = [z for z in output["folds"] if z["species_code"] == "129"]
    assert len(r) == 5
    assert all(z["status"] == "county_source_ready_for_response_design" for z in r)
    empty = [z for z in output["folds"] if z["species_code"] == "316"]
    assert len(empty) == 5
    assert all(z["status"] == "not_source_ready_for_response_design" for z in empty)
    assert output["source_ready_primary_taxon_fold_cells"] == 5
    assert output["biological_promotion_authorized"] is False


def test_outer_fold_climate_novelty_cannot_be_inferred_as_supported():
    cfg = conf()
    samples = source_rows()
    # All observations of one held-out VA county have unique climate.
    held = "51001"
    for s in samples:
        if s["county_fips"] == held:
            s["temperature_anomaly_c"] = 99.0
    output = mod.evaluate(samples, cfg)
    k = mod.county_fold(held)
    v = next(x for x in output["folds"] if x["species_code"] == "129" and x["fixed_county_fold"] == k)
    assert v["regions"]["VA"]["heldout_plot_source_coverage_fraction"] < 1.0
    assert v["VA_WI_train_joint_bins"] >= 1


def test_missing_heldout_state_cannot_be_passed_as_empty_zero():
    cfg = conf()
    data = [z for z in source_rows(n_counties=30) if z["state"] == "VA"]
    result = mod.evaluate(data, cfg)
    for z in result["folds"]:
        if z["species_code"] == "129":
            assert z["status"] == "not_source_ready_for_response_design"
            assert "WI:few_heldout_counties" in z["reasons"]
            assert z["regions"]["WI"]["heldout_plot_source_coverage_fraction"] is None
            assert z["regions"]["WI"]["heldout_source_coverage_missing_not_zero"] is True


def test_repeated_plot_intervals_not_inflated_as_new_plots():
    cfg = conf()
    data = source_rows()
    before = mod.evaluate(data, cfg)
    repeat = [{**r, "interval_id": "source-2"} for r in data]
    after = mod.evaluate(data + repeat, cfg)
    for a, b in zip(before["folds"], after["folds"]):
        assert a["species_code"] == b["species_code"] and a["fixed_county_fold"] == b["fixed_county_fold"]
        for state in ("VA", "WI"):
            assert a["regions"][state]["test_unique_plot_chains"] == b["regions"][state]["test_unique_plot_chains"]
            assert a["regions"][state]["test_intervals"] * 2 == b["regions"][state]["test_intervals"]
            assert a["regions"][state]["heldout_plot_source_coverage_fraction"] == b["regions"][state]["heldout_plot_source_coverage_fraction"]


def test_source_not_a_demographic_result_and_primary_five_frozen():
    result = mod.evaluate(source_rows(("129", "316", "802", "833", "837")), conf())
    assert result["source_ready_primary_taxon_fold_cells"] == 25
    assert result["n_taxon_fold_cells"] == 65
    assert result["new_growth_or_survival_outcome_read"] is False
    assert result["postsource_design_thresholds_not_prospective_validation"] is True
    assert tuple(result["primary_taxa"]) == mod.PRIMARY_SPECIES
    assert result["product_A_M5_preserved_and_product_B_blocked"] is True


def test_tampered_source_artifact_cannot_be_used(tmp_path):
    folder = tmp_path / "source"
    folder.mkdir()
    (folder / "fia_new_cohort_joint_source_only_county_stable_v2.csv").write_text("tampered")
    (folder / "derived_receipt.json").write_text("{}")
    with pytest.raises(ValueError, match="SHA mismatch"):
        mod.run(folder, ROOT / "configs/fia_joint_climate_support_gate_v1.json")
