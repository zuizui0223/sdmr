"""Rebuild one Product-A v2.6 empirical part from immutable raw source evidence.

This stage is intentionally *pretruth*: it assigns outer sealed occurrence roles
before M/background construction, but extracts CHELSA values only for model-pool
occurrences and model-pool backgrounds. Sealed occurrence coordinates are written
for a later audit stage without environmental raster extraction.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .data import OccurrenceAdmissionConfig, raster_specs_from_chelsa_manifest
from .pilot import MODEL_ROLE, OUTER_ROLE_COL, SEALED_ROLE, prepare_product_a_pilot
from .pilot_grid_cli import extract_protocol_grid_rasters, read_pilot_grid
from .specification import occurrence_table_fingerprint
from .v2_6_empirical_contract import load_v2_6_empirical_contract


def materialize_empirical_part(
    *,
    contract_path: str | Path,
    focal_path: str | Path,
    target_path: str | Path,
    taxa_path: str | Path,
    grid_path: str | Path,
    manifest_path: str | Path,
    output_dir: str | Path,
    seed: int,
    sealed_fraction: float,
) -> dict[str, object]:
    """Build model-pool environmental evidence while leaving sealed environments unopened."""

    contract = load_v2_6_empirical_contract(contract_path)
    design = contract["fixed_design"]
    if int(seed) not in {int(x) for x in design["split_seeds"]}:
        raise ValueError("seed is not in the frozen empirical confirmation design")
    if float(sealed_fraction) not in {float(x) for x in design["sealed_fractions"]}:
        raise ValueError("sealed fraction is not in the frozen empirical confirmation design")

    focal = pd.read_parquet(focal_path)
    target = pd.read_parquet(target_path)
    taxa = pd.read_csv(taxa_path)
    grid = read_pilot_grid(str(grid_path))
    expected_m = tuple(int(x) for x in design["M_km"])
    observed_m = tuple(int(round(float(x))) for x in grid["occurrence_buffer_km"])
    if observed_m != expected_m or not grid["m_strategy"].astype(str).eq("buffer").all():
        raise ValueError("empirical M grid differs from the frozen 150/300/500-km buffer design")

    expected_taxa = set(taxa["scientific_name"].astype(str))
    if len(expected_taxa) != 12:
        raise ValueError("empirical confirmation requires exactly 12 predeclared taxa")

    prepared_by_name = {}
    occurrence_sha = None
    for row in grid.itertuples(index=False):
        prepared = prepare_product_a_pilot(
            focal,
            taxa,
            admission_config=OccurrenceAdmissionConfig(),
            min_occurrences=80,
            min_unique_cells=50,
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
        eligible = set(prepared.species_gate.loc[prepared.species_gate["eligible"].astype(bool), "species"].astype(str))
        if eligible != expected_taxa:
            raise ValueError(
                f"empirical part lost predeclared taxa before modelling: missing={sorted(expected_taxa-eligible)}, extra={sorted(eligible-expected_taxa)}"
            )
        sha = occurrence_table_fingerprint(prepared.occurrences)
        if occurrence_sha is None:
            occurrence_sha = sha
        elif sha != occurrence_sha:
            raise ValueError("M specification changed the frozen focal occurrence split")
        prepared_by_name[str(row.name)] = prepared

    first = next(iter(prepared_by_name.values()))
    model_occurrences = first.occurrences.loc[
        first.occurrences[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
    ].reset_index(drop=True)
    sealed_occurrences_raw = first.occurrences.loc[
        first.occurrences[OUTER_ROLE_COL].astype(str).eq(SEALED_ROLE)
    ].reset_index(drop=True)
    if set(model_occurrences["species"].astype(str)) != expected_taxa:
        raise ValueError("model-pool occurrences lost a predeclared taxon")
    if set(sealed_occurrences_raw["species"].astype(str)) != expected_taxa:
        raise ValueError("sealed occurrences lost a predeclared taxon")

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
    audit_predictors = tuple(spec.predictor for spec in raster_specs)
    if len(audit_predictors) != 43:
        raise ValueError(f"empirical confirmation expected 43 active CHELSA predictors, found {len(audit_predictors)}")

    # Critical barrier: only model-pool rows enter raster extraction here.
    featured_occurrences, featured_backgrounds, raster_provenance = extract_protocol_grid_rasters(
        model_occurrences,
        model_backgrounds,
        raster_specs,
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
        featured_backgrounds[name].to_parquet(spec_dir / "model_background.parquet", index=False)
        sealed_backgrounds_raw[name].to_parquet(spec_dir / "sealed_background_raw.parquet", index=False)
        prepared_by_name[name].background_ledger.to_csv(spec_dir / "background_ledger.csv", index=False)

    metadata = {
        "purpose": "product_a_v2_6_empirical_part_model_pool_materialization",
        "seed": int(seed),
        "sealed_fraction": float(sealed_fraction),
        "occurrence_sha256": str(occurrence_sha),
        "n_taxa": len(expected_taxa),
        "M_specs": list(prepared_by_name),
        "n_active_audit_predictors": len(audit_predictors),
        "audit_predictors": list(audit_predictors),
        "outer_sealed_before_M": True,
        "M_built_from_model_pool_only": True,
        "model_pool_raster_values_extracted": True,
        "sealed_occurrence_raster_values_extracted": False,
        "sealed_background_raster_values_extracted": False,
        "old_real_model_outputs_reused": False,
        "old_real_background_outputs_reused": False,
        "old_real_sealed_outcomes_read": False,
    }
    (out / "contract.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--focal", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--taxa", required=True)
    parser.add_argument("--grid", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--sealed-fraction", type=float, required=True)
    args = parser.parse_args(argv)
    materialize_empirical_part(
        contract_path=args.contract,
        focal_path=args.focal,
        target_path=args.target,
        taxa_path=args.taxa,
        grid_path=args.grid,
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        seed=args.seed,
        sealed_fraction=args.sealed_fraction,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
