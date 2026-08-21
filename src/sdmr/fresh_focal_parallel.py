"""Exact shard-parallel GBIF focal materialization for a frozen taxon panel.

This module changes transport only. Every snapshot shard is assigned to exactly
one chunk, each chunk applies the same taxon/coordinate filter, and aggregation
concatenates the disjoint raw rows without deduplication. The result is therefore
the same logical evidence set as one monolithic snapshot query.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .data.raster import sha256_file
from .data.snapshot import (
    PREFERRED_SNAPSHOT_COLUMNS,
    _configure_duckdb_cloud,
    _query_sha256,
    _quote_identifier,
    _sql_literal,
    build_snapshot_filter_sql,
    gbif_snapshot_s3_uri,
)
from .data.snapshot_citation import validate_snapshot_citation
from .target_footprint_parallel_cli import _chunk_files, _list_snapshot_shards, _sql_list


def _read_panel(path: str | Path) -> tuple[list[str], str]:
    source = Path(path)
    frame = pd.read_csv(source)
    if "scientific_name" not in frame:
        raise ValueError("focal panel requires scientific_name")
    names = [str(x).strip() for x in frame["scientific_name"] if str(x).strip()]
    if not names or len(names) != len(set(names)):
        raise ValueError("focal panel must contain unique non-empty taxa")
    return names, hashlib.sha256(source.read_bytes()).hexdigest()


def _run_chunk(args) -> int:
    names, panel_sha = _read_panel(args.taxa)
    try:
        import duckdb
    except ImportError as exc:
        raise ImportError("Fresh focal materialization requires duckdb; install sdmr[cloud].") from exc

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        raise FileExistsError(output)

    uri = gbif_snapshot_s3_uri(args.snapshot_date, region=args.region)
    where_sql = build_snapshot_filter_sql(species_names=names, require_coordinates=True)
    con = duckdb.connect()
    try:
        _configure_duckdb_cloud(con, cloud_provider="aws", region=args.region)
        files = _list_snapshot_shards(con, args.snapshot_date, args.region)
        selected_files = _chunk_files(files, int(args.chunk_index), int(args.chunk_count))
        if not selected_files:
            raise ValueError(f"chunk {args.chunk_index} contains no snapshot shards")
        schema = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet({_sql_literal(selected_files[0])}, union_by_name=true)"
        ).fetchdf()
        available = {str(x).lower(): str(x) for x in schema["column_name"].tolist()}
        required = {"species", "decimallatitude", "decimallongitude"}
        missing = sorted(required - set(available))
        if missing:
            raise ValueError(f"GBIF snapshot schema missing focal columns: {missing}")
        columns = [available[name] for name in PREFERRED_SNAPSHOT_COLUMNS if name in available]
        select_sql = ",".join(_quote_identifier(name) for name in columns)
        source = f"read_parquet({_sql_list(selected_files)}, union_by_name=true)"
        query = f"SELECT {select_sql} FROM {source} WHERE {where_sql}"
        con.execute(
            f"COPY ({query}) TO {_sql_literal(str(output.resolve()))} (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        n_rows = int(
            con.execute(
                f"SELECT COUNT(*) FROM read_parquet({_sql_literal(str(output.resolve()))})"
            ).fetchone()[0]
        )
    finally:
        con.close()

    catalog_sha = hashlib.sha256(("\n".join(files) + "\n").encode("utf-8")).hexdigest()
    chunk_catalog_sha = hashlib.sha256(("\n".join(selected_files) + "\n").encode("utf-8")).hexdigest()
    metadata = {
        "purpose": "product_a_v2_7_1_fresh_focal_source_shard_chunk",
        "snapshot_date": args.snapshot_date,
        "snapshot_doi": args.snapshot_doi,
        "region": args.region,
        "chunk_index": int(args.chunk_index),
        "chunk_count": int(args.chunk_count),
        "snapshot_shard_count": len(files),
        "snapshot_shard_catalog_sha256": catalog_sha,
        "chunk_shard_count": len(selected_files),
        "chunk_shard_catalog_sha256": chunk_catalog_sha,
        "first_shard": selected_files[0],
        "last_shard": selected_files[-1],
        "taxon_panel_sha256": panel_sha,
        "n_taxa": len(names),
        "selected_columns": columns,
        "logical_query_sha256": _query_sha256(uri, columns, where_sql, ""),
        "partial_rows": n_rows,
        "partial_sha256": sha256_file(output),
        "environmental_values_read": False,
        "candidate_model_fitting_performed": False,
        "sealed_confirmation_outcomes_read": False,
    }
    meta_path = Path(args.metadata) if args.metadata else output.with_suffix(output.suffix + ".metadata.json")
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


def _run_aggregate(args) -> int:
    names, panel_sha = _read_panel(args.taxa)
    root = Path(args.parts_root)
    metadata_paths = sorted(root.rglob("metadata.json"))
    partial_paths = sorted(root.rglob("partial.parquet"))
    if not metadata_paths:
        raise ValueError("no focal chunk metadata found")
    metadata = [json.loads(path.read_text(encoding="utf-8")) for path in metadata_paths]
    expected_chunks = int(metadata[0]["chunk_count"])
    by_index = {int(row["chunk_index"]): row for row in metadata}
    if set(by_index) != set(range(expected_chunks)):
        raise ValueError(f"incomplete focal chunk indices: {sorted(by_index)}")
    if len(partial_paths) != expected_chunks:
        raise ValueError(f"expected {expected_chunks} focal partials, found {len(partial_paths)}")

    invariants = (
        "snapshot_date",
        "snapshot_doi",
        "region",
        "chunk_count",
        "snapshot_shard_count",
        "snapshot_shard_catalog_sha256",
        "taxon_panel_sha256",
        "n_taxa",
        "selected_columns",
        "logical_query_sha256",
    )
    for key in invariants:
        values = {json.dumps(row[key], sort_keys=True) for row in metadata}
        if len(values) != 1:
            raise ValueError(f"focal chunk invariant differs for {key}: {sorted(values)}")
    if metadata[0]["taxon_panel_sha256"] != panel_sha:
        raise ValueError("focal chunk taxon-panel SHA differs from requested panel")
    if sum(int(row["chunk_shard_count"]) for row in metadata) != int(metadata[0]["snapshot_shard_count"]):
        raise ValueError("focal chunks do not cover the full snapshot shard catalog")
    expected_shas = sorted(str(row["partial_sha256"]) for row in metadata)
    if sorted(sha256_file(path) for path in partial_paths) != expected_shas:
        raise ValueError("focal partial SHA set differs from chunk metadata")

    try:
        import duckdb
    except ImportError as exc:
        raise ImportError("Fresh focal aggregation requires duckdb; install sdmr[cloud].") from exc

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "focal.parquet"
    if output.exists() and not args.overwrite:
        raise FileExistsError(output)
    con = duckdb.connect()
    try:
        source = f"read_parquet({_sql_list([str(path.resolve()) for path in partial_paths])}, union_by_name=true)"
        con.execute(
            f"COPY (SELECT * FROM {source}) TO {_sql_literal(str(output.resolve()))} (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        out_literal = _sql_literal(str(output.resolve()))
        n_rows = int(con.execute(f"SELECT COUNT(*) FROM read_parquet({out_literal})").fetchone()[0])
        observed_species = {
            str(row[0]) for row in con.execute(f"SELECT DISTINCT species FROM read_parquet({out_literal})").fetchall()
        }
    finally:
        con.close()
    expected_species = set(names)
    if observed_species != expected_species:
        raise ValueError(
            f"fresh focal source taxa differ: missing={sorted(expected_species-observed_species)}, "
            f"extra={sorted(observed_species-expected_species)}"
        )

    citation = validate_snapshot_citation(args.snapshot_date, args.snapshot_doi, region=args.region)
    if args.citation_sha256 and citation.citation_sha256 != str(args.citation_sha256).lower():
        raise ValueError("fresh focal snapshot citation SHA mismatch")
    (out_dir / "focal.parquet.citation.txt").write_text(citation.citation_text, encoding="utf-8")
    focal_sha = sha256_file(output)
    columns = list(metadata[0]["selected_columns"])
    provenance = pd.DataFrame(
        [{
            "source_type": "gbif_monthly_cloud_snapshot_exact_parallel_fresh_taxon_panel",
            "snapshot_date": args.snapshot_date,
            "snapshot_doi": args.snapshot_doi,
            "snapshot_citation_sha256": citation.citation_sha256,
            "region": args.region,
            "taxon_panel_sha256": panel_sha,
            "n_taxa": len(names),
            "sampling_mode": "all_coordinate_valid_rows_for_frozen_taxon_panel",
            "query_sha256": metadata[0]["logical_query_sha256"],
            "selected_columns": ",".join(columns),
            "snapshot_shard_count": int(metadata[0]["snapshot_shard_count"]),
            "snapshot_shard_catalog_sha256": metadata[0]["snapshot_shard_catalog_sha256"],
            "parallel_chunk_count": expected_chunks,
            "parallel_reduction": "disjoint_shard_union_without_row_deduplication",
            "path": "focal.parquet",
            "sha256": focal_sha,
            "n_rows": n_rows,
        }]
    )
    provenance.to_csv(out_dir / "focal.provenance.csv", index=False)
    manifest = {
        "purpose": "product_a_v2_7_1_fresh_focal_source_manifest",
        "snapshot_date": args.snapshot_date,
        "snapshot_doi": args.snapshot_doi,
        "citation_sha256": citation.citation_sha256,
        "taxon_panel_sha256": panel_sha,
        "focal_sha256": focal_sha,
        "focal_query_sha256": metadata[0]["logical_query_sha256"],
        "focal_rows": n_rows,
        "focal_taxa": len(observed_species),
        "snapshot_shard_count": int(metadata[0]["snapshot_shard_count"]),
        "snapshot_shard_catalog_sha256": metadata[0]["snapshot_shard_catalog_sha256"],
        "parallel_chunk_count": expected_chunks,
        "environmental_values_read": False,
        "candidate_model_fitting_performed": False,
        "sealed_confirmation_outcomes_read": False,
    }
    (out_dir / "focal_source_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)

    chunk = sub.add_parser("chunk")
    chunk.add_argument("--snapshot-date", required=True)
    chunk.add_argument("--snapshot-doi", required=True)
    chunk.add_argument("--region", default="us-east-1")
    chunk.add_argument("--taxa", required=True)
    chunk.add_argument("--chunk-index", type=int, required=True)
    chunk.add_argument("--chunk-count", type=int, required=True)
    chunk.add_argument("--output", required=True)
    chunk.add_argument("--metadata")
    chunk.add_argument("--overwrite", action="store_true")
    chunk.set_defaults(func=_run_chunk)

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--parts-root", required=True)
    aggregate.add_argument("--snapshot-date", required=True)
    aggregate.add_argument("--snapshot-doi", required=True)
    aggregate.add_argument("--citation-sha256", default="")
    aggregate.add_argument("--region", default="us-east-1")
    aggregate.add_argument("--taxa", required=True)
    aggregate.add_argument("--output-dir", required=True)
    aggregate.add_argument("--overwrite", action="store_true")
    aggregate.set_defaults(func=_run_aggregate)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
