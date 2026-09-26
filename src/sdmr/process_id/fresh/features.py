"""Frozen environmental feature extraction for fresh empirical SDMR."""
from __future__ import annotations

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
    combined = combined.merge(
        unique_locations,
        on=["longitude", "latitude"],
        how="left",
        validate="many_to_one",
    )
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
    combined_ids = pd.concat(
        [
            model_points[["scientific_name", "point_role", "point_id", "longitude", "latitude"]],
            bg_points[["scientific_name", "point_role", "point_id", "longitude", "latitude"]],
        ],
        ignore_index=True,
    ).merge(
        unique_locations,
        on=["longitude", "latitude"],
        how="left",
        validate="many_to_one",
    )
    featured = combined_ids.merge(
        location_features,
        on="location_id",
        how="left",
        validate="many_to_one",
    )
    model_features = featured.loc[featured["point_role"].eq("model_pool")].reset_index(drop=True)
    background_features = featured.loc[featured["point_role"].eq("background_300km")].reset_index(drop=True)
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
