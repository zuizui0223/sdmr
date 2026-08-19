"""Frozen Product-A v2.6 redundant-calibration contract loader."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .v2_1_known_truth_gate_ablation import SimulatedTaxonSpec
from .v2_5_calibration_support import CalibrationSupportAudit, require_calibration_support


MAXIMUM_OPENED_KNOWN_TRUTH_SEED = 445
EXPECTED_PURPOSE = (
    "product_a_v2_6_pretruth_redundant_calibration_and_reserved_validation_contract"
)
RESERVED_VALIDATION = {
    "panel_D1": (("soft_threshold", 501), ("omitted_driver", 511), ("observation_confounded", 521)),
    "panel_D2": (("soft_threshold", 502), ("omitted_driver", 512), ("observation_confounded", 522)),
    "panel_D3": (("soft_threshold", 503), ("omitted_driver", 513), ("observation_confounded", 523)),
}


@dataclass(frozen=True)
class V26Panel:
    name: str
    calibration: tuple[SimulatedTaxonSpec, ...]
    validation: tuple[SimulatedTaxonSpec, ...]


@dataclass(frozen=True)
class V26Contract:
    payload: dict[str, Any]
    panels: tuple[V26Panel, ...]
    support_audit: CalibrationSupportAudit
    sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _spec(row: dict[str, object], *, role: str) -> SimulatedTaxonSpec:
    return SimulatedTaxonSpec(
        family=str(row["family"]), seed=int(row["seed"]), role=str(role)
    )


def load_v2_6_contract(path: str | Path) -> V26Contract:
    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if payload.get("purpose") != EXPECTED_PURPOSE:
        raise ValueError("v2.6 purpose changed after predeclaration")
    for key in (
        "scientific_promotion_run",
        "real_empirical_data_read",
        "old_external_sealed_outcomes_read",
    ):
        if payload.get(key) is not False:
            raise ValueError(f"v2.6 requires {key}=false")
    opened = payload.get("opened_known_truth_seeds_excluded", {})
    if int(opened.get("maximum", -1)) != MAXIMUM_OPENED_KNOWN_TRUTH_SEED:
        raise ValueError("v2.6 maximum previously opened seed must remain 445")

    support_audit = require_calibration_support(payload)
    if support_audit.minimum_support_per_key != 2:
        raise ValueError("v2.6 cannot relax the minimum of two complete calibration taxa")

    panels_raw = payload.get("panels", [])
    panels: list[V26Panel] = []
    names: set[str] = set()
    calibration_seeds: set[int] = set()
    validation_seeds: set[int] = set()
    for panel in panels_raw:
        name = str(panel["name"])
        if not name or name in names:
            raise ValueError("v2.6 panel names must be non-empty and unique")
        names.add(name)
        calibration = tuple(
            _spec(dict(row), role="calibration") for row in panel["calibration"]
        )
        validation = tuple(
            _spec(dict(row), role="validation") for row in panel["validation"]
        )
        if len(calibration) != 9:
            raise ValueError(f"panel {name} must freeze exactly nine calibration taxa")
        if len(validation) != 3:
            raise ValueError(f"panel {name} must retain exactly three validation taxa")
        n_soil_capable = sum(spec.family == "omitted_driver" for spec in calibration)
        if n_soil_capable != 6:
            raise ValueError(f"panel {name} must predeclare six soil-capable taxa")
        observed_validation = tuple((spec.family, spec.seed) for spec in validation)
        if observed_validation != RESERVED_VALIDATION[name]:
            raise ValueError(f"panel {name} reserved validation changed from v2.5")
        for spec in calibration:
            if not 446 <= spec.seed <= 472:
                raise ValueError("v2.6 calibration seeds must be within frozen 446-472 range")
            if spec.seed in calibration_seeds:
                raise ValueError("v2.6 calibration seeds must be globally unique")
            calibration_seeds.add(spec.seed)
        for spec in validation:
            if spec.seed <= 472:
                raise ValueError("reserved validation seed must remain above calibration range")
            if spec.seed in validation_seeds:
                raise ValueError("reserved validation seeds must be globally unique")
            validation_seeds.add(spec.seed)
        panels.append(V26Panel(name=name, calibration=calibration, validation=validation))

    if set(calibration_seeds) != set(range(446, 473)):
        raise ValueError("v2.6 must reserve every calibration seed 446-472 exactly once")
    if calibration_seeds & validation_seeds:
        raise ValueError("calibration and validation seeds must be disjoint")

    semantics = payload.get("calibration_semantics", {})
    if semantics.get("candidate_selection_allowed") is not False:
        raise ValueError("v2.6 calibration cannot select candidates")
    if semantics.get("scientific_threshold_tuning_allowed") is not False:
        raise ValueError("v2.6 calibration cannot tune scientific thresholds")
    if semantics.get("interval_radius") != (
        "maximum_normalized_outside_interval_miss_over_complete_calibration_taxa"
    ):
        raise ValueError("v2.6 calibration radius semantics changed")
    if semantics.get("validation_truth_used_for_radius") is not False:
        raise ValueError("v2.6 calibration cannot use validation truth")
    if semantics.get("soil_redundancy_is_predeclared_before_seeds_446_472_are_opened") is not True:
        raise ValueError("v2.6 soil redundancy must be frozen before calibration opening")

    validation_semantics = payload.get("validation_semantics", {})
    if validation_semantics.get("reserved_validation_seeds_unchanged_from_v2_5") is not True:
        raise ValueError("v2.6 must retain the unseen v2.5 validation seeds")
    if validation_semantics.get("candidate_selection_allowed") is not False:
        raise ValueError("v2.6 validation cannot select candidates")
    if validation_semantics.get("calibration_allowed") is not False:
        raise ValueError("v2.6 validation cannot recalibrate")
    if validation_semantics.get("threshold_tuning_allowed") is not False:
        raise ValueError("v2.6 validation cannot tune thresholds")

    return V26Contract(
        payload=payload,
        panels=tuple(panels),
        support_audit=support_audit,
        sha256=_sha256(config_path),
    )
