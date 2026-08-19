"""Run an auditable real-data Product-A pilot from versioned GBIF downloads."""
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
from .meta import benchmark_method_taxon_split
from .pilot import prepare_product_a_pilot
from .universe import (
    CandidateUniverse,
    benchmark_method_universe_taxon_split,
    candidate_universes_from_manifest,
)


def _read_taxa(path: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "scientific_name" not in frame:
        raise ValueError("Pilot taxa CSV must contain scientific_name")
    return frame


def _filter_manifest(manifest: pd.DataFrame, only: str | None) -> pd.DataFrame:
    if not only:
        return manifest
    wanted = {x.strip() for x in only.split(",") if x.strip()}
    missing = wanted - set(manifest["predictor"].astype(str))
    if missing:
        raise ValueError("Unknown predictors: " + ",".join(sorted(missing)))
    return manifest.loc[manifest["predictor"].astype(str).isin(wanted)].reset_index(drop=True)


def _supports_standard_universes(manifest: pd.DataFrame) -> bool:
    """Return true only when the standard universe labels are semantically real.

    A diagnostic ``--only`` subset must not be called ``bioclim19`` merely
    because it contains some core-climate rows. We require all BIO1--BIO19 and
    at least two genuinely different standard predictor sets; otherwise the
    pilot is treated as one custom candidate universe.
    """
    required = {"predictor", "source", "version", "candidate_class", "process", "mechanism"}
    if not required.issubset(manifest.columns):
        return False
    predictors = set(manifest["predictor"].astype(str))
    required_bioclim = {f"bio{i}" for i in range(1, 20)}
    if not required_bioclim.issubset(predictors):
        return False
    try:
        universes = candidate_universes_from_manifest(manifest)
    except ValueError:
        return False
    fingerprints = {universe.fingerprint for universe in universes.values()}
    return len(fingerprints) >= 2


def _extract_joint_rasters(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    specs,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Extract each raster once for both tables, then restore original row order.

    Remote CHELSA rasters are expensive to open. Concatenating the two point
    tables before calling ``extract_raster_values`` means each layer is opened
    and sampled once instead of once per table. A temporary row-role column is
    removed before returning, so downstream statistical semantics are unchanged.
    """
    marker = "__sdmr_point_role"
    if marker in occurrences.columns or marker in background.columns:
        raise ValueError(f"reserved column already present: {marker}")
    occ = occurrences.copy()
    bg = background.copy()
    occ[marker] = "occurrences"
    bg[marker] = "background"
    combined = pd.concat([occ, bg], ignore_index=True, sort=False)
    enriched, provenance = extract_raster_values(combined, specs)
    occ_out = enriched.loc[enriched[marker].eq("occurrences")].drop(columns=[marker]).reset_index(drop=True)
    bg_out = enriched.loc[enriched[marker].eq("background")].drop(columns=[marker]).reset_index(drop=True)
    provenance = provenance.copy()
    provenance["extraction_mode"] = "joint_occurrence_background"
    provenance["n_occurrence_points"] = len(occurrences)
    provenance["n_background_points"] = len(background)
    return occ_out, bg_out, provenance


def _validation_summary(metrics: pd.DataFrame, *, universe: str, strategy: str) -> pd.DataFrame:
    if not len(metrics):
        return pd.DataFrame()
    return pd.DataFrame([{
        "universe": universe,
        "strategy": strategy,
        "n_species": int(metrics["species"].nunique()),
        "mean_presence_rank": float(metrics["presence_rank"].mean()),
        "median_presence_rank": float(metrics["presence_rank"].median()),
        "mean_predictors": float(metrics["n_predictors"].mean()),
    }])


def _write_method_outputs(result, out: Path, *, args, predictors: list[str]) -> None:
    result.discovery_metrics.to_csv(out / "method_discovery_metrics.csv", index=False)
    result.discovery_summary.to_csv(out / "method_discovery_summary.csv", index=False)
    result.validation_metrics.to_csv(out / "method_validation_metrics.csv", index=False)

    if hasattr(result, "winning_universe"):
        winning_predictors = list(result.winning_predictors)
        winning_universe = str(result.winning_universe)
        universe_sha = str(result.winning_universe_sha256)
        _validation_summary(
            result.validation_metrics,
            universe=winning_universe,
            strategy=result.winning_strategy,
        ).to_csv(out / "method_validation_summary.csv", index=False)
    else:
        winning_predictors = list(predictors)
        winning_universe = "custom"
        universe_sha = CandidateUniverse("custom", tuple(winning_predictors)).fingerprint
        result.validation_summary.to_csv(out / "method_validation_summary.csv", index=False)

    (out / "method_choice.txt").write_text(
        "winning_strategy=" + result.winning_strategy + "\n"
        + "winning_universe=" + winning_universe + "\n"
        + "winning_universe_sha256=" + universe_sha + "\n"
        + "winning_predictors=" + ",".join(winning_predictors) + "\n"
        + f"n_winning_predictors={len(winning_predictors)}\n"
        + "discovery_species=" + ",".join(result.discovery_species) + "\n"
        + "validation_species=" + ",".join(result.validation_species) + "\n"
        + f"spatial_test_fraction={args.spatial_test_fraction}\n"
        + f"taxon_validation_fraction={args.taxon_validation_fraction}\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare and optionally run a real Product-A pilot from a versioned GBIF bulk download. "
            "The GBIF search API is intentionally not used for method comparison."
        )
    )
    parser.add_argument("--gbif-download", required=True, help="Versioned GBIF occurrence download ZIP/CSV/TSV/Parquet")
    parser.add_argument("--gbif-download-key", required=True, help="GBIF download key/DOI identifier retained in provenance")
    parser.add_argument("--checklist-key", default=GBIF_COL_XR_CHECKLIST_KEY)
    parser.add_argument("--taxa", required=True, help="Predeclared pilot taxa CSV with scientific_name and optional taxon_key")
    parser.add_argument("--target-group-download", help="Broader plant GBIF download used only to represent sampling effort")
    parser.add_argument("--target-group-download-key", default="")
    parser.add_argument(
        "--allow-pilot-target-group",
        action="store_true",
        help="Diagnostic only: allow target-group background to be constructed from the focal pilot taxa themselves.",
    )
    parser.add_argument("--output-dir", required=True)

    parser.add_argument("--max-coordinate-uncertainty-m", type=float)
    parser.add_argument("--min-year", type=int)
    parser.add_argument("--max-year", type=int)
    parser.add_argument("--allowed-basis-of-record", help="Comma-separated GBIF basisOfRecord values")
    parser.add_argument("--min-occurrences", type=int, required=True)
    parser.add_argument("--min-unique-cells", type=int, required=True)
    parser.add_argument("--gate-cell-size-degrees", type=float, default=1 / 120)

    parser.add_argument("--m-strategy", choices=("bbox", "buffer"), required=True)
    parser.add_argument("--bbox-buffer-degrees", type=float, default=2.0)
    parser.add_argument("--occurrence-buffer-km", type=float, default=300.0)
    parser.add_argument("--background-points", type=int, default=5000)
    parser.add_argument("--background-cell-size-degrees", type=float, default=1 / 120)

    parser.add_argument("--extract-chelsa", action="store_true")
    parser.add_argument("--manifest", default="configs/chelsa_v2_1_plant_candidates.csv")
    parser.add_argument("--chelsa-base-url")
    parser.add_argument("--only", help="Comma-separated CHELSA predictors for a smaller diagnostic pilot")
    parser.add_argument("--include-legacy-chelsa", action="store_true")

    parser.add_argument("--run-method", action="store_true", help="Run Product A after raster extraction")
    parser.add_argument("--spatial-test-fraction", type=float, default=0.20)
    parser.add_argument("--taxon-validation-fraction", type=float, default=0.20)
    parser.add_argument("--vif-threshold", type=float, default=5.0)
    parser.add_argument("--max-predictors", type=int, default=8)
    parser.add_argument("--random-baseline-repeats", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    if args.run_method and not args.extract_chelsa:
        parser.error("--run-method requires --extract-chelsa")
    if args.run_method and not args.target_group_download and not args.allow_pilot_target_group:
        parser.error(
            "Product-A method comparison requires --target-group-download; "
            "use --allow-pilot-target-group only for an explicitly diagnostic sensitivity run."
        )
    if args.target_group_download and not args.target_group_download_key:
        parser.error("--target-group-download requires --target-group-download-key")
    if not 0 < args.spatial_test_fraction < 1 or not 0 < args.taxon_validation_fraction < 1:
        parser.error("test fractions must be between 0 and 1")

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    taxa = _read_taxa(args.taxa)
    focal_download = load_gbif_download(
        args.gbif_download,
        download_key=args.gbif_download_key,
        checklist_key=args.checklist_key,
    )
    target_download = None
    if args.target_group_download:
        target_download = load_gbif_download(
            args.target_group_download,
            download_key=args.target_group_download_key,
            checklist_key=args.checklist_key,
        )

    allowed_basis = None
    if args.allowed_basis_of_record:
        allowed_basis = tuple(x.strip() for x in args.allowed_basis_of_record.split(",") if x.strip())
    admission_config = OccurrenceAdmissionConfig(
        max_coordinate_uncertainty_m=args.max_coordinate_uncertainty_m,
        min_year=args.min_year,
        max_year=args.max_year,
        allowed_basis_of_record=allowed_basis,
    )
    prepared = prepare_product_a_pilot(
        focal_download.records,
        taxa,
        admission_config=admission_config,
        min_occurrences=args.min_occurrences,
        min_unique_cells=args.min_unique_cells,
        gate_cell_size_degrees=args.gate_cell_size_degrees,
        m_strategy=args.m_strategy,
        target_group_pool=None if target_download is None else target_download.records,
        bbox_buffer_degrees=args.bbox_buffer_degrees,
        occurrence_buffer_km=args.occurrence_buffer_km,
        background_points=args.background_points,
        background_cell_size_degrees=args.background_cell_size_degrees,
        random_state=args.seed,
    )

    prepared.occurrences.to_csv(out / "pilot_occurrences_pre_raster.csv", index=False)
    prepared.background.to_csv(out / "pilot_background_pre_raster.csv", index=False)
    prepared.taxon_selection_ledger.to_csv(out / "taxon_selection_ledger.csv", index=False)
    prepared.occurrence_admission_ledger.to_csv(out / "occurrence_admission_ledger.csv", index=False)
    prepared.species_gate.to_csv(out / "species_gate.csv", index=False)
    prepared.background_ledger.to_csv(out / "background_ledger.csv", index=False)
    focal_download.provenance.to_csv(out / "gbif_focal_provenance.csv", index=False)
    if target_download is not None:
        target_download.provenance.to_csv(out / "gbif_target_group_provenance.csv", index=False)

    predictors: list[str] = []
    resolved_manifest: pd.DataFrame | None = None
    occurrences = prepared.occurrences
    background = prepared.background
    if args.extract_chelsa:
        manifest = _filter_manifest(pd.read_csv(args.manifest), args.only)
        availability = ("current", "legacy_archive") if args.include_legacy_chelsa else ("current",)
        kwargs = {"include_availability": availability, "strict": False}
        if args.chelsa_base_url:
            kwargs["base_url"] = args.chelsa_base_url
        specs, resolution = raster_specs_from_chelsa_manifest(manifest, **kwargs)
        if not specs:
            parser.error("No CHELSA predictors resolved for extraction")
        predictors = [spec.predictor for spec in specs]
        resolved_manifest = manifest.loc[manifest["predictor"].astype(str).isin(predictors)].reset_index(drop=True)
        resolution.to_csv(out / "chelsa_resolution_ledger.csv", index=False)
        occurrences, background, raster_provenance = _extract_joint_rasters(occurrences, background, specs)
        occurrences.to_csv(out / "pilot_occurrences.csv", index=False)
        background.to_csv(out / "pilot_background.csv", index=False)
        raster_provenance.assign(table="joint_occurrence_background").to_csv(
            out / "raster_provenance_joint.csv", index=False
        )
        # Compatibility ledgers retain the historical filenames while making it
        # explicit that both point tables were sampled in one raster-open pass.
        raster_provenance.assign(table="occurrences", shared_open=True).to_csv(
            out / "raster_provenance_occurrences.csv", index=False
        )
        raster_provenance.assign(table="background", shared_open=True).to_csv(
            out / "raster_provenance_background.csv", index=False
        )

    specification = {
        "gbif_download_key": args.gbif_download_key,
        "target_group_download_key": args.target_group_download_key,
        "checklist_key": args.checklist_key,
        "taxa_file": args.taxa,
        "max_coordinate_uncertainty_m": args.max_coordinate_uncertainty_m,
        "min_year": args.min_year,
        "max_year": args.max_year,
        "allowed_basis_of_record": allowed_basis,
        "min_occurrences": args.min_occurrences,
        "min_unique_cells": args.min_unique_cells,
        "gate_cell_size_degrees": args.gate_cell_size_degrees,
        "m_strategy": args.m_strategy,
        "bbox_buffer_degrees": args.bbox_buffer_degrees,
        "occurrence_buffer_km": args.occurrence_buffer_km,
        "background_points": args.background_points,
        "background_cell_size_degrees": args.background_cell_size_degrees,
        "allow_pilot_target_group": args.allow_pilot_target_group,
        "extract_chelsa": args.extract_chelsa,
        "raster_extraction_mode": "joint_occurrence_background" if args.extract_chelsa else None,
        "predictors": predictors,
        "candidate_universe_tuning": bool(resolved_manifest is not None and _supports_standard_universes(resolved_manifest)),
        "run_method": args.run_method,
        "spatial_test_fraction": args.spatial_test_fraction,
        "taxon_validation_fraction": args.taxon_validation_fraction,
        "seed": args.seed,
    }
    (out / "pilot_specification.json").write_text(json.dumps(specification, indent=2, sort_keys=True), encoding="utf-8")

    if args.run_method:
        species = sorted(set(occurrences["species"].astype(str)) & set(background["species"].astype(str)))
        if len(species) < 4:
            parser.error(f"At least four eligible species with background are required; found {len(species)}")

        if resolved_manifest is not None and _supports_standard_universes(resolved_manifest):
            universes = candidate_universes_from_manifest(resolved_manifest)
            result = benchmark_method_universe_taxon_split(
                occurrences,
                background,
                universes,
                taxon_validation_fraction=args.taxon_validation_fraction,
                sealed_fraction=args.spatial_test_fraction,
                vif_threshold=args.vif_threshold,
                max_predictors=args.max_predictors,
                random_repeats=args.random_baseline_repeats,
                compute_drop_one=False,
                random_state=args.seed,
            )
        else:
            result = benchmark_method_taxon_split(
                occurrences,
                background,
                predictors,
                taxon_validation_fraction=args.taxon_validation_fraction,
                sealed_fraction=args.spatial_test_fraction,
                vif_threshold=args.vif_threshold,
                max_predictors=args.max_predictors,
                random_repeats=args.random_baseline_repeats,
                compute_drop_one=False,
                random_state=args.seed,
            )
        _write_method_outputs(result, out, args=args, predictors=predictors)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
