"""Deterministic metadata-only selection for the first fresh empirical SDMR cohort."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from sdmr.data.snapshot import _configure_duckdb_cloud, _sql_literal, gbif_snapshot_s3_uri
from sdmr.target_footprint_parallel_cli import _chunk_files, _list_snapshot_shards, _sql_list


PROGRAM = "sdmr-fresh-empirical-cohort-v1"
SNAPSHOT_DATE = "2026-08-01"
SNAPSHOT_DOI = "10.15468/dl.fs3btq"
SNAPSHOT_REGION = "us-east-1"
YEAR_MIN = 2010
YEAR_MAX = 2025
GRID_DEGREES = 1.0
MIN_OCCURRENCES = 500
MIN_UNIQUE_CELLS = 20
EXACT_DENOMINATOR = 50
MAX_PER_GENUS = 1
MAX_PER_FAMILY = 2
HASH_SEED = "sdmr-fresh-empirical-cohort-v1|2026-09-26"
EXPECTED_EXCLUSION_TAXA = 84
EXPECTED_CHUNKS = 32


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def deterministic_rank(scientific_name: str) -> str:
    payload = f"{HASH_SEED}\n{str(scientific_name).strip()}\n".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_exclusion_manifest(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    expected = ["scientific_name", "source_files", "exclusion_reason"]
    if list(df.columns) != expected:
        raise ValueError(f"historical exclusion columns changed: {list(df.columns)}")
    df["scientific_name"] = df["scientific_name"].astype(str).str.strip()
    if len(df) != EXPECTED_EXCLUSION_TAXA:
        raise ValueError(
            f"historical exclusion denominator changed: expected {EXPECTED_EXCLUSION_TAXA}, got {len(df)}"
        )
    if df["scientific_name"].eq("").any() or df["scientific_name"].duplicated().any():
        raise ValueError("historical exclusion names must be non-empty and unique")
    return df.sort_values("scientific_name").reset_index(drop=True)


def validate_contract(path: str | Path) -> dict:
    c = json.loads(Path(path).read_text(encoding="utf-8"))
    if c.get("program") != PROGRAM:
        raise ValueError("wrong fresh cohort program")
    if int(c.get("exact_denominator", -1)) != EXACT_DENOMINATOR:
        raise ValueError("fresh cohort denominator changed")
    hist = c["historical_exclusion"]
    if int(hist.get("expected_taxa", -1)) != EXPECTED_EXCLUSION_TAXA:
        raise ValueError("historical exclusion count changed")
    snap = c["gbif_snapshot"]
    if snap.get("snapshot_date") != SNAPSHOT_DATE or snap.get("snapshot_doi") != SNAPSHOT_DOI:
        raise ValueError("GBIF snapshot identity changed")
    if list(snap.get("temporal_window", [])) != [YEAR_MIN, YEAR_MAX]:
        raise ValueError("temporal window changed")
    elig = c["eligibility"]
    expected_pairs = {
        "phylum": "Tracheophyta",
        "taxon_rank": "SPECIES",
        "minimum_occurrences": MIN_OCCURRENCES,
        "grid_degrees": GRID_DEGREES,
        "minimum_unique_grid_cells": MIN_UNIQUE_CELLS,
        "maximum_coordinate_uncertainty_m": 10000,
    }
    for key, expected in expected_pairs.items():
        if elig.get(key) != expected:
            raise ValueError(f"eligibility rule changed for {key}")
    breadth = c["breadth_constraints"]
    if int(breadth.get("maximum_per_genus", -1)) != MAX_PER_GENUS:
        raise ValueError("genus cap changed")
    if int(breadth.get("maximum_per_family", -1)) != MAX_PER_FAMILY:
        raise ValueError("family cap changed")
    sel = c["deterministic_selection"]
    if sel.get("seed") != HASH_SEED:
        raise ValueError("selection seed changed")
    for key in (
        "post_count_reordering_allowed",
        "threshold_relaxation_allowed",
        "replacement_after_selection_allowed",
    ):
        if sel.get(key) is not False:
            raise ValueError(f"fail-closed cohort rule changed: {key}")
    barrier = c["information_barrier"]
    if barrier.get("fresh_outcomes_opened") is not False:
        raise ValueError("fresh outcomes must remain unopened")
    return c


def _where_sql(excluded: Iterable[str]) -> str:
    names = sorted({str(x).strip() for x in excluded if str(x).strip()})
    excluded_sql = ",".join(_sql_literal(x) for x in names)
    return " AND ".join(
        [
            "phylum = 'Tracheophyta'",
            "upper(taxonrank) = 'SPECIES'",
            "species IS NOT NULL",
            "trim(species) <> ''",
            "family IS NOT NULL",
            "trim(family) <> ''",
            "genus IS NOT NULL",
            "trim(genus) <> ''",
            f"year BETWEEN {YEAR_MIN} AND {YEAR_MAX}",
            "(occurrencestatus IS NULL OR upper(occurrencestatus) = 'PRESENT')",
            "(basisofrecord IS NULL OR upper(basisofrecord) <> 'FOSSIL_SPECIMEN')",
            "(coordinateuncertaintyinmeters IS NULL OR coordinateuncertaintyinmeters <= 10000)",
            "decimallatitude IS NOT NULL",
            "decimallongitude IS NOT NULL",
            "decimallatitude BETWEEN -90 AND 90",
            "decimallongitude BETWEEN -180 AND 180",
            "NOT (decimallatitude = 0 AND decimallongitude = 0)",
            f"species NOT IN ({excluded_sql})",
        ]
    )


def run_chunk(
    *,
    contract_path: str | Path,
    exclusion_path: str | Path,
    chunk_index: int,
    chunk_count: int,
    output_dir: str | Path,
) -> dict:
    validate_contract(contract_path)
    exclusion = load_exclusion_manifest(exclusion_path)
    if int(chunk_count) != EXPECTED_CHUNKS:
        raise ValueError(f"chunk_count must remain {EXPECTED_CHUNKS}")
    if not 0 <= int(chunk_index) < int(chunk_count):
        raise ValueError("invalid chunk index")

    import duckdb

    uri = gbif_snapshot_s3_uri(SNAPSHOT_DATE, region=SNAPSHOT_REGION)
    con = duckdb.connect()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    partial = output_dir / f"partial_{int(chunk_index):02d}.parquet"
    metadata_path = output_dir / f"metadata_{int(chunk_index):02d}.json"
    try:
        _configure_duckdb_cloud(con, cloud_provider="aws", region=SNAPSHOT_REGION)
        files = _list_snapshot_shards(con, SNAPSHOT_DATE, SNAPSHOT_REGION)
        selected_files = _chunk_files(files, int(chunk_index), int(chunk_count))
        if not selected_files:
            raise RuntimeError(f"empty GBIF shard chunk {chunk_index}")
        source = f"read_parquet({_sql_list(selected_files)}, union_by_name=true)"
        where_sql = _where_sql(exclusion["scientific_name"].tolist())
        query = f"""
        WITH filtered AS (
          SELECT
            species AS scientific_name,
            family,
            genus,
            CAST(FLOOR((decimallongitude + 180.0) / {GRID_DEGREES}) AS BIGINT) AS cell_x,
            CAST(FLOOR((decimallatitude + 90.0) / {GRID_DEGREES}) AS BIGINT) AS cell_y
          FROM {source}
          WHERE {where_sql}
        )
        SELECT
          scientific_name,
          family,
          genus,
          cell_x,
          cell_y,
          COUNT(*)::BIGINT AS n_occurrences_in_cell
        FROM filtered
        GROUP BY scientific_name, family, genus, cell_x, cell_y
        ORDER BY scientific_name, family, genus, cell_x, cell_y
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
        "region": SNAPSHOT_REGION,
        "chunk_index": int(chunk_index),
        "chunk_count": int(chunk_count),
        "snapshot_shard_count": len(files),
        "chunk_shard_count": len(selected_files),
        "first_shard": selected_files[0],
        "last_shard": selected_files[-1],
        "contract_sha256": _sha256(contract_path),
        "exclusion_manifest_sha256": _sha256(exclusion_path),
        "exclusion_taxa": len(exclusion),
        "partial_rows": partial_rows,
        "partial_sha256": _sha256(partial),
        "environmental_values_read": False,
        "candidate_model_fitting_performed": False,
        "prediction_metrics_read": False,
        "process_states_read": False,
        "sealed_answer_check_read": False,
        "fresh_outcomes_opened": False,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def combine_partials(paths: Iterable[Path]) -> pd.DataFrame:
    frames = [pd.read_parquet(path) for path in paths]
    if not frames:
        raise ValueError("no cohort partials supplied")
    raw = pd.concat(frames, ignore_index=True)
    if raw.empty:
        raise ValueError("cohort partials are empty")

    cells = (
        raw.groupby(
            ["scientific_name", "family", "genus", "cell_x", "cell_y"],
            as_index=False,
        )["n_occurrences_in_cell"]
        .sum()
    )
    occurrence = (
        cells.groupby("scientific_name")["n_occurrences_in_cell"]
        .sum()
        .rename("n_occurrences")
    )
    unique_cells = (
        cells[["scientific_name", "cell_x", "cell_y"]]
        .drop_duplicates()
        .groupby("scientific_name")
        .size()
        .rename("n_unique_1_degree_cells")
    )
    taxonomy = (
        cells.groupby(["scientific_name", "family", "genus"], as_index=False)[
            "n_occurrences_in_cell"
        ]
        .sum()
        .sort_values(
            ["scientific_name", "n_occurrences_in_cell", "family", "genus"],
            ascending=[True, False, True, True],
        )
        .drop_duplicates("scientific_name", keep="first")
        .set_index("scientific_name")[["family", "genus"]]
    )
    summary = pd.concat([taxonomy, occurrence, unique_cells], axis=1).reset_index()
    summary[["n_occurrences", "n_unique_1_degree_cells"]] = summary[
        ["n_occurrences", "n_unique_1_degree_cells"]
    ].astype(int)
    return summary.sort_values("scientific_name").reset_index(drop=True)


