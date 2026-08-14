"""Resolve CHELSA v2.1 candidate rasters and optionally extract point values."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from .data.chelsa import CHELSA_V21_BASE, raster_specs_from_chelsa_manifest, resolve_chelsa_manifest
from .data.raster import extract_raster_values


def _read_points(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(p)
    return pd.read_csv(p)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve the SDMR CHELSA v2.1 manifest to COG URIs and optionally extract point values."
    )
    parser.add_argument("--manifest", default="configs/chelsa_v2_1_plant_candidates.csv")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--base-url", default=CHELSA_V21_BASE)
    parser.add_argument("--include-legacy", action="store_true", help="Include legacy_archive rows such as SWB.")
    parser.add_argument("--points", help="Optional CSV/Parquet with longitude/latitude; requires sdmr[geo].")
    parser.add_argument("--only", help="Comma-separated predictor names to resolve/extract.")
    args = parser.parse_args(argv)

    manifest = pd.read_csv(args.manifest)
    if args.only:
        wanted = {x.strip() for x in args.only.split(",") if x.strip()}
        missing = wanted - set(manifest["predictor"].astype(str))
        if missing:
            parser.error("Unknown predictors in --only: " + ",".join(sorted(missing)))
        manifest = manifest.loc[manifest["predictor"].astype(str).isin(wanted)].reset_index(drop=True)

    availability = ("current", "legacy_archive") if args.include_legacy else ("current",)
    resolved = resolve_chelsa_manifest(
        manifest,
        base_url=args.base_url,
        include_availability=availability,
        strict=False,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    resolved.to_csv(out / "chelsa_resolution_ledger.csv", index=False)
    resolved.loc[resolved.resolution_status == "resolved"].to_csv(out / "chelsa_layer_catalog.csv", index=False)
    resolved.loc[resolved.resolution_status != "resolved"].to_csv(out / "chelsa_unresolved.csv", index=False)

    if args.points:
        specs, _ = raster_specs_from_chelsa_manifest(
            manifest,
            base_url=args.base_url,
            include_availability=availability,
            strict=False,
        )
        if not specs:
            parser.error("No resolved CHELSA layers selected for extraction")
        points = _read_points(args.points)
        values, provenance = extract_raster_values(points, specs)
        values.to_csv(out / "points_with_chelsa.csv", index=False)
        provenance.to_csv(out / "raster_provenance.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
