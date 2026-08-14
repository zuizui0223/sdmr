"""Materialize auditable subsets of GBIF's public monthly cloud snapshots."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .data.snapshot import SnapshotBounds, materialize_gbif_snapshot_subset
from .data.snapshot_bounds import bounds_from_occurrences


def _read_taxa(path: str) -> list[str]:
    frame = pd.read_csv(path)
    if "scientific_name" not in frame:
        raise ValueError("taxa CSV must contain scientific_name")
    return frame["scientific_name"].dropna().astype(str).str.strip().loc[lambda x: x.ne("")].tolist()


def _read_table(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in {".parquet", ".pq"}:
        try:
            return pd.read_parquet(p)
        except ImportError as exc:
            raise ImportError("Reading focal Parquet for bounds requires pyarrow; install sdmr[parquet].") from exc
    return pd.read_csv(p)


def _read_bounds(path: str) -> list[SnapshotBounds]:
    frame = pd.read_csv(path)
    required = {"west", "east", "south", "north"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"bounds CSV missing columns: {sorted(missing)}")
    return [
        SnapshotBounds(
            west=float(row.west),
            east=float(row.east),
            south=float(row.south),
            north=float(row.north),
        )
        for row in frame.itertuples(index=False)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract a citable subset from GBIF's public monthly Parquet snapshot. "
            "Use --taxa for focal records or --kingdom plus spatial bounds for a target-group subset."
        )
    )
    parser.add_argument("--snapshot-date", required=True, help="Monthly snapshot date YYYY-MM-01")
    parser.add_argument("--snapshot-doi", required=True, help="DOI shown by GBIF for this monthly snapshot")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--taxa", help="CSV containing scientific_name")
    parser.add_argument("--kingdom", help="Taxonomic kingdom, e.g. Plantae")
    parser.add_argument("--bounds", help="Optional CSV: west,east,south,north; rows are OR-combined")
    parser.add_argument(
        "--bounds-from-occurrences",
        help="Optional focal CSV/Parquet; derive one dateline-aware bounding box per species/group.",
    )
    parser.add_argument("--bounds-buffer-degrees", type=float, default=2.0)
    parser.add_argument("--output", required=True, help="Local .parquet subset path")
    parser.add_argument("--provenance", help="Output provenance CSV; default <output>.provenance.csv")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    if args.bounds and args.bounds_from_occurrences:
        parser.error("Use --bounds or --bounds-from-occurrences, not both")
    if args.bounds_buffer_degrees < 0:
        parser.error("--bounds-buffer-degrees must be >= 0")
    species_names = _read_taxa(args.taxa) if args.taxa else None
    if args.bounds:
        bounds = _read_bounds(args.bounds)
    elif args.bounds_from_occurrences:
        bounds = bounds_from_occurrences(
            _read_table(args.bounds_from_occurrences),
            buffer_degrees=args.bounds_buffer_degrees,
        )
    else:
        bounds = None
    if not species_names and not args.kingdom:
        parser.error("Provide --taxa and/or --kingdom; unfiltered global snapshot extraction is intentionally disabled")
    if args.kingdom and not bounds and not species_names:
        parser.error("Kingdom-only extraction requires spatial bounds to avoid accidentally materializing a huge global subset")

    result = materialize_gbif_snapshot_subset(
        args.output,
        snapshot_date=args.snapshot_date,
        snapshot_doi=args.snapshot_doi,
        species_names=species_names,
        kingdom=args.kingdom,
        bounds=bounds,
        region=args.region,
        overwrite=args.overwrite,
    )
    provenance_path = Path(args.provenance) if args.provenance else Path(str(args.output) + ".provenance.csv")
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    result.provenance.to_csv(provenance_path, index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
