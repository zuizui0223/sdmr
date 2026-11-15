"""Reconcile first opened FIA source-only artifact without fetching or reading outcomes.

The original one-shot new cohort succeeded, but its downstream bivariate gate
abstained on a county-unstable plot chain. This post-source QC excludes EVERY
row of an unstable plot chain regardless of taxon, time or climate, retaining
the full original denominator and preserving the original failed gate.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import fia_joint_support_gate_v1 as gate

SOURCE_RUN = 43696751589
SOURCE_ARTIFACT = 14155086669
SOURCE_ARTIFACT_ZIP_SHA256 = "85d8cc0b6efb120736166a581f608ad10d7de70dd3732bd68a8c7b3fc44acff3"
ORIGINAL_CSV_SHA256 = "cc68e0604287a49f32fd791bcf72ee60254809ab648a9f88946f1c8a2c72bf7f"
ORIGINAL_RECEIPT_SHA256 = "0adcdeac7b974e91b83d986fca32ad0851000658f79fbe099407ce2fb37fa408"
SOURCE_ROWS = 89630
SOURCE_BY_STATE = {"RI": 1471, "VA": 38142, "WI": 50017}
SOURCE_STUDY = "fia_joint_source_only_v1"


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def original_input(source_dir: Path, config: dict) -> list[dict]:
    """Require immutable exact first-open source-only contents and signatures."""
    gate.verify_config(config)
    file = source_dir / "fia_new_cohort_joint_source_only.csv"
    manifest = source_dir / "source_receipt.json"
    raw = file.read_bytes()
    metadata = manifest.read_bytes()
    if checksum(raw) != ORIGINAL_CSV_SHA256 or checksum(metadata) != ORIGINAL_RECEIPT_SHA256:
        raise ValueError("Original first-open source-only file identity mismatch")
    receipt = json.loads(metadata)
    if (receipt.get("status") != "source_only_pre_response" or
        receipt.get("program") != SOURCE_STUDY or
        receipt.get("sha256") != checksum(raw) or
        receipt.get("n_taxon_plot_intervals") != SOURCE_ROWS or
        receipt.get("fixed_states") != config["regions"] or
        receipt.get("fixed_species_codes") != config["species_codes"] or
        receipt.get("no_status_diameter_growth_read") is not True or
        receipt.get("species_identity_only_not_survivor_selected") is not True or
        receipt.get("no_growth_or_survival_estimation") is not True or
        receipt.get("new_cohort_not_original_v4") is not True):
        raise ValueError("Not the frozen 3-state source-only cohort")
    states = receipt.get("states", [])
    if [s.get("state") for s in states] != config["regions"] or any(
        s.get("status") != "source_only_ready" or
        s.get("no_tree_growth_or_status_read") is not True or
        s.get("plot_source", {}).get("status") != "ready" or
        s.get("tree_source", {}).get("status") != "ready" for s in states
    ):
        raise ValueError("Source-only access/success boundary missing")
    # Do not deserialize hidden extra biological columns from an invalid table.
    with file.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if (set(reader.fieldnames or []) != gate.FIELDS or
            len(reader.fieldnames or []) != len(gate.FIELDS)):
            raise ValueError("Source-only schema includes missing/outcome fields")
        rows = list(reader)
    if len(rows) != SOURCE_ROWS or dict(Counter(r["state"] for r in rows)) != SOURCE_BY_STATE:
        raise ValueError("Complete first-open denominator changed")
    return rows


def reconcile_rows(rows: list[dict], config: dict) -> tuple[list[dict], dict]:
    """A uniform, climate/outcome-blind complete-plot-chain exclusion rule."""
    gate.verify_config(config)
    county_sets = defaultdict(set)
    seen = set()
    source_by_state = Counter()
    for row in rows:
        if set(row) != gate.FIELDS:
            raise ValueError("Source-only row has unexpected fields")
        state = row["state"]
        if (state not in config["regions"] or
            row["species_code"] not in config["species_codes"] or
            len(row["county_fips"]) != 5 or not row["county_fips"].isdigit() or
            not row["county_fips"].startswith(gate.STATES[state]) or
            not row["plot_chain_id"] or not row["interval_id"]):
            raise ValueError("Invalid source-only taxon/site identity")
        identity = (row["species_code"], state, row["plot_chain_id"], row["interval_id"])
        if identity in seen:
            raise ValueError("Duplicate source-only species/site/interval identity")
        seen.add(identity)
        year = row["interval_end_year"]
        if len(year) != 4 or not year.isdigit() or not 1991 <= int(year) <= 2026:
            raise ValueError("Invalid source-only interval year")
        for field in ("temperature_anomaly_c", "precipitation_anomaly_mm"):
            try:
                value = float(row[field])
            except (TypeError, ValueError) as e:
                raise ValueError("Invalid source-only environmental input") from e
            if not math.isfinite(value):
                raise ValueError("Nonfinite source-only environmental input")
        county_sets[(state, row["plot_chain_id"])].add(row["county_fips"])
        source_by_state[state] += 1
    bad_keys = {key for key, counties in county_sets.items() if len(counties) > 1}
    kept = [row for row in rows if (row["state"], row["plot_chain_id"]) not in bad_keys]
    rejected = [row for row in rows if (row["state"], row["plot_chain_id"]) in bad_keys]
    if len(kept) + len(rejected) != len(rows):
        raise RuntimeError("Quality-control denominator lost")
    # Hide the original public FIA CNs in the compact committed audit receipt.
    hashes = sorted(checksum((a + "|" + b).encode()) for a, b in bad_keys)
    report = {
        "program": "fia_first_source_only_county_stability_reconciliation_v2",
        "scope": "first_opened_new_source_only_cohort_not_old_v4",
        "original_source_run": SOURCE_RUN,
        "original_source_artifact": SOURCE_ARTIFACT,
        "original_artifact_zip_sha256": SOURCE_ARTIFACT_ZIP_SHA256,
        "original_csv_sha256": ORIGINAL_CSV_SHA256,
        "original_source_receipt_sha256": ORIGINAL_RECEIPT_SHA256,
        "n_original_rows": len(rows),
        "n_kept_rows": len(kept),
        "n_rejected_rows": len(rejected),
        "n_county_unstable_plot_chains": len(bad_keys),
        "county_unstable_chain_hashed_identities": hashes,
        "original_rows_by_state": dict(sorted(source_by_state.items())),
        "rejected_rows_by_state": dict(sorted(Counter(r["state"] for r in rejected).items())),
        "rejected_rows_by_species": dict(sorted(Counter(r["species_code"] for r in rejected).items())),
        "all_rows_of_county_unstable_plot_chains_excluded": True,
        "exclusion_rule_uses_climate_or_biological_outcomes": False,
        "post_source_quality_control_not_original_one_shot_gate": True,
        "no_new_FIA_download_or_growth_or_survival_opening": True,
        "biological_promotion_authorized": False,
    }
    return kept, report


def run(source_dir: Path, out_dir: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    rows = original_input(source_dir, config)
    kept, report = reconcile_rows(rows, config)
    out_dir.mkdir(parents=True, exist_ok=True)
    # The exact original source and its STOP must remain unchanged.
    clean_file = out_dir / "fia_new_cohort_joint_source_only_county_stable_v2.csv"
    with clean_file.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=sorted(gate.FIELDS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept)
    derived_receipt = {
        "program": "fia_joint_source_only_county_stable_v2",
        "status": "source_only_pre_response",
        "sha256": checksum(clean_file.read_bytes()),
        "climate_source": config["climate_source"],
        "species_identity_only_not_survivor_selected": True,
        "no_status_diameter_growth_read": True,
        "derived_from_first_source_only_artifact": SOURCE_ARTIFACT,
        "original_csv_sha256": ORIGINAL_CSV_SHA256,
        "n_original_rows": len(rows),
        "n_excluded_rows": report["n_rejected_rows"],
        "n_clean_rows": len(kept),
        "post_source_qc_not_preregistered_biological_test": True,
    }
    receipt_file = out_dir / "derived_receipt.json"
    receipt_file.write_text(json.dumps(derived_receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    verified = gate.read_source_only_csv(clean_file, receipt_file, config)
    support = gate.evaluate_source_only(verified, config)
    report["derived_csv_sha256"] = derived_receipt["sha256"]
    report["derived_receipt_sha256"] = checksum(receipt_file.read_bytes())
    report["source_support_eligible_species"] = support["source_eligible_species"]
    report["time_aligned_joint_support_positive_species"] = sum(
        x["n_shared_time_aligned_joint_bins"] > 0 for x in support["species"]
    )
    report["source_eligible_species_codes"] = [
        x["species_code"] for x in support["species"]
        if x["status"] == "descriptive_source_support_eligible"
    ]
    report["not_a_demographic_or_niche_adaptation_result"] = True
    (out_dir / "quality_audit_v2.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (out_dir / "joint_time_support_v2.json").write_text(json.dumps(support, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n_original_rows", "n_rejected_rows",
        "n_kept_rows", "n_county_unstable_plot_chains", "source_support_eligible_species")}, sort_keys=True))
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--config", type=Path, default=Path("configs/fia_joint_climate_support_gate_v1.json"))
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    run(a.source_dir, a.output_dir, a.config)


if __name__ == "__main__":
    main()
