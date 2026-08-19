"""Pre-outcome contract loader for Product-A v2.4 exclusion certificates.

This module freezes and validates the unseen known-truth panels, process aliases,
base procedures, knockout registry and discovery-only calibration contract before
the full experiment is connected.  It deliberately performs no validation-truth
analysis and cannot authorize Product-A promotion.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .known_truth_scenarios import KNOWN_TRUTH_FAMILIES
from .process_exclusion_certificate import freeze_process_knockout_registry
from .v2_1_known_truth_gate_ablation import SimulatedTaxonSpec, _procedure_library


PRODUCTS = (
    "canonical_auc_point",
    "complete_adequate_certificate",
    "v2_3_mean_pareto_certificate",
    "v2_4_exclusion_calibrated_certificate",
)
CANDIDATE_SET_ORDER = (
    "complete_candidate_evidence",
    "absolute_prediction_adequacy",
    "explicit_process_knockout_admission",
    "coverage_first_spatial_refit_envelope",
    "discovery_only_interval_calibration",
)
DECISION_STATES = (
    "exclusion_certificate_supported",
    "exclusion_certificate_process_only",
    "exclusion_certificate_boundary_only",
    "exclusion_certificate_not_supported",
    "exclusion_certificate_unavailable",
)
EXPECTED_PROCESS_ALIASES = {
    "temperature": "temperature",
    "temp_proxy": "temperature",
    "sparse_temp_proxy": "temperature",
    "water": "water",
    "soil": "soil",
    "seasonality": "seasonality",
    "noise": "noise",
    "sparse_noise": "noise",
    "recording_bias": "observation_process",
}
EXPECTED_PROCESS_UNIVERSE = (
    "temperature",
    "water",
    "soil",
    "seasonality",
    "noise",
)
EXPECTED_ECOLOGICAL_PREDICTORS = (
    "temperature",
    "water",
    "temp_proxy",
    "seasonality",
    "soil",
    "noise",
    "sparse_temp_proxy",
    "sparse_noise",
)
EXPECTED_OBSERVATION_PREDICTORS = ("recording_bias",)
MAXIMUM_OPENED_KNOWN_TRUTH_SEED = 323
EXPECTED_SPATIAL_REFITS_PER_MEMBER = 5


@dataclass(frozen=True)
class ExclusionCertificatePanel:
    name: str
    discovery: tuple[SimulatedTaxonSpec, ...]
    validation: tuple[SimulatedTaxonSpec, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_exclusion_certificate_config(
    path: str | Path,
) -> tuple[dict[str, Any], tuple[ExclusionCertificatePanel, ...], pd.DataFrame]:
    """Validate the exact v2.4 pre-outcome contract and knockout registry."""

    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if payload.get("purpose") != (
        "predeclared_unseen_known_truth_panels_for_product_a_v2_4_"
        "exclusion_calibrated_certificate"
    ):
        raise ValueError("v2.4 purpose changed after predeclaration")
    frozen_false = (
        "scientific_promotion_run",
        "real_empirical_data_read",
        "old_external_sealed_outcomes_read",
        "previously_opened_known_truth_used_for_validation",
    )
    for key in frozen_false:
        if payload.get(key) is not False:
            raise ValueError(f"v2.4 requires {key}=false")
    if tuple(payload.get("products", ())) != PRODUCTS:
        raise ValueError("v2.4 products changed after predeclaration")
    if tuple(payload.get("candidate_set_order", ())) != CANDIDATE_SET_ORDER:
        raise ValueError("v2.4 candidate-set order changed")
    if tuple(payload.get("decision_states", ())) != DECISION_STATES:
        raise ValueError("v2.4 decision states changed")

    opened = payload.get("opened_known_truth_seeds_excluded", {})
    maximum_opened = int(opened.get("maximum", -1))
    if maximum_opened != MAXIMUM_OPENED_KNOWN_TRUTH_SEED:
        raise ValueError("v2.4 maximum previously opened seed must remain 323")

    prediction = payload.get("prediction_adequacy", {})
    expected_prediction = {
        "metric": "presence_rank",
        "chance_auc": 0.5,
        "minimum_auc_margin": 0.01,
        "auc_sem_multiplier": 1.0,
        "relative_to_best_gate": False,
    }
    if prediction != expected_prediction:
        raise ValueError("v2.4 absolute prediction-adequacy contract changed")

    boundary = payload.get("boundary_semantics", {})
    if tuple(boundary.get("quantities", ())) != (
        "optimum",
        "lower_limit",
        "upper_limit",
    ):
        raise ValueError("v2.4 response quantities changed")
    if int(boundary.get("spatial_refits_per_member", -1)) != (
        EXPECTED_SPATIAL_REFITS_PER_MEMBER
    ):
        raise ValueError("v2.4 spatial-refit count changed")
    if boundary.get("calibration_source") != "discovery_taxa_only":
        raise ValueError("v2.4 calibration must use discovery taxa only")
    if boundary.get("calibration_radius") != (
        "maximum_normalized_outside_interval_miss_by_predictor_and_quantity_"
        "across_discovery_taxa"
    ):
        raise ValueError("v2.4 discovery calibration rule changed")
    if boundary.get("validation_truth_used_for_calibration") is not False:
        raise ValueError("v2.4 validation-truth calibration is forbidden")
    if boundary.get("coverage_priority") is not True:
        raise ValueError("v2.4 boundary coverage must remain primary")
    if boundary.get("width_can_override_coverage") is not False:
        raise ValueError("v2.4 width cannot override coverage")

    process_aliases = {
        str(key): str(value)
        for key, value in payload.get("process_predictor_aliases", {}).items()
    }
    process_universe = tuple(
        str(x) for x in payload.get("ecological_process_universe", ())
    )
    ecological_predictors = tuple(
        str(x) for x in payload.get("ecological_predictor_universe", ())
    )
    observation_predictors = tuple(
        str(x) for x in payload.get("observation_predictors", ())
    )
    if process_aliases != EXPECTED_PROCESS_ALIASES:
        raise ValueError("v2.4 process aliases changed after predeclaration")
    if process_universe != EXPECTED_PROCESS_UNIVERSE:
        raise ValueError("v2.4 process universe changed after predeclaration")
    if ecological_predictors != EXPECTED_ECOLOGICAL_PREDICTORS:
        raise ValueError("v2.4 ecological predictor universe changed")
    if observation_predictors != EXPECTED_OBSERVATION_PREDICTORS:
        raise ValueError("v2.4 observation predictor contract changed")

    expected_procedures = tuple(
        procedure.label
        for procedure in _procedure_library(inner_folds=2, max_predictors=4)
    )
    base_procedures = tuple(str(x) for x in payload.get("base_procedures", ()))
    if base_procedures != expected_procedures:
        raise ValueError("v2.4 base procedure library changed")
    registry = freeze_process_knockout_registry(
        base_candidates=base_procedures,
        ecological_predictors=ecological_predictors,
        process_aliases=process_aliases,
        process_universe=process_universe,
        observation_predictors=observation_predictors,
    )
    expected_knockouts = len(base_procedures) * len(process_universe)
    if len(registry) != expected_knockouts:
        raise AssertionError("v2.4 knockout registry is incomplete")

    knockout = payload.get("knockout_semantics", {})
    if knockout.get("candidate_label") != "<base_procedure>::exclude::<process>":
        raise ValueError("v2.4 knockout candidate-label contract changed")
    if knockout.get("observation_predictors_removed") is not False:
        raise ValueError("v2.4 ecological knockouts cannot remove observation terms")
    if knockout.get("missing_or_failed_knockout_means_required") is not False:
        raise ValueError("v2.4 cannot convert missing knockout evidence to necessity")

    panel_names: set[str] = set()
    seeds: set[int] = set()
    panels: list[ExclusionCertificatePanel] = []
    for raw_panel in payload.get("panels", ()):
        name = str(raw_panel["name"])
        if name in panel_names:
            raise ValueError(f"duplicate v2.4 panel name: {name}")
        panel_names.add(name)
        roles: dict[str, tuple[SimulatedTaxonSpec, ...]] = {}
        for role in ("discovery", "validation"):
            specs: list[SimulatedTaxonSpec] = []
            for raw_spec in raw_panel.get(role, ()):
                family = str(raw_spec["family"])
                seed = int(raw_spec["seed"])
                if family not in KNOWN_TRUTH_FAMILIES:
                    raise ValueError(f"unknown known-truth family: {family}")
                if seed <= maximum_opened:
                    raise ValueError(f"seed {seed} was previously opened")
                if seed in seeds:
                    raise ValueError(f"duplicate v2.4 seed: {seed}")
                seeds.add(seed)
                specs.append(SimulatedTaxonSpec(family, seed, role))
            if len(specs) != 3:
                raise ValueError(f"{name} must contain three {role} taxa")
            roles[role] = tuple(specs)
        panels.append(
            ExclusionCertificatePanel(
                name=name,
                discovery=roles["discovery"],
                validation=roles["validation"],
            )
        )
    if tuple(panel.name for panel in panels) != (
        "panel_D1",
        "panel_D2",
        "panel_D3",
    ):
        raise ValueError("v2.4 requires exactly the frozen D1-D3 panels")
    if len(seeds) != 18:
        raise ValueError("v2.4 requires 18 unique unseen seeds")
    return payload, tuple(panels), registry


def build_preoutcome_contract(
    config_path: str | Path,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Return a machine-readable validate-only v2.4 contract."""

    path = Path(config_path)
    payload, panels, registry = load_exclusion_certificate_config(path)
    contract = {
        "purpose": "product_a_v2_4_preoutcome_exclusion_certificate_scaffold",
        "implementation_stage": "preoutcome_contract_and_pure_semantics",
        "scientific_promotion_run": False,
        "scientific_promotion_allowed": False,
        "real_empirical_data_read": False,
        "validation_truth_read": False,
        "old_external_sealed_outcomes_read": False,
        "panel_config": str(path),
        "panel_config_sha256": _sha256(path),
        "products": list(PRODUCTS),
        "candidate_set_order": list(CANDIDATE_SET_ORDER),
        "decision_states": list(DECISION_STATES),
        "panels": [panel.name for panel in panels],
        "discovery_seeds": [
            spec.seed for panel in panels for spec in panel.discovery
        ],
        "validation_seeds": [
            spec.seed for panel in panels for spec in panel.validation
        ],
        "n_base_procedures": int(registry["base_candidate"].nunique()),
        "n_processes": int(registry["excluded_process"].nunique()),
        "n_knockout_routes": int(len(registry)),
        "spatial_refits_per_member": EXPECTED_SPATIAL_REFITS_PER_MEMBER,
        "calibration_source": payload["boundary_semantics"]["calibration_source"],
        "missing_or_failed_knockout_means_required": False,
    }
    return contract, registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    contract, registry = build_preoutcome_contract(args.panel_config)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    registry.to_csv(out / "process_knockout_registry.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
