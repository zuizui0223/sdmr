"""Model-only refit worker for Product-A v2.5 calibration and fresh validation.

The worker consumes only the frozen v2.4 discovery-selected candidates plus one
predeclared v2.5 taxon specification. It never exposes generating truth. For the
calibration role, truth is opened later by the aggregate only after every raw
response envelope has been reconstructed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .ecological_certificate import response_point_estimates
from .known_truth_response import infer_response_predictors
from .model import score_ecological_suitability
from .model_pool_predictor_admissibility import select_model_pool_admissible_predictors
from .recovery_procedure_fit import fit_recovery_procedure
from .v2_1_known_truth_gate_ablation import (
    CANDIDATE_ECOLOGICAL_PREDICTORS,
    M_SPECS,
    _model_only_frame,
    _nested_background_perturbations,
    _procedure_library,
    _simulate_taxon,
)
from .v2_3_ecological_certificate_experiment import _process_groups
from .v2_4_refit_contract import (
    FULL_FIT_CODE,
    GROUPS,
    SPATIAL_REFIT_CODES,
    load_frozen_group_candidates,
)
from .v2_4_refit_worker import _assert_model_only, _fit_rows
from .v2_5_contract import V25Contract, load_v2_5_contract


ROLE_OFFSETS = {"calibration": 0, "validation": 50000}
SEED_BASE = 510000


def v2_5_refit_seed(
    *,
    panel: str,
    role: str,
    taxon_index: int,
    group: str,
    candidate_index: int,
    m_index: int,
    fit_code: int,
) -> int:
    """Return the deterministic seed frozen in the v2.5 execution contract."""

    panels = ("panel_D1", "panel_D2", "panel_D3")
    if panel not in panels:
        raise ValueError(f"unknown v2.5 panel: {panel}")
    if role not in ROLE_OFFSETS:
        raise ValueError(f"unknown v2.5 role: {role}")
    if group not in GROUPS:
        raise ValueError(f"unknown v2.5 group: {group}")
    if not 0 <= int(taxon_index) < (5 if role == "calibration" else 3):
        raise ValueError("taxon_index is outside the frozen v2.5 role")
    if int(candidate_index) < 0:
        raise ValueError("candidate_index must be >= 0")
    if not 0 <= int(m_index) < len(M_SPECS):
        raise ValueError("m_index is outside the frozen M grid")
    if int(fit_code) not in (*SPATIAL_REFIT_CODES, FULL_FIT_CODE):
        raise ValueError("fit_code is not a frozen full/refit code")
    return int(
        SEED_BASE
        + panels.index(panel) * 100000
        + ROLE_OFFSETS[role]
        + int(taxon_index) * 10000
        + GROUPS.index(group) * 1000
        + int(candidate_index) * 100
        + int(m_index) * 10
        + int(fit_code)
    )


def _spec_from_contract(
    contract: V25Contract,
    *,
    panel: str,
    role: str,
    taxon_index: int,
):
    panel_by_name = {item.name: item for item in contract.panels}
    if panel not in panel_by_name:
        raise ValueError(f"unknown frozen panel: {panel}")
    specs = (
        panel_by_name[panel].calibration
        if role == "calibration"
        else panel_by_name[panel].validation
    )
    if not 0 <= int(taxon_index) < len(specs):
        raise ValueError("taxon_index is outside the frozen panel role")
    return specs[int(taxon_index)]


def run_v2_5_refit_worker(
    *,
    contract_path: str | Path,
    discovery_dir: str | Path,
    panel: str,
    role: str,
    taxon_index: int,
    group: str,
) -> dict[str, Any]:
    """Fit one frozen panel x taxon x group without opening generating truth."""

    if role not in ROLE_OFFSETS:
        raise ValueError("role must be calibration or validation")
    contract = load_v2_5_contract(contract_path)
    if group not in GROUPS:
        raise ValueError(f"unknown frozen group: {group}")
    spec = _spec_from_contract(
        contract,
        panel=panel,
        role=role,
        taxon_index=int(taxon_index),
    )
    source = load_frozen_group_candidates(
        discovery_dir,
        panel=panel,
        group=group,
    )
    simulation_contract = contract.payload["simulation_contract"]
    simulation = _simulate_taxon(
        spec,
        n_cells=int(simulation_contract["n_cells"]),
        n_occurrences=int(simulation_contract["n_occurrences"]),
        n_target_group=int(simulation_contract["n_target_group"]),
    )
    occurrence = _model_only_frame(simulation.occurrences).reset_index(drop=True)
    backgrounds = {
        name: _model_only_frame(frame).reset_index(drop=True)
        for name, frame in _nested_background_perturbations(simulation).items()
    }
    environment = _model_only_frame(simulation.environment).reset_index(drop=True)
    _assert_model_only(occurrence, label="occurrence")
    _assert_model_only(environment, label="projection-environment")
    for name, frame in backgrounds.items():
        _assert_model_only(frame, label=f"{name}-background")

    admissibility = select_model_pool_admissible_predictors(
        {name: (occurrence, backgrounds[name]) for name in M_SPECS},
        CANDIDATE_ECOLOGICAL_PREDICTORS,
        minimum_coverage=float(simulation_contract["minimum_predictor_coverage"]),
    )
    procedures = _procedure_library(
        inner_folds=int(simulation_contract["inner_folds"]),
        max_predictors=int(simulation_contract["max_predictors"]),
    )
    procedure_by_label = {procedure.label: procedure for procedure in procedures}
    response_predictors = tuple(infer_response_predictors(environment))
    if not response_predictors:
        raise ValueError("model-only environment has no declared response predictors")

    source_frame = source.as_frame()
    expected_rows: list[dict[str, object]] = []
    fit_rows: list[dict[str, object]] = []
    response_frames: list[pd.DataFrame] = []
    for candidate_index, row in enumerate(source_frame.itertuples(index=False)):
        candidate = str(row.candidate)
        base_candidate = str(row.base_candidate)
        excluded_process = (
            None
            if row.excluded_process is None or pd.isna(row.excluded_process)
            else str(row.excluded_process)
        )
        excluded_predictors = {
            value for value in str(row.excluded_predictors).split(",") if value
        }
        procedure = procedure_by_label.get(base_candidate)
        if procedure is None:
            raise KeyError(f"unknown frozen base procedure: {base_candidate}")
        ecological_predictors = tuple(
            predictor
            for predictor in admissibility.predictors
            if predictor not in excluded_predictors
        )
        if not ecological_predictors:
            raise ValueError(
                f"frozen candidate {candidate} leaves no admissible ecological predictor"
            )

        for m_index, perturbation in enumerate(M_SPECS):
            background = backgrounds[perturbation]
            fit_specs = [("full_fit", FULL_FIT_CODE, -1)] + [
                ("spatial_refit", fit_code, fit_code)
                for fit_code in SPATIAL_REFIT_CODES
            ]
            for fit_mode, fit_code, refit_index in fit_specs:
                member_id = (
                    f"{candidate}::M::{perturbation}::fit::{fit_mode}::{refit_index}"
                )
                partition_seed = v2_5_refit_seed(
                    panel=panel,
                    role=role,
                    taxon_index=int(taxon_index),
                    group=group,
                    candidate_index=candidate_index,
                    m_index=m_index,
                    fit_code=fit_code,
                )
                base = {
                    "panel": panel,
                    "role": role,
                    "species": spec.taxon,
                    "family": spec.family,
                    "seed": int(spec.seed),
                    "group": group,
                    "candidate": candidate,
                    "base_candidate": base_candidate,
                    "excluded_process": excluded_process,
                    "excluded_predictors": ",".join(sorted(excluded_predictors)),
                    "perturbation": perturbation,
                    "fit_mode": fit_mode,
                    "refit_index": int(refit_index),
                    "partition_seed": int(partition_seed),
                    "member_id": member_id,
                }
                expected_rows.append(base.copy())
                try:
                    p_fit, b_fit, p_groups, b_groups, train_blocks = _fit_rows(
                        occurrence,
                        background,
                        seed=partition_seed,
                        fit_mode=fit_mode,
                    )
                    fitted = fit_recovery_procedure(
                        p_fit,
                        b_fit,
                        p_groups,
                        b_groups,
                        ecological_predictors,
                        simulation.audit_predictors,
                        procedure,
                    )
                    predicted = score_ecological_suitability(
                        fitted.model,
                        environment,
                        fitted.selected_predictors,
                        observation_predictors=procedure.observation_predictors,
                        observation_reference=background,
                    )
                    surface_coverage = float(np.isfinite(predicted).mean())
                    if surface_coverage < float(
                        simulation_contract["prediction_surface_coverage_floor"]
                    ):
                        raise ValueError(
                            "prediction surface coverage below frozen floor: "
                            f"{surface_coverage:.6f}"
                        )
                    responses = response_point_estimates(
                        environment,
                        predicted,
                        response_predictors,
                        member_id=member_id,
                    )
                    if (
                        len(responses) != len(response_predictors) * 3
                        or not np.isfinite(
                            pd.to_numeric(responses["estimate"], errors="coerce")
                        ).all()
                    ):
                        raise ValueError("member response estimates are incomplete")
                except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                    fit_rows.append(
                        {
                            **base,
                            "fit_status": "abstain_member_fit",
                            "fit_error": str(exc),
                            "prediction_surface_coverage": float("nan"),
                            "n_fit_presence": float("nan"),
                            "n_fit_background": float("nan"),
                            "train_blocks": None,
                        }
                    )
                    continue

                fit_rows.append(
                    {
                        **base,
                        "fit_status": "success",
                        "fit_error": None,
                        "prediction_surface_coverage": surface_coverage,
                        "n_fit_presence": len(p_fit),
                        "n_fit_background": len(b_fit),
                        "train_blocks": ",".join(str(x) for x in train_blocks),
                        "selected_predictors": ",".join(fitted.selected_predictors),
                        "selected_ecological_predictors": ",".join(
                            fitted.selected_ecological_predictors
                        ),
                        "selected_processes": ",".join(
                            _process_groups(fitted.selected_ecological_predictors)
                        ),
                    }
                )
                for column, value in base.items():
                    responses[column] = value
                response_frames.append(responses)

    expected_members = pd.DataFrame(expected_rows)
    fit_ledger = pd.DataFrame(fit_rows)
    response_estimates = (
        pd.concat(response_frames, ignore_index=True)
        if response_frames
        else pd.DataFrame()
    )
    expected_keys = pd.DataFrame(
        [
            {
                "panel": panel,
                "role": role,
                "species": spec.taxon,
                "predictor": predictor,
                "quantity": quantity,
            }
            for predictor in response_predictors
            for quantity in ("optimum", "lower_limit", "upper_limit")
        ]
    )
    worker_contract = {
        "purpose": "product_a_v2_5_model_only_refit_worker",
        "contract_sha256": contract.sha256,
        "panel": panel,
        "role": role,
        "taxon_index": int(taxon_index),
        "species": spec.taxon,
        "family": spec.family,
        "seed": int(spec.seed),
        "group": group,
        "scientific_promotion_run": False,
        "scientific_promotion_allowed": False,
        "real_empirical_data_read": False,
        "generating_truth_read": False,
        "old_external_sealed_outcomes_read": False,
        "candidate_selection_performed": False,
        "scientific_threshold_tuning_performed": False,
        "n_frozen_candidates": len(source.candidates),
        "n_expected_members": len(expected_members),
        "n_successful_members": int(
            fit_ledger["fit_status"].astype(str).eq("success").sum()
        ),
        "n_full_fit_members_per_candidate_M": 1,
        "n_spatial_refits_per_candidate_M": len(SPATIAL_REFIT_CODES),
        "response_predictors": list(response_predictors),
        "source_discovery_panel": panel,
    }
    return {
        "contract": worker_contract,
        "frozen_candidates": source_frame,
        "expected_members": expected_members,
        "expected_response_keys": expected_keys,
        "fit_ledger": fit_ledger,
        "response_estimates": response_estimates,
        "predictor_coverage": admissibility.ledger,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--discovery-dir", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--role", choices=("calibration", "validation"), required=True)
    parser.add_argument("--taxon-index", type=int, required=True)
    parser.add_argument("--group", choices=GROUPS, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    result = run_v2_5_refit_worker(
        contract_path=args.contract,
        discovery_dir=args.discovery_dir,
        panel=args.panel,
        role=args.role,
        taxon_index=args.taxon_index,
        group=args.group,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name in (
        "frozen_candidates",
        "expected_members",
        "expected_response_keys",
        "fit_ledger",
        "response_estimates",
        "predictor_coverage",
    ):
        result[name].to_csv(out / f"{name}.csv", index=False)
    (out / "contract.json").write_text(
        json.dumps(result["contract"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
