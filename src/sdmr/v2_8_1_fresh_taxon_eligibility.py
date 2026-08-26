from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

import pandas as pd

EXPECTED_STRATA = {
    "temperate_annual_herb",
    "temperate_deciduous_tree",
    "boreal_temperate_conifer",
    "wetland_grass",
    "temperate_shrub",
    "fern",
    "arid_shrub",
    "tropical_mangrove",
    "southern_temperate_tree",
    "montane_tree",
    "boreal_conifer",
    "wetland_emergent",
}
EXPECTED_RANKS = {1, 2, 3}
SNAPSHOT_DATE = "2026-08-01"
SNAPSHOT_DOI = "10.15468/dl.fs3btq"
SNAPSHOT_REGION = "us-east-1"
GRID_DEGREES = 0.05
CALIBRATED_SEALED_FRACTION = 0.25


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_candidates(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    expected_columns = [
        "scientific_name",
        "validation_stratum",
        "candidate_rank",
        "selection_basis",
    ]
    if list(df.columns) != expected_columns:
        raise ValueError(f"candidate columns changed: {list(df.columns)}")
    if len(df) != 36:
        raise ValueError(f"expected exactly 36 predeclared candidates, got {len(df)}")
    if df["scientific_name"].astype(str).duplicated().any():
        raise ValueError("candidate scientific names must be unique")
    if set(df["validation_stratum"].astype(str)) != EXPECTED_STRATA:
        raise ValueError("validation strata changed")
    for stratum, group in df.groupby("validation_stratum", sort=False):
        if len(group) != 3:
            raise ValueError(f"{stratum}: expected exactly 3 candidates")
        if set(group["candidate_rank"].astype(int)) != EXPECTED_RANKS:
            raise ValueError(f"{stratum}: candidate ranks must be exactly 1,2,3")
    if df["selection_basis"].astype(str).str.strip().eq("").any():
        raise ValueError("every candidate must have a predeclared selection basis")
    return df


def _read_names(path: str | Path) -> set[str]:
    return set(pd.read_csv(path)["scientific_name"].astype(str))


def validate_preoutcome_contract(
    *,
    candidates_path: str | Path,
    pilot_path: str | Path,
    consumed_path: str | Path,
    contract_path: str | Path,
) -> dict:
    candidates = _load_candidates(candidates_path)
    names = set(candidates["scientific_name"].astype(str))
    pilot = _read_names(pilot_path)
    consumed = _read_names(consumed_path)
    if names & pilot:
        raise ValueError(f"candidate pool overlaps pilot taxa: {sorted(names & pilot)}")
    if names & consumed:
        raise ValueError(f"candidate pool overlaps 36 calibration taxa: {sorted(names & consumed)}")

    contract = json.loads(Path(contract_path).read_text())
    if contract.get("purpose") != "product_a_v2_8_1_fresh_taxon_panel_eligibility_contract":
        raise ValueError("wrong v2.8.1 eligibility contract purpose")
    receipt = contract["geometry_calibration_receipt"]
    if receipt.get("decision") != "geometry_calibration_fraction_selected":
        raise ValueError("geometry calibration did not select a fraction")
    if float(receipt.get("selected_global_sealed_fraction")) != CALIBRATED_SEALED_FRACTION:
        raise ValueError("calibrated sealed fraction changed")
    if receipt.get("retuning_allowed") is not False:
        raise ValueError("calibrated sealed fraction became retunable")

    thresholds = contract["thresholds"]
    if int(thresholds["minimum_occurrences"]) != 80:
        raise ValueError("minimum occurrence threshold changed")
    if int(thresholds["minimum_unique_0_05_degree_cells"]) != 50:
        raise ValueError("minimum unique-cell threshold changed")

    rule = contract["selection_rule"]
    if int(rule["required_strata"]) != 12 or int(rule["required_candidates_per_stratum"]) != 3:
        raise ValueError("fresh-panel denominator changed")
    if rule["within_stratum_rule"] != "lowest_predeclared_candidate_rank_meeting_both_eligibility_thresholds":
        raise ValueError("fresh-panel selection rule changed")
    if rule.get("post_eligibility_candidate_reordering_allowed") is not False:
        raise ValueError("post-count candidate reordering became allowed")
    if rule.get("threshold_relaxation_after_counts_are_seen_allowed") is not False:
        raise ValueError("post-count threshold relaxation became allowed")

    barrier = contract["information_barrier"]
    for key in (
        "environmental_values_read",
        "candidate_model_fitting_allowed",
        "candidate_scores_read",
        "sealed_confirmation_outcomes_read",
        "scientific_confirmation_execution_allowed",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if barrier.get(key) is not False:
            raise ValueError(f"eligibility contract crossed information barrier: {key}")
    return contract


def _logical_query_sha(candidate_sha: str, uri: str) -> str:
    payload = (
        "product_a_v2_8_1_fresh_taxon_eligibility_exact_shard_union_v1\n"
        + uri
        + "\ncandidate_pool_sha256="
        + candidate_sha
        + "\ngrid=0.05\nvalid_coordinates=true\n"
        + "outputs=raw_occurrence_count,unique_species_cell_count\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_chunk(
    *,
    candidates_path: str | Path,
    chunk_index: int,
    chunk_count: int,
    output_dir: str | Path,
) -> dict:
    import duckdb

    from sdmr.data.snapshot import (
        _configure_duckdb_cloud,
        _sql_literal,
        build_snapshot_filter_sql,
        gbif_snapshot_s3_uri,
    )
    from sdmr.target_footprint_parallel_cli import (
        _chunk_files,
        _list_snapshot_shards,
        _sql_list,
    )

    candidates = _load_candidates(candidates_path)
    names = candidates["scientific_name"].astype(str).tolist()
    candidate_sha = _sha256(candidates_path)
    uri = gbif_snapshot_s3_uri(SNAPSHOT_DATE, region=SNAPSHOT_REGION)
    where_sql = build_snapshot_filter_sql(species_names=names, require_coordinates=True)
    logical_query_sha = _logical_query_sha(candidate_sha, uri)

    con = duckdb.connect()
    try:
        _configure_duckdb_cloud(con, cloud_provider="aws", region=SNAPSHOT_REGION)
        files = _list_snapshot_shards(con, SNAPSHOT_DATE, SNAPSHOT_REGION)
        selected = _chunk_files(files, int(chunk_index), int(chunk_count))
        if not selected:
            raise RuntimeError(f"empty snapshot shard chunk {chunk_index}")
        source = f"read_parquet({_sql_list(selected)}, union_by_name=true)"
        query = f"""
        WITH filtered AS (
          SELECT
            species,
            CAST(FLOOR((decimallongitude + 180.0) / {GRID_DEGREES}) AS BIGINT) AS cell_x,
            CAST(FLOOR((decimallatitude + 90.0) / {GRID_DEGREES}) AS BIGINT) AS cell_y
          FROM {source}
          WHERE {where_sql}
        )
        SELECT
          species,
          cell_x,
          cell_y,
          COUNT(*)::BIGINT AS n_occurrences_in_cell
        FROM filtered
        GROUP BY species, cell_x, cell_y
        ORDER BY species, cell_x, cell_y
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output = (output_dir / "partial.parquet").resolve()
        con.execute(
            f"COPY ({query}) TO {_sql_literal(str(output))} "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        partial_rows = int(
            con.execute(
                f"SELECT COUNT(*) FROM read_parquet({_sql_literal(str(output))})"
            ).fetchone()[0]
        )
    finally:
        con.close()

    catalog_sha = hashlib.sha256(("\n".join(files) + "\n").encode("utf-8")).hexdigest()
    chunk_catalog_sha = hashlib.sha256(
        ("\n".join(selected) + "\n").encode("utf-8")
    ).hexdigest()
    partial_sha = _sha256(output)
    metadata = {
        "purpose": "product_a_v2_8_1_fresh_taxon_eligibility_shard_chunk",
        "snapshot_date": SNAPSHOT_DATE,
        "snapshot_doi": SNAPSHOT_DOI,
        "region": SNAPSHOT_REGION,
        "chunk_index": int(chunk_index),
        "chunk_count": int(chunk_count),
        "snapshot_shard_count": len(files),
        "snapshot_shard_catalog_sha256": catalog_sha,
        "chunk_shard_count": len(selected),
        "chunk_shard_catalog_sha256": chunk_catalog_sha,
        "first_shard": selected[0],
        "last_shard": selected[-1],
        "candidate_pool_sha256": candidate_sha,
        "logical_query_sha256": logical_query_sha,
        "partial_rows": partial_rows,
        "partial_sha256": partial_sha,
        "projected_source_columns": ["species", "decimallongitude", "decimallatitude"],
        "environmental_values_read": False,
        "candidate_model_scores_read": False,
        "candidate_model_fitting_performed": False,
        "sealed_confirmation_outcomes_read": False,
        "scientific_confirmation_executed": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    (Path(output_dir) / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    return metadata


def _combine_partials(partial_paths: Iterable[Path]) -> pd.DataFrame:
    paths = list(partial_paths)
    partial = pd.concat([pd.read_parquet(path) for path in paths], ignore_index=True)
    if not len(partial):
        return pd.DataFrame(
            columns=["species", "n_occurrences", "n_unique_0_05_degree_cells"]
        )
    cells = (
        partial.groupby(["species", "cell_x", "cell_y"], as_index=False)[
            "n_occurrences_in_cell"
        ].sum()
    )
    occurrence_counts = (
        cells.groupby("species")["n_occurrences_in_cell"].sum().rename("n_occurrences")
    )
    cell_counts = cells.groupby("species").size().rename("n_unique_0_05_degree_cells")
    counts = pd.concat([occurrence_counts, cell_counts], axis=1).reset_index()
    counts[["n_occurrences", "n_unique_0_05_degree_cells"]] = counts[
        ["n_occurrences", "n_unique_0_05_degree_cells"]
    ].astype(int)
    return counts.sort_values("species").reset_index(drop=True)


def select_panel(
    *,
    candidates: pd.DataFrame,
    counts: pd.DataFrame,
    minimum_occurrences: int,
    minimum_unique_cells: int,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    audit = candidates.merge(counts, how="left", left_on="scientific_name", right_on="species")
    audit = audit.drop(columns=["species"], errors="ignore")
    audit[["n_occurrences", "n_unique_0_05_degree_cells"]] = audit[
        ["n_occurrences", "n_unique_0_05_degree_cells"]
    ].fillna(0).astype(int)
    audit["eligible"] = (
        (audit["n_occurrences"] >= int(minimum_occurrences))
        & (audit["n_unique_0_05_degree_cells"] >= int(minimum_unique_cells))
    )
    audit = audit.sort_values(
        ["validation_stratum", "candidate_rank", "scientific_name"]
    ).reset_index(drop=True)

    selected_rows = []
    unavailable_strata: list[str] = []
    for stratum, group in audit.groupby("validation_stratum", sort=True):
        eligible = group.loc[group["eligible"]].sort_values(
            ["candidate_rank", "scientific_name"]
        )
        if eligible.empty:
            unavailable_strata.append(str(stratum))
        else:
            selected_rows.append(eligible.iloc[0])

    selected_columns = [
        "scientific_name",
        "validation_stratum",
        "candidate_rank",
        "n_occurrences",
        "n_unique_0_05_degree_cells",
    ]
    if selected_rows:
        selected = (
            pd.DataFrame(selected_rows)[selected_columns]
            .sort_values("validation_stratum")
            .reset_index(drop=True)
        )
    else:
        selected = pd.DataFrame(columns=selected_columns)
    return audit, selected, unavailable_strata


def run_aggregate(
    *,
    candidates_path: str | Path,
    pilot_path: str | Path,
    consumed_path: str | Path,
    contract_path: str | Path,
    parts_root: str | Path,
    output_dir: str | Path,
) -> dict:
    contract = validate_preoutcome_contract(
        candidates_path=candidates_path,
        pilot_path=pilot_path,
        consumed_path=consumed_path,
        contract_path=contract_path,
    )
    candidates = _load_candidates(candidates_path)
    root = Path(parts_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_paths = sorted(root.rglob("metadata.json"))
    partial_paths = sorted(root.rglob("partial.parquet"))
    expected_chunks = 16
    if len(metadata_paths) != expected_chunks or len(partial_paths) != expected_chunks:
        raise RuntimeError(
            f"expected {expected_chunks} exact shard chunks; "
            f"metadata={len(metadata_paths)} partials={len(partial_paths)}"
        )
    metadata = [json.loads(path.read_text()) for path in metadata_paths]
    by_index = {int(row["chunk_index"]): row for row in metadata}
    if set(by_index) != set(range(expected_chunks)):
        raise RuntimeError(f"incomplete shard chunk indices: {sorted(by_index)}")

    invariant_keys = (
        "snapshot_date",
        "snapshot_doi",
        "region",
        "chunk_count",
        "snapshot_shard_count",
        "snapshot_shard_catalog_sha256",
        "candidate_pool_sha256",
        "logical_query_sha256",
    )
    for key in invariant_keys:
        values = {str(row[key]) for row in metadata}
        if len(values) != 1:
            raise RuntimeError(f"chunk invariant differs for {key}: {sorted(values)}")
    if sum(int(row["chunk_shard_count"]) for row in metadata) != int(
        metadata[0]["snapshot_shard_count"]
    ):
        raise RuntimeError("chunk shard counts do not cover the complete snapshot catalog")

    for key in (
        "environmental_values_read",
        "candidate_model_scores_read",
        "candidate_model_fitting_performed",
        "sealed_confirmation_outcomes_read",
        "scientific_confirmation_executed",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if any(row.get(key) is not False for row in metadata):
            raise RuntimeError(f"eligibility chunk crossed information barrier: {key}")

    if sorted(str(row["partial_sha256"]) for row in metadata) != sorted(
        _sha256(path) for path in partial_paths
    ):
        raise RuntimeError("partial parquet SHA set differs from chunk metadata")
    if _sha256(candidates_path) != str(metadata[0]["candidate_pool_sha256"]):
        raise RuntimeError("candidate registry changed after chunk execution started")

    counts = _combine_partials(partial_paths)
    counts.to_csv(output_dir / "availability_counts.csv", index=False)
    thresholds = contract["thresholds"]
    audit, selected, unavailable_strata = select_panel(
        candidates=candidates,
        counts=counts,
        minimum_occurrences=int(thresholds["minimum_occurrences"]),
        minimum_unique_cells=int(thresholds["minimum_unique_0_05_degree_cells"]),
    )
    audit.to_csv(output_dir / "candidate_eligibility.csv", index=False)
    selected.to_csv(output_dir / "selected_fresh_taxa.csv", index=False)

    selected_names = set(selected["scientific_name"].astype(str))
    excluded = _read_names(pilot_path) | _read_names(consumed_path)
    if selected_names & excluded:
        raise RuntimeError("selected v2.8.1 fresh panel overlaps excluded focal taxa")

    status = (
        "available"
        if not unavailable_strata and len(selected) == 12
        else "unavailable"
    )
    query_contract = {
        "purpose": "product_a_v2_8_1_fresh_taxon_availability_parallel_exact_contract",
        "snapshot_date": metadata[0]["snapshot_date"],
        "snapshot_doi": metadata[0]["snapshot_doi"],
        "snapshot_shard_count": int(metadata[0]["snapshot_shard_count"]),
        "snapshot_shard_catalog_sha256": metadata[0]["snapshot_shard_catalog_sha256"],
        "parallel_chunk_count": expected_chunks,
        "logical_query_sha256": metadata[0]["logical_query_sha256"],
        "candidate_pool_sha256": metadata[0]["candidate_pool_sha256"],
        "candidate_pool_changed_after_execution_started": False,
        "eligibility_thresholds_changed_after_execution_started": False,
        "candidate_ranks_changed_after_execution_started": False,
        "environmental_values_read": False,
        "candidate_model_scores_read": False,
        "candidate_model_fitting_performed": False,
        "sealed_confirmation_outcomes_read": False,
        "scientific_confirmation_executed": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    (output_dir / "availability_query_contract.json").write_text(
        json.dumps(query_contract, indent=2, sort_keys=True) + "\n"
    )

    result = {
        "purpose": "product_a_v2_8_1_fresh_taxon_panel_eligibility_result",
        "status": status,
        "workflow_run_id": int(os.environ.get("GITHUB_RUN_ID", "0")),
        "workflow_sha": os.environ.get("GITHUB_SHA"),
        "candidate_pool_sha256": _sha256(candidates_path),
        "eligibility_contract_sha256": _sha256(contract_path),
        "pilot_registry_sha256": _sha256(pilot_path),
        "consumed_36_registry_sha256": _sha256(consumed_path),
        "selected_global_sealed_fraction_for_future_confirmation": CALIBRATED_SEALED_FRACTION,
        "selected_taxa": selected["scientific_name"].astype(str).tolist(),
        "selected_panel_sha256": _sha256(output_dir / "selected_fresh_taxa.csv"),
        "candidate_eligibility_sha256": _sha256(output_dir / "candidate_eligibility.csv"),
        "availability_counts_sha256": _sha256(output_dir / "availability_counts.csv"),
        "unavailable_strata": unavailable_strata,
        "next_gate": (
            "materialize_and_pin_new_raw_focal_and_excluding_target_artifacts_then_"
            "stage_and_freeze_v2_8_scientific_confirmation_runtime"
            if status == "available"
            else "fresh_panel_unavailable_fail_closed_no_scientific_confirmation"
        ),
        "selection_information_barrier": {
            "environmental_values_used": False,
            "candidate_model_scores_used": False,
            "candidate_model_fitting_performed": False,
            "niche_recovery_outcomes_used": False,
            "sealed_confirmation_outcomes_used": False,
            "post_count_candidate_reordering": False,
            "post_count_threshold_relaxation": False,
        },
        "scientific_confirmation_allowed": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    (output_dir / "selection_contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    chunk = sub.add_parser("chunk")
    chunk.add_argument("--candidates", required=True)
    chunk.add_argument("--chunk-index", type=int, required=True)
    chunk.add_argument("--chunk-count", type=int, default=16)
    chunk.add_argument("--output-dir", required=True)

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--candidates", required=True)
    aggregate.add_argument("--pilot", required=True)
    aggregate.add_argument("--consumed", required=True)
    aggregate.add_argument("--contract", required=True)
    aggregate.add_argument("--parts-root", required=True)
    aggregate.add_argument("--output-dir", required=True)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.command == "chunk":
        result = run_chunk(
            candidates_path=args.candidates,
            chunk_index=args.chunk_index,
            chunk_count=args.chunk_count,
            output_dir=args.output_dir,
        )
    else:
        result = run_aggregate(
            candidates_path=args.candidates,
            pilot_path=args.pilot,
            consumed_path=args.consumed,
            contract_path=args.contract,
            parts_root=args.parts_root,
            output_dir=args.output_dir,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
