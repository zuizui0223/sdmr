"""Source-only county-block feasibility for VA/WI common-vs-regional response.

No demographic model, no FIA/NOAA download, and no use of RI to define inner
training support. Outcome-blind county folds use historical FIA growth v4's
frozen sha256(FIPS) % 5 rule; this reuses a design, NOT the earlier response.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import fia_joint_support_gate_v1 as shared

CSV_SHA = "44b3281324f978c11012a115781aef663fc9d205722111bd5b5cf790dae482a7"
RECEIPT_SHA = "f167966bdd19529fe39955863effd666943e624cf939bd7c80ac8908b6a3f453"
ORIGINAL_ROWS = 89616
REGIONS = ("VA", "WI")
RI_REGION = "RI"
FOLDS = 5
PRIMARY_SPECIES = ("129", "316", "802", "833", "837")
# These are development-only response-readiness criteria, not empirical
# performance thresholds or a retroactive change to the old 3-state gate.
MIN_OUTER_TEST_COUNTIES = 3
MIN_OUTER_TEST_PLOTS = 20
MIN_OUTER_TRAIN_COUNTIES = 20
MIN_TEST_COVERAGE = 0.20


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def county_fold(fips: str) -> int:
    if len(fips) != 5 or not fips.isdigit():
        raise ValueError("county must be a five-digit FIPS string")
    return int.from_bytes(hashlib.sha256(fips.encode()).digest()[:4], "big") % FOLDS


def source_cell(row: dict, config: dict) -> tuple[int, int, int]:
    return (*shared.grid_cell(row, config), shared.period_bin(row, config))


def qualifying_cells(rows: list[dict], config: dict) -> set[tuple]:
    bins = defaultdict(lambda: {"counties": set(), "plots": set()})
    for r in rows:
        cell = source_cell(r, config)
        bins[cell]["counties"].add(r["county_fips"])
        bins[cell]["plots"].add((r["county_fips"], r["plot_chain_id"]))
    return {cell for cell, value in bins.items()
            if len(value["counties"]) >= config["min_bin_counties"]
            and len(value["plots"]) >= config["min_bin_plots"]}


def effective_counties(rows: list[dict]) -> float | None:
    plots = defaultdict(set)
    for r in rows:
        plots[r["county_fips"]].add(r["plot_chain_id"])
    n = sum(len(v) for v in plots.values())
    denom = sum(len(v) ** 2 for v in plots.values())
    return n*n/denom if denom else None


def evaluate(rows: list[dict], config: dict) -> dict:
    shared.verify_config(config)
    if set(config["regions"]) != {"RI", "VA", "WI"}:
        raise ValueError("unexpected fixed region panel")
    if not set(PRIMARY_SPECIES).issubset(config["species_codes"]):
        raise ValueError("primary species denominator missing")
    # Enforce full input and valid county identities independently of the
    # original source receipt; no new species or state can be added.
    data = defaultdict(lambda: {"VA": defaultdict(list), "WI": defaultdict(list)})
    source_rows = defaultdict(int)
    for r in rows:
        sp, region = r["species_code"], r["state"]
        if sp not in config["species_codes"] or region not in config["regions"]:
            raise ValueError("unregistered species or state")
        source_rows[region] += 1
        if region in REGIONS:
            data[sp][region][county_fold(r["county_fips"])].append(r)
    details = []
    for sp in config["species_codes"]:
        for f in range(FOLDS):
            train_by_region, test_by_region = {}, {}
            county_stats = {}
            reasons = []
            for region in REGIONS:
                region_folds = data[sp][region]
                train = [r for fold, group in region_folds.items()
                         if fold != f for r in group]
                test = list(region_folds[f])
                train_by_region[region] = train
                test_by_region[region] = test
                train_counties = {r["county_fips"] for r in train}
                test_counties = {r["county_fips"] for r in test}
                train_plots = {(r["county_fips"], r["plot_chain_id"]) for r in train}
                test_plots = {(r["county_fips"], r["plot_chain_id"]) for r in test}
                if train_counties & test_counties:
                    raise ValueError("county leakage across outer folds")
                if len(train_counties) < MIN_OUTER_TRAIN_COUNTIES:
                    reasons.append(region + ":few_train_counties")
                if len(test_counties) < MIN_OUTER_TEST_COUNTIES:
                    reasons.append(region + ":few_heldout_counties")
                if len(test_plots) < MIN_OUTER_TEST_PLOTS:
                    reasons.append(region + ":few_heldout_plots")
                county_stats[region] = {
                    "train_counties": len(train_counties),
                    "test_counties": len(test_counties),
                    "train_unique_plot_chains": len(train_plots),
                    "test_unique_plot_chains": len(test_plots),
                    "train_intervals": len(train),
                    "test_intervals": len(test),
                    "test_effective_counties_plot_HHI": effective_counties(test),
                }
            # Training environmental representation fixed BEFORE test-source
            # projection; test climate is never used to choose these bins.
            va = qualifying_cells(train_by_region["VA"], config)
            wi = qualifying_cells(train_by_region["WI"], config)
            common = va & wi
            if len(common) < config["min_shared_bins"]:
                reasons.append("few_common_training_environment_time_bins")
            for region in REGIONS:
                test = test_by_region[region]
                unique = {(r["county_fips"], r["plot_chain_id"]) for r in test}
                supported = {(r["county_fips"], r["plot_chain_id"])
                             for r in test if source_cell(r, config) in common}
                ratio = len(supported) / len(unique) if unique else None
                county_stats[region].update({
                    "supported_heldout_unique_plots": len(supported),
                    "heldout_plot_source_coverage_fraction": ratio,
                    "heldout_source_coverage_missing_not_zero": ratio is None,
                })
                if ratio is None or ratio < MIN_TEST_COVERAGE:
                    reasons.append(region + ":heldout_source_coverage_insufficient")
            details.append({
                "species_code": sp,
                "fixed_county_fold": f,
                "primary_five_source_taxa": sp in PRIMARY_SPECIES,
                "VA_WI_train_joint_bins": len(common),
                "regions": county_stats,
                "status": "county_source_ready_for_response_design" if not reasons
                           else "not_source_ready_for_response_design",
                "reasons": reasons,
                "training_source_bins_use_test_counties": False,
                "withheld_counties_fully_excluded_from_train": True,
            })
    by_taxon = []
    for sp in config["species_codes"]:
        subset = [r for r in details if r["species_code"] == sp]
        by_taxon.append({
            "species_code": sp, "primary_five_source_taxa": sp in PRIMARY_SPECIES,
            "n_available_source_folds": sum(r["status"] == "county_source_ready_for_response_design" for r in subset),
            "n_design_folds": FOLDS,
            "minimum_training_joint_cells": min(r["VA_WI_train_joint_bins"] for r in subset),
            "minimum_heldout_source_fraction_VA": min((r["regions"]["VA"]["heldout_plot_source_coverage_fraction"] or 0) for r in subset),
            "minimum_heldout_source_fraction_WI": min((r["regions"]["WI"]["heldout_plot_source_coverage_fraction"] or 0) for r in subset),
            "minimum_heldout_test_counties_VA": min(r["regions"]["VA"]["test_counties"] for r in subset),
            "minimum_heldout_test_counties_WI": min(r["regions"]["WI"]["test_counties"] for r in subset),
        })
    return {
        "program": "fia_VA_WI_county_block_source_only_response_readiness_v1",
        "source_csv_sha256": CSV_SHA,
        "source_receipt_sha256": RECEIPT_SHA,
        "source_rows": sum(source_rows.values()),
        "original_source_rows_required": ORIGINAL_ROWS,
        "states_and_source_rows": dict(source_rows),
        "n_taxa_declared": len(config["species_codes"]),
        "n_primary_source_taxa": len(PRIMARY_SPECIES),
        "primary_taxa": list(PRIMARY_SPECIES),
        "source_ready_taxon_fold_cells": sum(d["status"] == "county_source_ready_for_response_design" for d in details),
        "source_ready_primary_taxon_fold_cells": sum(d["status"] == "county_source_ready_for_response_design" and d["primary_five_source_taxa"] for d in details),
        "n_taxon_fold_cells": len(details),
        "n_folds": FOLDS,
        "fold_assignment": "first4bytes_sha256_county_FIPS_mod5",
        "VA_WI_train_only_no_heldout_environment_used_for_bin_discovery": True,
        "minimums": {
            "train_counties_per_state": MIN_OUTER_TRAIN_COUNTIES,
            "test_counties_per_state": MIN_OUTER_TEST_COUNTIES,
            "test_unique_plot_chains_per_state": MIN_OUTER_TEST_PLOTS,
            "shared_environment_time_cells": config["min_shared_bins"],
            "training_bin_counties_per_state": config["min_bin_counties"],
            "training_bin_plots_per_state": config["min_bin_plots"],
            "heldout_unique_plot_source_fraction": MIN_TEST_COVERAGE
        },
        "species": by_taxon,
        "folds": details,
        "new_growth_or_survival_outcome_read": False,
        "source_only_not_a_demographic_test": True,
        "postsource_design_thresholds_not_prospective_validation": True,
        "biological_promotion_authorized": False,
        "product_A_M5_preserved_and_product_B_blocked": True,
    }


def run(source_dir: Path, config_path: Path) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    filename = source_dir / "fia_new_cohort_joint_source_only_county_stable_v2.csv"
    receipt = source_dir / "derived_receipt.json"
    if sha_file(filename) != CSV_SHA or sha_file(receipt) != RECEIPT_SHA:
        raise ValueError("source-only first-open derived artifact SHA mismatch")
    source = shared.read_source_only_csv(filename, receipt, cfg)
    if len(source) != ORIGINAL_ROWS:
        raise ValueError("source-only full denominator changed")
    result = evaluate(source, cfg)
    if result["source_rows"] != ORIGINAL_ROWS or len(result["folds"]) != 13 * FOLDS:
        raise ValueError("frozen 13 taxon by 5 fold contract changed")
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--config", type=Path, default=Path("configs/fia_joint_climate_support_gate_v1.json"))
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = run(a.source_dir, a.config)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("source-only county folds:", result["source_ready_taxon_fold_cells"], "/", result["n_taxon_fold_cells"])
    print("five primary taxa folds:", result["source_ready_primary_taxon_fold_cells"], "/ 25; NO biological outcome read")


if __name__ == "__main__":
    main()
