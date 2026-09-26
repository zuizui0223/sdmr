"""Pre-feature occurrence materialization and coordinate-only outer sealing."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from sdmr.data.snapshot import _configure_duckdb_cloud, _sql_literal, gbif_snapshot_s3_uri
from sdmr.process_id.fresh.contract import validate_final_freeze_contract
from sdmr.sealed_occurrence_contract import freeze_occurrence_answer_check_split
from sdmr.target_footprint_parallel_cli import _chunk_files, _list_snapshot_shards, _sql_list


PROGRAM = "sdmr-fresh-empirical-occurrence-split-v1"
SNAPSHOT_DATE = "2026-08-01"
SNAPSHOT_DOI = "10.15468/dl.fs3btq"
SNAPSHOT_REGION = "us-east-1"
YEAR_MIN = 2010
YEAR_MAX = 2025
CELL_DEGREES = 0.05
EXPECTED_TAXA = 50
EXPECTED_SELECTED_SHA256 = "930821c74cc76820907f7c942b98189ddc4f28aca1597198db431ef6eebb40c2"
MIN_RAW_OCCURRENCES = 80
MIN_THINNED_CELLS = 50
OUTER_N_BLOCKS = 8
ANSWER_CHECK_FRACTION = 0.20
OUTER_SEED = 42
EXPECTED_CHUNKS = 32


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_selected(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if _sha256(source) != EXPECTED_SELECTED_SHA256:
        raise ValueError("frozen 50-taxon manifest fingerprint changed")
    df = pd.read_csv(source)
    required = {
        "selection_rank",
        "scientific_name",
        "family",
        "genus",
        "n_occurrences",
        "n_unique_1_degree_cells",
        "selection_hash",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"selected-taxa manifest missing columns: {missing}")
    if len(df) != EXPECTED_TAXA or df["scientific_name"].astype(str).nunique() != EXPECTED_TAXA:
        raise ValueError("selected-taxa manifest must contain exactly 50 unique taxa")
    ranks = sorted(pd.to_numeric(df["selection_rank"], errors="raise").astype(int).tolist())
    if ranks != list(range(1, EXPECTED_TAXA + 1)):
        raise ValueError("selected-taxa ranks must be exactly 1..50")
    return df.sort_values("selection_rank").reset_index(drop=True)


def validate_pre_feature_contract(
    *,
    final_contract_path: str | Path,
    source_contract_path: str | Path,
    selected_taxa_path: str | Path,
) -> tuple[dict, dict, pd.DataFrame]:
    final = json.loads(Path(final_contract_path).read_text(encoding="utf-8"))
    validate_final_freeze_contract(final)
    source = json.loads(Path(source_contract_path).read_text(encoding="utf-8"))
    selected = _load_selected(selected_taxa_path)

    if final.get("fresh_outcomes_opened") is not False:
        raise ValueError("fresh outcomes opened before occurrence sealing")
    evidence = final.get("final_freeze_evidence", {})
    if evidence.get("environmental_features_opened") is not False:
        raise ValueError("environmental features opened before occurrence sealing")
    if evidence.get("answer_check_features_opened") is not False:
        raise ValueError("answer-check features opened before occurrence sealing")

    occurrence = source.get("occurrence_source", {})
    if occurrence.get("snapshot_date") != SNAPSHOT_DATE or occurrence.get("snapshot_doi") != SNAPSHOT_DOI:
        raise ValueError("GBIF source identity changed")
    if list(occurrence.get("temporal_window", [])) != [YEAR_MIN, YEAR_MAX]:
        raise ValueError("occurrence temporal window changed")
    thinning = occurrence.get("thinning", {})
    if thinning.get("rule") != "one_record_per_species_per_0.05_degree_cell":
        raise ValueError("focal thinning rule changed")
    if thinning.get("tie_breaker") != "minimum_gbifid":
        raise ValueError("focal thinning tie-breaker changed")
    if int(thinning.get("minimum_raw_occurrences", -1)) != MIN_RAW_OCCURRENCES:
        raise ValueError("minimum raw-occurrence gate changed")
    if int(thinning.get("minimum_thinned_cells", -1)) != MIN_THINNED_CELLS:
        raise ValueError("minimum thinned-cell gate changed")
    if "no_replacement" not in str(thinning.get("failure_rule", "")):
        raise ValueError("source failure rule must forbid replacement")

    outer = source.get("outer_split", {})
    expected_outer = {
        "unit": "within_taxon",
        "occurrence_id": "species_pipe_gbifid",
        "n_blocks": OUTER_N_BLOCKS,
        "answer_check_fraction": ANSWER_CHECK_FRACTION,
        "random_state": OUTER_SEED,
        "algorithm": "freeze_occurrence_answer_check_split",
    }
    for key, expected in expected_outer.items():
        if outer.get(key) != expected:
            raise ValueError(f"outer split rule changed for {key}")
    if outer.get("answer_check_environmental_features_opened") is not False:
        raise ValueError("answer-check environmental features opened before sealing")

    accessible = source.get("accessible_area", {})
    if accessible.get("focal_coordinates_allowed") != "model_pool_only":
        raise ValueError("M construction may only use model-pool focal coordinates")
    if accessible.get("answer_check_coordinates_for_M_allowed") is not False:
        raise ValueError("answer-check coordinates became available to M construction")
    return final, source, selected


def _species_sql(names: Iterable[str]) -> str:
    return ",".join(_sql_literal(x) for x in sorted({str(v).strip() for v in names}))


def _where_sql(names: Iterable[str]) -> str:
    return " AND ".join(
        [
            f"species IN ({_species_sql(names)})",
            "upper(taxonrank) = 'SPECIES'",
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
    selected_taxa_path: str | Path,
    chunk_index: int,
    chunk_count: int,
    output_dir: str | Path,
) -> dict:
    _, _, selected = validate_pre_feature_contract(
        final_contract_path=final_contract_path,
        source_contract_path=source_contract_path,
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
            raise RuntimeError(f"empty GBIF shard chunk {chunk_index}")
        source = f"read_parquet({_sql_list(shard_files)}, union_by_name=true)"
        where = _where_sql(selected["scientific_name"].astype(str))
        query = f"""
        WITH filtered AS (
          SELECT
            species,
            gbifid,
            decimallongitude,
            decimallatitude,
            CAST(FLOOR((decimallongitude + 180.0) / {CELL_DEGREES}) AS BIGINT) AS cell_x,
            CAST(FLOOR((decimallatitude + 90.0) / {CELL_DEGREES}) AS BIGINT) AS cell_y
          FROM {source}
          WHERE {where}
        )
        SELECT
          species,
          cell_x,
          cell_y,
          COUNT(*)::BIGINT AS n_occurrences_in_cell,
          CAST(ARG_MIN(gbifid, gbifid) AS VARCHAR) AS gbifid,
          ARG_MIN(decimallongitude, gbifid) AS longitude,
          ARG_MIN(decimallatitude, gbifid) AS latitude
        FROM filtered
        GROUP BY species, cell_x, cell_y
        ORDER BY species, cell_x, cell_y
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

    metadata = {
        "program": PROGRAM,
        "snapshot_date": SNAPSHOT_DATE,
        "snapshot_doi": SNAPSHOT_DOI,
        "chunk_index": int(chunk_index),
        "chunk_count": int(chunk_count),
        "snapshot_shard_count": len(files),
        "chunk_shard_count": len(shard_files),
        "first_shard": shard_files[0],
        "last_shard": shard_files[-1],
        "final_contract_sha256": _sha256(final_contract_path),
        "source_contract_sha256": _sha256(source_contract_path),
        "selected_taxa_sha256": _sha256(selected_taxa_path),
        "partial_rows": partial_rows,
        "partial_sha256": _sha256(partial),
        "environmental_values_read": False,
        "answer_check_features_read": False,
        "model_fitting_performed": False,
        "accessible_area_built": False,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def _combine_cells(partial_paths: Iterable[Path]) -> pd.DataFrame:
    frames = [pd.read_parquet(path) for path in partial_paths]
    if not frames:
        raise ValueError("no occurrence partials supplied")
    raw = pd.concat(frames, ignore_index=True)
    if raw.empty:
        raise ValueError("occurrence partials are empty")
    raw["gbifid_num"] = pd.to_numeric(raw["gbifid"], errors="raise").astype("uint64")
    group_cols = ["species", "cell_x", "cell_y"]
    counts = (
        raw.groupby(group_cols, as_index=False)["n_occurrences_in_cell"]
        .sum()
    )
    rep_index = raw.groupby(group_cols)["gbifid_num"].idxmin()
    reps = raw.loc[
        rep_index,
        ["species", "cell_x", "cell_y", "gbifid", "gbifid_num", "longitude", "latitude"],
    ].copy()
    cells = counts.merge(reps, on=group_cols, how="left", validate="one_to_one")
    return cells.sort_values(["species", "cell_x", "cell_y"]).reset_index(drop=True)


def _freeze_taxon_split(cells: pd.DataFrame, taxon: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    subset = cells.loc[cells["species"].astype(str).eq(str(taxon))].copy()
    raw_count = int(subset["n_occurrences_in_cell"].sum())
    thinned_count = int(len(subset))
    if raw_count < MIN_RAW_OCCURRENCES or thinned_count < MIN_THINNED_CELLS:
        raise RuntimeError(
            f"frozen taxon failed source gate without replacement: {taxon}: "
            f"raw={raw_count}, thinned_cells={thinned_count}"
        )
    subset["occurrence_id"] = (
        subset["species"].astype(str) + "|" + subset["gbifid"].astype(str)
    )
    index = subset.rename(columns={"longitude": "longitude", "latitude": "latitude"})[
        ["occurrence_id", "longitude", "latitude"]
    ]
    split = freeze_occurrence_answer_check_split(
        index,
        id_col="occurrence_id",
        lon_col="longitude",
        lat_col="latitude",
        n_blocks=OUTER_N_BLOCKS,
        holdout_fraction=ANSWER_CHECK_FRACTION,
        random_state=OUTER_SEED,
    )
    assignment = split.assignment.copy()
    assignment.insert(0, "scientific_name", str(taxon))
    joined = subset.merge(
        assignment[["occurrence_id", "outer_role", "spatial_block"]],
        on="occurrence_id",
        how="left",
        validate="one_to_one",
    )
    model_pool = joined.loc[joined["outer_role"].eq("model_pool")].copy()
    answer_n = int(joined["outer_role"].eq("answer_check").sum())
    model_n = int(len(model_pool))
    if answer_n < 1 or model_n < 1:
        raise RuntimeError(f"outer split lost a role for {taxon}")
    model_pool = model_pool[
        [
            "species",
            "occurrence_id",
            "gbifid",
            "longitude",
            "latitude",
            "cell_x",
            "cell_y",
            "spatial_block",
        ]
    ].rename(columns={"species": "scientific_name"})
    ledger = assignment[
        ["scientific_name", "occurrence_id", "spatial_block", "outer_role"]
    ].copy()
    summary = {
        "scientific_name": str(taxon),
        "raw_occurrences": raw_count,
        "thinned_occurrences": thinned_count,
        "model_pool_occurrences": model_n,
        "answer_check_occurrences": answer_n,
        "split_digest": split.split_digest,
        "source_gate_passed": True,
    }
    return model_pool, ledger, summary


def run_aggregate(
    *,
    final_contract_path: str | Path,
    source_contract_path: str | Path,
    selected_taxa_path: str | Path,
    parts_root: str | Path,
    output_dir: str | Path,
) -> dict:
    _, _, selected = validate_pre_feature_contract(
        final_contract_path=final_contract_path,
        source_contract_path=source_contract_path,
        selected_taxa_path=selected_taxa_path,
    )
    root = Path(parts_root)
    metadata_paths = sorted(root.rglob("metadata_*.json"))
    partial_paths = sorted(root.rglob("partial_*.parquet"))
    if len(metadata_paths) != EXPECTED_CHUNKS or len(partial_paths) != EXPECTED_CHUNKS:
        raise RuntimeError(
            f"expected {EXPECTED_CHUNKS} occurrence chunks; "
            f"metadata={len(metadata_paths)} partials={len(partial_paths)}"
        )
    metadata = [json.loads(path.read_text(encoding="utf-8")) for path in metadata_paths]
    if {int(row["chunk_index"]) for row in metadata} != set(range(EXPECTED_CHUNKS)):
        raise RuntimeError("occurrence chunk index set is incomplete")
    invariant_keys = (
        "program",
        "snapshot_date",
        "snapshot_doi",
        "chunk_count",
        "snapshot_shard_count",
        "final_contract_sha256",
        "source_contract_sha256",
        "selected_taxa_sha256",
    )
    for key in invariant_keys:
        if len({str(row[key]) for row in metadata}) != 1:
            raise RuntimeError(f"occurrence chunk invariant differs for {key}")
    for key in (
        "environmental_values_read",
        "answer_check_features_read",
        "model_fitting_performed",
        "accessible_area_built",
    ):
        if any(row.get(key) is not False for row in metadata):
            raise RuntimeError(f"pre-feature information barrier crossed: {key}")

    cells = _combine_cells(partial_paths)
    expected_names = selected["scientific_name"].astype(str).tolist()
    observed_names = set(cells["species"].astype(str))
    missing = [name for name in expected_names if name not in observed_names]
    if missing:
        raise RuntimeError("frozen taxa absent from occurrence scan: " + ", ".join(missing))

    model_frames = []
    ledger_frames = []
    summaries = []
    for taxon in expected_names:
        model, ledger, summary = _freeze_taxon_split(cells, taxon)
        model_frames.append(model)
        ledger_frames.append(ledger)
        summaries.append(summary)

    model_pool = pd.concat(model_frames, ignore_index=True)
    outer_split = pd.concat(ledger_frames, ignore_index=True)
    taxon_summary = pd.DataFrame(summaries)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model_pool_occurrences.csv"
    split_path = output_dir / "outer_split.csv"
    summary_path = output_dir / "taxon_source_gate.csv"
    model_pool.to_csv(model_path, index=False)
    outer_split.to_csv(split_path, index=False)
    taxon_summary.to_csv(summary_path, index=False)

    if set(model_pool["occurrence_id"].astype(str)) & set(
        outer_split.loc[outer_split["outer_role"].eq("answer_check"), "occurrence_id"].astype(str)
    ):
        raise RuntimeError("answer-check coordinates leaked into model-pool artifact")

    result = {
        "program": PROGRAM,
        "status": "occurrence_source_gate_and_outer_split_passed",
        "taxon_count": int(len(taxon_summary)),
        "all_source_gates_passed": bool(taxon_summary["source_gate_passed"].all()),
        "model_pool_occurrences": int(len(model_pool)),
        "answer_check_occurrences": int(outer_split["outer_role"].eq("answer_check").sum()),
        "model_pool_occurrences_sha256": _sha256(model_path),
        "outer_split_sha256": _sha256(split_path),
        "taxon_source_gate_sha256": _sha256(summary_path),
        "environmental_values_read": False,
        "answer_check_features_read": False,
        "answer_check_coordinates_persisted_for_M": False,
        "model_fitting_performed": False,
        "accessible_area_built": False,
        "next_gate": "build_model_pool_only_target_group_M_and_freeze_background_receipt",
    }
    (output_dir / "occurrence_split_result.json").write_text(
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
        cmd.add_argument("--selected-taxa", required=True)
    chunk.add_argument("--chunk-index", type=int, required=True)
    chunk.add_argument("--chunk-count", type=int, default=EXPECTED_CHUNKS)
    chunk.add_argument("--output-dir", required=True)
    aggregate.add_argument("--parts-root", required=True)
    aggregate.add_argument("--output-dir", required=True)
    return p


def main() -> None:
    args = _parser().parse_args()
    if args.command == "chunk":
        result = run_chunk(
            final_contract_path=args.final_contract,
            source_contract_path=args.source_contract,
            selected_taxa_path=args.selected_taxa,
            chunk_index=args.chunk_index,
            chunk_count=args.chunk_count,
            output_dir=args.output_dir,
        )
    else:
        result = run_aggregate(
            final_contract_path=args.final_contract,
            source_contract_path=args.source_contract,
            selected_taxa_path=args.selected_taxa,
            parts_root=args.parts_root,
            output_dir=args.output_dir,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
