"""Post-source-only climate-bin-origin sensitivity (NO biology / no FIA GET).

Only re-evaluates the already frozen first source-only derived table, checks
its exact SHA256, and demonstrates arbitrary discretization sensitivity.
The original 0/0/1990 result must agree with the canonical unchanged gate.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path

import fia_joint_support_gate_v1 as gate

SOURCE_RUN = 43696751589
RECONCILIATION_RUN = 43711159676
SOURCE_ARTIFACT = 14160283759
DERIVED_CSV_SHA = "44b3281324f978c11012a115781aef663fc9d205722111bd5b5cf790dae482a7"
DERIVED_RECEIPT_SHA = "f167966bdd19529fe39955863effd666943e624cf939bd7c80ac8908b6a3f453"


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_offset(rows: list[dict], conf: dict, t_origin: float,
                    p_origin: float, year_origin: int) -> dict:
    """Recompute only spatially and temporally joint source opportunity."""
    gate.verify_config(conf)
    samples = defaultdict(list)
    for row in rows:
        cell = (math.floor((row["temperature_anomaly_c"] - t_origin) / conf["temperature_bin_c"]),
                math.floor((row["precipitation_anomaly_mm"] - p_origin) / conf["precipitation_bin_mm"]),
                math.floor((row["interval_end_year"] - year_origin) / conf["period_bin_years"]))
        samples[(row["species_code"], row["state"])].append(
            (row["county_fips"], row["plot_chain_id"], cell)
        )
    out = []
    for sp in conf["species_codes"]:
        sources = {}
        problems = []
        for state in conf["regions"]:
            obs = samples[(sp, state)]
            counties = {county for county, _, _ in obs}
            plots = {(county, plot) for county, plot, _ in obs}
            if len(counties) < conf["min_region_counties"]:
                problems.append(state + ":insufficient_counties")
            if len(plots) < conf["min_region_plots"]:
                problems.append(state + ":insufficient_plots")
            bins = defaultdict(lambda: {"counties": set(), "plots": set()})
            for county, plot, cell in obs:
                bins[cell]["counties"].add(county)
                bins[cell]["plots"].add((county, plot))
            qualify = {cell for cell, v in bins.items()
                       if len(v["counties"]) >= conf["min_bin_counties"]
                       and len(v["plots"]) >= conf["min_bin_plots"]}
            sources[state] = {"obs": obs, "plots": plots, "qualify": qualify}
        shared = set.intersection(*(sources[s]["qualify"] for s in conf["regions"]))
        if len(shared) < conf["min_shared_bins"]:
            problems.append("insufficient_time_aligned_joint_bins")
        fractions = {}
        for state in conf["regions"]:
            src = sources[state]
            n = len({(county, plot) for county, plot, cell in src["obs"] if cell in shared})
            fractions[state] = n / len(src["plots"]) if src["plots"] else 0.0
            if fractions[state] < conf["min_region_covered_fraction"]:
                problems.append(state + ":insufficient_joint_time_unique_plot_coverage")
        out.append({"species_code": sp, "source_eligible": not problems,
                    "n_shared_time_aligned_joint_bins": len(shared),
                    "unique_plot_coverage_by_state": fractions,
                    "reasons": problems})
    return {"temperature_origin_c": t_origin, "precipitation_origin_mm": p_origin,
            "five_year_cohort_origin": year_origin,
            "source_eligible_species_codes": [x["species_code"] for x in out if x["source_eligible"]],
            "source_eligible_species_count": sum(x["source_eligible"] for x in out),
            "per_species": out}


def run(source_dir: Path, config_path: Path) -> dict:
    conf = json.loads(config_path.read_text(encoding="utf-8"))
    gate.verify_config(conf)
    raw = source_dir / "fia_new_cohort_joint_source_only_county_stable_v2.csv"
    receipt = source_dir / "derived_receipt.json"
    if checksum(raw) != DERIVED_CSV_SHA or checksum(receipt) != DERIVED_RECEIPT_SHA:
        raise ValueError("original derived source-only identity mismatch")
    rows = gate.read_source_only_csv(raw, receipt, conf)
    if len(rows) != 89616:
        raise ValueError("complete source-only denominator changed")
    canonical = gate.evaluate_source_only(rows, conf)
    variants = [evaluate_offset(rows, conf, t, p, year)
                for t, p, year in itertools.product((0.0, 0.5), (0.0, 50.0), (1990, 1992))]
    first = variants[0]
    if first["source_eligible_species_count"] != canonical["source_eligible_species"]:
        raise ValueError("baseline differs from canonical evaluator")
    for expected, found in zip(canonical["species"], first["per_species"]):
        if ((expected["status"] == "descriptive_source_support_eligible") != found["source_eligible"]
            or expected["n_shared_time_aligned_joint_bins"] != found["n_shared_time_aligned_joint_bins"]):
            raise ValueError("canonical source-only primary result was reinterpreted")
    all_sets = [set(x["source_eligible_species_codes"]) for x in variants]
    invariant = sorted(set.intersection(*all_sets), key=int)
    any_pass = sorted(set.union(*all_sets), key=int)
    return {
        "program": "fia_joint_source_only_origin_sensitivity_v1",
        "source_first_run": SOURCE_RUN,
        "reconciliation_run": RECONCILIATION_RUN,
        "reconciled_source_artifact": SOURCE_ARTIFACT,
        "source_csv_sha256": DERIVED_CSV_SHA,
        "source_receipt_sha256": DERIVED_RECEIPT_SHA,
        "source_rows": len(rows),
        "n_declared_taxa": len(conf["species_codes"]),
        "canonical_result_kept_unchanged": True,
        "grid_widths_unchanged": {"temperature_c": conf["temperature_bin_c"],
                                 "precipitation_mm": conf["precipitation_bin_mm"],
                                 "period_years": conf["period_bin_years"]},
        "origin_phase_options_postsource_exploratory_only": {
            "temperature_c": [0.0, 0.5], "precipitation_mm": [0.0, 50.0],
            "year": [1990, 1992],
        },
        "taxa_passing_all_eight_phases": invariant,
        "taxa_passing_any_phase": any_pass,
        "n_taxa_passing_all_eight_phases": len(invariant),
        "source_only_not_demographic_or_causal_inference": True,
        "biological_promotion_authorized": False,
        "variants": variants,
    }


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--source-dir", type=Path, required=True)
    a.add_argument("--config", type=Path, default=Path("configs/fia_joint_climate_support_gate_v1.json"))
    a.add_argument("--output", type=Path, required=True)
    args = a.parse_args()
    result = run(args.source_dir, args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("canonical preserved; 8-phase source-only invariant taxa", result["taxa_passing_all_eight_phases"])


if __name__ == "__main__":
    main()
