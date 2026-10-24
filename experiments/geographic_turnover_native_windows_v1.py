"""Read-only real-source preflight for invariant-niche geographic driver turnover.

The units here are exogenously fixed *rectangles*, not taxon-specific accessible
M. Report native-country membership only; planted occurrences are not screened.
This script is a strict data-source gate and never estimates process turnover.

Uses pinned native-range URLs, versioned climate metadata and full (not capped)
GBIF search results ONLY when the requested geographical source window is below
the configured extraction limit. A truncated Search API sample is never admitted.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.data.gbif import GBIF_COL_XR_CHECKLIST_KEY, fetch_occurrence_search, match_taxon
from sdmr.data.chelsa import build_chelsa_cog_uri
from sdmr.data.raster import RasterLayerSpec, extract_raster_values


def validate_config(config: dict) -> None:
    if config.get("study_status") != "source_and_geometry_diagnostic_only":
        raise ValueError("Only diagnostic study status authorized")
    if config.get("source_checklist_key") != GBIF_COL_XR_CHECKLIST_KEY:
        raise ValueError("Taxon checklist differs from SDMR CoL XR match/search")
    if config.get("gbif_years") != "2010,2025":
        raise ValueError("Year window must be fixed before record opening")
    if config.get("raster_axes") != {"temperature": "bio1", "moisture": "bio12"}:
        raise ValueError("Unfrozen or ambiguous climate axes")
    if float(config.get("cell_side_km", 0)) <= 0 or config.get("max_api_total_per_taxon_window", 0) < 1:
        raise ValueError("Invalid grid side or API cap")
    names = list(config.get("target_group_names") or [])
    if not names or len(names) != len(set(names)):
        raise ValueError("Unique nonempty independent target-group species are required")
    windows = config.get("windows") or []
    if not windows:
        raise ValueError("No declared native comparison windows")
    keys = set()
    for w in windows:
        if w["region"] in keys:
            raise ValueError("Duplicated window/region")
        keys.add(w["region"])
        if w["focal_taxon"] in names:
            raise ValueError("Focal taxon cannot be an observation-effort target-group species")
        if not ("powo.science.kew.org" in w["native_range_reference"] and len(w["country"]) == 2):
            raise ValueError("Missing explicit native-range provenance/country")
        if not (-180 <= w["west"] < w["east"] <= 180 and -85 <= w["south"] < w["north"] <= 85):
            raise ValueError("Invalid WGS84 window; antimeridian crossing not implemented")


def _geometry(w: dict) -> str:
    west, south, east, north = (float(w[k]) for k in ("west", "south", "east", "north"))
    return (f"POLYGON (({west} {south}, {east} {south}, {east} {north}, "
            f"{west} {north}, {west} {south}))")


def equal_area_grid(w: dict, cell_side_km: float) -> pd.DataFrame:
    """Cell centres in cylindrical equal-area EPSG:6933; fixed pre-occurrence."""
    from pyproj import Transformer
    step = float(cell_side_km) * 1000.0
    fwd = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
    inv = Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True)
    # Dense perimeter avoids relying on a corner-only projected bbox.
    nedge = 51
    xs = np.linspace(w["west"], w["east"], nedge)
    ys = np.linspace(w["south"], w["north"], nedge)
    perimeter_lon = np.r_[xs, xs, np.full(nedge, w["west"]), np.full(nedge, w["east"])]
    perimeter_lat = np.r_[np.full(nedge, w["south"]), np.full(nedge, w["north"]), ys, ys]
    xx, yy = fwd.transform(perimeter_lon, perimeter_lat)
    # Cells with centres inside the fixed polygon only; no outcome-derived M.
    east_min, east_max = np.floor(min(xx) / step), np.ceil(max(xx) / step)
    north_min, north_max = np.floor(min(yy) / step), np.ceil(max(yy) / step)
    ix = np.arange(east_min, east_max, dtype=np.int64)
    iy = np.arange(north_min, north_max, dtype=np.int64)
    gx, gy = np.meshgrid(ix, iy)
    eastings = (gx.flatten() + 0.5) * step
    northings = (gy.flatten() + 0.5) * step
    lon, lat = inv.transform(eastings, northings)
    keep = ((lon >= w["west"]) & (lon < w["east"]) &
            (lat >= w["south"]) & (lat < w["north"]))
    grid = pd.DataFrame({
        "region": str(w["region"]), "cell_x": gx.flatten()[keep],
        "cell_y": gy.flatten()[keep], "longitude": np.asarray(lon)[keep],
        "latitude": np.asarray(lat)[keep],
    })
    grid["cell_id"] = grid.cell_x.astype(str) + ":" + grid.cell_y.astype(str)
    # Equal area, exogenous spatial checkerboard quadrants (not random points).
    mx = float(np.median(grid.cell_x)); my = float(np.median(grid.cell_y))
    grid["spatial_block"] = ((grid.cell_x > mx).astype(int) * 2 + (grid.cell_y > my).astype(int)).astype(str)
    return grid.sort_values("cell_id", kind="mergesort").reset_index(drop=True)


def _coord_to_cell(records: pd.DataFrame, window: dict, cell_side_km: float) -> pd.Series:
    """Reproduce equal-area cell IDs from independent raw point coordinates."""
    from pyproj import Transformer
    fwd = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
    x, y = fwd.transform(records.longitude.to_numpy(float), records.latitude.to_numpy(float))
    ix = np.floor(np.asarray(x) / (1000 * cell_side_km)).astype(np.int64)
    iy = np.floor(np.asarray(y) / (1000 * cell_side_km)).astype(np.int64)
    return pd.Series(ix.astype(str) + ":" + iy.astype(str), index=records.index)


def clean_gbif_records(records: pd.DataFrame, config: dict, *, focal_name: str) -> tuple[pd.DataFrame, dict]:
    """Row-level QC. Missing coordinate uncertainty remains excluded, not 0m."""
    reasons = Counter()
    out = []
    allowed = set(config["allowed_basis_of_record"])
    max_unc = config["strict_reported_coordinate_uncertainty_m"]
    seen_ids = set()
    for row in records.to_dict("records"):
        key = str(row.get("gbifID") or "")
        if not key or key in seen_ids:
            reasons["missing_or_duplicate_gbif_id"] += 1; continue
        seen_ids.add(key)
        name = str(row.get("species") or "")
        if name != focal_name and name.split(" ")[0:2] != focal_name.split(" ")[0:2]:
            reasons["taxon_name_mismatch"] += 1; continue
        if str(row.get("basisOfRecord") or "") not in allowed:
            reasons["disallowed_basis_of_record"] += 1; continue
        try:
            lon, lat = float(row["longitude"]), float(row["latitude"])
            if pd.isna(row.get("coordinateUncertaintyInMeters")):
                raise ValueError("unreported coordinate uncertainty")
            uncertainty = float(row["coordinateUncertaintyInMeters"])
        except (ValueError, TypeError, KeyError):
            reasons["missing_coordinates_or_reported_uncertainty"] += 1; continue
        if not (np.isfinite(lon) and np.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
            reasons["invalid_coordinates"] += 1; continue
        if not np.isfinite(uncertainty) or uncertainty < 0 or uncertainty > max_unc:
            reasons["coordinate_uncertainty_out_of_scope"] += 1; continue
        # No evidence of provenance-level planted/wild origin; do not infer.
        out.append({"gbifID": key, "longitude": lon, "latitude": lat})
    return pd.DataFrame(out, columns=["gbifID", "longitude", "latitude"]), {
        "n_raw": int(len(records)), "n_accepted": int(len(out)), "rejection_reasons": dict(sorted(reasons.items())),
    }


def _search_once(*, query_name: str, window: dict, config: dict,
                 matcher, fetcher) -> tuple[pd.DataFrame | None, dict]:
    entry = {"region": window["region"], "country": window["country"], "requested_taxon": query_name}
    try:
        taxon = matcher(query_name, checklist_key=config["source_checklist_key"])
        entry.update({"accepted_name": taxon.canonical_name, "taxon_key": taxon.taxon_key,
                      "taxon_status": taxon.status, "checklist_key": taxon.checklist_key})
        kwargs = {"country": window["country"], "year": config["gbif_years"], "geometry": _geometry(window)}
        count = fetcher(taxon.taxon_key, checklist_key=config["source_checklist_key"], max_records=1,
                        extra_params=kwargs)
        entry.update({"indexed_count": int(count.total_count), "count_query_sha256": count.query_sha256})
        if count.total_count > config["max_api_total_per_taxon_window"]:
            entry["status"] = "bulk_required_count_over_diagnostic_cap"
            return None, entry
        if count.total_count == 0:
            entry["status"] = "no_search_records"
            return None, entry
        full = fetcher(taxon.taxon_key, checklist_key=config["source_checklist_key"],
                       max_records=None, extra_params=kwargs)
        entry.update({"n_retrieved": int(full.retrieved_count), "full_query_sha256": full.query_sha256,
                      "search_truncated": bool(full.truncated)})
        if full.truncated or int(full.total_count) != int(full.retrieved_count):
            entry["status"] = "incomplete_search_archive"
            return None, entry
        clean, qc = clean_gbif_records(full.records, config, focal_name=taxon.canonical_name)
        entry["qc"] = qc
        entry["status"] = "complete_diagnostic_search_archive"
        return clean, entry
    except Exception as e:
        entry.update({"status": "unavailable", "error": f"{type(e).__name__}: {e}"})
        return None, entry


def assemble(config: dict, *, matcher=match_taxon, fetcher=fetch_occurrence_search,
             raster_extractor=extract_raster_values, counts_only=False) -> tuple[dict, pd.DataFrame]:
    """Per-window search integrity and CHELSA land-cell availability, no modelling."""
    validate_config(config)
    rows = []
    grid_rows = []
    for w in config["windows"]:
        grid = equal_area_grid(w, config["cell_side_km"])
        window_summary = {
            "region": w["region"], "country": w["country"], "focal_taxon": w["focal_taxon"],
            "native_country_reference": w["native_range_reference"],
            "n_equal_area_rectangle_cells": len(grid), "grid_cell_km": config["cell_side_km"],
            "status": "source_diagnostic_only", "environmental_source_status": "not_checked",
            "target_group_effort_status": "not_identified",
        }
        try:
            if not counts_only:
                layers = [RasterLayerSpec(predictor=axis, uri=build_chelsa_cog_uri(remote_name=name, retrieval="annual_bio_cog"),
                                          source="CHELSA-bioclim", version="2.1")
                          for axis, name in config["raster_axes"].items()]
                sampled, provenance = raster_extractor(grid, layers, lon_col="longitude", lat_col="latitude")
                ok = np.isfinite(sampled[["temperature", "moisture"]].to_numpy(float)).all(axis=1)
                window_summary["n_climate_complete_cells"] = int(ok.sum())
                window_summary["climate_provenance"] = provenance.to_dict("records")
                window_summary["environmental_source_status"] = "climate_complete" if ok.sum() > 0 else "climate_no_complete_cells"
                # Native rectangular available-climate window, NOT calibrated taxon M.
                if ok.any():
                    climate = sampled.loc[ok, ["cell_id", "temperature", "moisture", "spatial_block"]].copy()
                    window_summary["climate_temperature_percentiles_raw"] = np.percentile(climate.temperature, [5, 50, 95]).tolist()
                    window_summary["climate_moisture_percentiles_raw"] = np.percentile(climate.moisture, [5, 50, 95]).tolist()
                    for key, val in zip(("p05", "p50", "p95"), window_summary["climate_temperature_percentiles_raw"]):
                        window_summary["temperature_"+key+"_raw"] = float(val)
                    for key, val in zip(("p05", "p50", "p95"), window_summary["climate_moisture_percentiles_raw"]):
                        window_summary["moisture_"+key+"_raw"] = float(val)
                    grid_rows.append(sampled.loc[ok, ["region", "cell_id", "spatial_block", "longitude", "latitude", "temperature", "moisture"]].copy())
        except Exception as e:
            window_summary["environmental_source_status"] = "climate_unavailable"
            window_summary["climate_error"] = f"{type(e).__name__}: {e}"
        focal, entry = _search_once(query_name=w["focal_taxon"], window=w, config=config, matcher=matcher, fetcher=fetcher)
        window_summary["focal_source"] = entry
        # Source support is computed only against the exogenous climate grid.
        # No response-conditioned grid or zero-imputed effort is produced.
        if grid_rows and grid_rows[-1].region.iloc[0] == w["region"]:
            clipped = grid_rows[-1]
            allowed_cells = set(clipped.cell_id)
            if focal is not None:
                counts = _coord_to_cell(focal, w, config["cell_side_km"]).value_counts()
                clipped["n_focal_records_diagnostic"] = clipped.cell_id.map(counts).fillna(0).astype(int)
                window_summary["n_admitted_focal_records_in_climate_cells"] = int(clipped.n_focal_records_diagnostic.sum())
                window_summary["n_climate_cells_with_focal_records"] = int((clipped.n_focal_records_diagnostic > 0).sum())
                window_summary["n_admitted_focal_records_outside_grid"] = int(len(focal) - clipped.n_focal_records_diagnostic.sum())
                window_summary["focal_climate_cell_coverage_fraction"] = float((clipped.n_focal_records_diagnostic > 0).mean())
        # No sentinel names may include a focal taxon, but sentinel source
        # archives can still be unavailable / spatially nonuniform.
        sentinels = []
        if not counts_only:
            all_sentinel_counts = Counter()
            all_sentinel_complete = True
            for target in config["target_group_names"]:
                clean, record = _search_once(query_name=target, window=w, config=config, matcher=matcher, fetcher=fetcher)
                sentinels.append(record)
                if clean is None:
                    all_sentinel_complete = False
                elif grid_rows and grid_rows[-1].region.iloc[0] == w["region"]:
                    all_sentinel_counts.update(_coord_to_cell(clean, w, config["cell_side_km"]).tolist())
            window_summary["target_group_sources"] = sentinels
            window_summary["target_group_all_archives_complete"] = all_sentinel_complete
            if all_sentinel_complete and grid_rows and grid_rows[-1].region.iloc[0] == w["region"]:
                clipped = grid_rows[-1]
                clipped["n_independent_target_group_records_diagnostic"] = clipped.cell_id.map(all_sentinel_counts).fillna(0).astype(int)
                supported = clipped.n_independent_target_group_records_diagnostic > 0
                window_summary["n_climate_cells_with_target_group_records"] = int(supported.sum())
                window_summary["target_group_effort_cell_coverage_fraction"] = float(supported.mean())
                window_summary["target_group_effort_status"] = "candidate_proxy_only_not_calibrated"
            else:
                window_summary["target_group_effort_status"] = "incomplete_source_or_climate"
        window_summary["macro_inference_allowed"] = False
        window_summary["why_macro_blocked"] = [
            "rectangles_not_species_accessible_area_M", "nonindependent_and_uncalibrated_effort",
            "planted_or_introduced_individuals_not_record-level_excluded", "spatial_block_and_effect_size_calibration_not_frozen",
            "source_diagnostic_only_no_predeclared_real_effect_test",
        ]
        rows.append(window_summary)
    receipt = {
        "analysis": "geographic_turnover_native_window_source_diagnostic_v1",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),
        "window_count": len(rows),
        "windows": rows,
        "n_climate_complete_windows": sum(x["environmental_source_status"] == "climate_complete" for x in rows),
        "n_focal_search_archives_complete": sum(x["focal_source"]["status"] == "complete_diagnostic_search_archive" for x in rows),
        "macro_inference_blocked": True,
        "positive_biological_evidence": False,
        "claim_ceiling": "Observed source support/environmental availability only; no response or niche-shift estimate",
    }
    return receipt, pd.concat(grid_rows, ignore_index=True) if grid_rows else pd.DataFrame()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=Path("configs/geographic_turnover_native_windows_v1.json"))
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--counts-only", action="store_true")
    args = ap.parse_args()
    raw = args.config.read_bytes()
    config = json.loads(raw)
    receipt, grid = assemble(config, counts_only=args.counts_only)
    receipt["config_file_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "source_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    if not grid.empty:
        grid.to_csv(args.output_dir / "available_climate_cells.csv", index=False)
    print(f"climate_complete_windows={receipt['n_climate_complete_windows']}/{receipt['window_count']} "
          f"complete_search_archives={receipt['n_focal_search_archives_complete']}/{receipt['window_count']} "
          f"macro_inference_blocked={receipt['macro_inference_blocked']}")

if __name__ == "__main__":
    main()
