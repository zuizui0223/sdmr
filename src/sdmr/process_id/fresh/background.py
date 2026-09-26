"""Model-pool-only target-group accessible area and deterministic background."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from sdmr.data.snapshot import _configure_duckdb_cloud, _sql_literal, gbif_snapshot_s3_uri
from sdmr.process_id.fresh.contract import validate_final_freeze_contract
from sdmr.target_footprint_parallel_cli import _chunk_files, _list_snapshot_shards, _sql_list


PROGRAM = "sdmr-fresh-empirical-background-v1"
SNAPSHOT_DATE = "2026-08-01"
SNAPSHOT_DOI = "10.15468/dl.fs3btq"
SNAPSHOT_REGION = "us-east-1"
YEAR_MIN = 2010
YEAR_MAX = 2025
CELL_DEGREES = 0.05
EXPECTED_TAXA = 50
EXPECTED_SELECTED_SHA256 = "930821c74cc76820907f7c942b98189ddc4f28aca1597198db431ef6eebb40c2"
EXPECTED_MODEL_POOL_SHA256 = "57aed9612e1a5dc69f6d8c6789ef2c55ed6963698f15172e02d8ff3dc89c9137"
PRIMARY_M_KM = 300
SENSITIVITY_M_KM = (150, 500)
M_KM = (150, 300, 500)
BACKGROUND_POINTS = 5000
BACKGROUND_SEED = "sdmr-fresh-background-v1|2026-09-26"
EXPECTED_CHUNKS = 32
EARTH_RADIUS_KM = 6371.0088


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_selected(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if _sha256(source) != EXPECTED_SELECTED_SHA256:
        raise ValueError("frozen selected-taxa fingerprint changed")
    df = pd.read_csv(source)
    if len(df) != EXPECTED_TAXA or df["scientific_name"].astype(str).nunique() != EXPECTED_TAXA:
        raise ValueError("fresh background requires exactly 50 unique frozen taxa")
    return df.sort_values("selection_rank").reset_index(drop=True)


def validate_background_contract(
    *,
    final_contract_path: str | Path,
    source_contract_path: str | Path,
    occurrence_receipt_path: str | Path,
    selected_taxa_path: str | Path,
) -> tuple[dict, dict, dict, pd.DataFrame]:
    final = json.loads(Path(final_contract_path).read_text(encoding="utf-8"))
    validate_final_freeze_contract(final)
    source = json.loads(Path(source_contract_path).read_text(encoding="utf-8"))
    receipt = json.loads(Path(occurrence_receipt_path).read_text(encoding="utf-8"))
    selected = _load_selected(selected_taxa_path)

    if final.get("fresh_outcomes_opened") is not False:
        raise ValueError("fresh outcomes opened before background construction")
    evidence = final.get("final_freeze_evidence", {})
    if evidence.get("environmental_features_opened") is not False:
        raise ValueError("environmental features opened before background construction")
    if evidence.get("answer_check_features_opened") is not False:
        raise ValueError("answer-check features opened before background construction")

    if receipt.get("program") != "sdmr-fresh-empirical-occurrence-split-v1-artifact-receipt":
        raise ValueError("wrong occurrence-split artifact receipt")
    if receipt.get("all_source_gates_passed") is not True:
        raise ValueError("occurrence source gate did not pass")
    if receipt.get("answer_check_coordinates_persisted_for_M") is not False:
        raise ValueError("answer-check coordinates crossed into M boundary")
    if receipt.get("environmental_values_read") is not False:
        raise ValueError("environmental values already read before M construction")
    expected_model = str(receipt.get("files", {}).get("model_pool_occurrences.csv", ""))
    if expected_model != "sha256:" + EXPECTED_MODEL_POOL_SHA256:
        raise ValueError("model-pool occurrence artifact fingerprint changed")

    accessible = source.get("accessible_area", {})
    if accessible.get("primary_rule") != "target_group_cells_within_300km_of_any_model_pool_occurrence":
        raise ValueError("primary M rule changed")
    if accessible.get("focal_coordinates_allowed") != "model_pool_only":
        raise ValueError("M must remain model-pool-only")
    if accessible.get("answer_check_coordinates_for_M_allowed") is not False:
        raise ValueError("answer-check coordinates became available to M")
    if accessible.get("target_group") != "Tracheophyta excluding frozen 50 taxa":
        raise ValueError("target-group taxonomic scope changed")
    if int(accessible.get("background_points_per_taxon", -1)) != BACKGROUND_POINTS:
        raise ValueError("background denominator changed")
    if int(accessible.get("primary_M_km", -1)) != PRIMARY_M_KM:
        raise ValueError("primary M distance changed")
    if tuple(int(x) for x in accessible.get("sensitivity_M_km", ())) != SENSITIVITY_M_KM:
        raise ValueError("sensitivity M distances changed")
    if accessible.get("background_seed") != BACKGROUND_SEED:
        raise ValueError("background seed changed")
    return final, source, receipt, selected


def _target_where_sql(excluded_names: Iterable[str]) -> str:
    names = sorted({str(x).strip() for x in excluded_names if str(x).strip()})
    if len(names) != EXPECTED_TAXA:
        raise ValueError("target footprint must exclude the exact 50 frozen taxa")
    excluded_sql = ",".join(_sql_literal(x) for x in names)
    return " AND ".join(
        [
            "phylum = 'Tracheophyta'",
            "species IS NOT NULL",
            "trim(species) <> ''",
            f"species NOT IN ({excluded_sql})",
            f"year BETWEEN {YEAR_MIN} AND {YEAR_MAX}",
            "(occurrencestatus IS NULL OR upper(occurrencestatus) = 'PRESENT')",
            "(basisofrecord IS NULL OR upper(basisofrecord) <> 'FOSSIL_SPECIMEN')",
            "(coordinateuncertaintyinmeters IS NULL OR coordinateuncertaintyinmeters <= 10000)",
            "gbifid IS NOT NULL",
            "decimallatitude IS NOT NULL",
            "decimallongitude IS NOT NULL",
            "decimallatitude BETWEEN -90 AND 90",
            "decimallongitude BETWEEN -180 AND 180",
            "NOT (decimallatitude = 0 AND decimallongitude = 0)",
        ]
    )


def run_chunk(
    *,
    final_contract_path: str | Path,
    source_contract_path: str | Path,
    occurrence_receipt_path: str | Path,
    selected_taxa_path: str | Path,
    chunk_index: int,
    chunk_count: int,
    output_dir: str | Path,
) -> dict:
    _, _, _, selected = validate_background_contract(
        final_contract_path=final_contract_path,
        source_contract_path=source_contract_path,
        occurrence_receipt_path=occurrence_receipt_path,
        selected_taxa_path=selected_taxa_path,
    )
    if int(chunk_count) != EXPECTED_CHUNKS:
        raise ValueError(f"chunk_count must remain {EXPECTED_CHUNKS}")
    if not 0 <= int(chunk_index) < int(chunk_count):
        raise ValueError("invalid chunk index")

    import duckdb

    con = duckdb.connect()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    partial = output_dir / f"partial_{int(chunk_index):02d}.parquet"
    metadata_path = output_dir / f"metadata_{int(chunk_index):02d}.json"
    try:
        _configure_duckdb_cloud(con, cloud_provider="aws", region=SNAPSHOT_REGION)
        files = _list_snapshot_shards(con, SNAPSHOT_DATE, SNAPSHOT_REGION)
        shard_files = _chunk_files(files, int(chunk_index), int(chunk_count))
        if not shard_files:
            raise RuntimeError(f"empty target-footprint shard chunk {chunk_index}")
        source = f"read_parquet({_sql_list(shard_files)}, union_by_name=true)"
        where = _target_where_sql(selected["scientific_name"].astype(str))
        query = f"""
        WITH filtered AS (
          SELECT
            CAST(gbifid AS VARCHAR) AS gbifid,
            decimallongitude AS longitude,
            decimallatitude AS latitude,
            CAST(FLOOR((decimallongitude + 180.0) / {CELL_DEGREES}) AS BIGINT) AS gx,
            CAST(FLOOR((decimallatitude + 90.0) / {CELL_DEGREES}) AS BIGINT) AS gy
          FROM {source}
          WHERE {where}
        )
        SELECT
          gx,
          gy,
          ARG_MIN(gbifid, gbifid) AS gbifid,
          ARG_MIN(longitude, gbifid) AS longitude,
          ARG_MIN(latitude, gbifid) AS latitude
        FROM filtered
        GROUP BY gx, gy
        ORDER BY gx, gy
        """
        con.execute(
            f"COPY ({query}) TO {_sql_literal(str(partial.resolve()))} "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        partial_rows = int(
            con.execute(
                f"SELECT COUNT(*) FROM read_parquet({_sql_literal(str(partial.resolve()))})"
            ).fetchone()[0]
        )
    finally:
        con.close()

    catalog_sha = hashlib.sha256(("\n".join(files) + "\n").encode("utf-8")).hexdigest()
    chunk_catalog_sha = hashlib.sha256(
        ("\n".join(shard_files) + "\n").encode("utf-8")
    ).hexdigest()
    metadata = {
        "program": PROGRAM,
        "snapshot_date": SNAPSHOT_DATE,
        "snapshot_doi": SNAPSHOT_DOI,
        "region": SNAPSHOT_REGION,
        "chunk_index": int(chunk_index),
        "chunk_count": int(chunk_count),
        "snapshot_shard_count": len(files),
        "snapshot_shard_catalog_sha256": catalog_sha,
        "chunk_shard_count": len(shard_files),
        "chunk_shard_catalog_sha256": chunk_catalog_sha,
        "first_shard": shard_files[0],
        "last_shard": shard_files[-1],
        "selected_taxa_sha256": _sha256(selected_taxa_path),
        "final_contract_sha256": _sha256(final_contract_path),
        "source_contract_sha256": _sha256(source_contract_path),
        "occurrence_receipt_sha256": _sha256(occurrence_receipt_path),
        "partial_rows": partial_rows,
        "partial_sha256": _sha256(partial),
        "target_group": "Tracheophyta_nonfocal",
        "year_min": YEAR_MIN,
        "year_max": YEAR_MAX,
        "grid_degrees": CELL_DEGREES,
        "environmental_values_read": False,
        "answer_check_coordinates_read": False,
        "answer_check_features_read": False,
        "model_fitting_performed": False,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metadata


def _combine_target_footprint(partial_paths: list[Path], output_path: Path) -> int:
    import duckdb

    con = duckdb.connect()
    try:
        source = f"read_parquet({_sql_list([str(p.resolve()) for p in partial_paths])}, union_by_name=true)"
        query = f"""
        SELECT
          gx,
          gy,
          ARG_MIN(gbifid, gbifid) AS gbifid,
          ARG_MIN(longitude, gbifid) AS longitude,
          ARG_MIN(latitude, gbifid) AS latitude
        FROM {source}
        GROUP BY gx, gy
        ORDER BY gx, gy
        """
        con.execute(
            f"COPY ({query}) TO {_sql_literal(str(output_path.resolve()))} "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        return int(
            con.execute(
                f"SELECT COUNT(*) FROM read_parquet({_sql_literal(str(output_path.resolve()))})"
            ).fetchone()[0]
        )
    finally:
        con.close()


def _lonlat_to_xyz(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    lon_r = np.radians(np.asarray(lon, dtype=float))
    lat_r = np.radians(np.asarray(lat, dtype=float))
    cos_lat = np.cos(lat_r)
    return np.column_stack(
        [cos_lat * np.cos(lon_r), cos_lat * np.sin(lon_r), np.sin(lat_r)]
    )


def _chord_for_km(km: float) -> float:
    angle = float(km) / EARTH_RADIUS_KM
    return 2.0 * math.sin(angle / 2.0)


def _background_hash(taxon: str, gbifid: str) -> str:
    payload = f"{BACKGROUND_SEED}\n{taxon}\n{gbifid}\n".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_backgrounds(
    *,
    target_footprint: pd.DataFrame,
    model_pool: pd.DataFrame,
    taxa: Iterable[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    from scipy.spatial import cKDTree

    required_target = {"gx", "gy", "gbifid", "longitude", "latitude"}
    missing_target = sorted(required_target - set(target_footprint.columns))
    if missing_target:
        raise ValueError(f"target footprint missing columns: {missing_target}")
    required_model = {"scientific_name", "occurrence_id", "longitude", "latitude"}
    missing_model = sorted(required_model - set(model_pool.columns))
    if missing_model:
        raise ValueError(f"model-pool occurrence file missing columns: {missing_model}")

    target = target_footprint.copy().reset_index(drop=True)
    target["gbifid"] = target["gbifid"].astype(str)
    if target[["gx", "gy"]].duplicated().any():
        raise ValueError("target footprint must contain one row per 0.05-degree cell")
    target_xyz = _lonlat_to_xyz(
        pd.to_numeric(target["longitude"], errors="raise").to_numpy(float),
        pd.to_numeric(target["latitude"], errors="raise").to_numpy(float),
    )
    threshold = {km: _chord_for_km(km) for km in M_KM}
    max_chord = threshold[max(M_KM)]

    background_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, object]] = []
    for taxon in taxa:
        focal = model_pool.loc[
            model_pool["scientific_name"].astype(str).eq(str(taxon))
        ].copy()
        if focal.empty:
            raise RuntimeError(f"model-pool coordinates unavailable for frozen taxon: {taxon}")
        focal_xyz = _lonlat_to_xyz(
            pd.to_numeric(focal["longitude"], errors="raise").to_numpy(float),
            pd.to_numeric(focal["latitude"], errors="raise").to_numpy(float),
        )
        tree = cKDTree(focal_xyz)
        nearest_chord, _ = tree.query(
            target_xyz,
            k=1,
            distance_upper_bound=max_chord,
            workers=-1,
        )
        finite = np.isfinite(nearest_chord)

        hashes_cache: dict[str, str] = {}
        for km in M_KM:
            mask = finite & (nearest_chord <= threshold[km] + 1e-15)
            candidate = target.loc[mask].copy()
            candidate_count = int(len(candidate))
            if candidate_count == 0:
                raise RuntimeError(f"no target-group M cells for {taxon} at {km} km")
            candidate["selection_hash"] = [
                hashes_cache.setdefault(gid, _background_hash(str(taxon), gid))
                for gid in candidate["gbifid"].astype(str)
            ]
            candidate = candidate.sort_values(
                ["selection_hash", "gbifid", "gx", "gy"],
                kind="mergesort",
            ).reset_index(drop=True)
            selected = candidate.head(BACKGROUND_POINTS).copy()
            selected.insert(0, "background_rank", range(1, len(selected) + 1))
            selected.insert(0, "m_km", int(km))
            selected.insert(0, "scientific_name", str(taxon))
            background_frames.append(
                selected[
                    [
                        "scientific_name",
                        "m_km",
                        "background_rank",
                        "gbifid",
                        "longitude",
                        "latitude",
                        "gx",
                        "gy",
                        "selection_hash",
                    ]
                ]
            )
            summary_rows.append(
                {
                    "scientific_name": str(taxon),
                    "m_km": int(km),
                    "model_pool_occurrences": int(len(focal)),
                    "candidate_target_cells": candidate_count,
                    "background_points": int(len(selected)),
                    "used_all_available": bool(candidate_count < BACKGROUND_POINTS),
                }
            )

    backgrounds = pd.concat(background_frames, ignore_index=True)
    summary = pd.DataFrame(summary_rows)
    if len(summary) != EXPECTED_TAXA * len(M_KM):
        raise AssertionError("background M summary denominator changed")
    return backgrounds, summary


def run_aggregate(
    *,
    final_contract_path: str | Path,
    source_contract_path: str | Path,
    occurrence_receipt_path: str | Path,
    selected_taxa_path: str | Path,
    model_pool_path: str | Path,
    parts_root: str | Path,
    output_dir: str | Path,
) -> dict:
    _, _, receipt, selected = validate_background_contract(
        final_contract_path=final_contract_path,
        source_contract_path=source_contract_path,
        occurrence_receipt_path=occurrence_receipt_path,
        selected_taxa_path=selected_taxa_path,
    )
    if _sha256(model_pool_path) != EXPECTED_MODEL_POOL_SHA256:
        raise RuntimeError("model-pool occurrence artifact SHA does not match frozen receipt")

    root = Path(parts_root)
    metadata_paths = sorted(root.rglob("metadata_*.json"))
    partial_paths = sorted(root.rglob("partial_*.parquet"))
    if len(metadata_paths) != EXPECTED_CHUNKS or len(partial_paths) != EXPECTED_CHUNKS:
        raise RuntimeError(
            f"expected {EXPECTED_CHUNKS} target chunks; "
            f"metadata={len(metadata_paths)} partials={len(partial_paths)}"
        )
    metadata = [json.loads(path.read_text(encoding="utf-8")) for path in metadata_paths]
    by_index = {int(row["chunk_index"]): row for row in metadata}
    partial_by_index = {
        int(path.stem.rsplit("_", 1)[1]): path for path in partial_paths
    }
    if set(by_index) != set(range(EXPECTED_CHUNKS)):
        raise RuntimeError("target-footprint chunk index set is incomplete")
    if set(partial_by_index) != set(range(EXPECTED_CHUNKS)):
        raise RuntimeError("target-footprint partial index set is incomplete")
    invariant_keys = (
        "program",
        "snapshot_date",
        "snapshot_doi",
        "region",
        "chunk_count",
        "snapshot_shard_count",
        "snapshot_shard_catalog_sha256",
        "selected_taxa_sha256",
        "final_contract_sha256",
        "source_contract_sha256",
        "occurrence_receipt_sha256",
        "target_group",
        "year_min",
        "year_max",
        "grid_degrees",
    )
    for key in invariant_keys:
        if len({str(row[key]) for row in metadata}) != 1:
            raise RuntimeError(f"target-footprint chunk invariant differs for {key}")
    if sum(int(row["chunk_shard_count"]) for row in metadata) != int(
        metadata[0]["snapshot_shard_count"]
    ):
        raise RuntimeError("target-footprint chunks do not cover the complete snapshot catalog")
    for idx in range(EXPECTED_CHUNKS):
        if _sha256(partial_by_index[idx]) != str(by_index[idx]["partial_sha256"]):
            raise RuntimeError(f"target-footprint partial SHA mismatch for chunk {idx}")
    for key in (
        "environmental_values_read",
        "answer_check_coordinates_read",
        "answer_check_features_read",
        "model_fitting_performed",
    ):
        if any(row.get(key) is not False for row in metadata):
            raise RuntimeError(f"target-footprint information barrier crossed: {key}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    footprint_path = output_dir / "target_footprint.parquet"
    footprint_rows = _combine_target_footprint(
        [partial_by_index[i] for i in range(EXPECTED_CHUNKS)],
        footprint_path,
    )
    target = pd.read_parquet(footprint_path)
    model_pool = pd.read_csv(model_pool_path)
    backgrounds, m_summary = build_backgrounds(
        target_footprint=target,
        model_pool=model_pool,
        taxa=selected["scientific_name"].astype(str).tolist(),
    )
    background_path = output_dir / "background_points.csv"
    summary_path = output_dir / "accessible_area_summary.csv"
    backgrounds.to_csv(background_path, index=False)
    m_summary.to_csv(summary_path, index=False)

    primary = m_summary.loc[m_summary["m_km"].eq(PRIMARY_M_KM)]
    result = {
        "program": PROGRAM,
        "status": "model_pool_only_accessible_area_and_background_passed",
        "taxon_count": EXPECTED_TAXA,
        "target_footprint_rows": int(footprint_rows),
        "target_footprint_sha256": _sha256(footprint_path),
        "background_points_sha256": _sha256(background_path),
        "accessible_area_summary_sha256": _sha256(summary_path),
        "primary_m_km": PRIMARY_M_KM,
        "sensitivity_m_km": list(SENSITIVITY_M_KM),
        "primary_background_rows": int(
            backgrounds["m_km"].eq(PRIMARY_M_KM).sum()
        ),
        "minimum_primary_candidate_cells": int(primary["candidate_target_cells"].min()),
        "minimum_primary_background_points": int(primary["background_points"].min()),
        "taxa_using_all_available_primary_cells": int(primary["used_all_available"].sum()),
        "occurrence_split_artifact_id": int(receipt["artifact_id"]),
        "model_pool_occurrences_sha256": EXPECTED_MODEL_POOL_SHA256,
        "answer_check_coordinates_read": False,
        "answer_check_features_read": False,
        "environmental_values_read": False,
        "model_fitting_performed": False,
        "next_gate": "extract_frozen_environmental_features_for_model_pool_and_background_only",
    }
    (output_dir / "background_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    chunk = sub.add_parser("chunk")
    aggregate = sub.add_parser("aggregate")
    for cmd in (chunk, aggregate):
        cmd.add_argument("--final-contract", required=True)
        cmd.add_argument("--source-contract", required=True)
        cmd.add_argument("--occurrence-receipt", required=True)
        cmd.add_argument("--selected-taxa", required=True)
    chunk.add_argument("--chunk-index", type=int, required=True)
    chunk.add_argument("--chunk-count", type=int, default=EXPECTED_CHUNKS)
    chunk.add_argument("--output-dir", required=True)
    aggregate.add_argument("--model-pool", required=True)
    aggregate.add_argument("--parts-root", required=True)
    aggregate.add_argument("--output-dir", required=True)
    return p


def main() -> None:
    args = _parser().parse_args()
    if args.command == "chunk":
        result = run_chunk(
            final_contract_path=args.final_contract,
            source_contract_path=args.source_contract,
            occurrence_receipt_path=args.occurrence_receipt,
            selected_taxa_path=args.selected_taxa,
            chunk_index=args.chunk_index,
            chunk_count=args.chunk_count,
            output_dir=args.output_dir,
        )
    else:
        result = run_aggregate(
            final_contract_path=args.final_contract,
            source_contract_path=args.source_contract,
            occurrence_receipt_path=args.occurrence_receipt,
            selected_taxa_path=args.selected_taxa,
            model_pool_path=args.model_pool,
            parts_root=args.parts_root,
            output_dir=args.output_dir,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
