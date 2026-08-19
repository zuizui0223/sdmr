"""Aggregate frozen Product-A v2.4 validation workers and open truth once.

All validation workers are model-only.  This module first reconstructs process
transfer statuses, possible/unsupported process sets, four raw boundary products
and the discovery-calibrated v2.4 intervals.  Those pre-truth products are
fingerprinted before validation generating truth is recreated for one final audit
and the predeclared five-state decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .ecological_certificate import response_point_estimates
from .known_truth_response import infer_response_predictors, infer_true_processes
from .process_exclusion_certificate import (
    KnockoutDiscoveryEvidence,
    apply_discovery_interval_calibration,
    build_complete_refit_envelope,
    classify_validation_process_exclusion,
)
from .v2_1_known_truth_gate_ablation import M_SPECS, _simulate_taxon
from .v2_4_discovery_calibration import (
    PRODUCTS,
    _product_expected_members,
    _source_products,
    _truth_audit,
)
from .v2_4_exclusion_certificate_experiment import load_exclusion_certificate_config
from .v2_4_refit_contract import GROUPS, PANELS, load_refit_contract
from .v2_4_validation_contract import (
    CALIBRATION_ARTIFACT_DIGEST,
    CALIBRATION_ARTIFACT_ID,
    CALIBRATION_HEAD_SHA,
    CALIBRATION_RUN_ID,
    PROCESS_UNIVERSE,
    exclusion_certificate_decision,
    load_validation_contract,
)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _frame_sha256(frame: pd.DataFrame, *, sort_by: list[str]) -> str:
    data = frame.copy()
    existing = [column for column in sort_by if column in data.columns]
    if existing:
        data = data.sort_values(existing, kind="mergesort", na_position="last")
    data = data.reset_index(drop=True)
    raw = data.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_validation_workers(root: Path) -> dict[str, Any]:
    contracts: list[dict[str, Any]] = []
    expected_frames: list[pd.DataFrame] = []
    key_frames: list[pd.DataFrame] = []
    fit_frames: list[pd.DataFrame] = []
    response_frames: list[pd.DataFrame] = []
    candidate_frames: list[pd.DataFrame] = []
    for path in sorted(root.rglob("contract.json")):
        contract = json.loads(path.read_text(encoding="utf-8"))
        if contract.get("purpose") != "product_a_v2_4_model_only_refit_worker":
            continue
        if contract.get("role") != "validation":
            raise ValueError("validation aggregate input contains a discovery worker")
        if contract.get("generating_truth_read") is not False:
            raise ValueError("validation worker crossed the generating-truth barrier")
        if contract.get("real_empirical_data_read") is not False:
            raise ValueError("validation worker read empirical data")
        worker = path.parent
        expected = _read_csv(worker / "expected_members.csv")
        keys = _read_csv(worker / "expected_response_keys.csv")
        fits = _read_csv(worker / "fit_ledger.csv")
        responses = _read_csv(worker / "response_estimates.csv")
        candidates = _read_csv(worker / "frozen_candidates.csv")
        for frame, label in (
            (expected, "expected_members"),
            (keys, "expected_response_keys"),
            (fits, "fit_ledger"),
            (candidates, "frozen_candidates"),
        ):
            if frame.empty:
                raise ValueError(f"validation worker {worker} has empty {label}")
        contracts.append(contract)
        expected_frames.append(expected)
        key_frames.append(keys)
        fit_frames.append(fits)
        if not responses.empty:
            response_frames.append(responses)
        candidates["worker_panel"] = contract["panel"]
        candidates["worker_species"] = contract["species"]
        candidates["worker_group"] = contract["group"]
        candidate_frames.append(candidates)

    expected_workers = len(PANELS) * 3 * len(GROUPS)
    if len(contracts) != expected_workers:
        raise ValueError(
            f"expected {expected_workers} validation workers, found {len(contracts)}"
        )
    keys = {
        (str(row["panel"]), int(row["taxon_index"]), str(row["group"]))
        for row in contracts
    }
    if len(keys) != expected_workers:
        raise ValueError("validation worker panel x taxon x group keys are not unique")
    responses = (
        pd.concat(response_frames, ignore_index=True)
        if response_frames
        else pd.DataFrame()
    )
    if responses.empty:
        raise ValueError("no successful validation responses were supplied")
    return {
        "contracts": contracts,
        "expected_members": pd.concat(expected_frames, ignore_index=True),
        "expected_response_keys": pd.concat(key_frames, ignore_index=True),
        "fit_ledger": pd.concat(fit_frames, ignore_index=True),
        "response_estimates": responses,
        "frozen_candidates": pd.concat(candidate_frames, ignore_index=True),
    }


def _load_discovery_evidence(root: Path, panel: str) -> KnockoutDiscoveryEvidence:
    panel_root = root / panel
    registry = pd.read_csv(panel_root / "knockout_registry.csv")
    candidates = pd.read_csv(panel_root / "knockout_candidate_summary.csv")
    processes = pd.read_csv(panel_root / "knockout_process_summary.csv")
    cells = pd.read_csv(panel_root / "knockout_cell_ledger.csv")
    return KnockoutDiscoveryEvidence(
        registry=registry,
        candidate_summary=candidates,
        process_summary=processes,
        cell_ledger=cells,
        chance_auc=0.50,
        auc_mean_floor=0.51,
        auc_sem_multiplier=1.0,
    )


def _split_processes(value: object) -> set[str]:
    if value is None or pd.isna(value) or not str(value):
        return set()
    return {item for item in str(value).split(",") if item}


def build_process_certificates(
    process_status: pd.DataFrame,
    fit_ledger: pd.DataFrame,
    *,
    process_universe: tuple[str, ...] = PROCESS_UNIVERSE,
) -> pd.DataFrame:
    """Build pre-truth required/refuted/unresolved and possible process sets."""

    required_status = {
        "species",
        "process",
        "process_status",
        "discovery_process_state",
    }
    missing = sorted(required_status - set(process_status.columns))
    if missing:
        raise KeyError(f"process status ledger missing columns: {missing}")
    fit_required = {
        "panel",
        "species",
        "fit_mode",
        "fit_status",
        "selected_processes",
    }
    missing_fit = sorted(fit_required - set(fit_ledger.columns))
    if missing_fit:
        raise KeyError(f"validation fit ledger missing columns: {missing_fit}")

    universe = set(str(value) for value in process_universe)
    statuses = process_status.copy()
    fits = fit_ledger.copy()
    rows: list[dict[str, object]] = []
    species_panel = (
        fits[["panel", "species"]].drop_duplicates().set_index("species")["panel"]
    )
    for species, group in statuses.groupby("species", sort=True):
        observed = set(group["process"].astype(str))
        complete = observed == universe and len(group) == len(universe)
        required = set(
            group.loc[
                group["process_status"].astype(str).eq(
                    "required_by_frozen_evidence_contract"
                ),
                "process",
            ].astype(str)
        )
        refuted = set(
            group.loc[
                group["process_status"].astype(str).eq("refuted_as_necessary"),
                "process",
            ].astype(str)
        )
        unresolved = set(
            group.loc[
                group["process_status"].astype(str).eq("unresolved"),
                "process",
            ].astype(str)
        )
        full = fits.loc[
            fits["species"].astype(str).eq(str(species))
            & fits["fit_mode"].astype(str).eq("full_fit")
            & fits["fit_status"].astype(str).eq("success")
        ]
        possible: set[str] = set()
        for value in full["selected_processes"]:
            possible.update(_split_processes(value))
        unknown = sorted(possible - universe)
        if unknown:
            raise ValueError(
                "selected validation processes outside frozen universe: "
                + ", ".join(unknown)
            )
        rows.append(
            {
                "panel": str(species_panel.loc[str(species)]),
                "species": str(species),
                "certificate_status": (
                    "complete" if complete else "unavailable_incomplete_process_cells"
                ),
                "required_processes": ",".join(sorted(required)),
                "refuted_as_necessary_processes": ",".join(sorted(refuted)),
                "unresolved_processes": ",".join(sorted(unresolved)),
                "possible_processes": ",".join(sorted(possible)),
                "unsupported_processes": ",".join(sorted(universe - possible)),
                "n_required_processes": len(required),
                "n_refuted_as_necessary_processes": len(refuted),
                "n_unresolved_processes": len(unresolved),
                "n_possible_processes": len(possible),
                "n_unsupported_processes": len(universe - possible),
                "n_successful_full_fit_members": len(full),
            }
        )
    return pd.DataFrame(rows)


def _audit_process_certificates(
    certificates: pd.DataFrame,
    truth_processes: pd.DataFrame,
) -> pd.DataFrame:
    truth = truth_processes.set_index(["panel", "species"])
    rows: list[dict[str, object]] = []
    for row in certificates.itertuples(index=False):
        key = (str(row.panel), str(row.species))
        true_set = _split_processes(truth.loc[key, "true_processes"])
        required = _split_processes(row.required_processes)
        possible = _split_processes(row.possible_processes)
        false_required = required - true_set
        possible_true = possible & true_set
        rows.append(
            {
                **row._asdict(),
                "true_processes": ",".join(sorted(true_set)),
                "n_true_processes": len(true_set),
                "false_required_processes": ",".join(sorted(false_required)),
                "n_false_required_processes": len(false_required),
                "possible_process_recall": (
                    float(len(possible_true) / len(true_set))
                    if true_set
                    else float("nan")
                ),
                "possible_process_precision": (
                    float(len(possible_true) / len(possible))
                    if possible
                    else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


def run_validation_aggregate(
    *,
    panel_config: str | Path,
    refit_contract: str | Path,
    validation_contract: str | Path,
    worker_root: str | Path,
    discovery_root: str | Path,
    calibration_root: str | Path,
) -> dict[str, Any]:
    """Freeze validation products, then open truth and apply the decision rule."""

    load_refit_contract(refit_contract)
    validation_spec = load_validation_contract(validation_contract)
    config, panels, _ = load_exclusion_certificate_config(panel_config)
    workers = _load_validation_workers(Path(worker_root))
    expected = workers["expected_members"].drop_duplicates().reset_index(drop=True)
    keys = workers["expected_response_keys"].drop_duplicates().reset_index(drop=True)
    fits = workers["fit_ledger"].copy()
    responses = workers["response_estimates"].copy()
    if expected.duplicated(["panel", "species", "member_id"]).any():
        raise ValueError("validation expected members are duplicated")
    if responses.duplicated(
        ["panel", "species", "member_id", "predictor", "quantity"]
    ).any():
        raise ValueError("validation response estimates are duplicated")

    calibration_root = Path(calibration_root)
    calibration_contract = json.loads(
        (calibration_root / "contract.json").read_text(encoding="utf-8")
    )
    if calibration_contract.get("validation_stage_allowed") is not True:
        raise ValueError("frozen discovery calibration did not allow validation")
    if calibration_contract.get("calibration_uses_validation_truth") is not False:
        raise ValueError("frozen calibration used validation truth")
    calibration = pd.read_csv(calibration_root / "calibration.csv")
    if len(calibration) != 18 or not calibration[
        "calibration_status"
    ].astype(str).eq("complete").all():
        raise ValueError("frozen discovery calibration is incomplete")
    if calibration["calibration_uses_validation_truth"].astype(bool).any():
        raise ValueError("validation-truth calibration is forbidden")

    discovery_root = Path(discovery_root)
    raw_frames: list[pd.DataFrame] = []
    membership_frames: list[pd.DataFrame] = []
    process_status_frames: list[pd.DataFrame] = []
    for panel in PANELS:
        products = _source_products(discovery_root, panel)
        for product in PRODUCTS:
            member_rows = _product_expected_members(
                expected,
                panel=panel,
                product=product,
                source_products=products,
            )
            product_responses = responses.merge(
                member_rows[["panel", "species", "member_id"]],
                on=["panel", "species", "member_id"],
                how="inner",
                validate="many_to_one",
            )
            product_keys = keys.loc[keys["panel"].astype(str).eq(panel)].copy()
            envelope = build_complete_refit_envelope(
                product_responses,
                member_rows,
                expected_response_keys=product_keys,
            )
            envelope["panel"] = panel
            envelope["product"] = product
            envelope["envelope_stage"] = "validation_raw_before_truth"
            raw_frames.append(envelope)
            membership = member_rows.copy()
            membership["product"] = product
            membership_frames.append(membership)

        evidence = _load_discovery_evidence(discovery_root, panel)
        panel_fits = fits.loc[
            fits["panel"].astype(str).eq(panel)
            & fits["fit_mode"].astype(str).eq("full_fit")
        ].copy()
        taxa = tuple(
            spec.taxon
            for item in panels
            if item.name == panel
            for spec in item.validation
        )
        statuses = classify_validation_process_exclusion(
            evidence,
            panel_fits,
            validation_taxa=taxa,
            perturbations=M_SPECS,
        )
        statuses["panel"] = panel
        process_status_frames.append(statuses)

    raw_envelopes = pd.concat(raw_frames, ignore_index=True)
    product_membership = pd.concat(membership_frames, ignore_index=True)
    process_status = pd.concat(process_status_frames, ignore_index=True)
    process_certificates = build_process_certificates(process_status, fits)

    v24_raw = raw_envelopes.loc[
        raw_envelopes["product"].astype(str).eq(
            "v2_4_exclusion_calibrated_certificate"
        )
    ].copy()
    calibrated_frames: list[pd.DataFrame] = []
    for panel in PANELS:
        panel_raw = v24_raw.loc[v24_raw["panel"].astype(str).eq(panel)].copy()
        panel_calibration = calibration.loc[
            calibration["panel"].astype(str).eq(panel)
        ].copy()
        calibrated = apply_discovery_interval_calibration(
            panel_raw,
            panel_calibration,
        )
        calibrated["panel"] = panel
        calibrated["product"] = "v2_4_exclusion_calibrated_certificate"
        calibrated["envelope_stage"] = "validation_calibrated_before_truth"
        calibrated_frames.append(calibrated)
    calibrated_envelopes = pd.concat(calibrated_frames, ignore_index=True)

    pretruth_fingerprints = {
        "product_membership_sha256": _frame_sha256(
            product_membership,
            sort_by=["panel", "species", "product", "member_id"],
        ),
        "process_status_sha256": _frame_sha256(
            process_status,
            sort_by=["panel", "species", "process"],
        ),
        "process_certificates_sha256": _frame_sha256(
            process_certificates,
            sort_by=["panel", "species"],
        ),
        "raw_envelopes_sha256": _frame_sha256(
            raw_envelopes,
            sort_by=["panel", "species", "product", "predictor", "quantity"],
        ),
        "calibrated_envelopes_sha256": _frame_sha256(
            calibrated_envelopes,
            sort_by=["panel", "species", "predictor", "quantity"],
        ),
    }

    # Validation generating truth is first accessed after every process and
    # boundary product above has been frozen and fingerprinted.
    truth_response_frames: list[pd.DataFrame] = []
    truth_process_rows: list[dict[str, object]] = []
    for panel in panels:
        for spec in panel.validation:
            simulation = _simulate_taxon(
                spec,
                n_cells=int(config["simulation_contract"]["n_cells"]),
                n_occurrences=int(config["simulation_contract"]["n_occurrences"]),
                n_target_group=int(config["simulation_contract"]["n_target_group"]),
            )
            environment = simulation.environment
            suitability = environment[
                simulation.true_suitability_column
            ].to_numpy(float)
            response_predictors = tuple(infer_response_predictors(environment))
            truth = response_point_estimates(
                environment,
                suitability,
                response_predictors,
                member_id="truth",
            ).rename(columns={"estimate": "truth_estimate"})
            truth["panel"] = panel.name
            truth["species"] = spec.taxon
            truth["family"] = spec.family
            truth["seed"] = int(spec.seed)
            truth_response_frames.append(truth)
            true_processes = tuple(sorted(infer_true_processes(environment)))
            truth_process_rows.append(
                {
                    "panel": panel.name,
                    "species": spec.taxon,
                    "family": spec.family,
                    "seed": int(spec.seed),
                    "true_processes": ",".join(true_processes),
                }
            )
    truth_response = pd.concat(truth_response_frames, ignore_index=True)
    truth_processes = pd.DataFrame(truth_process_rows)

    raw_boundary_audit = _truth_audit(raw_envelopes, truth_response)
    calibrated_for_audit = calibrated_envelopes.rename(
        columns={
            "calibrated_lower_bound": "audit_lower_bound",
            "calibrated_upper_bound": "audit_upper_bound",
            "calibrated_interval_status": "audit_interval_status",
        }
    )
    calibrated_boundary_audit = _truth_audit(
        calibrated_for_audit,
        truth_response,
        lower_col="audit_lower_bound",
        upper_col="audit_upper_bound",
        status_col="audit_interval_status",
    )
    process_truth_audit = _audit_process_certificates(
        process_certificates,
        truth_processes,
    )

    boundary_summary = (
        raw_boundary_audit.groupby(["panel", "product"], as_index=False)
        .agg(
            n_response_keys=("truth_covered", "size"),
            n_complete_intervals=(
                "interval_status",
                lambda values: int(pd.Series(values).astype(str).eq("complete").sum()),
            ),
            boundary_coverage=("truth_covered", "mean"),
            mean_normalized_width=("normalized_width", "mean"),
        )
    )
    v24_summary = (
        calibrated_boundary_audit.groupby("panel", as_index=False)
        .agg(
            n_calibrated_response_keys=("truth_covered", "size"),
            n_complete_calibrated_intervals=(
                "audit_interval_status",
                lambda values: int(pd.Series(values).astype(str).eq("complete").sum()),
            ),
            v2_4_calibrated_boundary_coverage=("truth_covered", "mean"),
            v2_4_mean_calibrated_width=(
                "calibrated_normalized_width",
                "mean",
            ),
        )
    )
    complete = boundary_summary.loc[
        boundary_summary["product"].astype(str).eq(
            "complete_adequate_certificate"
        )
    ][["panel", "boundary_coverage"]].rename(
        columns={"boundary_coverage": "complete_adequate_boundary_coverage"}
    )

    process_panel = (
        process_truth_audit.groupby("panel", as_index=False)
        .agg(
            n_validation_taxa=("species", "nunique"),
            n_complete_process_certificates=(
                "certificate_status",
                lambda values: int(pd.Series(values).astype(str).eq("complete").sum()),
            ),
            total_false_required_processes=(
                "n_false_required_processes",
                "sum",
            ),
            minimum_possible_process_recall=(
                "possible_process_recall",
                "min",
            ),
            mean_possible_process_precision=(
                "possible_process_precision",
                "mean",
            ),
        )
    )
    boundary_complete_by_species = (
        raw_envelopes.assign(
            complete=raw_envelopes["interval_status"].astype(str).eq("complete")
        )
        .groupby(["panel", "species", "product"], as_index=False)
        .agg(all_keys_complete=("complete", "all"))
        .groupby(["panel", "species"], as_index=False)
        .agg(all_products_complete=("all_keys_complete", "all"))
    )
    boundary_panel = (
        boundary_complete_by_species.groupby("panel", as_index=False)
        .agg(
            n_complete_boundary_certificates=(
                "all_products_complete",
                "sum",
            )
        )
    )
    panel_summary = (
        process_panel.merge(boundary_panel, on="panel", validate="one_to_one")
        .merge(complete, on="panel", validate="one_to_one")
        .merge(v24_summary, on="panel", validate="one_to_one")
        .sort_values("panel", kind="mergesort")
        .reset_index(drop=True)
    )
    decision = exclusion_certificate_decision(panel_summary)

    contract = {
        "purpose": "product_a_v2_4_predeclared_validation_decision",
        "scientific_promotion_run": False,
        "scientific_promotion_allowed": False,
        "real_empirical_data_read": False,
        "old_external_sealed_outcomes_read": False,
        "source_calibration_run_id": CALIBRATION_RUN_ID,
        "source_calibration_head_sha": CALIBRATION_HEAD_SHA,
        "source_calibration_artifact_id": CALIBRATION_ARTIFACT_ID,
        "source_calibration_artifact_digest": CALIBRATION_ARTIFACT_DIGEST,
        "n_model_only_validation_workers": len(workers["contracts"]),
        "all_process_and_boundary_products_frozen_before_truth_read": True,
        "pretruth_fingerprints": pretruth_fingerprints,
        "validation_generating_truth_read_after_product_freeze": True,
        "validation_truth_used_for_calibration": False,
        "n_expected_members": len(expected),
        "n_successful_members": int(
            fits["fit_status"].astype(str).eq("success").sum()
        ),
        "n_complete_raw_intervals": int(
            raw_envelopes["interval_status"].astype(str).eq("complete").sum()
        ),
        "n_complete_calibrated_intervals": int(
            calibrated_envelopes["calibrated_interval_status"]
            .astype(str)
            .eq("complete")
            .sum()
        ),
        "decision": str(decision.iloc[0]["decision"]),
        "process_support": bool(decision.iloc[0]["process_support"]),
        "boundary_support": bool(decision.iloc[0]["boundary_support"]),
        "known_truth_result_directly_allows_empirical_promotion": False,
    }
    return {
        "contract": contract,
        "worker_contracts": pd.DataFrame(workers["contracts"]),
        "frozen_candidates": workers["frozen_candidates"],
        "product_membership": product_membership,
        "expected_members": expected,
        "expected_response_keys": keys,
        "fit_ledger": fits,
        "response_estimates": responses,
        "process_status": process_status,
        "process_certificates": process_certificates,
        "raw_envelopes": raw_envelopes,
        "calibrated_envelopes": calibrated_envelopes,
        "pretruth_fingerprints": pd.DataFrame(
            [{"name": key, "sha256": value} for key, value in pretruth_fingerprints.items()]
        ),
        "truth_response": truth_response,
        "truth_processes": truth_processes,
        "raw_boundary_audit": raw_boundary_audit,
        "calibrated_boundary_audit": calibrated_boundary_audit,
        "process_truth_audit": process_truth_audit,
        "boundary_summary": boundary_summary,
        "panel_summary": panel_summary,
        "decision": decision,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-config", required=True)
    parser.add_argument("--refit-contract", required=True)
    parser.add_argument("--validation-contract", required=True)
    parser.add_argument("--worker-root", required=True)
    parser.add_argument("--discovery-root", required=True)
    parser.add_argument("--calibration-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    result = run_validation_aggregate(
        panel_config=args.panel_config,
        refit_contract=args.refit_contract,
        validation_contract=args.validation_contract,
        worker_root=args.worker_root,
        discovery_root=args.discovery_root,
        calibration_root=args.calibration_root,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name in (
        "worker_contracts",
        "frozen_candidates",
        "product_membership",
        "expected_members",
        "expected_response_keys",
        "fit_ledger",
        "response_estimates",
        "process_status",
        "process_certificates",
        "raw_envelopes",
        "calibrated_envelopes",
        "pretruth_fingerprints",
        "truth_response",
        "truth_processes",
        "raw_boundary_audit",
        "calibrated_boundary_audit",
        "process_truth_audit",
        "boundary_summary",
        "panel_summary",
        "decision",
    ):
        result[name].to_csv(out / f"{name}.csv", index=False)
    (out / "contract.json").write_text(
        json.dumps(result["contract"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
