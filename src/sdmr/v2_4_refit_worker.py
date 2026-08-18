"""Fit frozen Product-A v2.4 members without reading generating truth.

One worker handles one panel x taxon x frozen candidate group. It consumes an
immutable discovery-selection artifact, refits every frozen candidate under all M
specifications using one full fit and five predeclared spatial refits, and projects
the ecological response on the complete model-only environment. Generating truth
is not accessed or returned.
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
from .v2_4_exclusion_certificate_experiment import load_exclusion_certificate_config
from .v2_4_refit_contract import (
    FULL_FIT_CODE,
    GROUPS,
    HOLDOUT_FRACTION,
    N_BLOCKS,
    SPATIAL_REFIT_CODES,
    load_frozen_group_candidates,
    load_refit_contract,
    refit_seed,
)
from .validation import make_spatial_partition


FORBIDDEN_GENERATING_COLUMNS = {
    "true_suitability",
    "sampling_effort",
    "focal_recording_multiplier",
}


def _assert_model_only(frame: pd.DataFrame, *, label: str) -> None:
    forbidden = sorted(FORBIDDEN_GENERATING_COLUMNS & set(frame.columns))
    if forbidden:
        raise AssertionError(
            f"generating truth crossed the {label} barrier: " + ", ".join(forbidden)
        )


def _fit_rows(
    occurrence: pd.DataFrame,
    background: pd.DataFrame,
    *,
    seed: int,
    fit_mode: str,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, tuple[int, ...]]:
    partition = make_spatial_partition(
        occurrence["longitude"].to_numpy(float),
        occurrence["latitude"].to_numpy(float),
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        n_blocks=N_BLOCKS,
        holdout_fraction=HOLDOUT_FRACTION,
        random_state=int(seed),
    )
    if fit_mode == "full_fit":
        return (
            occurrence.reset_index(drop=True),
            background.reset_index(drop=True),
            np.asarray(partition.presence_blocks),
            np.asarray(partition.background_blocks),
            tuple(partition.train_blocks),
        )
    if fit_mode != "spatial_refit":
        raise ValueError("fit_mode must be full_fit or spatial_refit")
    p_keep = np.isin(partition.presence_blocks, partition.train_blocks)
    b_keep = np.isin(partition.background_blocks, partition.train_blocks)
    if int(p_keep.sum()) < 5 or int(b_keep.sum()) < 5:
        raise ValueError("spatial refit training blocks contain insufficient rows")
    return (
        occurrence.loc[p_keep].reset_index(drop=True),
        background.loc[b_keep].reset_index(drop=True),
        np.asarray(partition.presence_blocks)[p_keep],
        np.asarray(partition.background_blocks)[b_keep],
        tuple(partition.train_blocks),
    )


def run_refit_worker(
    *,
    panel_config: str | Path,
    refit_contract: str | Path,
    discovery_dir: str | Path,
    panel: str,
    role: str,
    taxon_index: int,
    group: str,
) -> dict[str, Any]:
    """Execute one frozen refit worker and return model-only products."""

    if role not in {"discovery", "validation"}:
        raise ValueError("role must be discovery or validation")
    load_refit_contract(refit_contract)
    config, panels, _ = load_exclusion_certificate_config(panel_config)
    panel_by_name = {item.name: item for item in panels}
    if panel not in panel_by_name:
        raise ValueError(f"unknown frozen panel: {panel}")
    if group not in GROUPS:
        raise ValueError(f"unknown frozen group: {group}")
    taxon_index = int(taxon_index)
    specs = (
        panel_by_name[panel].discovery
        if role == "discovery"
        else panel_by_name[panel].validation
    )
    if not 0 <= taxon_index < len(specs):
        raise ValueError("taxon_index is outside the frozen panel role")
    spec = specs[taxon_index]

    source = load_frozen_group_candidates(
        discovery_dir,
        panel=panel,
        group=group,
    )
    simulation_contract = config["simulation_contract"]
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
            None if row.excluded_process is None or pd.isna(row.excluded_process)
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
                seed = refit_seed(
                    panel=panel,
                    role=role,
                    taxon_index=taxon_index,
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
                    "partition_seed": int(seed),
                    "member_id": member_id,
                }
                expected_rows.append(base.copy())
                try:
                    p_fit, b_fit, p_groups, b_groups, train_blocks = _fit_rows(
                        occurrence,
                        background,
                        seed=seed,
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
                    expected_response_rows = len(response_predictors) * 3
                    if (
                        len(responses) != expected_response_rows
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

                selected_processes = _process_groups(
                    fitted.selected_ecological_predictors
                )
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
                        "selected_processes": ",".join(selected_processes),
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
        else pd.DataFrame(
            columns=[
                "member_id",
                "predictor",
                "quantity",
                "estimate",
                "environment_span",
                "panel",
                "role",
                "species",
                "family",
                "seed",
                "group",
                "candidate",
                "base_candidate",
                "excluded_process",
                "excluded_predictors",
                "perturbation",
                "fit_mode",
                "refit_index",
                "partition_seed",
            ]
        )
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
    contract = {
        "purpose": "product_a_v2_4_model_only_refit_worker",
        "panel": panel,
        "role": role,
        "taxon_index": taxon_index,
        "species": spec.taxon,
        "seed": int(spec.seed),
        "group": group,
        "scientific_promotion_run": False,
        "scientific_promotion_allowed": False,
        "real_empirical_data_read": False,
        "generating_truth_read": False,
        "old_external_sealed_outcomes_read": False,
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
        "contract": contract,
        "frozen_candidates": source_frame,
        "expected_members": expected_members,
        "expected_response_keys": expected_keys,
        "fit_ledger": fit_ledger,
        "response_estimates": response_estimates,
        "predictor_coverage": admissibility.ledger,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-config", required=True)
    parser.add_argument("--refit-contract", required=True)
    parser.add_argument("--discovery-dir", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--role", choices=("discovery", "validation"), required=True)
    parser.add_argument("--taxon-index", type=int, required=True)
    parser.add_argument("--group", choices=GROUPS, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    result = run_refit_worker(
        panel_config=args.panel_config,
        refit_contract=args.refit_contract,
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
