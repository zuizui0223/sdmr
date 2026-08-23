"""Materialize one Product-A v2.7.2 rank-2 part without opening sealed environments."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .data import OccurrenceAdmissionConfig, load_gbif_download, raster_specs_from_chelsa_manifest
from .pilot import MODEL_ROLE, OUTER_ROLE_COL, SEALED_ROLE, prepare_product_a_pilot
from .pilot_grid_cli import extract_protocol_grid_rasters, read_pilot_grid
from .specification import occurrence_table_fingerprint
from .v2_7_1_fresh_contract import load_fresh_eligibility_thresholds
from .v2_7_2_fresh_contract import (
    load_v2_7_2_fresh_confirmation_contract,
    load_v2_7_2_source_receipt,
    sha256_file,
)

PURPOSE = "product_a_v2_7_2_fresh_part_model_pool_materialization"


def materialize_fresh_part(
    *, contract_path: str | Path, source_gate_path: str | Path,
    source_receipt_path: str | Path, focal_path: str | Path,
    target_path: str | Path, taxa_path: str | Path, grid_path: str | Path,
    manifest_path: str | Path, output_dir: str | Path, seed: int,
    sealed_fraction: float,
) -> dict[str, object]:
    contract = load_v2_7_2_fresh_confirmation_contract(contract_path)
    receipt = load_v2_7_2_source_receipt(
        source_receipt_path, source_gate_path=source_gate_path
    )
    thresholds = load_fresh_eligibility_thresholds(contract_path)
    design = contract["fixed_design"]
    if int(seed) not in {int(x) for x in design["split_seeds"]}:
        raise ValueError("v2.7.2 seed is not frozen")
    if float(sealed_fraction) not in {float(x) for x in design["sealed_fractions"]}:
        raise ValueError("v2.7.2 sealed fraction is not frozen")
    if sha256_file(focal_path) != receipt["focal"]["file_sha256"]:
        raise ValueError("v2.7.2 focal parquet SHA mismatch")
    if sha256_file(target_path) != receipt["target_group"]["file_sha256"]:
        raise ValueError("v2.7.2 target parquet SHA mismatch")
    if sha256_file(taxa_path) != contract["fresh_taxon_panel"]["sha256"]:
        raise ValueError("v2.7.2 taxon panel SHA mismatch")

    focal = load_gbif_download(focal_path).records
    target = load_gbif_download(target_path).records
    taxa = pd.read_csv(taxa_path)
    expected_taxa = set(taxa["scientific_name"].astype(str))
    if len(expected_taxa) != 12:
        raise ValueError("v2.7.2 confirmation requires exactly 12 taxa")
    grid = read_pilot_grid(str(grid_path))
    observed_m = tuple(int(round(float(x))) for x in grid["occurrence_buffer_km"])
    if observed_m != tuple(int(x) for x in design["M_km"]):
        raise ValueError("v2.7.2 M grid differs from frozen 150/300/500 km design")
    if not grid["m_strategy"].astype(str).eq("buffer").all():
        raise ValueError("v2.7.2 M grid must remain buffer based")

    prepared_by_name = {}
    occurrence_sha = None
    for row in grid.itertuples(index=False):
        prepared = prepare_product_a_pilot(
            focal,
            taxa,
            admission_config=OccurrenceAdmissionConfig(),
            min_occurrences=int(thresholds["minimum_occurrences"]),
            min_unique_cells=int(thresholds["minimum_unique_cells"]),
            gate_cell_size_degrees=0.05,
            m_strategy=str(row.m_strategy),
            target_group_pool=target,
            bbox_buffer_degrees=float(row.bbox_buffer_degrees),
            occurrence_buffer_km=float(row.occurrence_buffer_km),
            background_points=int(row.background_points),
            background_cell_size_degrees=float(row.background_cell_size_degrees),
            random_state=int(seed),
            strict_background=True,
            focal_thin_cell_size_degrees=0.05,
            outer_sealed_fraction=float(sealed_fraction),
        )
        eligible = set(
            prepared.species_gate.loc[
                prepared.species_gate["eligible"].astype(bool), "species"
            ].astype(str)
        )
        if eligible != expected_taxa:
            raise ValueError(
                "v2.7.2 part lost predeclared taxa: "
                f"missing={sorted(expected_taxa-eligible)} extra={sorted(eligible-expected_taxa)}"
            )
        sha = occurrence_table_fingerprint(prepared.occurrences)
        if occurrence_sha is None:
            occurrence_sha = sha
        elif sha != occurrence_sha:
            raise ValueError("v2.7.2 M specification changed the frozen focal occurrence split")
        prepared_by_name[str(row.name)] = prepared

    first = next(iter(prepared_by_name.values()))
    model_occurrences = first.occurrences.loc[
        first.occurrences[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
    ].reset_index(drop=True)
    sealed_occurrences_raw = first.occurrences.loc[
        first.occurrences[OUTER_ROLE_COL].astype(str).eq(SEALED_ROLE)
    ].reset_index(drop=True)
    if (
        set(model_occurrences["species"].astype(str)) != expected_taxa
        or set(sealed_occurrences_raw["species"].astype(str)) != expected_taxa
    ):
        raise ValueError("v2.7.2 outer split lost a predeclared taxon")

    model_backgrounds = {}
    sealed_backgrounds_raw = {}
    for name, prepared in prepared_by_name.items():
        model_backgrounds[name] = prepared.background.loc[
            prepared.background[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
        ].reset_index(drop=True)
        sealed_backgrounds_raw[name] = prepared.background.loc[
            prepared.background[OUTER_ROLE_COL].astype(str).eq(SEALED_ROLE)
        ].reset_index(drop=True)

    manifest = pd.read_csv(manifest_path)
    raster_specs, resolution = raster_specs_from_chelsa_manifest(
        manifest, include_availability=("current",), strict=True
    )
    if len(raster_specs) != 43:
        raise ValueError(
            f"v2.7.2 confirmation expected 43 active CHELSA predictors, found {len(raster_specs)}"
        )
    featured_occurrences, featured_backgrounds, raster_provenance = (
        extract_protocol_grid_rasters(model_occurrences, model_backgrounds, raster_specs)
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    featured_occurrences.to_parquet(out / "model_occurrences.parquet", index=False)
    sealed_occurrences_raw.to_parquet(out / "sealed_occurrences_raw.parquet", index=False)
    first.species_gate.to_csv(out / "species_gate.csv", index=False)
    first.occurrence_admission_ledger.to_csv(out / "occurrence_admission_ledger.csv", index=False)
    first.taxon_selection_ledger.to_csv(out / "taxon_selection_ledger.csv", index=False)
    resolution.to_csv(out / "chelsa_resolution_ledger.csv", index=False)
    raster_provenance.to_csv(out / "model_raster_provenance.csv", index=False)
    grid.to_csv(out / "M_grid_frozen.csv", index=False)
    for name in prepared_by_name:
        spec_dir = out / "M" / name
        spec_dir.mkdir(parents=True, exist_ok=True)
        featured_backgrounds[name].to_parquet(
            spec_dir / "model_background.parquet", index=False
        )
        sealed_backgrounds_raw[name].to_parquet(
            spec_dir / "sealed_background_raw.parquet", index=False
        )
        prepared_by_name[name].background_ledger.to_csv(
            spec_dir / "background_ledger.csv", index=False
        )

    result = {
        "purpose": PURPOSE,
        "seed": int(seed),
        "sealed_fraction": float(sealed_fraction),
        "occurrence_sha256": str(occurrence_sha),
        "n_taxa": 12,
        "M_specs": list(prepared_by_name),
        "n_active_CHELSA_predictors": len(raster_specs),
        "outer_sealed_before_M": True,
        "M_built_from_model_pool_only": True,
        "model_pool_raster_values_extracted": True,
        "sealed_occurrence_raster_values_extracted": False,
        "sealed_background_raster_values_extracted": False,
        "fresh_focal_sha256": receipt["focal"]["file_sha256"],
        "fresh_target_sha256": receipt["target_group"]["file_sha256"],
        "v2_7_1_split_parts_reused": False,
        "v2_7_1_focal_artifact_reused": False,
        "v2_7_1_target_artifact_reused": False,
        "deterministic_successor": True,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", required=True)
    p.add_argument("--source-gate", required=True)
    p.add_argument("--source-receipt", required=True)
    p.add_argument("--focal", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--taxa", required=True)
    p.add_argument("--grid", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--sealed-fraction", type=float, required=True)
    a = p.parse_args(argv)
    materialize_fresh_part(
        contract_path=a.contract,
        source_gate_path=a.source_gate,
        source_receipt_path=a.source_receipt,
        focal_path=a.focal,
        target_path=a.target,
        taxa_path=a.taxa,
        grid_path=a.grid,
        manifest_path=a.manifest,
        output_dir=a.output_dir,
        seed=a.seed,
        sealed_fraction=a.sealed_fraction,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
