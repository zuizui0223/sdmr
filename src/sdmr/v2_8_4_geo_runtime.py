"""Fail-closed geospatial import gate for the v2.8.4 sealed recovery.

This module validates the frozen runtime and imports rasterio without opening a
raster.  It never accepts a scientific source path or an artifact receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
from typing import Mapping


GEO_RECEIPT_PURPOSE = "product_a_v2_8_4_sealed_geo_environment_receipt"


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _newline_canonical_sha256(path: str | Path) -> str:
    return hashlib.sha256(
        Path(path).read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()


def validate_geo_environment_receipt(
    receipt: Mapping[str, object], *, freeze: Mapping[str, object]
) -> dict:
    body = dict(receipt)
    embedded = str(body.pop("receipt_digest", ""))
    if embedded != hashlib.sha256(_canonical(body)).hexdigest():
        raise ValueError("Product-A v2.8.4 geo environment receipt digest changed")
    if receipt.get("purpose") != GEO_RECEIPT_PURPOSE:
        raise ValueError("Product-A v2.8.4 received the wrong geo environment receipt")

    identity = freeze["frozen_runtime_identity"]
    if receipt.get("python_version") != identity["python_patch"]:
        raise ValueError("Product-A v2.8.4 geo Python patch changed")
    if receipt.get("runner_os") != "Linux":
        raise ValueError("Product-A v2.8.4 geo runner OS changed")
    if receipt.get("package_versions") != identity["package_versions"]:
        raise ValueError("Product-A v2.8.4 geo package versions changed")
    expected_lock = identity["geo_requirements_lock"]["newline_canonical_sha256"]
    if receipt.get("geo_requirements_lock_sha256") != expected_lock:
        raise ValueError("Product-A v2.8.4 geo dependency lock changed")
    if receipt.get("rasterio_imported") is not True:
        raise ValueError("Product-A v2.8.4 rasterio was not imported")
    for key in (
        "scientific_source_accessed",
        "presealed_receipts_accessed",
        "github_input_artifacts_accessed",
        "raster_dataset_opened",
        "environmental_values_read",
        "sealed_read_entered",
        "scientific_outcome_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if receipt.get(key) is not False:
            raise ValueError(f"Product-A v2.8.4 geo receipt crossed boundary: {key}")
    return dict(receipt)


def write_geo_environment_receipt(
    *, freeze_path: str | Path, output_path: str | Path
) -> dict:
    freeze = _load(freeze_path)
    boundary = freeze["execution_boundary"]
    if boundary.get("geo_runtime_freeze_complete") is not True:
        raise ValueError("Product-A v2.8.4 geo runtime is not frozen")
    if boundary.get("sealed_recovery_dispatch_authorized") is not False:
        raise ValueError("geo runtime freeze unexpectedly authorizes sealed recovery")

    identity = freeze["frozen_runtime_identity"]
    lock = identity["geo_requirements_lock"]
    observed_lock = _newline_canonical_sha256(lock["path"])
    if observed_lock != lock["newline_canonical_sha256"]:
        raise ValueError("Product-A v2.8.4 frozen geo lock bytes changed")
    expected_versions = identity["package_versions"]
    observed_versions = {
        name: importlib.metadata.version(name) for name in expected_versions
    }
    if observed_versions != expected_versions:
        raise ValueError(
            f"Product-A v2.8.4 geo package identity changed: {observed_versions}"
        )

    import rasterio

    if rasterio.__version__ != expected_versions["rasterio"]:
        raise ValueError("Product-A v2.8.4 rasterio import version changed")
    receipt = {
        "purpose": GEO_RECEIPT_PURPOSE,
        "python_version": platform.python_version(),
        "runner_os": os.environ.get("RUNNER_OS", platform.system()),
        "package_versions": observed_versions,
        "geo_requirements_lock_sha256": observed_lock,
        "rasterio_imported": True,
        "scientific_source_accessed": False,
        "presealed_receipts_accessed": False,
        "github_input_artifacts_accessed": False,
        "raster_dataset_opened": False,
        "environmental_values_read": False,
        "sealed_read_entered": False,
        "scientific_outcome_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    receipt["receipt_digest"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    validated = validate_geo_environment_receipt(receipt, freeze=freeze)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(validated, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return validated


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    write_geo_environment_receipt(freeze_path=args.freeze, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
