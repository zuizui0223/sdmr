"""Bridge citable GBIF cloud-snapshot subsets into the Product-A pilot runner."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .data.raster import sha256_file
from .pilot_cli import main as pilot_main

_RESERVED = {
    "--gbif-download",
    "--gbif-download-key",
    "--target-group-download",
    "--target-group-download-key",
    "--checklist-key",
    "--output-dir",
    "--allow-pilot-target-group",
}


def _read_snapshot_provenance(path: str, subset_path: str) -> dict[str, object]:
    frame = pd.read_csv(path)
    if len(frame) != 1:
        raise ValueError("snapshot provenance CSV must contain exactly one row")
    row = frame.iloc[0].to_dict()
    if str(row.get("source_type", "")) != "gbif_monthly_cloud_snapshot":
        raise ValueError("provenance source_type must be gbif_monthly_cloud_snapshot")
    required = ("snapshot_date", "snapshot_doi", "remote_uri", "query_sha256", "sha256")
    missing = [key for key in required if not str(row.get(key, "")).strip()]
    if missing:
        raise ValueError(f"snapshot provenance missing fields: {missing}")
    actual_sha = sha256_file(subset_path)
    if actual_sha != str(row["sha256"]):
        raise ValueError(
            f"snapshot subset SHA mismatch for {subset_path}: expected {row['sha256']}, got {actual_sha}"
        )
    return row


def _enrich_pilot_provenance(path: Path, snapshot: dict[str, object]) -> None:
    frame = pd.read_csv(path)
    frame["source_type"] = "gbif_monthly_cloud_snapshot_subset"
    for column in ("snapshot_date", "snapshot_doi", "region", "remote_uri", "where_sql", "query_sha256"):
        if column in snapshot:
            frame[column] = snapshot[column]
    frame["taxonomy_provenance"] = snapshot.get(
        "taxonomy_provenance", "GBIF interpreted taxonomy embedded in declared monthly snapshot"
    )
    frame.to_csv(path, index=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run sdmr-pilot from focal and target-group subsets materialized from the same citable GBIF monthly snapshot. "
            "Additional sdmr-pilot arguments follow a standalone --."
        )
    )
    parser.add_argument("--focal-subset", required=True)
    parser.add_argument("--focal-provenance", required=True)
    parser.add_argument("--target-group-subset", required=True)
    parser.add_argument("--target-group-provenance", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("pilot_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    focal = _read_snapshot_provenance(args.focal_provenance, args.focal_subset)
    target = _read_snapshot_provenance(args.target_group_provenance, args.target_group_subset)
    for key in ("snapshot_date", "snapshot_doi"):
        if str(focal[key]) != str(target[key]):
            parser.error(f"focal and target-group subsets must come from the same {key}")

    extra = list(args.pilot_args)
    if extra and extra[0] == "--":
        extra = extra[1:]
    conflicts = sorted(flag for flag in _RESERVED if flag in extra)
    if conflicts:
        parser.error("Do not repeat snapshot-controlled pilot arguments: " + ",".join(conflicts))

    date = str(focal["snapshot_date"])
    doi = str(focal["snapshot_doi"])
    source_key = f"snapshot:{date}:{doi}"
    pilot_argv = [
        "--gbif-download", args.focal_subset,
        "--gbif-download-key", source_key,
        "--checklist-key", f"snapshot-interpreted:{date}",
        "--target-group-download", args.target_group_subset,
        "--target-group-download-key", source_key,
        "--output-dir", args.output_dir,
        *extra,
    ]
    code = pilot_main(pilot_argv)
    if code != 0:
        return int(code)

    out = Path(args.output_dir)
    focal_pilot = out / "gbif_focal_provenance.csv"
    target_pilot = out / "gbif_target_group_provenance.csv"
    _enrich_pilot_provenance(focal_pilot, focal)
    _enrich_pilot_provenance(target_pilot, target)
    pd.DataFrame([focal]).to_csv(out / "gbif_focal_snapshot_extraction_provenance.csv", index=False)
    pd.DataFrame([target]).to_csv(out / "gbif_target_group_snapshot_extraction_provenance.csv", index=False)
    (out / "snapshot_pilot_contract.json").write_text(
        json.dumps(
            {
                "snapshot_date": date,
                "snapshot_doi": doi,
                "focal_query_sha256": str(focal["query_sha256"]),
                "target_group_query_sha256": str(target["query_sha256"]),
                "focal_subset_sha256": str(focal["sha256"]),
                "target_group_subset_sha256": str(target["sha256"]),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
