"""Frozen environmental feature extraction for fresh empirical SDMR."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from sdmr.data.chelsa import raster_specs_from_chelsa_manifest
from sdmr.data.raster import RasterLayerSpec, extract_raster_values, probe_raster_layers
from sdmr.process_information_closure import normalize_process_information_registry


PROGRAM = "sdmr-fresh-empirical-feature-extraction-v1"
EXPECTED_SELECTED_SHA256 = "930821c74cc76820907f7c942b98189ddc4f28aca1597198db431ef6eebb40c2"
EXPECTED_MODEL_POOL_SHA256 = "57aed9612e1a5dc69f6d8c6789ef2c55ed6963698f15172e02d8ff3dc89c9137"
EXPECTED_BACKGROUND_SHA256 = "99b7fe02380d5be27fd14eeb821cb24b86d7684e82c705e3ca8781928e454776"
EXPECTED_REGISTRY_SHA256 = "523d18e95b9120eb1670403a60e542017576398f21be423c717f72c5355e2cf6"
EXPECTED_TAXA = 50
EXPECTED_PREDICTORS = 46
EXPECTED_CHELSA = 42
EXPECTED_SOILGRIDS = 4
PRIMARY_M_KM = 300
EXPECTED_PRIMARY_BACKGROUND_ROWS = 250000
EXPECTED_PROCESSES = (
    "thermal",
    "water",
    "seasonality",
    "radiation_energy",
    "soil_substrate",
    "productivity",
)
SOIL_TRANSFORM_SCALE = {
    "divide_by_10": 0.1,
    "divide_by_100": 0.01,
}


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_feature_contract(
    *,
    feature_contract_path: str | Path,
    process_registry_path: str | Path,
    selected_taxa_path: str | Path,
    occurrence_receipt_path: str | Path,
    background_receipt_path: str | Path,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    contract = json.loads(Path(feature_contract_path).read_text(encoding="utf-8"))
    if contract.get("program") != PROGRAM:
        raise ValueError("wrong feature-extraction program")
    if contract.get("status") != "frozen_before_environmental_value_read":
        raise ValueError("feature extraction must be frozen before environmental value read")

    selected = pd.read_csv(selected_taxa_path)
    if _sha256(selected_taxa_path) != EXPECTED_SELECTED_SHA256:
        raise ValueError("selected-taxa fingerprint changed")
    if len(selected) != EXPECTED_TAXA or selected["scientific_name"].astype(str).nunique() != EXPECTED_TAXA:
        raise ValueError("feature extraction requires exactly 50 frozen taxa")

    if _sha256(process_registry_path) != EXPECTED_REGISTRY_SHA256:
        raise ValueError("process registry fingerprint changed")
    registry = pd.read_csv(process_registry_path)
    if len(registry) != EXPECTED_PREDICTORS or registry["predictor"].astype(str).nunique() != EXPECTED_PREDICTORS:
        raise ValueError("feature extraction requires exactly 46 unique predictors")
    normalize_process_information_registry(
        registry[["predictor", "process", "role"]],
        process_universe=EXPECTED_PROCESSES,
        predictor_universe=tuple(registry["predictor"].astype(str)),
    )

    occurrence_receipt = json.loads(Path(occurrence_receipt_path).read_text(encoding="utf-8"))
    if occurrence_receipt.get("all_source_gates_passed") is not True:
        raise ValueError("occurrence source gate is not terminal PASS")
    if occurrence_receipt.get("answer_check_coordinates_persisted_for_M") is not False:
        raise ValueError("answer-check coordinates crossed occurrence boundary")
    if occurrence_receipt.get("files", {}).get("model_pool_occurrences.csv") != "sha256:" + EXPECTED_MODEL_POOL_SHA256:
        raise ValueError("model-pool occurrence artifact changed")

    background_receipt = json.loads(Path(background_receipt_path).read_text(encoding="utf-8"))
    if background_receipt.get("program") != "sdmr-fresh-empirical-background-v1-artifact-receipt":
        raise ValueError("wrong background artifact receipt")
    if background_receipt.get("background_points_sha256") not in (None, EXPECTED_BACKGROUND_SHA256):
        raise ValueError("background artifact fingerprint changed")
    bg_hash = background_receipt.get("files", {}).get("background_points.csv")
    if bg_hash != "sha256:" + EXPECTED_BACKGROUND_SHA256:
        raise ValueError("background-points artifact changed")
    for key in (
        "environmental_values_read",
        "answer_check_coordinates_read",
        "answer_check_features_read",
        "model_fitting_performed",
    ):
        if background_receipt.get(key) is not False:
            raise ValueError(f"background artifact crossed pre-feature boundary: {key}")

    scope = contract.get("extraction_scope", {})
    expected_scope = {
        "model_pool_occurrences": True,
        "primary_300km_background": True,
        "sensitivity_150_500_background": False,
        "answer_check_occurrences": False,
        "answer_check_features": False,
    }
    for key, expected in expected_scope.items():
        if scope.get(key) is not expected:
            raise ValueError(f"feature extraction scope changed for {key}")

    missing = contract.get("missingness", {})
    if missing.get("imputation") != "none":
        raise ValueError("feature imputation rule changed")
    if missing.get("predictor_deletion_after_value_read") is not False:
        raise ValueError("post-value predictor deletion must remain forbidden")
    if missing.get("complete_case_across_all_46") is not True:
        raise ValueError("complete-case rule changed")
    if float(missing.get("minimum_model_pool_retention_fraction", -1)) != 0.80:
        raise ValueError("model-pool retention gate changed")
    if int(missing.get("minimum_model_pool_complete_rows", -1)) != 50:
        raise ValueError("model-pool row gate changed")
    if int(missing.get("minimum_primary_background_complete_rows", -1)) != 4000:
        raise ValueError("background row gate changed")
    if missing.get("taxon_replacement") is not False:
        raise ValueError("taxon replacement became allowed")
    if "whole_50_taxon_program_unavailable" not in str(missing.get("failure_rule", "")):
        raise ValueError("missingness failure rule changed")

    execution = contract.get("execution", {})
    if int(execution.get("raster_layer_parallel_jobs", -1)) != 4:
        raise ValueError("raster layer parallelism changed")
    if execution.get("preflight_probe_required") is not True:
        raise ValueError("raster probe must remain required")
    if execution.get("require_all_46_probe_success") is not True:
        raise ValueError("all 46 layers must probe successfully")
    if execution.get("feature_extraction_allowed_only_after_probe_pass") is not True:
        raise ValueError("feature values cannot open before probe PASS")
    return contract, registry, selected


def build_frozen_layer_specs(
    *,
    process_registry_path: str | Path,
    chelsa_manifest_path: str | Path,
) -> tuple[list[RasterLayerSpec], pd.DataFrame]:
    if _sha256(process_registry_path) != EXPECTED_REGISTRY_SHA256:
        raise ValueError("process registry fingerprint changed")
    registry = pd.read_csv(process_registry_path)
    if len(registry) != EXPECTED_PREDICTORS:
        raise ValueError("process registry denominator changed")

    chelsa_rows = registry.loc[registry["source_family"].astype(str).eq("CHELSA")].copy()
    soil_rows = registry.loc[registry["source_family"].astype(str).eq("SoilGrids")].copy()
    if len(chelsa_rows) != EXPECTED_CHELSA or len(soil_rows) != EXPECTED_SOILGRIDS:
        raise ValueError("CHELSA/SoilGrids predictor denominator changed")

    chelsa_manifest = pd.read_csv(chelsa_manifest_path)
    wanted = tuple(chelsa_rows["predictor"].astype(str))
    manifest_subset = chelsa_manifest.loc[
        chelsa_manifest["predictor"].astype(str).isin(set(wanted))
    ].copy()
    if set(manifest_subset["predictor"].astype(str)) != set(wanted):
        missing = sorted(set(wanted) - set(manifest_subset["predictor"].astype(str)))
        raise ValueError("CHELSA registry predictors missing from resolver manifest: " + ", ".join(missing))
    chelsa_specs, resolved = raster_specs_from_chelsa_manifest(
        manifest_subset,
        include_availability=("current",),
        strict=True,
    )
    by_predictor = {spec.predictor: spec for spec in chelsa_specs}
    if set(by_predictor) != set(wanted):
        raise ValueError("CHELSA resolver did not resolve the exact frozen predictor set")

    soil_specs: dict[str, RasterLayerSpec] = {}
    for row in soil_rows.itertuples(index=False):
        transform = str(row.transform)
        if transform not in SOIL_TRANSFORM_SCALE:
            raise ValueError(f"unsupported frozen SoilGrids transform: {transform}")
        uri = str(row.source_locator).strip()
        if not uri.startswith("https://files.isric.org/soilgrids/latest/data/") or not uri.endswith(".vrt"):
            raise ValueError(f"SoilGrids locator drifted outside frozen WebDAV VRT scope: {uri}")
        soil_specs[str(row.predictor)] = RasterLayerSpec(
            predictor=str(row.predictor),
            uri=uri,
            source="SoilGrids",
            version=str(row.source_version),
            scale=SOIL_TRANSFORM_SCALE[transform],
            offset=0.0,
        )

    specs: list[RasterLayerSpec] = []
    for predictor in registry["predictor"].astype(str):
        if predictor in by_predictor:
            specs.append(by_predictor[predictor])
        elif predictor in soil_specs:
            specs.append(soil_specs[predictor])
        else:
            raise ValueError(f"frozen predictor has no layer spec: {predictor}")
    if len(specs) != EXPECTED_PREDICTORS or len({spec.predictor for spec in specs}) != EXPECTED_PREDICTORS:
        raise AssertionError("frozen feature layer spec denominator changed")
    return specs, resolved


def probe_frozen_layers(
    *,
    process_registry_path: str | Path,
    chelsa_manifest_path: str | Path,
) -> pd.DataFrame:
    specs, _ = build_frozen_layer_specs(
        process_registry_path=process_registry_path,
        chelsa_manifest_path=chelsa_manifest_path,
    )
    probe = probe_raster_layers(specs)
    if len(probe) != EXPECTED_PREDICTORS:
        raise RuntimeError("raster probe denominator changed")
    return probe


def prepare_primary_points(
    *,
    model_pool_path: str | Path,
    background_points_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if _sha256(model_pool_path) != EXPECTED_MODEL_POOL_SHA256:
        raise ValueError("model-pool occurrence artifact fingerprint changed")
    if _sha256(background_points_path) != EXPECTED_BACKGROUND_SHA256:
        raise ValueError("background-points artifact fingerprint changed")

    model = pd.read_csv(model_pool_path)
    required_model = {"scientific_name", "occurrence_id", "longitude", "latitude"}
    missing_model = sorted(required_model - set(model.columns))
    if missing_model:
        raise ValueError(f"model-pool artifact missing columns: {missing_model}")
    if len(model) != 43201:
        raise ValueError("model-pool occurrence denominator changed")
    if model["occurrence_id"].astype(str).duplicated().any():
        raise ValueError("model-pool occurrence identities must be unique")

    background = pd.read_csv(background_points_path)
    required_bg = {
        "scientific_name",
        "m_km",
        "background_rank",
        "gbifid",
        "longitude",
        "latitude",
    }
    missing_bg = sorted(required_bg - set(background.columns))
    if missing_bg:
        raise ValueError(f"background artifact missing columns: {missing_bg}")
    background = background.loc[
        pd.to_numeric(background["m_km"], errors="raise").astype(int).eq(PRIMARY_M_KM)
    ].copy()
    if len(background) != EXPECTED_PRIMARY_BACKGROUND_ROWS:
        raise ValueError("primary 300-km background denominator changed")
    per_taxon = background.groupby(background["scientific_name"].astype(str)).size()
    if len(per_taxon) != EXPECTED_TAXA or not per_taxon.eq(5000).all():
        raise ValueError("primary background is not exactly 5000 rows for each frozen taxon")

    model_points = model[["scientific_name", "occurrence_id", "longitude", "latitude"]].copy()
    model_points.insert(1, "point_role", "model_pool")
    model_points["point_id"] = model_points["occurrence_id"].astype(str)

    bg_points = background[
        ["scientific_name", "background_rank", "gbifid", "longitude", "latitude"]
    ].copy()
    bg_points.insert(1, "point_role", "background_300km")
    bg_points["point_id"] = (
        bg_points["scientific_name"].astype(str)
        + "|bg300|"
        + bg_points["background_rank"].astype(int).astype(str)
    )
    if bg_points["point_id"].duplicated().any():
        raise ValueError("background point identities must be unique")

    combined = pd.concat(
        [
            model_points[["scientific_name", "point_role", "point_id", "longitude", "latitude"]],
            bg_points[["scientific_name", "point_role", "point_id", "longitude", "latitude"]],
        ],
        ignore_index=True,
    )
    lon = pd.to_numeric(combined["longitude"], errors="raise")
    lat = pd.to_numeric(combined["latitude"], errors="raise")
    if not np.isfinite(lon.to_numpy(float)).all() or not np.isfinite(lat.to_numpy(float)).all():
        raise ValueError("feature-extraction coordinates must be finite")
    combined["longitude"] = lon.astype(float)
    combined["latitude"] = lat.astype(float)

    unique_locations = (
        combined[["longitude", "latitude"]]
        .drop_duplicates()
        .sort_values(["longitude", "latitude"], kind="mergesort")
        .reset_index(drop=True)
    )
    unique_locations.insert(0, "location_id", np.arange(len(unique_locations), dtype=np.int64))
    model_points = model_points.merge(
        unique_locations,
        on=["longitude", "latitude"],
        how="left",
        validate="many_to_one",
    )
    bg_points = bg_points.merge(
        unique_locations,
        on=["longitude", "latitude"],
        how="left",
        validate="many_to_one",
    )
    if model_points["location_id"].isna().any() or bg_points["location_id"].isna().any():
        raise RuntimeError("failed to map primary points onto frozen unique-location index")
    model_points["location_id"] = model_points["location_id"].astype("int64")
    bg_points["location_id"] = bg_points["location_id"].astype("int64")
    return model_points, bg_points, unique_locations


def extract_primary_feature_bundle(
    *,
    model_pool_path: str | Path,
    background_points_path: str | Path,
    process_registry_path: str | Path,
    chelsa_manifest_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    model_points, bg_points, unique_locations = prepare_primary_points(
        model_pool_path=model_pool_path,
        background_points_path=background_points_path,
    )
    specs, _ = build_frozen_layer_specs(
        process_registry_path=process_registry_path,
        chelsa_manifest_path=chelsa_manifest_path,
    )
    featured_locations, provenance = extract_raster_values(
        unique_locations,
        specs,
        lon_col="longitude",
        lat_col="latitude",
        checksum_local_files=False,
    )
    predictors = [spec.predictor for spec in specs]
    if tuple(predictors) != tuple(pd.read_csv(process_registry_path)["predictor"].astype(str)):
        raise RuntimeError("feature extraction predictor order changed")

    location_features = featured_locations[["location_id", *predictors]].copy()
    model_features = model_points.merge(
        location_features,
        on="location_id",
        how="left",
        validate="many_to_one",
    ).reset_index(drop=True)
    background_features = bg_points.merge(
        location_features,
        on="location_id",
        how="left",
        validate="many_to_one",
    ).reset_index(drop=True)
    if len(model_features) != 43201 or len(background_features) != EXPECTED_PRIMARY_BACKGROUND_ROWS:
        raise RuntimeError("featured row denominator changed")
    return model_features, background_features, provenance, unique_locations


def evaluate_complete_case_gate(
    *,
    model_features: pd.DataFrame,
    background_features: pd.DataFrame,
    predictors: Sequence[str],
) -> pd.DataFrame:
    predictor_tuple = tuple(str(x) for x in predictors)
    if len(predictor_tuple) != EXPECTED_PREDICTORS or len(set(predictor_tuple)) != EXPECTED_PREDICTORS:
        raise ValueError("complete-case gate requires the exact 46-predictor universe")
    for predictor in predictor_tuple:
        if predictor not in model_features or predictor not in background_features:
            raise KeyError(f"missing featured predictor: {predictor}")

    rows = []
    taxa = sorted(set(model_features["scientific_name"].astype(str)))
    if len(taxa) != EXPECTED_TAXA:
        raise ValueError("model feature taxon denominator changed")
    for taxon in taxa:
        model = model_features.loc[model_features["scientific_name"].astype(str).eq(taxon)]
        bg = background_features.loc[background_features["scientific_name"].astype(str).eq(taxon)]
        model_complete = model.loc[model[list(predictor_tuple)].notna().all(axis=1)]
        bg_complete = bg.loc[bg[list(predictor_tuple)].notna().all(axis=1)]
        retention = len(model_complete) / len(model) if len(model) else 0.0
        passed = (
            retention >= 0.80
            and len(model_complete) >= 50
            and len(bg_complete) >= 4000
        )
        rows.append(
            {
                "scientific_name": taxon,
                "model_pool_rows": int(len(model)),
                "model_pool_complete_rows": int(len(model_complete)),
                "model_pool_retention_fraction": float(retention),
                "background_rows": int(len(bg)),
                "background_complete_rows": int(len(bg_complete)),
                "complete_case_gate_passed": bool(passed),
            }
        )
    return pd.DataFrame(rows)


def _location_index_sha256(unique_locations: pd.DataFrame) -> str:
    required = ["location_id", "longitude", "latitude"]
    if list(unique_locations.columns) != required:
        raise ValueError("unique-location index columns changed")
    canonical = unique_locations.copy()
    canonical["location_id"] = pd.to_numeric(
        canonical["location_id"], errors="raise"
    ).astype("int64")
    payload = canonical.to_csv(
        index=False,
        float_format="%.17g",
        lineterminator="\n",
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def extract_one_predictor(
    *,
    predictor: str,
    model_pool_path: str | Path,
    background_points_path: str | Path,
    process_registry_path: str | Path,
    chelsa_manifest_path: str | Path,
    output_dir: str | Path,
) -> dict:
    predictor = str(predictor).strip()
    if not predictor:
        raise ValueError("predictor must be non-empty")
    _, _, unique_locations = prepare_primary_points(
        model_pool_path=model_pool_path,
        background_points_path=background_points_path,
    )
    specs, _ = build_frozen_layer_specs(
        process_registry_path=process_registry_path,
        chelsa_manifest_path=chelsa_manifest_path,
    )
    by_predictor = {spec.predictor: spec for spec in specs}
    if predictor not in by_predictor:
        raise ValueError(f"predictor is outside the frozen 46-layer universe: {predictor}")
    featured, provenance = extract_raster_values(
        unique_locations,
        [by_predictor[predictor]],
        lon_col="longitude",
        lat_col="latitude",
        checksum_local_files=False,
    )
    if list(provenance["predictor"].astype(str)) != [predictor]:
        raise RuntimeError("single-layer provenance identity changed")

    part = featured[["location_id", predictor]].copy()
    if len(part) != len(unique_locations):
        raise RuntimeError("single-layer feature denominator changed")
    if part["location_id"].duplicated().any():
        raise RuntimeError("single-layer feature location IDs must be unique")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    feature_path = output / "feature.parquet"
    provenance_path = output / "provenance.csv"
    metadata_path = output / "metadata.json"
    part.to_parquet(feature_path, index=False)
    provenance.to_csv(provenance_path, index=False)
    finite = pd.to_numeric(part[predictor], errors="coerce").notna()
    metadata = {
        "program": PROGRAM,
        "predictor": predictor,
        "location_rows": int(len(part)),
        "location_index_sha256": _location_index_sha256(unique_locations),
        "feature_sha256": _sha256(feature_path),
        "provenance_sha256": _sha256(provenance_path),
        "finite_rows": int(finite.sum()),
        "missing_rows": int((~finite).sum()),
        "environmental_values_read": True,
        "answer_check_accessed": False,
        "model_fitting_performed": False,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metadata


def aggregate_feature_parts(
    *,
    parts_root: str | Path,
    model_pool_path: str | Path,
    background_points_path: str | Path,
    process_registry_path: str | Path,
    output_dir: str | Path,
) -> dict:
    registry = pd.read_csv(process_registry_path)
    predictors = tuple(registry["predictor"].astype(str))
    if len(predictors) != EXPECTED_PREDICTORS or len(set(predictors)) != EXPECTED_PREDICTORS:
        raise ValueError("aggregate requires the exact frozen 46-predictor universe")
    model_points, bg_points, unique_locations = prepare_primary_points(
        model_pool_path=model_pool_path,
        background_points_path=background_points_path,
    )
    location_sha = _location_index_sha256(unique_locations)

    root = Path(parts_root)
    metadata_paths = sorted(root.rglob("metadata.json"))
    feature_paths = sorted(root.rglob("feature.parquet"))
    provenance_paths = sorted(root.rglob("provenance.csv"))
    if (
        len(metadata_paths) != EXPECTED_PREDICTORS
        or len(feature_paths) != EXPECTED_PREDICTORS
        or len(provenance_paths) != EXPECTED_PREDICTORS
    ):
        raise RuntimeError(
            "expected exactly 46 feature parts; "
            f"metadata={len(metadata_paths)} features={len(feature_paths)} "
            f"provenance={len(provenance_paths)}"
        )

    metadata = [json.loads(path.read_text(encoding="utf-8")) for path in metadata_paths]
    by_predictor = {str(row["predictor"]): row for row in metadata}
    if set(by_predictor) != set(predictors) or len(by_predictor) != EXPECTED_PREDICTORS:
        raise RuntimeError("feature-part predictor set differs from frozen registry")
    for predictor, row in by_predictor.items():
        if row.get("location_index_sha256") != location_sha:
            raise RuntimeError(f"location-index fingerprint differs for {predictor}")
        if int(row.get("location_rows", -1)) != len(unique_locations):
            raise RuntimeError(f"location denominator differs for {predictor}")
        if row.get("environmental_values_read") is not True:
            raise RuntimeError(f"feature part does not record value extraction for {predictor}")
        if row.get("answer_check_accessed") is not False:
            raise RuntimeError(f"answer-check boundary crossed for {predictor}")
        if row.get("model_fitting_performed") is not False:
            raise RuntimeError(f"model fitting occurred before feature aggregation for {predictor}")

    feature_path_by_predictor: dict[str, Path] = {}
    for path in feature_paths:
        frame = pd.read_parquet(path, columns=["location_id"])
        meta_path = path.with_name("metadata.json")
        if not meta_path.exists():
            raise RuntimeError(f"feature part lacks colocated metadata: {path}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        predictor = str(meta["predictor"])
        if _sha256(path) != str(meta["feature_sha256"]):
            raise RuntimeError(f"feature SHA mismatch for {predictor}")
        feature_path_by_predictor[predictor] = path
    if set(feature_path_by_predictor) != set(predictors):
        raise RuntimeError("could not map exact feature-part files to predictors")

    locations = unique_locations.copy().set_index("location_id")
    missingness_rows: list[dict[str, object]] = []
    for predictor in predictors:
        part = pd.read_parquet(feature_path_by_predictor[predictor])
        if list(part.columns) != ["location_id", predictor]:
            raise RuntimeError(f"feature part columns changed for {predictor}")
        part["location_id"] = pd.to_numeric(
            part["location_id"], errors="raise"
        ).astype("int64")
        if part["location_id"].duplicated().any() or len(part) != len(unique_locations):
            raise RuntimeError(f"feature location denominator changed for {predictor}")
        series = part.set_index("location_id")[predictor].reindex(locations.index)
        locations[predictor] = pd.to_numeric(series, errors="coerce")
        missingness_rows.append(
            {
                "predictor": predictor,
                "unique_location_rows": int(len(series)),
                "finite_rows": int(series.notna().sum()),
                "missing_rows": int(series.isna().sum()),
                "finite_fraction": float(series.notna().mean()),
            }
        )
    locations = locations.reset_index()

    feature_columns = ["location_id", *predictors]
    location_features = locations[feature_columns].copy()
    model_features = model_points.merge(
        location_features,
        on="location_id",
        how="left",
        validate="many_to_one",
    )
    background_features = bg_points.merge(
        location_features,
        on="location_id",
        how="left",
        validate="many_to_one",
    )
    gate = evaluate_complete_case_gate(
        model_features=model_features,
        background_features=background_features,
        predictors=predictors,
    )
    all_passed = bool(gate["complete_case_gate_passed"].all())

    complete_locations = set(
        location_features.loc[
            location_features[list(predictors)].notna().all(axis=1),
            "location_id",
        ].astype(int)
    )
    model_index = model_points.copy()
    model_index["complete_case"] = model_index["location_id"].astype(int).isin(
        complete_locations
    )
    background_index = bg_points.copy()
    background_index["complete_case"] = background_index["location_id"].astype(int).isin(
        complete_locations
    )

    provenance_frames = [pd.read_csv(path) for path in provenance_paths]
    provenance = pd.concat(provenance_frames, ignore_index=True)
    if set(provenance["predictor"].astype(str)) != set(predictors):
        raise RuntimeError("raster provenance predictor set changed")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    location_path = output / "location_features.parquet"
    model_index_path = output / "model_pool_feature_index.csv"
    background_index_path = output / "background_300km_feature_index.csv"
    gate_path = output / "complete_case_gate.csv"
    missingness_path = output / "predictor_missingness.csv"
    provenance_path = output / "raster_provenance.csv"

    location_features.to_parquet(location_path, index=False)
    model_index.to_csv(model_index_path, index=False)
    background_index.to_csv(background_index_path, index=False)
    gate.to_csv(gate_path, index=False)
    pd.DataFrame(missingness_rows).to_csv(missingness_path, index=False)
    provenance.to_csv(provenance_path, index=False)

    min_retention_idx = gate["model_pool_retention_fraction"].astype(float).idxmin()
    min_bg_idx = gate["background_complete_rows"].astype(int).idxmin()
    result = {
        "program": PROGRAM,
        "status": (
            "feature_extraction_complete_case_gate_passed"
            if all_passed
            else "feature_extraction_unavailable_complete_case_gate_failed"
        ),
        "predictor_count": EXPECTED_PREDICTORS,
        "taxon_count": EXPECTED_TAXA,
        "unique_location_rows": int(len(location_features)),
        "model_pool_rows": int(len(model_index)),
        "primary_background_rows": int(len(background_index)),
        "all_taxa_complete_case_gate_passed": all_passed,
        "taxa_passing_complete_case_gate": int(
            gate["complete_case_gate_passed"].sum()
        ),
        "minimum_model_pool_retention_fraction": float(
            gate.loc[min_retention_idx, "model_pool_retention_fraction"]
        ),
        "minimum_model_pool_retention_taxon": str(
            gate.loc[min_retention_idx, "scientific_name"]
        ),
        "minimum_background_complete_rows": int(
            gate.loc[min_bg_idx, "background_complete_rows"]
        ),
        "minimum_background_complete_taxon": str(
            gate.loc[min_bg_idx, "scientific_name"]
        ),
        "location_features_sha256": _sha256(location_path),
        "model_pool_feature_index_sha256": _sha256(model_index_path),
        "background_300km_feature_index_sha256": _sha256(background_index_path),
        "complete_case_gate_sha256": _sha256(gate_path),
        "predictor_missingness_sha256": _sha256(missingness_path),
        "raster_provenance_sha256": _sha256(provenance_path),
        "environmental_values_read": True,
        "answer_check_accessed": False,
        "model_fitting_performed": False,
        "next_gate": (
            "fit_frozen_process_first_and_flat_comparators_on_model_pool_only"
            if all_passed
            else "terminal_unavailable_no_taxon_or_predictor_replacement"
        ),
    }
    result_path = output / "feature_extraction_result.json"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    layer = sub.add_parser("layer")
    layer.add_argument("--predictor", required=True)
    layer.add_argument("--model-pool", required=True)
    layer.add_argument("--background-points", required=True)
    layer.add_argument("--process-registry", required=True)
    layer.add_argument("--chelsa-manifest", required=True)
    layer.add_argument("--output-dir", required=True)

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--parts-root", required=True)
    aggregate.add_argument("--model-pool", required=True)
    aggregate.add_argument("--background-points", required=True)
    aggregate.add_argument("--process-registry", required=True)
    aggregate.add_argument("--output-dir", required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "layer":
        result = extract_one_predictor(
            predictor=args.predictor,
            model_pool_path=args.model_pool,
            background_points_path=args.background_points,
            process_registry_path=args.process_registry,
            chelsa_manifest_path=args.chelsa_manifest,
            output_dir=args.output_dir,
        )
    else:
        result = aggregate_feature_parts(
            parts_root=args.parts_root,
            model_pool_path=args.model_pool,
            background_points_path=args.background_points,
            process_registry_path=args.process_registry,
            output_dir=args.output_dir,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