def select_cohort(
    summary: pd.DataFrame,
    *,
    excluded_names: Iterable[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {
        "scientific_name",
        "family",
        "genus",
        "n_occurrences",
        "n_unique_1_degree_cells",
    }
    missing = required - set(summary.columns)
    if missing:
        raise ValueError(f"cohort summary missing columns: {sorted(missing)}")

    excluded = {str(x).strip() for x in excluded_names}
    audit = summary.copy()
    audit["historically_excluded"] = audit["scientific_name"].astype(str).isin(excluded)
    audit["eligible"] = (
        ~audit["historically_excluded"]
        & (audit["n_occurrences"].astype(int) >= MIN_OCCURRENCES)
        & (audit["n_unique_1_degree_cells"].astype(int) >= MIN_UNIQUE_CELLS)
        & audit["family"].astype(str).str.strip().ne("")
        & audit["genus"].astype(str).str.strip().ne("")
    )
    audit["selection_hash"] = audit["scientific_name"].astype(str).map(deterministic_rank)
    audit = audit.sort_values(["selection_hash", "scientific_name"]).reset_index(drop=True)

    selected_rows = []
    genus_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    for row in audit.loc[audit["eligible"]].itertuples(index=False):
        genus = str(row.genus)
        family = str(row.family)
        if genus_counts.get(genus, 0) >= MAX_PER_GENUS:
            continue
        if family_counts.get(family, 0) >= MAX_PER_FAMILY:
            continue
        selected_rows.append(row._asdict())
        genus_counts[genus] = genus_counts.get(genus, 0) + 1
        family_counts[family] = family_counts.get(family, 0) + 1
        if len(selected_rows) == EXACT_DENOMINATOR:
            break

    if len(selected_rows) != EXACT_DENOMINATOR:
        raise RuntimeError(
            f"fresh cohort unavailable under frozen breadth constraints: selected {len(selected_rows)}"
        )

    selected = pd.DataFrame(selected_rows)
    selected["selection_rank"] = range(1, EXACT_DENOMINATOR + 1)
    keep = [
        "selection_rank",
        "scientific_name",
        "family",
        "genus",
        "n_occurrences",
        "n_unique_1_degree_cells",
        "selection_hash",
    ]
    selected = selected[keep]
    if set(selected["scientific_name"]) & excluded:
        raise RuntimeError("historically excluded taxon entered fresh cohort")
    if selected["genus"].value_counts().max() > MAX_PER_GENUS:
        raise RuntimeError("genus cap violated")
    if selected["family"].value_counts().max() > MAX_PER_FAMILY:
        raise RuntimeError("family cap violated")
    return audit, selected


def run_aggregate(
    *,
    contract_path: str | Path,
    exclusion_path: str | Path,
    parts_root: str | Path,
    output_dir: str | Path,
) -> dict:
    validate_contract(contract_path)
    exclusion = load_exclusion_manifest(exclusion_path)
    root = Path(parts_root)
    metadata_paths = sorted(root.rglob("metadata_*.json"))
    partial_paths = sorted(root.rglob("partial_*.parquet"))
    if len(metadata_paths) != EXPECTED_CHUNKS or len(partial_paths) != EXPECTED_CHUNKS:
        raise RuntimeError(
            f"expected {EXPECTED_CHUNKS} cohort chunks; "
            f"metadata={len(metadata_paths)} partials={len(partial_paths)}"
        )
    metadata = [json.loads(path.read_text()) for path in metadata_paths]
    if {int(x["chunk_index"]) for x in metadata} != set(range(EXPECTED_CHUNKS)):
        raise RuntimeError("cohort chunk index set is incomplete")
    invariant_keys = (
        "program",
        "snapshot_date",
        "snapshot_doi",
        "region",
        "chunk_count",
        "snapshot_shard_count",
        "contract_sha256",
        "exclusion_manifest_sha256",
        "exclusion_taxa",
    )
    for key in invariant_keys:
        values = {str(x[key]) for x in metadata}
        if len(values) != 1:
            raise RuntimeError(f"cohort chunk invariant differs for {key}")
    for key in (
        "environmental_values_read",
        "candidate_model_fitting_performed",
        "prediction_metrics_read",
        "process_states_read",
        "sealed_answer_check_read",
        "fresh_outcomes_opened",
    ):
        if any(x.get(key) is not False for x in metadata):
            raise RuntimeError(f"cohort information barrier crossed: {key}")

    summary = combine_partials(partial_paths)
    audit, selected = select_cohort(
        summary,
        excluded_names=exclusion["scientific_name"].tolist(),
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "cohort_availability_summary.csv"
    audit_path = output_dir / "cohort_selection_audit.csv"
    selected_path = output_dir / "selected_fresh_taxa.csv"
    summary.to_csv(summary_path, index=False)
    audit.to_csv(audit_path, index=False)
    selected.to_csv(selected_path, index=False)

    result = {
        "program": PROGRAM,
        "status": "fresh_cohort_selected_outcomes_unopened",
        "selected_taxa": selected["scientific_name"].tolist(),
        "selected_count": int(len(selected)),
        "selected_families": int(selected["family"].nunique()),
        "selected_genera": int(selected["genus"].nunique()),
        "selected_manifest_sha256": _sha256(selected_path),
        "selection_audit_sha256": _sha256(audit_path),
        "availability_summary_sha256": _sha256(summary_path),
        "contract_sha256": _sha256(contract_path),
        "exclusion_manifest_sha256": _sha256(exclusion_path),
        "fresh_outcomes_opened": False,
        "environmental_values_read": False,
        "candidate_model_fitting_performed": False,
        "prediction_metrics_read": False,
        "process_states_read": False,
        "sealed_answer_check_read": False,
        "next_gate": "freeze_source_process_registry_accessible_area_and_outer_split_before_environmental_feature_access",
    }
    (output_dir / "cohort_selection_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    chunk = sub.add_parser("chunk")
    chunk.add_argument("--contract", required=True)
    chunk.add_argument("--exclusion", required=True)
    chunk.add_argument("--chunk-index", type=int, required=True)
    chunk.add_argument("--chunk-count", type=int, default=EXPECTED_CHUNKS)
    chunk.add_argument("--output-dir", required=True)
    agg = sub.add_parser("aggregate")
    agg.add_argument("--contract", required=True)
    agg.add_argument("--exclusion", required=True)
    agg.add_argument("--parts-root", required=True)
    agg.add_argument("--output-dir", required=True)
    return p


def main() -> None:
    args = _parser().parse_args()
    if args.command == "chunk":
        result = run_chunk(
            contract_path=args.contract,
            exclusion_path=args.exclusion,
            chunk_index=args.chunk_index,
            chunk_count=args.chunk_count,
            output_dir=args.output_dir,
        )
    else:
        result = run_aggregate(
            contract_path=args.contract,
            exclusion_path=args.exclusion,
            parts_root=args.parts_root,
            output_dir=args.output_dir,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
