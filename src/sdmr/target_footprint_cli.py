"""Materialize a minimal global non-focal Plantae sampling-effort grid from a frozen GBIF snapshot."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

from .data.raster import sha256_file
from .data.snapshot import (
    GBIF_HTTP_RETRIES,
    GBIF_HTTP_RETRY_BACKOFF,
    GBIF_HTTP_RETRY_WAIT_MS,
    GBIF_HTTP_TIMEOUT_SECONDS,
    _configure_duckdb_cloud,
    _sql_literal,
    gbif_snapshot_s3_uri,
)
from .data.snapshot_citation import validate_snapshot_citation


def _query_sha(uri: str, cell: float, query: str, excluded_taxa_sha256: str) -> str:
    payload = f"{uri}\nPlantae\n{cell:.17g}\n{excluded_taxa_sha256}\n{query}\n".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_excluded_taxa(path: str | Path) -> tuple[list[str], str]:
    source = Path(path)
    data = pd.read_csv(source)
    if "scientific_name" not in data:
        raise KeyError("excluded-taxa table must contain scientific_name")
    names = sorted({str(x).strip() for x in data["scientific_name"] if str(x).strip()})
    if not names:
        raise ValueError("excluded-taxa table contains no scientific names")
    return names, hashlib.sha256(source.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a global one-record-per-grid-cell non-focal Plantae sampling-effort footprint from one DOI-backed GBIF monthly snapshot. "
            "Predeclared focal taxa are excluded as whole species before any spatial sealing, so their model or sealed occurrences can never return as background."
        )
    )
    parser.add_argument("--snapshot-date", required=True)
    parser.add_argument("--snapshot-doi", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--grid-cell-degrees", type=float, default=0.05)
    parser.add_argument("--exclude-taxa", required=True, help="CSV with predeclared scientific_name values to exclude from target-group background.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--provenance")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if args.grid_cell_degrees <= 0:
        parser.error("--grid-cell-degrees must be > 0")

    excluded_taxa, excluded_taxa_sha256 = _read_excluded_taxa(args.exclude_taxa)
    excluded_sql = ",".join(_sql_literal(name) for name in excluded_taxa)

    output = Path(args.output)
    if output.exists() and not args.overwrite:
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    citation = validate_snapshot_citation(args.snapshot_date, args.snapshot_doi, region=args.region)
    uri = gbif_snapshot_s3_uri(args.snapshot_date, region=args.region)

    try:
        import duckdb
    except ImportError as exc:
        raise ImportError("Global target footprint requires duckdb; install sdmr[cloud].") from exc

    con = duckdb.connect()
    duckdb_version = str(getattr(duckdb, "__version__", ""))
    cell = float(args.grid_cell_degrees)
    try:
        _configure_duckdb_cloud(con, cloud_provider="aws", region=args.region)
        schema = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet({_sql_literal(uri)}, union_by_name=true)"
        ).fetchdf()
        available = {str(x).lower(): str(x) for x in schema["column_name"].tolist()}
        required = {"gbifid", "kingdom", "species", "decimallatitude", "decimallongitude"}
        missing = sorted(required - set(available))
        if missing:
            raise ValueError(f"GBIF snapshot schema missing footprint columns: {missing}")
        gbifid = '"' + available["gbifid"].replace('"', '""') + '"'
        kingdom = '"' + available["kingdom"].replace('"', '""') + '"'
        species = '"' + available["species"].replace('"', '""') + '"'
        lat = '"' + available["decimallatitude"].replace('"', '""') + '"'
        lon = '"' + available["decimallongitude"].replace('"', '""') + '"'
        source = f"read_parquet({_sql_literal(uri)}, union_by_name=true)"
        query = f"""
        WITH filtered AS (
          SELECT
            {gbifid} AS gbifid,
            {lon} AS decimallongitude,
            {lat} AS decimallatitude,
            FLOOR(({lon} + 180.0) / {cell})::BIGINT AS gx,
            FLOOR(({lat} + 90.0) / {cell})::BIGINT AS gy
          FROM {source}
          WHERE {kingdom} = 'Plantae'
            AND ({species} IS NULL OR {species} NOT IN ({excluded_sql}))
            AND {lat} IS NOT NULL AND {lon} IS NOT NULL
            AND {lat} BETWEEN -90 AND 90
            AND {lon} BETWEEN -180 AND 180
        )
        SELECT
          ARG_MIN(gbifid, gbifid) AS gbifid,
          'Plantae_nonfocal_target_group' AS species,
          ARG_MIN(decimallongitude, gbifid) AS decimallongitude,
          ARG_MIN(decimallatitude, gbifid) AS decimallatitude
        FROM filtered
        GROUP BY gx, gy
        """.strip()
        out_literal = _sql_literal(str(output.resolve()))
        con.execute(f"COPY ({query}) TO {out_literal} (FORMAT PARQUET, COMPRESSION ZSTD)")
        n_rows = int(con.execute(f"SELECT COUNT(*) FROM read_parquet({out_literal})").fetchone()[0])
        settings = {
            str(name): str(value)
            for name, value in con.execute(
                "SELECT name, value FROM duckdb_settings() WHERE name IN ("
                "'http_keep_alive','http_retries','http_retry_wait_ms','http_retry_backoff','http_timeout',"
                "'enable_http_metadata_cache','enable_external_file_cache')"
            ).fetchall()
        }
    finally:
        con.close()

    provenance = pd.DataFrame(
        [
            {
                "source_type": "gbif_monthly_cloud_snapshot_global_nonfocal_target_group_footprint",
                "snapshot_date": args.snapshot_date,
                "snapshot_doi": citation.doi,
                "snapshot_citation_url": citation.citation_url,
                "snapshot_citation_sha256": citation.citation_sha256,
                "snapshot_citation_doi": citation.doi,
                "cloud_provider": "aws",
                "region": args.region,
                "remote_uri": uri,
                "query_engine": "duckdb",
                "duckdb_version": duckdb_version,
                "where_sql": "kingdom='Plantae' AND species NOT IN predeclared focal panel AND finite valid coordinates",
                "selected_columns": "gbifid,kingdom,species,decimallongitude,decimallatitude",
                "sampling_mode": "global_nonfocal_one_per_grid_cell_sampling_footprint",
                "one_per_grid_cell_degrees": cell,
                "excluded_taxa_count": len(excluded_taxa),
                "excluded_taxa_sha256": excluded_taxa_sha256,
                "excluded_taxa": "|".join(excluded_taxa),
                "query_sha256": _query_sha(uri, cell, query, excluded_taxa_sha256),
                "path": str(output),
                "sha256": sha256_file(output),
                "bytes": int(output.stat().st_size),
                "n_rows": n_rows,
                "taxonomy_provenance": "GBIF interpreted kingdom/species embedded in declared monthly snapshot; the complete predeclared focal taxon panel is excluded before footprint aggregation",
                "http_keep_alive": settings.get("http_keep_alive", "false"),
                "http_retries": settings.get("http_retries", str(GBIF_HTTP_RETRIES)),
                "http_retry_wait_ms": settings.get("http_retry_wait_ms", str(GBIF_HTTP_RETRY_WAIT_MS)),
                "http_retry_backoff": settings.get("http_retry_backoff", str(GBIF_HTTP_RETRY_BACKOFF)),
                "http_timeout": settings.get("http_timeout", str(GBIF_HTTP_TIMEOUT_SECONDS)),
                "enable_http_metadata_cache": settings.get("enable_http_metadata_cache", "true"),
                "enable_external_file_cache": settings.get("enable_external_file_cache", "true"),
            }
        ]
    )
    prov_path = Path(args.provenance) if args.provenance else Path(str(output) + ".provenance.csv")
    provenance.to_csv(prov_path, index=False)
    Path(str(output) + ".citation.txt").write_text(citation.citation_text, encoding="utf-8")
    print("target_footprint_rows", n_rows)
    print("excluded_focal_taxa", len(excluded_taxa))
    print("target_footprint_sha256", provenance.iloc[0]["sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
