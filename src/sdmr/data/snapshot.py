"""Credential-free access to versioned GBIF monthly cloud occurrence snapshots.

GBIF publishes monthly occurrence snapshots as public Parquet data. This module
keeps cloud-snapshot provenance distinct from custom GBIF occurrence downloads:
the caller must declare the snapshot date and DOI, and every materialized subset
records the remote URI, extraction query hash, and local file hash.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
from pathlib import Path
from typing import Sequence

import pandas as pd

from .raster import sha256_file

GBIF_AWS_REGIONS = (
    "us-east-1",
    "eu-central-1",
    "ap-southeast-2",
    "af-south-1",
    "sa-east-1",
)

PREFERRED_SNAPSHOT_COLUMNS = (
    "gbifid",
    "datasetkey",
    "occurrenceid",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "species",
    "specieskey",
    "taxonkey",
    "scientificname",
    "acceptedscientificname",
    "taxonrank",
    "basisofrecord",
    "occurrencestatus",
    "decimallatitude",
    "decimallongitude",
    "coordinateuncertaintyinmeters",
    "year",
    "month",
    "day",
    "eventdate",
    "countrycode",
    "institutioncode",
    "issues",
    "license",
)


@dataclass(frozen=True)
class SnapshotBounds:
    west: float
    east: float
    south: float
    north: float

    def __post_init__(self):
        if not (-180 <= self.west <= 180 and -180 <= self.east <= 180):
            raise ValueError("longitude bounds must be in [-180, 180]")
        if not (-90 <= self.south <= self.north <= 90):
            raise ValueError("latitude bounds must satisfy -90 <= south <= north <= 90")


@dataclass
class GBIFSnapshotSubsetResult:
    path: Path
    provenance: pd.DataFrame


def _validate_snapshot_date(value: str) -> str:
    parsed = date.fromisoformat(str(value))
    if parsed.day != 1:
        raise ValueError("GBIF monthly snapshot date must be the first day of a month (YYYY-MM-01)")
    return parsed.isoformat()


def gbif_snapshot_s3_uri(snapshot_date: str, *, region: str = "us-east-1") -> str:
    """Return the public AWS Open Data Parquet glob for one GBIF snapshot."""
    snapshot_date = _validate_snapshot_date(snapshot_date)
    if region not in GBIF_AWS_REGIONS:
        raise ValueError(f"Unsupported GBIF AWS region: {region!r}")
    bucket = f"gbif-open-data-{region}"
    return f"s3://{bucket}/occurrence/{snapshot_date}/occurrence.parquet/*"


def _sql_literal(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _bounds_sql(bounds: SnapshotBounds) -> str:
    lat = f"decimallatitude BETWEEN {float(bounds.south)} AND {float(bounds.north)}"
    if bounds.west <= bounds.east:
        lon = f"decimallongitude BETWEEN {float(bounds.west)} AND {float(bounds.east)}"
    else:
        lon = (
            f"(decimallongitude >= {float(bounds.west)} OR "
            f"decimallongitude <= {float(bounds.east)})"
        )
    return f"({lat} AND {lon})"


def build_snapshot_filter_sql(
    *,
    species_names: Sequence[str] | None = None,
    kingdom: str | None = None,
    bounds: Sequence[SnapshotBounds] | None = None,
    require_coordinates: bool = True,
) -> str:
    """Build a deterministic WHERE clause for focal or target-group extraction."""
    scope_terms: list[str] = []
    names = [str(x).strip() for x in (species_names or ()) if str(x).strip()]
    if names:
        scope_terms.append("species IN (" + ",".join(_sql_literal(x) for x in sorted(set(names))) + ")")
    if kingdom:
        scope_terms.append("kingdom = " + _sql_literal(str(kingdom).strip()))
    if bounds:
        scope_terms.append("(" + " OR ".join(_bounds_sql(b) for b in bounds) + ")")
    if not scope_terms:
        raise ValueError("Snapshot extraction requires at least one taxonomic/spatial filter")

    terms = list(scope_terms)
    if require_coordinates:
        terms.extend(
            [
                "decimallatitude IS NOT NULL",
                "decimallongitude IS NOT NULL",
                "decimallatitude BETWEEN -90 AND 90",
                "decimallongitude BETWEEN -180 AND 180",
            ]
        )
    return " AND ".join(f"({term})" for term in terms)


def _query_sha256(uri: str, columns: Sequence[str], where_sql: str) -> str:
    payload = (uri + "\n" + ",".join(columns) + "\n" + where_sql + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _quote_identifier(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def materialize_gbif_snapshot_subset(
    output_path: str | Path,
    *,
    snapshot_date: str,
    snapshot_doi: str,
    species_names: Sequence[str] | None = None,
    kingdom: str | None = None,
    bounds: Sequence[SnapshotBounds] | None = None,
    region: str = "us-east-1",
    overwrite: bool = False,
) -> GBIFSnapshotSubsetResult:
    """Materialize a filtered public GBIF monthly snapshot subset as Parquet.

    Requires the optional ``sdmr[cloud]`` dependency. DuckDB performs remote S3
    Parquet scanning; no AWS credentials are required for the public GBIF bucket.
    Because the source dataset is very large, use narrow, predeclared filters and
    run close to an AWS mirror when practical.
    """
    if not str(snapshot_doi).strip():
        raise ValueError("snapshot_doi is required for auditable/citable cloud-snapshot use")
    output = Path(output_path)
    if output.exists() and not overwrite:
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    uri = gbif_snapshot_s3_uri(snapshot_date, region=region)
    where_sql = build_snapshot_filter_sql(
        species_names=species_names,
        kingdom=kingdom,
        bounds=bounds,
        require_coordinates=True,
    )

    try:
        import duckdb
    except ImportError as exc:
        raise ImportError("GBIF cloud snapshots require duckdb; install sdmr[cloud].") from exc

    con = duckdb.connect()
    try:
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
        con.execute(f"SET s3_region={_sql_literal(region)}")
        schema = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet({_sql_literal(uri)}, union_by_name=true)"
        ).fetchdf()
        available = {str(x).lower(): str(x) for x in schema["column_name"].tolist()}
        required = {"species", "decimallatitude", "decimallongitude"}
        if kingdom:
            required.add("kingdom")
        missing = sorted(required - set(available))
        if missing:
            raise ValueError(f"GBIF snapshot schema missing required columns: {missing}")
        selected = [available[name] for name in PREFERRED_SNAPSHOT_COLUMNS if name in available]
        select_sql = ",".join(_quote_identifier(name) for name in selected)
        query = (
            f"SELECT {select_sql} FROM read_parquet({_sql_literal(uri)}, union_by_name=true) "
            f"WHERE {where_sql}"
        )
        out_literal = _sql_literal(str(output.resolve()))
        con.execute(f"COPY ({query}) TO {out_literal} (FORMAT PARQUET, COMPRESSION ZSTD)")
        n_rows = int(con.execute(f"SELECT COUNT(*) FROM read_parquet({out_literal})").fetchone()[0])
    finally:
        con.close()

    provenance = pd.DataFrame(
        [
            {
                "source_type": "gbif_monthly_cloud_snapshot",
                "snapshot_date": _validate_snapshot_date(snapshot_date),
                "snapshot_doi": str(snapshot_doi).strip(),
                "region": region,
                "remote_uri": uri,
                "where_sql": where_sql,
                "selected_columns": ",".join(selected),
                "query_sha256": _query_sha256(uri, selected, where_sql),
                "path": str(output),
                "sha256": sha256_file(output),
                "bytes": int(output.stat().st_size),
                "n_rows": n_rows,
                "taxonomy_provenance": "GBIF interpreted taxonomy embedded in declared monthly snapshot",
            }
        ]
    )
    return GBIFSnapshotSubsetResult(path=output, provenance=provenance)
