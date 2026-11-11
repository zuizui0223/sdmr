"""Exact shard-parallel class-matched target-group footprints for cross-taxon positive controls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .data.raster import sha256_file
from .data.snapshot import _configure_duckdb_cloud, _sql_literal, gbif_snapshot_s3_uri
from .data.snapshot_citation import validate_snapshot_citation
from .target_footprint_parallel_cli import _chunk_files, _list_snapshot_shards, _quoted_identifier, _settings, _sql_list


def _read_groups(path: str | Path) -> tuple[pd.DataFrame, str]:
    p = Path(path)
    frame = pd.read_csv(p)
    required = {"target_group", "taxon_rank", "taxon_value"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"target-group file missing columns: {sorted(missing)}")
    if len(frame) != 4 or frame["target_group"].duplicated().any():
        raise ValueError("cross-taxon v1 requires four unique target groups")
    if set(frame["taxon_rank"].astype(str)) != {"class"}:
        raise ValueError("cross-taxon v1 target groups must all use GBIF class")
    if any(frame["target_group"].astype(str) != frame["taxon_value"].astype(str)):
        raise ValueError("cross-taxon v1 requires target_group == taxon_value")
    return frame, hashlib.sha256(p.read_bytes()).hexdigest()


def _read_taxa(path: str | Path) -> tuple[list[str], str]:
    p = Path(path)
    frame = pd.read_csv(p)
    if "scientific_name" not in frame:
        raise ValueError("focal panel requires scientific_name")
    names = [str(x).strip() for x in frame["scientific_name"] if str(x).strip()]
    if len(names) != 4 or len(set(names)) != 4:
        raise ValueError("cross-taxon v1 requires four unique focal taxa")
    return names, hashlib.sha256(p.read_bytes()).hexdigest()


def _logical_sha(snapshot_uri: str, group_sha: str, taxa_sha: str, cell: float) -> str:
    payload = (
        "cross_taxon_class_target_argmin_v1\n" + snapshot_uri +
        "\nrank=class\ngroups_sha256=" + group_sha +
        "\nexcluded_taxa_sha256=" + taxa_sha +
        f"\ngrid={cell:.17g}\nvalid_coordinates=true\n" +
        "chunk_local_argmin_then_global_argmin=true\n"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _run_chunk(args) -> int:
    groups, group_sha = _read_groups(args.target_groups)
    focal_names, taxa_sha = _read_taxa(args.exclude_taxa)
    values = groups["taxon_value"].astype(str).tolist()
    if args.grid_cell_degrees <= 0:
        raise ValueError("grid_cell_degrees must be > 0")
    try:
        import duckdb
    except ImportError as exc:
        raise ImportError("cross-taxon target materialization requires duckdb") from exc

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        _configure_duckdb_cloud(con, cloud_provider="aws", region=args.region)
        files = _list_snapshot_shards(con, args.snapshot_date, args.region)
        selected = _chunk_files(files, int(args.chunk_index), int(args.chunk_count))
        if not selected:
            raise ValueError("empty snapshot chunk")
        schema = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet({_sql_literal(selected[0])}, union_by_name=true)"
        ).fetchdf()
        available = {str(x).lower(): str(x) for x in schema["column_name"].tolist()}
        required = {"gbifid", "class", "species", "decimallatitude", "decimallongitude"}
        missing = sorted(required - set(available))
        if missing:
            raise ValueError(f"GBIF snapshot schema missing columns: {missing}")
        gbifid = _quoted_identifier(available["gbifid"])
        klass = _quoted_identifier(available["class"])
        species = _quoted_identifier(available["species"])
        lat = _quoted_identifier(available["decimallatitude"])
        lon = _quoted_identifier(available["decimallongitude"])
        source = f"read_parquet({_sql_list(selected)}, union_by_name=true)"
        value_sql = ",".join(_sql_literal(x) for x in values)
        excluded_sql = ",".join(_sql_literal(x) for x in focal_names)
        cell = float(args.grid_cell_degrees)
        query = f"""
        WITH filtered AS (
          SELECT {klass} AS target_group, {gbifid} AS gbifid,
            {lon} AS decimallongitude, {lat} AS decimallatitude,
            FLOOR(({lon} + 180.0) / {cell})::BIGINT AS gx,
            FLOOR(({lat} + 90.0) / {cell})::BIGINT AS gy
          FROM {source}
          WHERE {klass} IN ({value_sql})
            AND ({species} IS NULL OR {species} NOT IN ({excluded_sql}))
            AND {lat} IS NOT NULL AND {lon} IS NOT NULL
            AND {lat} BETWEEN -90 AND 90 AND {lon} BETWEEN -180 AND 180
        )
        SELECT target_group, gx, gy,
          ARG_MIN(gbifid, gbifid) AS gbifid,
          ARG_MIN(decimallongitude, gbifid) AS decimallongitude,
          ARG_MIN(decimallatitude, gbifid) AS decimallatitude
        FROM filtered GROUP BY target_group, gx, gy
        """.strip()
        out_literal = _sql_literal(str(output.resolve()))
        con.execute(f"COPY ({query}) TO {out_literal} (FORMAT PARQUET, COMPRESSION ZSTD)")
        n_rows = int(con.execute(f"SELECT COUNT(*) FROM read_parquet({out_literal})").fetchone()[0])
        settings = _settings(con)
    finally:
        con.close()

    catalog_sha = hashlib.sha256(("\n".join(files) + "\n").encode()).hexdigest()
    chunk_catalog_sha = hashlib.sha256(("\n".join(selected) + "\n").encode()).hexdigest()
    meta = {
        "purpose": "product_a_cross_taxon_target_footprint_chunk_v1",
        "snapshot_date": args.snapshot_date, "snapshot_doi": args.snapshot_doi,
        "region": args.region, "chunk_index": int(args.chunk_index),
        "chunk_count": int(args.chunk_count), "snapshot_shard_count": len(files),
        "snapshot_shard_catalog_sha256": catalog_sha,
        "chunk_shard_count": len(selected), "chunk_shard_catalog_sha256": chunk_catalog_sha,
        "target_groups_sha256": group_sha, "focal_taxa_sha256": taxa_sha,
        "target_groups": values, "one_per_grid_cell_degrees": cell,
        "logical_query_sha256": _logical_sha(gbif_snapshot_s3_uri(args.snapshot_date, region=args.region), group_sha, taxa_sha, cell),
        "partial_rows": n_rows, "partial_sha256": sha256_file(output),
        "environmental_values_read": False, "candidate_model_fitting_performed": False,
        "external_positive_labels_read": False, "http_settings": settings,
    }
    Path(args.metadata).write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2, sort_keys=True))
    return 0


def _run_aggregate(args) -> int:
    groups, group_sha = _read_groups(args.target_groups)
    _, taxa_sha = _read_taxa(args.exclude_taxa)
    root = Path(args.parts_root)
    metas = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(root.rglob("metadata.json"))]
    partials = sorted(root.rglob("partial.parquet"))
    if not metas:
        raise ValueError("no target chunk metadata found")
    expected = int(metas[0]["chunk_count"])
    by_index = {int(row["chunk_index"]): row for row in metas}
    if set(by_index) != set(range(expected)) or len(partials) != expected:
        raise ValueError("incomplete target-group chunk set")
    for key in ("snapshot_date", "snapshot_doi", "region", "chunk_count", "snapshot_shard_count", "snapshot_shard_catalog_sha256", "target_groups_sha256", "focal_taxa_sha256", "one_per_grid_cell_degrees", "logical_query_sha256"):
        if len({json.dumps(row[key], sort_keys=True) for row in metas}) != 1:
            raise ValueError(f"target chunk invariant differs: {key}")
    if metas[0]["target_groups_sha256"] != group_sha or metas[0]["focal_taxa_sha256"] != taxa_sha:
        raise ValueError("requested cross-taxon registry differs from chunk registry")
    if sum(int(x["chunk_shard_count"]) for x in metas) != int(metas[0]["snapshot_shard_count"]):
        raise ValueError("target chunks do not cover complete snapshot")
    if sorted(sha256_file(p) for p in partials) != sorted(str(x["partial_sha256"]) for x in metas):
        raise ValueError("target partial SHA set mismatch")

    try:
        import duckdb
    except ImportError as exc:
        raise ImportError("cross-taxon target aggregation requires duckdb") from exc
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "target_groups.parquet"
    con = duckdb.connect()
    try:
        source = f"read_parquet({_sql_list([str(p.resolve()) for p in partials])}, union_by_name=true)"
        query = f"""
        SELECT target_group, ARG_MIN(gbifid, gbifid) AS gbifid,
          target_group || '_target_group' AS species,
          ARG_MIN(decimallongitude, gbifid) AS decimallongitude,
          ARG_MIN(decimallatitude, gbifid) AS decimallatitude
        FROM {source} GROUP BY target_group, gx, gy
        """.strip()
        out_literal = _sql_literal(str(output.resolve()))
        con.execute(f"COPY ({query}) TO {out_literal} (FORMAT PARQUET, COMPRESSION ZSTD)")
        counts = con.execute(f"SELECT target_group, COUNT(*) FROM read_parquet({out_literal}) GROUP BY target_group ORDER BY target_group").fetchall()
    finally:
        con.close()

    observed = {str(x[0]) for x in counts}
    expected_groups = set(groups["target_group"].astype(str))
    if observed != expected_groups:
        raise ValueError(f"target groups differ: observed={sorted(observed)} expected={sorted(expected_groups)}")
    citation = validate_snapshot_citation(args.snapshot_date, args.snapshot_doi, region=args.region)
    if args.citation_sha256 and citation.citation_sha256 != str(args.citation_sha256).lower():
        raise ValueError("cross-taxon snapshot citation SHA mismatch")
    output_sha = sha256_file(output)
    rows = []
    for group, n_rows in counts:
        rows.append({
            "source_type": "gbif_monthly_cloud_snapshot_class_matched_target_group_parallel_exact",
            "snapshot_date": args.snapshot_date, "snapshot_doi": args.snapshot_doi,
            "snapshot_citation_sha256": citation.citation_sha256, "region": args.region,
            "target_group": str(group), "taxon_rank": "class", "taxon_value": str(group),
            "sampling_mode": "class_matched_one_per_grid_cell_sampling_footprint",
            "one_per_grid_cell_degrees": float(metas[0]["one_per_grid_cell_degrees"]),
            "focal_taxa_sha256": taxa_sha, "target_groups_sha256": group_sha,
            "query_sha256": metas[0]["logical_query_sha256"], "path": "target_groups.parquet",
            "sha256": output_sha, "n_rows": int(n_rows),
            "snapshot_shard_count": int(metas[0]["snapshot_shard_count"]), "parallel_chunk_count": expected,
        })
    pd.DataFrame(rows).to_csv(out_dir / "target_groups.provenance.csv", index=False)
    (out_dir / "target_groups.parquet.citation.txt").write_text(citation.citation_text, encoding="utf-8")
    manifest = {
        "purpose": "product_a_cross_taxon_target_footprint_manifest_v1",
        "snapshot_date": args.snapshot_date, "snapshot_doi": args.snapshot_doi,
        "citation_sha256": citation.citation_sha256, "target_groups_sha256": group_sha,
        "focal_taxa_sha256": taxa_sha, "target_groups": sorted(observed),
        "target_group_counts": {str(k): int(v) for k, v in counts},
        "target_groups_file_sha256": output_sha,
        "snapshot_shard_count": int(metas[0]["snapshot_shard_count"]),
        "parallel_chunk_count": expected, "environmental_values_read": False,
        "candidate_model_fitting_performed": False, "external_positive_labels_read": False,
    }
    (out_dir / "target_groups_source_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("chunk")
    c.add_argument("--snapshot-date", required=True); c.add_argument("--snapshot-doi", required=True)
    c.add_argument("--region", default="us-east-1"); c.add_argument("--target-groups", required=True)
    c.add_argument("--exclude-taxa", required=True); c.add_argument("--chunk-index", type=int, required=True)
    c.add_argument("--chunk-count", type=int, required=True); c.add_argument("--grid-cell-degrees", type=float, default=0.05)
    c.add_argument("--output", required=True); c.add_argument("--metadata", required=True)
    a = sub.add_parser("aggregate")
    a.add_argument("--parts-root", required=True); a.add_argument("--snapshot-date", required=True)
    a.add_argument("--snapshot-doi", required=True); a.add_argument("--citation-sha256")
    a.add_argument("--region", default="us-east-1"); a.add_argument("--target-groups", required=True)
    a.add_argument("--exclude-taxa", required=True); a.add_argument("--output-dir", required=True)
    args = p.parse_args(argv)
    return _run_chunk(args) if args.mode == "chunk" else _run_aggregate(args)


if __name__ == "__main__":
    raise SystemExit(main())
