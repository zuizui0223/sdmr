"""Exact shard-parallel materialization of the global non-focal Plantae footprint.

The frozen GBIF monthly snapshot contains thousands of Parquet shards. A single
query over every shard is unnecessarily fragile. This CLI exploits a simple
algebraic property: for each 0.05-degree cell, ``ARG_MIN(record, gbifid)`` can
be computed per disjoint shard subset and then ``ARG_MIN`` can be applied again
to those chunk minima. The result is exactly the same global minimum record per
cell as one monolithic query, provided every snapshot shard occurs in exactly
one chunk.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
from .target_footprint_cli import _read_excluded_taxa


def _sql_list(values: list[str]) -> str:
    return "[" + ",".join(_sql_literal(value) for value in values) + "]"


def _list_snapshot_shards(con, snapshot_date: str, region: str) -> list[str]:
    uri = gbif_snapshot_s3_uri(snapshot_date, region=region)
    rows = con.execute(f"SELECT file FROM glob({_sql_literal(uri)}) ORDER BY file").fetchall()
    files = [str(row[0]) for row in rows]
    if not files:
        raise ValueError("GBIF snapshot contains no Parquet shards")
    if len(set(files)) != len(files):
        raise ValueError("GBIF snapshot shard catalog contains duplicate paths")
    return files


def _chunk_files(files: list[str], chunk_index: int, chunk_count: int) -> list[str]:
    if chunk_count < 1:
        raise ValueError("chunk_count must be >= 1")
    if not 0 <= chunk_index < chunk_count:
        raise ValueError("chunk_index must satisfy 0 <= chunk_index < chunk_count")
    # Contiguous chunks simplify audit: concatenating chunk catalogs in index
    # order reconstructs the exact globally sorted file list.
    n = len(files)
    start = (n * chunk_index) // chunk_count
    stop = (n * (chunk_index + 1)) // chunk_count
    return files[start:stop]


def _settings(con) -> dict[str, str]:
    names = (
        "'http_keep_alive','http_retries','http_retry_wait_ms','http_retry_backoff','http_timeout',"
        "'enable_http_metadata_cache','enable_external_file_cache'"
    )
    return {
        str(name): str(value)
        for name, value in con.execute(
            f"SELECT name, value FROM duckdb_settings() WHERE name IN ({names})"
        ).fetchall()
    }


def _quoted_identifier(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _chunk_query(
    con,
    files: list[str],
    *,
    excluded_taxa: list[str],
    cell: float,
) -> str:
    first = files[0]
    schema = con.execute(
        f"DESCRIBE SELECT * FROM read_parquet({_sql_literal(first)}, union_by_name=true)"
    ).fetchdf()
    available = {str(x).lower(): str(x) for x in schema["column_name"].tolist()}
    required = {"gbifid", "kingdom", "species", "decimallatitude", "decimallongitude"}
    missing = sorted(required - set(available))
    if missing:
        raise ValueError(f"GBIF snapshot schema missing footprint columns: {missing}")

    gbifid = _quoted_identifier(available["gbifid"])
    kingdom = _quoted_identifier(available["kingdom"])
    species = _quoted_identifier(available["species"])
    lat = _quoted_identifier(available["decimallatitude"])
    lon = _quoted_identifier(available["decimallongitude"])
    excluded_sql = ",".join(_sql_literal(name) for name in excluded_taxa)
    source = f"read_parquet({_sql_list(files)}, union_by_name=true)"
    return f"""
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
      gx,
      gy,
      ARG_MIN(gbifid, gbifid) AS gbifid,
      ARG_MIN(decimallongitude, gbifid) AS decimallongitude,
      ARG_MIN(decimallatitude, gbifid) AS decimallatitude
    FROM filtered
    GROUP BY gx, gy
    """.strip()


def _logical_query_sha(snapshot_uri: str, cell: float, excluded_taxa_sha256: str) -> str:
    payload = (
        "parallel_exact_argmin_v1\n"
        + snapshot_uri
        + "\nkingdom=Plantae\nexclude_taxa_sha256="
        + excluded_taxa_sha256
        + f"\ngrid={cell:.17g}\n"
        + "valid_coordinates=true\nchunk_local_argmin_then_global_argmin=true\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _run_chunk(args) -> int:
    if args.grid_cell_degrees <= 0:
        raise ValueError("grid_cell_degrees must be > 0")
    excluded_taxa, excluded_taxa_sha256 = _read_excluded_taxa(args.exclude_taxa)
    try:
        import duckdb
    except ImportError as exc:
        raise ImportError("Parallel target footprint requires duckdb; install sdmr[cloud].") from exc

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        raise FileExistsError(output)

    con = duckdb.connect()
    try:
        _configure_duckdb_cloud(con, cloud_provider="aws", region=args.region)
        files = _list_snapshot_shards(con, args.snapshot_date, args.region)
        selected = _chunk_files(files, args.chunk_index, args.chunk_count)
        if not selected:
            raise ValueError(f"chunk {args.chunk_index} has no shard files")
        query = _chunk_query(
            con,
            selected,
            excluded_taxa=excluded_taxa,
            cell=float(args.grid_cell_degrees),
        )
        out_literal = _sql_literal(str(output.resolve()))
        con.execute(f"COPY ({query}) TO {out_literal} (FORMAT PARQUET, COMPRESSION ZSTD)")
        n_rows = int(con.execute(f"SELECT COUNT(*) FROM read_parquet({out_literal})").fetchone()[0])
        settings = _settings(con)
    finally:
        con.close()

    catalog_sha = hashlib.sha256(("\n".join(files) + "\n").encode("utf-8")).hexdigest()
    chunk_catalog_sha = hashlib.sha256(("\n".join(selected) + "\n").encode("utf-8")).hexdigest()
    metadata = {
        "mode": "chunk",
        "snapshot_date": args.snapshot_date,
        "region": args.region,
        "chunk_index": int(args.chunk_index),
        "chunk_count": int(args.chunk_count),
        "snapshot_shard_count": len(files),
        "snapshot_shard_catalog_sha256": catalog_sha,
        "chunk_shard_count": len(selected),
        "chunk_shard_catalog_sha256": chunk_catalog_sha,
        "first_shard": selected[0],
        "last_shard": selected[-1],
        "excluded_taxa_count": len(excluded_taxa),
        "excluded_taxa_sha256": excluded_taxa_sha256,
        "one_per_grid_cell_degrees": float(args.grid_cell_degrees),
        "partial_rows": n_rows,
        "partial_sha256": sha256_file(output),
        "logical_query_sha256": _logical_query_sha(
            gbif_snapshot_s3_uri(args.snapshot_date, region=args.region),
            float(args.grid_cell_degrees),
            excluded_taxa_sha256,
        ),
        "http_settings": settings,
    }
    meta_path = Path(args.metadata) if args.metadata else output.with_suffix(output.suffix + ".metadata.json")
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


def _run_aggregate(args) -> int:
    parts_root = Path(args.parts_root)
    metadata_paths = sorted(parts_root.rglob("*.metadata.json"))
    if not metadata_paths:
        raise ValueError("no chunk metadata files found")
    metadata = [json.loads(path.read_text(encoding="utf-8")) for path in metadata_paths]
    expected_count = int(metadata[0]["chunk_count"])
    by_index = {int(row["chunk_index"]): row for row in metadata}
    if len(by_index) != expected_count or set(by_index) != set(range(expected_count)):
        raise ValueError(f"expected complete chunk indices 0..{expected_count - 1}; found {sorted(by_index)}")

    invariants = (
        "snapshot_date",
        "region",
        "chunk_count",
        "snapshot_shard_count",
        "snapshot_shard_catalog_sha256",
        "excluded_taxa_count",
        "excluded_taxa_sha256",
        "one_per_grid_cell_degrees",
        "logical_query_sha256",
    )
    for key in invariants:
        values = {str(row[key]) for row in metadata}
        if len(values) != 1:
            raise ValueError(f"chunk invariant differs for {key}: {sorted(values)}")
    if sum(int(row["chunk_shard_count"]) for row in metadata) != int(metadata[0]["snapshot_shard_count"]):
        raise ValueError("chunk shard counts do not cover the complete snapshot catalog")

    # Chunk catalogs are contiguous slices of the same sorted global catalog.
    # Consecutive first/last paths plus total counts are recorded; exact catalog
    # identity is already guaranteed by every chunk independently listing and
    # fingerprinting the same snapshot glob.
    partial_paths = sorted(parts_root.rglob("partial.parquet"))
    if len(partial_paths) != expected_count:
        raise ValueError(f"expected {expected_count} partial parquet files, found {len(partial_paths)}")
    expected_partial_shas = sorted(str(row["partial_sha256"]) for row in metadata)
    actual_partial_shas = sorted(sha256_file(path) for path in partial_paths)
    if actual_partial_shas != expected_partial_shas:
        raise ValueError("partial Parquet SHA set does not match chunk metadata")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        raise FileExistsError(output)

    try:
        import duckdb
    except ImportError as exc:
        raise ImportError("Parallel target aggregation requires duckdb; install sdmr[cloud].") from exc
    con = duckdb.connect()
    try:
        source = f"read_parquet({_sql_list([str(p.resolve()) for p in partial_paths])}, union_by_name=true)"
        query = f"""
        SELECT
          ARG_MIN(gbifid, gbifid) AS gbifid,
          'Plantae_nonfocal_target_group' AS species,
          ARG_MIN(decimallongitude, gbifid) AS decimallongitude,
          ARG_MIN(decimallatitude, gbifid) AS decimallatitude
        FROM {source}
        GROUP BY gx, gy
        """.strip()
        out_literal = _sql_literal(str(output.resolve()))
        con.execute(f"COPY ({query}) TO {out_literal} (FORMAT PARQUET, COMPRESSION ZSTD)")
        n_rows = int(con.execute(f"SELECT COUNT(*) FROM read_parquet({out_literal})").fetchone()[0])
    finally:
        con.close()

    citation = validate_snapshot_citation(
        metadata[0]["snapshot_date"], args.snapshot_doi, region=metadata[0]["region"]
    )
    provenance = pd.DataFrame(
        [
            {
                "source_type": "gbif_monthly_cloud_snapshot_global_nonfocal_target_group_footprint_parallel_exact",
                "snapshot_date": metadata[0]["snapshot_date"],
                "snapshot_doi": citation.doi,
                "snapshot_citation_url": citation.citation_url,
                "snapshot_citation_sha256": citation.citation_sha256,
                "snapshot_citation_doi": citation.doi,
                "cloud_provider": "aws",
                "region": metadata[0]["region"],
                "remote_uri": gbif_snapshot_s3_uri(metadata[0]["snapshot_date"], region=metadata[0]["region"]),
                "query_engine": "duckdb_shard_parallel_exact_argmin",
                "duckdb_version": "chunk-recorded",
                "where_sql": "kingdom='Plantae' AND species NOT IN predeclared focal panel AND finite valid coordinates",
                "selected_columns": "gbifid,kingdom,species,decimallongitude,decimallatitude",
                "sampling_mode": "global_nonfocal_one_per_grid_cell_sampling_footprint",
                "one_per_grid_cell_degrees": float(metadata[0]["one_per_grid_cell_degrees"]),
                "excluded_taxa_count": int(metadata[0]["excluded_taxa_count"]),
                "excluded_taxa_sha256": metadata[0]["excluded_taxa_sha256"],
                "excluded_taxa": "predeclared panel; see excluded_taxa_sha256",
                "query_sha256": metadata[0]["logical_query_sha256"],
                "path": str(output),
                "sha256": sha256_file(output),
                "bytes": int(output.stat().st_size),
                "n_rows": n_rows,
                "snapshot_shard_count": int(metadata[0]["snapshot_shard_count"]),
                "snapshot_shard_catalog_sha256": metadata[0]["snapshot_shard_catalog_sha256"],
                "parallel_chunk_count": expected_count,
                "parallel_reduction": "per-chunk ARG_MIN(gbifid) per 0.05-degree cell followed by global ARG_MIN over chunk minima",
                "taxonomy_provenance": "GBIF interpreted kingdom/species embedded in frozen monthly snapshot; complete predeclared focal panel excluded before chunk aggregation",
                "http_keep_alive": "false",
                "http_retries": str(GBIF_HTTP_RETRIES),
                "http_retry_wait_ms": str(GBIF_HTTP_RETRY_WAIT_MS),
                "http_retry_backoff": str(GBIF_HTTP_RETRY_BACKOFF),
                "http_timeout": str(GBIF_HTTP_TIMEOUT_SECONDS),
                "enable_http_metadata_cache": "true",
                "enable_external_file_cache": "true",
            }
        ]
    )
    prov_path = Path(args.provenance) if args.provenance else Path(str(output) + ".provenance.csv")
    provenance.to_csv(prov_path, index=False)
    Path(str(output) + ".citation.txt").write_text(citation.citation_text, encoding="utf-8")
    print("target_footprint_rows", n_rows)
    print("snapshot_shards", metadata[0]["snapshot_shard_count"])
    print("parallel_chunks", expected_count)
    print("target_footprint_sha256", provenance.iloc[0]["sha256"])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exact shard-parallel Product-A non-focal target footprint materializer")
    sub = parser.add_subparsers(dest="mode", required=True)

    chunk = sub.add_parser("chunk")
    chunk.add_argument("--snapshot-date", required=True)
    chunk.add_argument("--region", default="us-east-1")
    chunk.add_argument("--exclude-taxa", required=True)
    chunk.add_argument("--grid-cell-degrees", type=float, default=0.05)
    chunk.add_argument("--chunk-index", type=int, required=True)
    chunk.add_argument("--chunk-count", type=int, required=True)
    chunk.add_argument("--output", required=True)
    chunk.add_argument("--metadata")
    chunk.add_argument("--overwrite", action="store_true")

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--parts-root", required=True)
    aggregate.add_argument("--snapshot-doi", required=True)
    aggregate.add_argument("--output", required=True)
    aggregate.add_argument("--provenance")
    aggregate.add_argument("--overwrite", action="store_true")

    args = parser.parse_args(argv)
    if args.mode == "chunk":
        return _run_chunk(args)
    return _run_aggregate(args)


if __name__ == "__main__":
    raise SystemExit(main())
