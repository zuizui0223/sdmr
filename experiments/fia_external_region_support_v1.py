"""Postsource, source-only transport-opportunity diagnostic: VA/WI -> unseen RI.

Use only the exact county-stable first-source artifact. VA and WI define all
joint T/P/time bins and eligibility; RI is NEVER used to discover those bins.
No FIA/NOAA GET, tree responses, niche-process claims or post-hoc promotions.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import fia_joint_support_gate_v1 as gate

SOURCE_RUN = 43711159676
SOURCE_ARTIFACT = 14160283759
SOURCE_CSV_SHA256 = "44b3281324f978c11012a115781aef663fc9d205722111bd5b5cf790dae482a7"
SOURCE_RECEIPT_SHA256 = "f167966bdd19529fe39955863effd666943e624cf939bd7c80ac8908b6a3f453"
ORIGINAL_SOURCE_ROWS = 89616
TRAIN_REGIONS = ("VA", "WI")
TEST_REGION = "RI"
PRIOR_ORIGIN_STABLE_TAXA = ("129", "316", "802", "833", "837")
PHASES = tuple(itertools.product((0.0, 0.5), (0.0, 50.0), (1990, 1992)))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cell(row: dict, cfg: dict, phase: tuple[float, float, int]) -> tuple[int, int, int]:
    t, p, y = phase
    return (math.floor((row["temperature_anomaly_c"] - t) / cfg["temperature_bin_c"]),
            math.floor((row["precipitation_anomaly_mm"] - p) / cfg["precipitation_bin_mm"]),
            math.floor((row["interval_end_year"] - y) / cfg["period_bin_years"]))


def effective_counties(ri: list[dict]) -> dict:
    """Descriptive Hill q=2 effective number using unique RI plot chains."""
    members = defaultdict(set)
    for row in ri:
        members[row["county_fips"]].add(row["plot_chain_id"])
    counts = sorted(len(x) for x in members.values())
    n = sum(counts)
    return {"n_counties": len(counts), "n_plot_chains": n,
            "effective_counties_plot_HHI": n*n/sum(x*x for x in counts) if n else None,
            "largest_county_plot_share": max(counts)/n if n else None,
            "county_plot_count_sorted": counts,
            "RI_leave_one_county_out_training_cannot_meet_original_five_county_floor":
                len(counts) > 0 and len(counts)-1 < 5}


def phase_projection(rows: list[dict], cfg: dict,
                     phase: tuple[float, float, int]) -> dict:
    """Construct support exclusively from VA/WI; project *then* inspect RI."""
    gate.verify_config(cfg)
    by_taxon_region = defaultdict(list)
    for r in rows:
        if r["state"] not in cfg["regions"] or r["species_code"] not in cfg["species_codes"]:
            raise ValueError("foreign taxon or region in source-only panel")
        by_taxon_region[(r["species_code"], r["state"])].append(r)
    result = []
    for sp in cfg["species_codes"]:
        training = {}
        for region in TRAIN_REGIONS:
            rr = by_taxon_region[(sp, region)]
            counts = defaultdict(lambda: {"counties": set(), "plots": set()})
            for r in rr:
                b = counts[cell(r, cfg, phase)]
                b["counties"].add(r["county_fips"])
                b["plots"].add((r["county_fips"], r["plot_chain_id"]))
            regions_counties = {r["county_fips"] for r in rr}
            regions_plots = {(r["county_fips"], r["plot_chain_id"]) for r in rr}
            available = (len(regions_counties) >= cfg["min_region_counties"] and
                         len(regions_plots) >= cfg["min_region_plots"])
            qualified = {k for k, v in counts.items()
                         if len(v["counties"]) >= cfg["min_bin_counties"] and
                         len(v["plots"]) >= cfg["min_bin_plots"]}
            training[region] = {"eligible": available, "bins": qualified,
                                "n_counties": len(regions_counties),
                                "n_plots": len(regions_plots)}
        both_available = all(training[s]["eligible"] for s in TRAIN_REGIONS)
        training_bins = set.intersection(*(training[s]["bins"] for s in TRAIN_REGIONS)) if both_available else set()
        ri = by_taxon_region[(sp, TEST_REGION)]
        all_plots = {(r["county_fips"], r["plot_chain_id"]) for r in ri}
        covered = [r for r in ri if cell(r, cfg, phase) in training_bins]
        covered_plots = {(r["county_fips"], r["plot_chain_id"]) for r in covered}
        covered_counties = {r["county_fips"] for r in covered}
        ri_stats = effective_counties(ri)
        result.append({"species_code": sp,
                       "VA_WI_training_only": True,
                       "VA_WI_complete_region_support": both_available,
                       "VA_WI_qualified_joint_time_bins": len(training_bins),
                       "RI_counties_total": ri_stats["n_counties"],
                       "RI_unique_plots_total": len(all_plots),
                       "RI_unique_plots_projected": len(covered_plots),
                       "RI_unique_plot_coverage_fraction":
                           len(covered_plots)/len(all_plots) if all_plots else 0.0,
                       "RI_counties_projected": len(covered_counties),
                       "RI_intervals_projected": len(covered),
                       "RI_effective_counties_plot_HHI": ri_stats["effective_counties_plot_HHI"],
                       "RI_largest_county_plot_share": ri_stats["largest_county_plot_share"],
                       "RI_county_plot_counts_sorted": ri_stats["county_plot_count_sorted"],
                       "RI_LOCO_train_cannot_preserve_5_county_floor":
                           ri_stats["RI_leave_one_county_out_training_cannot_meet_original_five_county_floor"]})
    return {"phase": {"t_origin_c": phase[0], "p_origin_mm": phase[1],
                      "year_origin": phase[2]}, "species": result,
            "training_bin_selection_uses_RI": False}


def summarize(phases: list[dict], cfg: dict) -> dict:
    out = []
    for sp in cfg["species_codes"]:
        variants = [next(x for x in phase["species"] if x["species_code"] == sp)
                    for phase in phases]
        f = [x["RI_unique_plot_coverage_fraction"] for x in variants]
        sample = variants[0]
        out.append({
            "species_code": sp,
            "previously_origin_stable_source_taxon": sp in PRIOR_ORIGIN_STABLE_TAXA,
            "n_grid_origins": len(f),
            "RI_unique_plot_coverage_min": min(f),
            "RI_unique_plot_coverage_max": max(f),
            "RI_unique_plot_coverage_reference": f[0],
            "RI_unique_plot_chains_total": sample["RI_unique_plots_total"],
            "RI_effective_counties_plot_HHI": sample["RI_effective_counties_plot_HHI"],
            "RI_largest_county_plot_share": sample["RI_largest_county_plot_share"],
            "RI_counties_total": sample["RI_counties_total"],
            "RI_train_five_county_floor_survives_leave_one_out":
                not sample["RI_LOCO_train_cannot_preserve_5_county_floor"],
            "VA_WI_train_full_support_all_phases":
                all(x["VA_WI_complete_region_support"] for x in variants),
        })
    return {"program": "fia_source_only_VA_WI_to_RI_environment_projection_v1",
            "source_reconciliation_run": SOURCE_RUN, "source_artifact": SOURCE_ARTIFACT,
            "source_csv_sha256": SOURCE_CSV_SHA256,
            "source_receipt_sha256": SOURCE_RECEIPT_SHA256,
            "n_source_rows": ORIGINAL_SOURCE_ROWS,
            "source_panel_species": len(cfg["species_codes"]),
            "training_regions": list(TRAIN_REGIONS), "test_region": TEST_REGION,
            "n_phases": len(PHASES), "projection_phase_options": [list(x) for x in PHASES],
            "original_source_support_method_unchanged": True,
            "postsource_exploratory_design_not_prospective_validation": True,
            "no_biological_outcomes_read": True, "biological_promotion_authorized": False,
            "held_out_RI_source_is_not_a_held_out_demographic_validation": True,
            "source_only_projection_has_no_model_fits": True,
            "prior_origin_stable_taxa_from_separate_2026_11_15_result":
                list(PRIOR_ORIGIN_STABLE_TAXA),
            "per_species": out, "phases": phases}


def run(source_dir: Path, cfg_file: Path) -> dict:
    cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
    gate.verify_config(cfg)
    csv_file = source_dir / "fia_new_cohort_joint_source_only_county_stable_v2.csv"
    receipt = source_dir / "derived_receipt.json"
    if sha(csv_file) != SOURCE_CSV_SHA256 or sha(receipt) != SOURCE_RECEIPT_SHA256:
        raise ValueError("frozen source-only identity changed")
    rows = gate.read_source_only_csv(csv_file, receipt, cfg)
    if len(rows) != ORIGINAL_SOURCE_ROWS or len(cfg["species_codes"]) != 13:
        raise ValueError("frozen denominator differs")
    results = [phase_projection(rows, cfg, phase) for phase in PHASES]
    return summarize(results, cfg)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=Path("configs/fia_joint_climate_support_gate_v1.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source_dir, args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("source-only VA+WI->RI projected", result["source_panel_species"], "taxa",
          result["n_phases"], "grid origins; no demographic inference")


if __name__ == "__main__":
    main()
