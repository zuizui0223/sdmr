"""Source-only VA/WI->RI projection tests; no outcome or remote source access."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import fia_external_region_support_v1 as probe


def config():
    return json.loads((ROOT / "configs/fia_joint_climate_support_gate_v1.json").read_text())


def synthetic():
    rows = []
    for state, pref in (("RI", "44"), ("VA", "51"), ("WI", "55")):
        for county in range(1, 6):
            for plot in range(5):
                band = (county % 2)
                rows.append({
                    "species_code": "129", "state": state,
                    "county_fips": f"{pref}{county:03d}",
                    "plot_chain_id": f"{state}-{county}-{plot}",
                    "interval_id": "i1",
                    "interval_end_year": 2010,
                    "temperature_anomaly_c": 0.25 + 2 * band,
                    "precipitation_anomaly_mm": 10 + 200 * band,
                })
    return rows


def test_regions_define_training_bins_without_RI_input():
    cfg = config()
    cfg["species_codes"] = ["129"]
    data = synthetic()
    same = probe.phase_projection(data, cfg, (0., 0., 1990))["species"][0]
    assert same["VA_WI_qualified_joint_time_bins"] == 2
    assert same["RI_unique_plot_coverage_fraction"] == 1
    assert same["RI_counties_projected"] == 5
    altered = copy.deepcopy(data)
    for r in altered:
        if r["state"] == "RI":
            r["temperature_anomaly_c"] += 100
    different = probe.phase_projection(altered, cfg, (0., 0., 1990))["species"][0]
    assert different["VA_WI_qualified_joint_time_bins"] == same["VA_WI_qualified_joint_time_bins"]
    assert different["RI_unique_plot_coverage_fraction"] == 0
    assert different["VA_WI_training_only"] is True


def test_joint_time_support_requires_same_period():
    cfg = config()
    cfg["species_codes"] = ["129"]
    data = synthetic()
    for r in data:
        if r["state"] == "RI":
            r["interval_end_year"] = 2025
    a = probe.phase_projection(data, cfg, (0., 0., 1990))["species"][0]
    assert a["VA_WI_qualified_joint_time_bins"] == 2
    assert a["RI_unique_plot_coverage_fraction"] == 0


def test_plot_revisit_cannot_inflate_effective_counties():
    cfg = config()
    cfg["species_codes"] = ["129"]
    rows = synthetic()
    base = probe.phase_projection(rows, cfg, (0., 0., 1990))["species"][0]
    extra = [dict(r, interval_id="i2") for r in rows if r["state"] == "RI"]
    repeated = probe.phase_projection(rows + extra, cfg, (0., 0., 1990))["species"][0]
    assert base["RI_unique_plots_total"] == repeated["RI_unique_plots_total"] == 25
    assert base["RI_effective_counties_plot_HHI"] == repeated["RI_effective_counties_plot_HHI"] == 5
    assert repeated["RI_intervals_projected"] == 2*base["RI_intervals_projected"]


def test_five_counties_can_mean_fewer_effective_clusters():
    rows = []
    for county, n in [(1, 1), (2, 1), (3, 1), (4, 20), (5, 20)]:
        for i in range(n):
            rows.append({"county_fips": f"44{county:03d}", "plot_chain_id": f"{county}-{i}"})
    result = probe.effective_counties(rows)
    assert result["n_counties"] == 5
    assert result["n_plot_chains"] == 43
    assert 2 < result["effective_counties_plot_HHI"] < 3
    assert result["RI_leave_one_county_out_training_cannot_meet_original_five_county_floor"] is True


def test_all_taxa_preserved_when_region_unobserved():
    cfg = config()
    phases = [probe.phase_projection(synthetic(), cfg, (0., 0., 1990))]
    summary = probe.summarize(phases, cfg)
    assert len(summary["per_species"]) == 13
    absent = next(x for x in summary["per_species"] if x["species_code"] == "261")
    assert absent["RI_unique_plot_chains_total"] == 0
    assert absent["RI_unique_plot_coverage_reference"] == 0
    assert summary["biological_promotion_authorized"] is False


def test_pinned_source_checksum_abstains_on_tamper(tmp_path):
    folder = tmp_path / "source"
    folder.mkdir()
    (folder / "fia_new_cohort_joint_source_only_county_stable_v2.csv").write_text("mutated")
    (folder / "derived_receipt.json").write_text("{}")
    with pytest.raises(ValueError, match="identity changed"):
        probe.run(folder, ROOT / "configs/fia_joint_climate_support_gate_v1.json")


def test_source_provenance_and_postsource_eight_phases():
    assert len(probe.PHASES) == 8
    assert probe.PHASES[0] == (0., 0., 1990)
    assert probe.SOURCE_RUN == 43711159676
    assert probe.SOURCE_ARTIFACT == 14160283759
    assert len(probe.SOURCE_CSV_SHA256) == len(probe.SOURCE_RECEIPT_SHA256) == 64
    assert probe.PRIOR_ORIGIN_STABLE_TAXA == ("129", "316", "802", "833", "837")
