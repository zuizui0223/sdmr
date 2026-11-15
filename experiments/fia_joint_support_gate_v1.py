"""Response-blind bivariate climate-support gate. No model fitting or network I/O.

The legacy FIA v4 archive has ONLY per-region marginal climate bounds, so it
must remain UNAVAILABLE for joint support. A distinct future source-only table
can be tested at fixed, ecologically interpretable joint climate resolutions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path

STATES = {"RI": "44", "VA": "51", "WI": "55"}
FIELDS = {"species_code", "state", "county_fips", "plot_chain_id",
          "interval_id", "temperature_anomaly_c", "precipitation_anomaly_mm"}
LEGACY_ARCHIVE_SHA = "66fe0e81815f99b0112b991f1ee6f766f968889fc858989e4a2f878993cfcaa3"
LEGACY_RESPONSE_SHA = "a336e0da49588dc81d89ef5e87826285d8d3afeaa80b6bf013c72599abce7512"
LEGACY_SOURCE_SHA = "5ace92c42a912fdd9d1a720849a458b28821c16764b088defdfc2ce1488c83b5"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_config(config: dict) -> None:
    if config.get("stage") != "future_source_only_design_not_frozen_empirical" or config.get("biological_promotion_authorized") is not False:
        raise ValueError("source-only scientific-boundary contract missing")
    if config.get("regions") != ["RI", "VA", "WI"]:
        raise ValueError("regions changed")
    species = config.get("species_codes")
    if not isinstance(species, list) or len(species) != len(set(species)) or not species:
        raise ValueError("invalid fixed species denominator")
    for name in ("temperature_bin_c", "precipitation_bin_mm"):
        value = config.get(name)
        if not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError("invalid fixed climate grid resolution: " + name)
    for name in ("min_region_counties", "min_region_plots", "min_bin_counties",
                 "min_bin_plots", "min_shared_bins"):
        val = config.get(name)
        if isinstance(val, bool) or not isinstance(val, int) or val < 1:
            raise ValueError("invalid future design threshold: " + name)
    if not 0 < config.get("min_region_covered_fraction", -1) <= 1:
        raise ValueError("invalid coverage threshold")
    if config.get("climate_source") != "NOAA_20261006_county_interval_anomalies":
        raise ValueError("climate identity missing")


def legacy_boundary(archive: Path, config: dict) -> dict:
    """Inspects saved per-taxon source support *without* fitting/reading growth."""
    verify_config(config)
    raw = archive.read_bytes()
    if sha(raw) != LEGACY_ARCHIVE_SHA:
        raise ValueError("legacy artifact ZIP SHA changed")
    with zipfile.ZipFile(archive) as z:
        if set(z.namelist()) != {"exploratory_climate_density_growth_v4.json", "source_phase_receipt.json"}:
            raise ValueError("legacy archive members changed")
        response = z.read("exploratory_climate_density_growth_v4.json")
        source = z.read("source_phase_receipt.json")
        if sha(response) != LEGACY_RESPONSE_SHA or sha(source) != LEGACY_SOURCE_SHA:
            raise ValueError("legacy JSON receipt SHA changed")
        result = json.loads(response)
        receipt = json.loads(source)
    if receipt.get("n_source_ready") != 3 or not receipt.get("source_only_no_status_or_diameter_opened"):
        raise ValueError("invalid legacy source receipt")
    rows = result.get("species", [])
    if set(str(s.get("spcd")) for s in rows) != set(config["species_codes"]) or len(rows) != len(config["species_codes"]):
        raise ValueError("frozen denominator changed")
    out = []
    for rec in sorted(rows, key=lambda x: int(x["spcd"])):
        regions = rec.get("relative_climate_support", {})
        if set(regions) != set(config["regions"]):
            raise ValueError("missing fixed state support")
        marginal = {}
        for axis in ("tanom3", "panom200"):
            lo = max(float(regions[s]["min_" + axis]) for s in config["regions"])
            hi = min(float(regions[s]["max_" + axis]) for s in config["regions"])
            marginal[axis] = {"interval_intersects": lo <= hi, "intersection_lower": lo,
                              "intersection_upper": hi}
        out.append({"species_code": str(rec["spcd"]),
                    "status": "not_evaluable_joint_samples_not_archived",
                    "marginal_overlap_only": marginal,
                    "RI_counties_in_postresponse_selected_cohort": int(regions["RI"]["n_counties"]),
                    "RI_links_in_postresponse_selected_cohort": int(regions["RI"]["n_links"]),
                    "not_a_source_only_future_gate": True})
    return {"program": "fia_joint_climate_support_legacy_boundary_v1",
            "source_artifact_sha256": LEGACY_ARCHIVE_SHA,
            "status": "not_evaluable_joint_samples_not_archived",
            "n_species_declared": len(config["species_codes"]),
            "n_species_joint_overlap_measured": 0,
            "n_species_joint_overlap_unknown": len(out),
            "n_species_marginal_overlap_both": sum(all(x["interval_intersects"] for x in row["marginal_overlap_only"].values()) for row in out),
            "species": out,
            "no_reopening_or_refitting": True,
            "biological_promotion_authorized": False}


def read_source_only_csv(path: Path, receipt_path: Path, config: dict) -> list[dict]:
    verify_config(config)
    raw = path.read_bytes()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (receipt.get("status") != "source_only_pre_response" or
        receipt.get("no_status_diameter_growth_read") is not True or
        receipt.get("species_identity_only_not_survivor_selected") is not True or
        receipt.get("sha256") != sha(raw) or
        receipt.get("climate_source") != config["climate_source"]):
        raise ValueError("source-only receipt and content hash required")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if set(reader.fieldnames or []) != FIELDS or len(reader.fieldnames or []) != len(FIELDS):
            raise ValueError("incorrect source-only schema or outcome columns present")
        rows = []
        ids = set()
        for row in reader:
            if (row["state"] not in STATES or row["species_code"] not in config["species_codes"] or
                len(row["county_fips"]) != 5 or not row["county_fips"].isdigit() or
                not row["county_fips"].startswith(STATES[row["state"]])):
                raise ValueError("invalid taxon/state/county identity")
            if not row["plot_chain_id"] or not row["interval_id"]:
                raise ValueError("invalid plot or interval")
            identity = (row["species_code"], row["state"], row["plot_chain_id"], row["interval_id"])
            if identity in ids:
                raise ValueError("tree-level duplicates must first be collapsed to plot-interval clusters")
            ids.add(identity)
            for key in ("temperature_anomaly_c", "precipitation_anomaly_mm"):
                try:
                    value = float(row[key])
                except (ValueError, TypeError) as e:
                    raise ValueError("invalid joint environmental measurement") from e
                if not math.isfinite(value):
                    raise ValueError("nonfinite joint environmental measurement")
                row[key] = value
            rows.append(row)
    return rows


def grid_cell(row: dict, config: dict) -> tuple[int, int]:
    # Fixed origin 0; math.floor intentionally handles negative anomalies.
    return (math.floor(row["temperature_anomaly_c"] / config["temperature_bin_c"]),
            math.floor(row["precipitation_anomaly_mm"] / config["precipitation_bin_mm"]))


def evaluate_source_only(rows: list[dict], config: dict) -> dict:
    verify_config(config)
    by_sp_state = defaultdict(list)
    for r in rows:
        by_sp_state[(r["species_code"], r["state"])].append(r)
    output = []
    for sp in config["species_codes"]:
        buckets = {}
        reasons = []
        for state in config["regions"]:
            items = by_sp_state[(sp, state)]
            counties = {r["county_fips"] for r in items}
            plots = {r["plot_chain_id"] for r in items}
            if len(counties) < config["min_region_counties"]:
                reasons.append(state + ":insufficient_counties")
            if len(plots) < config["min_region_plots"]:
                reasons.append(state + ":insufficient_plots")
            bins = defaultdict(lambda: {"counties": set(), "plots": set(), "intervals": 0})
            for r in items:
                b = bins[grid_cell(r, config)]
                b["counties"].add(r["county_fips"])
                b["plots"].add(r["plot_chain_id"])
                b["intervals"] += 1
            qualified = {cell for cell, v in bins.items()
                         if len(v["counties"]) >= config["min_bin_counties"]
                         and len(v["plots"]) >= config["min_bin_plots"]}
            buckets[state] = {"bins": bins, "qualified": qualified, "n_counties": len(counties),
                              "n_plots": len(plots), "n_plot_intervals": len(items)}
        shared = set.intersection(*(buckets[s]["qualified"] for s in config["regions"]))
        if len(shared) < config["min_shared_bins"]:
            reasons.append("insufficient_shared_joint_bins")
        coverage = {}
        for s in config["regions"]:
            v = buckets[s]
            n = sum(v["bins"][cell]["intervals"] for cell in shared)
            fraction = (n / v["n_plot_intervals"]) if v["n_plot_intervals"] else 0.0
            coverage[s] = {"county_count": v["n_counties"], "plot_count": v["n_plots"],
                           "plot_interval_count": v["n_plot_intervals"],
                           "shared_cell_coverage_fraction": fraction}
            if fraction < config["min_region_covered_fraction"]:
                reasons.append(s + ":insufficient_joint_coverage")
        output.append({"species_code": sp,
                       "status": "descriptive_source_support_eligible" if not reasons else "not_eligible_design_support",
                       "reasons": reasons, "n_shared_joint_bins": len(shared),
                       "shared_joint_bins": [list(z) for z in sorted(shared)],
                       "regions": coverage})
    return {"program": "fia_joint_climate_support_future_source_gate_v1",
            "status": "design_only_no_fitted_biological_response",
            "source_eligible_species": sum(x["status"] == "descriptive_source_support_eligible" for x in output),
            "n_species_declared": len(config["species_codes"]),
            "species": output,
            "grid_origin": [0, 0], "grid_widths": [config["temperature_bin_c"], config["precipitation_bin_mm"]],
            "grid_discretization_cannot_establish_physiological_equivalence": True,
            "unmeasured_climate_space_not_assumed_absent": True,
            "no_growth_or_survival_or_refitting": True,
            "biological_promotion_authorized": False}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--archive-v4", type=Path)
    p.add_argument("--samples", type=Path)
    p.add_argument("--source-receipt", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.archive_v4 and not (args.samples or args.source_receipt):
        result = legacy_boundary(args.archive_v4, config)
    elif args.samples and args.source_receipt and not args.archive_v4:
        rows = read_source_only_csv(args.samples, args.source_receipt, config)
        result = evaluate_source_only(rows, config)
        result["source_sha256"] = sha(args.samples.read_bytes())
    else:
        p.error("pass either --archive-v4 or both --samples and --source-receipt")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["status"], result.get("source_eligible_species", result.get("n_species_joint_overlap_measured")))


if __name__ == "__main__":
    main()
