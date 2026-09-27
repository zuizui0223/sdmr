"""Spatial-shard recovery for the four frozen SoilGrids layers.

The original one-job-per-layer extraction opened the correct frozen WebDAV VRTs
but timed out after 90 minutes because 249,919 globally distributed locations
were sampled through one remote VRT handle.  This recovery changes execution
geometry only: the exact frozen locations, layer URIs, transforms, and pixel
sampling semantics remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.data.raster import extract_raster_values
from sdmr.process_id.fresh.features import (
    EXPECTED_BACKGROUND_SHA256,
    EXPECTED_MODEL_POOL_SHA256,
    _location_index_sha256,
    _sha256,
    build_frozen_layer_specs,
    prepare_primary_points,
)

PROGRAM = "sdmr-fresh-empirical-soil-recovery-v1"
SOIL_PREDICTORS = (
    "sg_phh2o_0_5",
    "sg_clay_0_5",
    "sg_soc_0_5",
    "sg_nitrogen_0_5",
)
SOIL_SHARD_COUNT = 16
EXPECTED_LOCATION_ROWS = 249_919
EXPECTED_LOCATION_INDEX_SHA256 = (
    "ed25443651c3c9717ac83847de8e257be4947cfe8a84974d6fede9a30e869bed"
)


def spatial_shard_bounds(n_rows: int, shard_index: int, shard_count: int) -> tuple[int, int]:
    if isinstance(n_rows, bool) or not isinstance(n_rows, int) or n_rows < 1:
        raise ValueError("n_rows must be a positive integer")
    if isinstance(shard_count, bool) or not isinstance(shard_count, int) or shard_count < 1:
        raise ValueError("shard_count must be a positive integer")
    if isinstance(shard_index, bool) or not isinstance(shard_index, int):
        raise ValueError("shard_index must be an integer")
    if not 0 <= shard_index < shard_count:
        raise ValueError("shard_index must satisfy 0 <= shard_index < shard_count")
    start = (n_rows * shard_index) // shard_count
    stop = (n_rows * (shard_index + 1)) // shard_count
    if stop <= start:
        raise ValueError("spatial shard is empty")
    return start, stop


def _load_primary_locations(
    *,
    model_pool_path: str | Path,
    background_points_path: str | Path,
) -> pd.DataFrame:
    if _sha256(model_pool_path) != EXPECTED_MODEL_POOL_SHA256:
        raise ValueError("model-pool occurrence artifact fingerprint changed")
    if _sha256(background_points_path) != EXPECTED_BACKGROUND_SHA256:
        raise ValueError("background-points artifact fingerprint changed")
    _, _, locations = prepare_primary_points(
        model_pool_path=model_pool_path,
        background_points_path=background_points_path,
    )
    if len(locations) != EXPECTED_LOCATION_ROWS:
        raise ValueError(
            f"frozen unique-location denominator changed: {len(locations)} != "
            f"{EXPECTED_LOCATION_ROWS}"
        )
    observed = _location_index_sha256(locations)
    if observed != EXPECTED_LOCATION_INDEX_SHA256:
        raise ValueError(
            "frozen unique-location fingerprint changed: "
            f"{observed} != {EXPECTED_LOCATION_INDEX_SHA256}"
        )
    return locations


def extract_soil_shard(
    *,
    predictor: str,
    shard_index: int,
    shard_count: int,
    model_pool_path: str | Path,
    background_points_path: str | Path,
    process_registry_path: str | Path,
    chelsa_manifest_path: str | Path,
    output_dir: str | Path,
) -> dict:
    predictor = str(predictor).strip()
    if predictor not in SOIL_PREDICTORS:
        raise ValueError(f"predictor is not one of the four frozen SoilGrids layers: {predictor}")
    if int(shard_count) != SOIL_SHARD_COUNT:
        raise ValueError(f"SoilGrids recovery shard_count must remain {SOIL_SHARD_COUNT}")

    locations = _load_primary_locations(
        model_pool_path=model_pool_path,
        background_points_path=background_points_path,
    )
    start, stop = spatial_shard_bounds(len(locations), int(shard_index), int(shard_count))
    # prepare_primary_points already sorts exact unique locations by longitude,
    # latitude before assigning location_id, so contiguous ranges are spatially
    # coherent longitude-first shards.
    shard = locations.iloc[start:stop].copy().reset_index(drop=True)

    specs, _ = build_frozen_layer_specs(
        process_registry_path=process_registry_path,
        chelsa_manifest_path=chelsa_manifest_path,
    )
    by_predictor = {spec.predictor: spec for spec in specs}
    spec = by_predictor[predictor]
    if spec.source != "SoilGrids":
        raise ValueError(f"recovery predictor is not SoilGrids: {predictor}")

    featured, provenance = extract_raster_values(
        shard,
        [spec],
        lon_col="longitude",
        lat_col="latitude",
        checksum_local_files=False,
    )
    part = featured[["location_id", predictor]].copy()
    expected_ids = locations.iloc[start:stop]["location_id"].astype("int64").tolist()
    observed_ids = part["location_id"].astype("int64").tolist()
    if observed_ids != expected_ids:
        raise RuntimeError(f"SoilGrids shard location order changed for {predictor}/{shard_index}")

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
        "shard_index": int(shard_index),
        "shard_count": int(shard_count),
        "start_row": int(start),
        "stop_row": int(stop),
        "shard_rows": int(len(part)),
        "full_location_rows": EXPECTED_LOCATION_ROWS,
        "location_index_sha256": EXPECTED_LOCATION_INDEX_SHA256,
        "feature_sha256": _sha256(feature_path),
        "provenance_sha256": _sha256(provenance_path),
        "finite_rows": int(finite.sum()),
        "missing_rows": int((~finite).sum()),
        "environmental_values_read": True,
        "answer_check_accessed": False,
        "model_fitting_performed": False,
        "execution_change_only": True,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metadata


def assemble_soil_shards(
    *,
    parts_root: str | Path,
    model_pool_path: str | Path,
    background_points_path: str | Path,
    output_dir: str | Path,
    shard_count: int = SOIL_SHARD_COUNT,
) -> dict:
    if int(shard_count) != SOIL_SHARD_COUNT:
        raise ValueError(f"SoilGrids recovery shard_count must remain {SOIL_SHARD_COUNT}")
    locations = _load_primary_locations(
        model_pool_path=model_pool_path,
        background_points_path=background_points_path,
    )
    expected_ids = locations["location_id"].astype("int64").tolist()

    root = Path(parts_root)
    metadata_paths = sorted(root.rglob("metadata.json"))
    metadata = [json.loads(path.read_text(encoding="utf-8")) for path in metadata_paths]
    expected_parts = len(SOIL_PREDICTORS) * SOIL_SHARD_COUNT
    if len(metadata) != expected_parts:
        raise RuntimeError(
            f"expected exactly {expected_parts} SoilGrids shard metadata files; "
            f"found {len(metadata)}"
        )

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    assembled: dict[str, dict[str, object]] = {}

    for predictor in SOIL_PREDICTORS:
        rows = [row for row in metadata if str(row.get("predictor")) == predictor]
        by_index = {int(row["shard_index"]): row for row in rows}
        if set(by_index) != set(range(SOIL_SHARD_COUNT)):
            raise RuntimeError(f"incomplete SoilGrids shard set for {predictor}")
        if any(int(row.get("shard_count", -1)) != SOIL_SHARD_COUNT for row in rows):
            raise RuntimeError(f"SoilGrids shard-count drift for {predictor}")
        if any(
            row.get("location_index_sha256") != EXPECTED_LOCATION_INDEX_SHA256
            for row in rows
        ):
            raise RuntimeError(f"location fingerprint drift across SoilGrids shards: {predictor}")
        for key in ("environmental_values_read",):
            if any(row.get(key) is not True for row in rows):
                raise RuntimeError(f"SoilGrids shard value-read receipt missing for {predictor}")
        for key in ("answer_check_accessed", "model_fitting_performed"):
            if any(row.get(key) is not False for row in rows):
                raise RuntimeError(f"SoilGrids shard crossed frozen boundary: {predictor}/{key}")

        feature_frames = []
        provenance_frames = []
        for idx in range(SOIL_SHARD_COUNT):
            meta = by_index[idx]
            meta_path = next(
                path
                for path in metadata_paths
                if json.loads(path.read_text(encoding="utf-8")).get("predictor") == predictor
                and int(json.loads(path.read_text(encoding="utf-8")).get("shard_index")) == idx
            )
            feature_path = meta_path.with_name("feature.parquet")
            provenance_path = meta_path.with_name("provenance.csv")
            if _sha256(feature_path) != str(meta["feature_sha256"]):
                raise RuntimeError(f"SoilGrids feature SHA mismatch: {predictor}/{idx}")
            if _sha256(provenance_path) != str(meta["provenance_sha256"]):
                raise RuntimeError(f"SoilGrids provenance SHA mismatch: {predictor}/{idx}")
            frame = pd.read_parquet(feature_path)
            if list(frame.columns) != ["location_id", predictor]:
                raise RuntimeError(f"SoilGrids shard columns changed: {predictor}/{idx}")
            feature_frames.append(frame)
            provenance_frames.append(pd.read_csv(provenance_path))

        feature = pd.concat(feature_frames, ignore_index=True)
        feature["location_id"] = pd.to_numeric(
            feature["location_id"], errors="raise"
        ).astype("int64")
        feature = feature.sort_values("location_id", kind="mergesort").reset_index(drop=True)
        if feature["location_id"].duplicated().any():
            raise RuntimeError(f"duplicate SoilGrids locations after assembly: {predictor}")
        if feature["location_id"].tolist() != expected_ids:
            raise RuntimeError(f"SoilGrids shard coverage is not exact: {predictor}")

        provenance = pd.concat(provenance_frames, ignore_index=True).drop_duplicates()
        if len(provenance) != 1:
            raise RuntimeError(
                f"SoilGrids provenance differs across spatial shards: {predictor}"
            )

        pred_dir = output / predictor
        pred_dir.mkdir(parents=True, exist_ok=True)
        feature_path = pred_dir / "feature.parquet"
        provenance_path = pred_dir / "provenance.csv"
        metadata_path = pred_dir / "metadata.json"
        feature.to_parquet(feature_path, index=False)
        provenance.to_csv(provenance_path, index=False)
        finite = pd.to_numeric(feature[predictor], errors="coerce").notna()
        final_metadata = {
            "program": "sdmr-fresh-empirical-feature-extraction-v1",
            "predictor": predictor,
            "location_rows": EXPECTED_LOCATION_ROWS,
            "location_index_sha256": EXPECTED_LOCATION_INDEX_SHA256,
            "feature_sha256": _sha256(feature_path),
            "provenance_sha256": _sha256(provenance_path),
            "finite_rows": int(finite.sum()),
            "missing_rows": int((~finite).sum()),
            "environmental_values_read": True,
            "answer_check_accessed": False,
            "model_fitting_performed": False,
            "recovery_spatial_shards": SOIL_SHARD_COUNT,
            "recovery_reason": "single_global_remote_vrt_job_exceeded_90_minute_timeout",
        }
        metadata_path.write_text(
            json.dumps(final_metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        assembled[predictor] = final_metadata

    result = {
        "program": PROGRAM,
        "status": "soilgrids_spatial_shard_recovery_passed",
        "predictor_count": len(SOIL_PREDICTORS),
        "spatial_shards_per_predictor": SOIL_SHARD_COUNT,
        "total_shard_jobs": len(SOIL_PREDICTORS) * SOIL_SHARD_COUNT,
        "location_rows": EXPECTED_LOCATION_ROWS,
        "location_index_sha256": EXPECTED_LOCATION_INDEX_SHA256,
        "environmental_values_read": True,
        "answer_check_accessed": False,
        "model_fitting_performed": False,
        "predictors": assembled,
    }
    (output / "soil_recovery_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    shard = sub.add_parser("shard")
    shard.add_argument("--predictor", required=True)
    shard.add_argument("--shard-index", type=int, required=True)
    shard.add_argument("--shard-count", type=int, default=SOIL_SHARD_COUNT)
    shard.add_argument("--model-pool", required=True)
    shard.add_argument("--background-points", required=True)
    shard.add_argument("--process-registry", required=True)
    shard.add_argument("--chelsa-manifest", required=True)
    shard.add_argument("--output-dir", required=True)

    assemble = sub.add_parser("assemble")
    assemble.add_argument("--parts-root", required=True)
    assemble.add_argument("--model-pool", required=True)
    assemble.add_argument("--background-points", required=True)
    assemble.add_argument("--output-dir", required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "shard":
        result = extract_soil_shard(
            predictor=args.predictor,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
            model_pool_path=args.model_pool,
            background_points_path=args.background_points,
            process_registry_path=args.process_registry,
            chelsa_manifest_path=args.chelsa_manifest,
            output_dir=args.output_dir,
        )
    else:
        result = assemble_soil_shards(
            parts_root=args.parts_root,
            model_pool_path=args.model_pool,
            background_points_path=args.background_points,
            output_dir=args.output_dir,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
