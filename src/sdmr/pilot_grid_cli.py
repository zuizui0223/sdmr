"""Run a matched multi-specification Product-A pilot grid.

Occurrence admission and environmental extraction are held fixed while only the
predeclared M/background specifications vary. The resulting data-specification ×
candidate-universe × strategy grid is selected on discovery taxa and frozen
before unseen-taxon validation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .data import (
    GBIF_COL_XR_CHECKLIST_KEY,
    OccurrenceAdmissionConfig,
    extract_raster_values,
    load_gbif_download,
    raster_specs_from_chelsa_manifest,
)
from .pilot import prepare_product_a_pilot
from .protocol import benchmark_product_a_protocol_grid, occurrence_feature_fingerprint
from .specification import occurrence_table_fingerprint
from .universe import candidate_universes_from_manifest

_REQUIRED_GRID_COLUMNS = {"name", "m_strategy"}


def read_pilot_grid(path: str) -> pd.DataFrame:
    """Read/validate a predeclared M/background specification grid."""
    frame = pd.read_csv(path)
    missing = _REQUIRED_GRID_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"pilot grid missing columns: {sorted(missing)}")
    frame = frame.copy()
    frame["name"] = frame["name"].astype(str).str.strip()
    frame["m_strategy"] = frame["m_strategy"].astype(str).str.strip()
    if frame["name"].eq("").any():
        raise ValueError("pilot grid specification names must not be empty")
    if frame["name"].duplicated().any():
        raise ValueError("pilot grid specification names must be unique")
    invalid = sorted(set(frame["m_strategy"]) - {"bbox", "buffer"})
    if invalid:
        raise ValueError(f"unsupported m_strategy values: {invalid}")
    defaults = {
        "bbox_buffer_degrees": 2.0,
        "occurrence_buffer_km": 300.0,
        "background_points": 5000,
        "background_cell_size_degrees": 1 / 120,
    }
    for column, default in defaults.items():
        if column not in frame:
            frame[column] = default
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(default)
    if (frame["bbox_buffer_degrees"] < 0).any():
        raise ValueError("bbox_buffer_degrees must be >= 0")
    if (frame["occurrence_buffer_km"] <= 0).any():
        raise ValueError("occurrence_buffer_km must be > 0")
    if (frame["background_points"] < 1).any():
        raise ValueError("background_points must be >= 1")
    if (frame["background_cell_size_degrees"] <= 0).any():
        raise ValueError("background_cell_size_degrees must be > 0")
    frame["background_points"] = frame["background_points"].astype(int)
    return frame


def _read_taxa(path: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "scientific_name" not in frame:
        raise ValueError("Pilot taxa CSV must contain scientific_name")
    return frame


def _write_protocol_outputs(result, out: Path, *, args) -> None:
    result.discovery_metrics.to_csv(out / "protocol_discovery_metrics.csv", index=False)
    result.discovery_summary.to_csv(out / "protocol_discovery_summary.csv", index=False)
    result.validation_metrics.to_csv(out / "protocol_validation_metrics.csv", index=False)
    result.validation_summary.to_csv(out / "protocol_validation_summary.csv", index=False)
    result.paired_validation_deltas.to_csv(out / "protocol_validation_paired_deltas.csv", index=False)
    (out / "product_a_protocol_choice.txt").write_text(
        "winning_data_specification=" + result.winning_data_specification + "\n"
        + "winning_universe=" + result.winning_universe + "\n"
        + "winning_strategy=" + result.winning_strategy + "\n"
        + "winning_universe_sha256=" + result.winning_universe_sha256 + "\n"
        + "winning_predictors=" + ",".join(result.winning_predictors) + "\n"
        + "occurrence_sha256=" + result.occurrence_sha256 + "\n"
        + "occurrence_feature_sha256=" + result.occurrence_feature_sha256 + "\n"
        + "discovery_species=" + ",".join(result.discovery_species) + "\n"
        + "validation_species=" + ",".join(result.validation_species) + "\n"
        + f"spatial_test_fraction={args.spatial_test_fraction}\n"
        + f"taxon_validation_fraction={args.taxon_validation_fraction}\n"
        + f"seed={args.seed}\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build several matched M/background Product-A specifications from one occurrence corpus, "
            "extract CHELSA once for the shared occurrences, and freeze the winning full protocol on discovery taxa."
        )
    )
    parser.add_argument("--gbif-download", required=True)
    parser.add_argument("--gbif-download-key", required=True)
    parser.add_argument("--target-group-download", required=True)
    parser.add_argument("--target-group-download-key", required=True)
    parser.add_argument("--checklist-key", default=GBIF_COL_XR_CHECKLIST_KEY)
    parser.add_argument("--taxa", required=True)
    parser.add_argument("--grid", required=True, help="CSV of predeclared M/background specifications")
    parser.add_argument("--manifest", default="configs/chelsa_v2_1_plant_candidates.csv")
    parser.add_argument("--output-dir", required=True)

    parser.add_argument("--max-coordinate-uncertainty-m", type=float)
    parser.add_argument("--min-year", type=int)
    parser.add_argument("--max-year", type=int)
    parser.add_argument("--allowed-basis-of-record")
    parser.add_argument("--min-occurrences", type=int, required=True)
    parser.add_argument("--min-unique-cells", type=int, required=True)
    parser.add_argument("--gate-cell-size-degrees", type=float, default=1 / 120)

    parser.add_argument("--spatial-test-fraction", type=float, default=0.20)
    parser.add_argument("--taxon-validation-fraction", type=float, default=0.20)
    parser.add_argument("--vif-threshold", type=float, default=5.0)
    parser.add_argument("--max-predictors", type=int, default=8)
    parser.add_argument("--random-baseline-repeats", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    if not 0 < args.spatial_test_fraction < 1 or not 0 < args.taxon_validation_fraction < 1:
        parser.error("test fractions must be between 0 and 1")
    if args.vif_threshold <= 1:
        parser.error("--vif-threshold must be > 1")
    if args.max_predictors < 1:
        parser.error("--max-predictors must be >= 1")
    if args.random_baseline_repeats < 0:
        parser.error("--random-baseline-repeats must be >= 0")

    grid = read_pilot_grid(args.grid)
    taxa = _read_taxa(args.taxa)
    focal_download = load_gbif_download(
        args.gbif_download,
        download_key=args.gbif_download_key,
        checklist_key=args.checklist_key,
    )
    target_download = load_gbif_download(
        args.target_group_download,
        download_key=args.target_group_download_key,
        checklist_key=args.checklist_key,
    )
    allowed_basis = None
    if args.allowed_basis_of_record:
        allowed_basis = tuple(x.strip() for x in args.allowed_basis_of_record.split(",") if x.strip())
    admission = OccurrenceAdmissionConfig(
        max_coordinate_uncertainty_m=args.max_coordinate_uncertainty_m,
        min_year=args.min_year,
        max_year=args.max_year,
        allowed_basis_of_record=allowed_basis,
    )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    focal_download.provenance.to_csv(out / "gbif_focal_provenance.csv", index=False)
    target_download.provenance.to_csv(out / "gbif_target_group_provenance.csv", index=False)
    grid.to_csv(out / "pilot_grid_frozen.csv", index=False)

    prepared_by_name = {}
    reference_occurrence_sha = None
    for row in grid.itertuples(index=False):
        prepared = prepare_product_a_pilot(
            focal_download.records,
            taxa,
            admission_config=admission,
            min_occurrences=args.min_occurrences,
            min_unique_cells=args.min_unique_cells,
            gate_cell_size_degrees=args.gate_cell_size_degrees,
            m_strategy=str(row.m_strategy),
            target_group_pool=target_download.records,
            bbox_buffer_degrees=float(row.bbox_buffer_degrees),
            occurrence_buffer_km=float(row.occurrence_buffer_km),
            background_points=int(row.background_points),
            background_cell_size_degrees=float(row.background_cell_size_degrees),
            random_state=args.seed,
            strict_background=True,
        )
        occ_sha = occurrence_table_fingerprint(prepared.occurrences)
        if reference_occurrence_sha is None:
            reference_occurrence_sha = occ_sha
        elif occ_sha != reference_occurrence_sha:
            raise ValueError(
                f"Grid specification {row.name!r} changed the occurrence evidence. "
                "M/background grids must share the same occurrence table."
            )
        prepared_by_name[str(row.name)] = prepared
        spec_dir = out / "specifications" / str(row.name)
        spec_dir.mkdir(parents=True, exist_ok=True)
        prepared.background_ledger.to_csv(spec_dir / "background_ledger.csv", index=False)
        prepared.background.to_csv(spec_dir / "background_pre_raster.csv", index=False)

    first = next(iter(prepared_by_name.values()))
    first.taxon_selection_ledger.to_csv(out / "taxon_selection_ledger.csv", index=False)
    first.occurrence_admission_ledger.to_csv(out / "occurrence_admission_ledger.csv", index=False)
    first.species_gate.to_csv(out / "species_gate.csv", index=False)
    first.occurrences.to_csv(out / "pilot_occurrences_pre_raster.csv", index=False)

    manifest = pd.read_csv(args.manifest)
    specs, resolution = raster_specs_from_chelsa_manifest(manifest, include_availability=("current",), strict=True)
    resolution.to_csv(out / "chelsa_resolution_ledger.csv", index=False)
    predictors = [spec.predictor for spec in specs]
    active_manifest = manifest.loc[manifest["predictor"].astype(str).isin(predictors)].reset_index(drop=True)
    universes = candidate_universes_from_manifest(active_manifest)

    shared_occurrences, occ_provenance = extract_raster_values(first.occurrences, specs)
    shared_occurrences.to_csv(out / "pilot_occurrences.csv", index=False)
    occ_provenance.assign(table="occurrences").to_csv(out / "raster_provenance_occurrences.csv", index=False)

    protocol_specs = {}
    for name, prepared in prepared_by_name.items():
        background, bg_provenance = extract_raster_values(prepared.background, specs)
        spec_dir = out / "specifications" / name
        background.to_csv(spec_dir / "background.csv", index=False)
        bg_provenance.assign(table="background", data_specification=name).to_csv(
            spec_dir / "raster_provenance_background.csv", index=False
        )
        protocol_specs[name] = (shared_occurrences.copy(), background)

    result = benchmark_product_a_protocol_grid(
        protocol_specs,
        universes,
        taxon_validation_fraction=args.taxon_validation_fraction,
        sealed_fraction=args.spatial_test_fraction,
        vif_threshold=args.vif_threshold,
        max_predictors=args.max_predictors,
        random_repeats=args.random_baseline_repeats,
        compute_drop_one=False,
        random_state=args.seed,
    )
    _write_protocol_outputs(result, out, args=args)

    run_spec = {
        "gbif_download_key": args.gbif_download_key,
        "target_group_download_key": args.target_group_download_key,
        "checklist_key": args.checklist_key,
        "grid_file": args.grid,
        "taxa_file": args.taxa,
        "manifest": args.manifest,
        "max_coordinate_uncertainty_m": args.max_coordinate_uncertainty_m,
        "min_year": args.min_year,
        "max_year": args.max_year,
        "allowed_basis_of_record": allowed_basis,
        "min_occurrences": args.min_occurrences,
        "min_unique_cells": args.min_unique_cells,
        "gate_cell_size_degrees": args.gate_cell_size_degrees,
        "spatial_test_fraction": args.spatial_test_fraction,
        "taxon_validation_fraction": args.taxon_validation_fraction,
        "vif_threshold": args.vif_threshold,
        "max_predictors": args.max_predictors,
        "random_baseline_repeats": args.random_baseline_repeats,
        "seed": args.seed,
        "occurrence_sha256": result.occurrence_sha256,
        "occurrence_feature_sha256": result.occurrence_feature_sha256,
    }
    (out / "pilot_grid_specification.json").write_text(
        json.dumps(run_spec, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
