"""Frozen Product-A v2.5 calibration/validation contract loader."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .v2_1_known_truth_gate_ablation import SimulatedTaxonSpec
from .v2_5_calibration_support import CalibrationSupportAudit, require_calibration_support


MAXIMUM_OPENED_KNOWN_TRUTH_SEED = 423
EXPECTED_PURPOSE = "product_a_v2_5_pretruth_calibration_support_and_fresh_validation_contract"


@dataclass(frozen=True)
class V25Panel:
    name: str
    calibration: tuple[SimulatedTaxonSpec, ...]
    validation: tuple[SimulatedTaxonSpec, ...]


@dataclass(frozen=True)
class V25Contract:
    payload: dict[str, Any]
    panels: tuple[V25Panel, ...]
    support_audit: CalibrationSupportAudit
    sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _spec(row: dict[str, object]) -> SimulatedTaxonSpec:
    return SimulatedTaxonSpec(family=str(row["family"]), seed=int(row["seed"]))


def load_v2_5_contract(path: str | Path) -> V25Contract:
    """Validate v2.5 before any calibration or fresh validation execution."""

    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if payload.get("purpose") != EXPECTED_PURPOSE:
        raise ValueError("v2.5 purpose changed after predeclaration")
    for key in ("scientific_promotion_run", "real_empirical_data_read", "old_external_sealed_outcomes_read"):
        if payload.get(key) is not False:
            raise ValueError(f"v2.5 requires {key}=false")
    opened = payload.get("opened_known_truth_seeds_excluded", {})
    if int(opened.get("maximum", -1)) != MAXIMUM_OPENED_KNOWN_TRUTH_SEED:
        raise ValueError("v2.5 maximum previously opened seed must remain 423")

    support_audit = require_calibration_support(payload)
    panels_raw = payload.get("panels", [])
    panels: list[V25Panel] = []
    names: set[str] = set()
    calibration_seeds: set[int] = set()
    validation_seeds: set[int] = set()
    for panel in panels_raw:
        name = str(panel["name"])
        if not name or name in names:
            raise ValueError("v2.5 panel names must be non-empty and unique")
        names.add(name)
        calibration = tuple(_spec(dict(row)) for row in panel["calibration"])
        validation = tuple(_spec(dict(row)) for row in panel["validation"])
        if not calibration or not validation:
            raise ValueError(f"panel {name} requires calibration and validation taxa")
        for spec in calibration:
            if spec.seed <= MAXIMUM_OPENED_KNOWN_TRUTH_SEED:
                raise ValueError("calibration seed reuses previously opened known truth")
            if spec.seed in calibration_seeds:
                raise ValueError("calibration seeds must be globally unique")
            calibration_seeds.add(spec.seed)
        for spec in validation:
            if spec.seed <= MAXIMUM_OPENED_KNOWN_TRUTH_SEED:
                raise ValueError("validation seed reuses previously opened known truth")
            if spec.seed in validation_seeds:
                raise ValueError("validation seeds must be globally unique")
            validation_seeds.add(spec.seed)
        panels.append(V25Panel(name=name, calibration=calibration, validation=validation))

    overlap = calibration_seeds & validation_seeds
    if overlap:
        raise ValueError("calibration and validation seeds must be disjoint")

    calibration_semantics = payload.get("calibration_semantics", {})
    if calibration_semantics.get("candidate_selection_allowed") is not False:
        raise ValueError("v2.5 calibration cannot select candidates")
    if calibration_semantics.get("scientific_threshold_tuning_allowed") is not False:
        raise ValueError("v2.5 calibration cannot tune scientific thresholds")
    if calibration_semantics.get("validation_truth_used_for_radius") is not False:
        raise ValueError("v2.5 calibration cannot use validation truth")

    validation_semantics = payload.get("validation_semantics", {})
    if validation_semantics.get("candidate_selection_allowed") is not False:
        raise ValueError("v2.5 validation cannot select candidates")
    if validation_semantics.get("calibration_allowed") is not False:
        raise ValueError("v2.5 validation cannot recalibrate")
    if validation_semantics.get("threshold_tuning_allowed") is not False:
        raise ValueError("v2.5 validation cannot tune thresholds")
    if validation_semantics.get("truth_opened_once_after_products_frozen") is not True:
        raise ValueError("v2.5 validation truth must open once after freeze")

    return V25Contract(
        payload=payload,
        panels=tuple(panels),
        support_audit=support_audit,
        sha256=_sha256(config_path),
    )
