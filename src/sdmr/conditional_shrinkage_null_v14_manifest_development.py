"""Manifest-anchored wrapper for v14 consumed-development diagnosis.

The underlying v14 runner may recompute v8 states to obtain fitted baseline
objects, but successor diagnostic membership is never re-derived from those
floating-point-sensitive states. The authoritative denominator is the frozen v9
shared-candidate manifest.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .conditional_shrinkage_null_v14_development import fit_family as _fit_family_raw
from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "configs" / "shared_candidate_manifest_v9_consumed.csv"


def _manifest() -> pd.DataFrame:
    frame = pd.read_csv(MANIFEST)
    expected = {"family", "seed", "target_process"}
    if set(frame.columns) != expected:
        raise ValueError("unexpected v9 shared-candidate manifest schema")
    frame["seed"] = frame["seed"].astype(int)
    if len(frame) != 13 or frame.duplicated(["family", "seed", "target_process"]).any():
        raise ValueError("v9 shared-candidate manifest must contain exactly 13 unique cells")
    if not set(frame["family"]).issubset(set(KNOWN_TRUTH_FAMILIES)):
        raise ValueError("manifest contains unknown family")
    return frame.sort_values(["family", "seed", "target_process"]).reset_index(drop=True)


def _filter_csv(path: Path, allowed: pd.DataFrame, *, process_col: str = "target_process") -> pd.DataFrame:
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    if frame.empty:
        frame.to_csv(path, index=False)
        return frame
    required = {"family", "seed", process_col}
    if not required.issubset(frame.columns):
        raise ValueError(f"diagnostic output lacks manifest keys: {path.name}")
    frame["seed"] = frame["seed"].astype(int)
    allowed_keys = allowed.rename(columns={"target_process": process_col})
    keys = ["family", "seed", process_col]
    keep = frame.merge(allowed_keys.assign(_manifest_member=True), on=keys, how="left")
    keep = keep.loc[keep["_manifest_member"].fillna(False)].drop(columns="_manifest_member")
    keep.to_csv(path, index=False)
    return keep


def fit_family(family: str, output_dir: str | Path):
    out = Path(output_dir)
    _fit_family_raw(family, out)
    manifest = _manifest()
    allowed = manifest.loc[manifest["family"].eq(str(family))].copy()
    cases = _filter_csv(out / "case_summary.csv", allowed)
    statuses = _filter_csv(out / "null_status.csv", allowed)
    _filter_csv(out / "null_route_summary.csv", allowed, process_col="process")
    _filter_csv(out / "null_fold_evidence.csv", allowed, process_col="process")

    if len(cases) != len(allowed):
        missing = allowed.merge(cases[["family", "seed", "target_process"]] if len(cases) else pd.DataFrame(columns=["family", "seed", "target_process"]), on=["family", "seed", "target_process"], how="left", indicator=True)
        raise ValueError("raw v14 runner failed to evaluate frozen manifest cells: " + missing.loc[missing["_merge"].eq("left_only")].to_csv(index=False))

    # Current rerun status is diagnostic only; membership remains frozen by v9.
    drift = pd.DataFrame()
    if len(statuses):
        drift = statuses.groupby(["family", "seed", "target_process"], as_index=False).agg(
            recomputed_v8_status=("v8_status", "first"),
            recomputed_v5_status=("v5_status", "first"),
        )
        drift["authoritative_v9_state"] = "shared_candidate"
        drift["recomputed_definition_matches_authoritative"] = (
            drift["recomputed_v5_status"].astype(str).eq("contributory_under_evidence_contract")
            & ~drift["recomputed_v8_status"].astype(str).eq("contributory_under_evidence_contract")
        )
    drift.to_csv(out / "denominator_drift_audit.csv", index=False)
    return {
        "family": str(family),
        "n_frozen_shared_candidates": int(len(cases)),
        "n_shrinkage_reproduced": int((cases["classification"].astype(str).eq("shrinkage_reproduced")).sum()) if len(cases) else 0,
        "n_recomputed_definition_mismatches": int((~drift["recomputed_definition_matches_authoritative"].astype(bool)).sum()) if len(drift) else 0,
    }


def _read(path: Path):
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def aggregate(input_dir: str | Path, output_dir: str | Path):
    root = Path(input_dir)
    expected = len(KNOWN_TRUTH_FAMILIES)
    names = ["case_summary.csv", "null_status.csv", "null_route_summary.csv", "null_fold_evidence.csv", "denominator_drift_audit.csv"]
    files = {name: list(root.rglob(name)) for name in names}
    if any(len(paths) != expected for paths in files.values()):
        raise ValueError("v14 manifest aggregate requires one artifact per family for every output")
    merged = {name: pd.concat([_read(p) for p in paths], ignore_index=True) for name, paths in files.items()}
    cases = merged["case_summary.csv"]
    manifest = _manifest()
    observed = cases[["family", "seed", "target_process"]].sort_values(["family", "seed", "target_process"]).reset_index(drop=True)
    if not observed.equals(manifest):
        raise ValueError("aggregate denominator does not equal frozen v9 manifest")
    counts = cases["classification"].value_counts()
    drift = merged["denominator_drift_audit.csv"]
    result = {
        "purpose": "conditional_shrinkage_null_v14_manifest_anchored_consumed_development_decision",
        "development_only": True,
        "eligible_for_prospective_performance_claim": False,
        "authoritative_denominator_source": "configs/shared_candidate_manifest_v9_consumed.csv",
        "n_shared_candidate_cells": 13,
        "n_shrinkage_reproduced": int(counts.get("shrinkage_reproduced", 0)),
        "n_conditioning_alignment_required": int(counts.get("conditioning_alignment_required", 0)),
        "n_mixed": int(counts.get("mixed", 0)),
        "n_recomputed_definition_mismatches": int((~drift["recomputed_definition_matches_authoritative"].astype(bool)).sum()) if len(drift) else 0,
        "fresh_known_truth_validation_authorized": False,
        "fresh_empirical_validation_authorized": False,
    }
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    for name, frame in merged.items():
        frame.to_csv(out / name, index=False)
    (out / "development_decision.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit-family"); f.add_argument("--family", required=True); f.add_argument("--output-dir", required=True)
    a = sub.add_parser("aggregate"); a.add_argument("--input-dir", required=True); a.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    result = fit_family(args.family, args.output_dir) if args.cmd == "fit-family" else aggregate(args.input_dir, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
