"""Freeze Product-A v2.5 fresh-validation products, then open truth once."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .ecological_certificate import response_point_estimates
from .known_truth_response import infer_response_predictors, infer_true_processes
from .process_exclusion_certificate import (
    apply_discovery_interval_calibration,
    build_complete_refit_envelope,
    classify_validation_process_exclusion,
)
from .v2_1_known_truth_gate_ablation import M_SPECS, _simulate_taxon
from .v2_4_discovery_calibration import _product_expected_members, _source_products, _truth_audit
from .v2_4_refit_contract import GROUPS
from .v2_4_validation_aggregate import (
    _audit_process_certificates,
    _frame_sha256,
    _load_discovery_evidence,
    build_process_certificates,
)
from .v2_5_contract import load_v2_5_contract
from .v2_5_validation_contract import (
    PANELS,
    PROCESS_UNIVERSE,
    PRODUCTS,
    SOURCE_CALIBRATION_CONTRACT_SHA256,
    load_v2_5_validation_contract,
    v2_5_decision,
)


EXPECTED_WORKERS = len(PANELS) * 3 * len(GROUPS)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _load_validation_workers(root: Path, *, source_contract_sha256: str) -> dict[str, Any]:
    contracts: list[dict[str, Any]] = []
    expected_frames: list[pd.DataFrame] = []
    key_frames: list[pd.DataFrame] = []
    fit_frames: list[pd.DataFrame] = []
    response_frames: list[pd.DataFrame] = []
    candidate_frames: list[pd.DataFrame] = []
    for path in sorted(root.rglob("contract.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("purpose") != "product_a_v2_5_model_only_refit_worker":
            continue
        if row.get("role") != "validation":
            raise ValueError("fresh validation aggregate contains a non-validation worker")
        if row.get("contract_sha256") != source_contract_sha256:
            raise ValueError("fresh validation worker used a different frozen v2.5 contract")
        for flag in (
            "generating_truth_read",
            "real_empirical_data_read",
            "candidate_selection_performed",
            "scientific_threshold_tuning_performed",
        ):
            if row.get(flag) is not False:
                raise ValueError(f"fresh validation worker violates {flag}=false")
        worker = path.parent
        expected = _read_csv(worker / "expected_members.csv")
        keys = _read_csv(worker / "expected_response_keys.csv")
        fits = _read_csv(worker / "fit_ledger.csv")
        responses = _read_csv(worker / "response_estimates.csv")
        candidates = _read_csv(worker / "frozen_candidates.csv")
        for frame, label in ((expected, "expected_members"), (keys, "expected_response_keys"), (fits, "fit_ledger"), (candidates, "frozen_candidates")):
            if frame.empty:
                raise ValueError(f"fresh validation worker {worker} has empty {label}")
        contracts.append(row)
        expected_frames.append(expected)
        key_frames.append(keys)
        fit_frames.append(fits)
        if not responses.empty:
            response_frames.append(responses)
        candidates["worker_panel"] = row["panel"]
        candidates["worker_species"] = row["species"]
        candidates["worker_group"] = row["group"]
        candidate_frames.append(candidates)
    if len(contracts) != EXPECTED_WORKERS:
        raise ValueError(f"expected {EXPECTED_WORKERS} validation workers, found {len(contracts)}")
    unique = {(str(r["panel"]), int(r["taxon_index"]), str(r["group"])) for r in contracts}
    if len(unique) != EXPECTED_WORKERS:
        raise ValueError("validation worker panel x taxon x group keys are not unique")
    responses = pd.concat(response_frames, ignore_index=True) if response_frames else pd.DataFrame()
    if responses.empty:
        raise ValueError("no successful fresh validation responses were supplied")
    return {
        "contracts": contracts,
        "expected_members": pd.concat(expected_frames, ignore_index=True),
        "expected_response_keys": pd.concat(key_frames, ignore_index=True),
        "fit_ledger": pd.concat(fit_frames, ignore_index=True),
        "response_estimates": responses,
        "frozen_candidates": pd.concat(candidate_frames, ignore_index=True),
    }


def _verify_calibration(root: Path, *, source_contract_sha256: str) -> tuple[dict[str, Any], pd.DataFrame]:
    contract = json.loads((root / "contract.json").read_text(encoding="utf-8"))
    if contract.get("purpose") != "product_a_v2_5_frozen_calibration_radii":
        raise ValueError("source is not a frozen v2.5 calibration artifact")
    if contract.get("source_contract_sha256") != source_contract_sha256:
        raise ValueError("frozen calibration derives from a different v2.5 contract")
    if contract.get("all_required_validation_keys_calibrated") is not True:
        raise ValueError("frozen v2.5 calibration did not cover every required key")
    if contract.get("raw_envelopes_frozen_before_calibration_truth_read") is not True:
        raise ValueError("v2.5 calibration truth barrier was not satisfied")
    if contract.get("fresh_validation_taxa_simulated_or_read") is not False:
        raise ValueError("v2.5 calibration accessed fresh validation taxa")
    if contract.get("fresh_validation_truth_read") is not False:
        raise ValueError("v2.5 calibration accessed fresh validation truth")
    if contract.get("validation_truth_used_for_calibration") is not False:
        raise ValueError("validation truth calibrated v2.5 intervals")
    calibration = pd.read_csv(root / "calibration.csv")
    if len(calibration) != 27:
        raise ValueError("v2.5 calibration must contain 27 panel x response keys")
    if not calibration["calibration_status"].astype(str).eq("complete").all():
        raise ValueError("v2.5 calibration contains unavailable keys")
    if calibration["calibration_uses_validation_truth"].fillna(True).astype(bool).any():
        raise ValueError("v2.5 calibration records validation-truth use")
    return contract, calibration


def run_v2_5_validation_aggregate(
    *,
    base_contract_path: str | Path,
    validation_contract_path: str | Path,
    worker_root: str | Path,
    discovery_root: str | Path,
    calibration_root: str | Path,
    output_dir: str | Path,
    calibration_run_id: str,
    calibration_head_sha: str,
    calibration_artifact_id: str,
    calibration_artifact_digest: str,
) -> dict[str, Any]:
    """Freeze every v2.5 validation product before opening seeds 501--523 truth."""

    base_contract = load_v2_5_contract(base_contract_path)
    load_v2_5_validation_contract(validation_contract_path)
    if base_contract.sha256 != SOURCE_CALIBRATION_CONTRACT_SHA256:
        raise ValueError("base v2.5 contract hash differs from predeclared validation source")
    workers = _load_validation_workers(
        Path(worker_root), source_contract_sha256=base_contract.sha256
    )
    expected = workers["expected_members"].drop_duplicates().reset_index(drop=True)
    keys = workers["expected_response_keys"].drop_duplicates().reset_index(drop=True)
    fits = workers["fit_ledger"].copy()
    responses = workers["response_estimates"].copy()
    if expected.duplicated(["panel", "species", "member_id"]).any():
        raise ValueError("fresh validation expected members are duplicated")
    if responses.duplicated(["panel", "species", "member_id", "predictor", "quantity"]).any():
        raise ValueError("fresh validation response estimates are duplicated")

    calibration_contract, calibration = _verify_calibration(
        Path(calibration_root), source_contract_sha256=base_contract.sha256
    )
    discovery_root = Path(discovery_root)
    raw_frames: list[pd.DataFrame] = []
    membership_frames: list[pd.DataFrame] = []
    process_status_frames: list[pd.DataFrame] = []
    for panel in PANELS:
        source_products = _source_products(discovery_root, panel)
        for product in PRODUCTS:
            membership_product = (
                "v2_4_exclusion_calibrated_certificate"
                if product == "v2_5_exclusion_calibrated_certificate"
                else product
            )
            member_rows = _product_expected_members(
                expected,
                panel=panel,
                product=membership_product,
                source_products=source_products,
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
            envelope["envelope_stage"] = "fresh_validation_raw_before_truth"
            raw_frames.append(envelope)
            membership = member_rows.copy()
            membership["product"] = product
            membership_frames.append(membership)

        discovery = _load_discovery_evidence(discovery_root, panel)
        panel_fits = fits.loc[
            fits["panel"].astype(str).eq(panel)
            & fits["fit_mode"].astype(str).eq("full_fit")
        ].copy()
        taxa = tuple(
            spec.taxon
            for item in base_contract.panels
            if item.name == panel
            for spec in item.validation
        )
        status = classify_validation_process_exclusion(
            discovery,
            panel_fits,
            validation_taxa=taxa,
            perturbations=M_SPECS,
        )
        status["panel"] = panel
        process_status_frames.append(status)

    raw_envelopes = pd.concat(raw_frames, ignore_index=True)
    product_membership = pd.concat(membership_frames, ignore_index=True)
    process_status = pd.concat(process_status_frames, ignore_index=True)
    process_certificates = build_process_certificates(
        process_status, fits, process_universe=PROCESS_UNIVERSE
    )

    v25_raw = raw_envelopes.loc[
        raw_envelopes["product"].astype(str).eq("v2_5_exclusion_calibrated_certificate")
    ].copy()
    calibrated_frames: list[pd.DataFrame] = []
    for panel in PANELS:
        panel_raw = v25_raw.loc[v25_raw["panel"].astype(str).eq(panel)].copy()
        panel_calibration = calibration.loc[calibration["panel"].astype(str).eq(panel)].copy()
        calibrated = apply_discovery_interval_calibration(panel_raw, panel_calibration)
        calibrated["panel"] = panel
        calibrated["product"] = "v2_5_exclusion_calibrated_certificate"
        calibrated["envelope_stage"] = "fresh_validation_calibrated_before_truth"
        calibrated_frames.append(calibrated)
    calibrated_envelopes = pd.concat(calibrated_frames, ignore_index=True)

    fingerprints = {
        "product_membership_sha256": _frame_sha256(product_membership, sort_by=["panel", "species", "product", "member_id"]),
        "process_status_sha256": _frame_sha256(process_status, sort_by=["panel", "species", "process"]),
        "process_certificates_sha256": _frame_sha256(process_certificates, sort_by=["panel", "species"]),
        "raw_envelopes_sha256": _frame_sha256(raw_envelopes, sort_by=["panel", "species", "product", "predictor", "quantity"]),
        "calibrated_envelopes_sha256": _frame_sha256(calibrated_envelopes, sort_by=["panel", "species", "predictor", "quantity"]),
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    product_membership.to_csv(out / "pretruth_product_membership.csv", index=False)
    process_status.to_csv(out / "pretruth_process_status.csv", index=False)
    process_certificates.to_csv(out / "pretruth_process_certificates.csv", index=False)
    raw_envelopes.to_csv(out / "pretruth_raw_envelopes.csv", index=False)
    calibrated_envelopes.to_csv(out / "pretruth_calibrated_envelopes.csv", index=False)
    pd.DataFrame([{"name": k, "sha256": v} for k, v in fingerprints.items()]).to_csv(
        out / "pretruth_fingerprints.csv", index=False
    )

    # Fresh validation generating truth is first accessed after all files above exist.
    truth_response_frames: list[pd.DataFrame] = []
    truth_process_rows: list[dict[str, object]] = []
    simulation_contract = base_contract.payload["simulation_contract"]
    for panel in base_contract.panels:
        for spec in panel.validation:
            simulation = _simulate_taxon(
                spec,
                n_cells=int(simulation_contract["n_cells"]),
                n_occurrences=int(simulation_contract["n_occurrences"]),
                n_target_group=int(simulation_contract["n_target_group"]),
            )
            environment = simulation.environment
            suitability = environment[simulation.true_suitability_column].to_numpy(float)
            response_predictors = tuple(infer_response_predictors(environment))
            truth = response_point_estimates(
                environment, suitability, response_predictors, member_id="truth"
            ).rename(columns={"estimate": "truth_estimate"})
            truth["panel"] = panel.name
            truth["species"] = spec.taxon
            truth["family"] = spec.family
            truth["seed"] = int(spec.seed)
            truth_response_frames.append(truth)
            truth_process_rows.append({
                "panel": panel.name,
                "species": spec.taxon,
                "family": spec.family,
                "seed": int(spec.seed),
                "true_processes": ",".join(sorted(infer_true_processes(environment))),
            })
    truth_response = pd.concat(truth_response_frames, ignore_index=True)
    truth_processes = pd.DataFrame(truth_process_rows)

    raw_boundary_audit = _truth_audit(raw_envelopes, truth_response)
    calibrated_for_audit = calibrated_envelopes.rename(columns={
        "calibrated_lower_bound": "audit_lower_bound",
        "calibrated_upper_bound": "audit_upper_bound",
        "calibrated_interval_status": "audit_interval_status",
    })
    calibrated_boundary_audit = _truth_audit(
        calibrated_for_audit,
        truth_response,
        lower_col="audit_lower_bound",
        upper_col="audit_upper_bound",
        status_col="audit_interval_status",
    )
    process_truth_audit = _audit_process_certificates(process_certificates, truth_processes)

    boundary_summary = raw_boundary_audit.groupby(["panel", "product"], as_index=False).agg(
        n_response_keys=("truth_covered", "size"),
        n_complete_intervals=("interval_status", lambda x: int(pd.Series(x).astype(str).eq("complete").sum())),
        boundary_coverage=("truth_covered", "mean"),
        mean_normalized_width=("normalized_width", "mean"),
    )
    calibrated_summary = calibrated_boundary_audit.groupby("panel", as_index=False).agg(
        n_calibrated_response_keys=("truth_covered", "size"),
        n_complete_calibrated_intervals=("audit_interval_status", lambda x: int(pd.Series(x).astype(str).eq("complete").sum())),
        v2_5_calibrated_boundary_coverage=("truth_covered", "mean"),
        v2_5_mean_calibrated_width=("calibrated_normalized_width", "mean"),
    )
    comparator = boundary_summary.loc[
        boundary_summary["product"].astype(str).eq("complete_adequate_certificate"),
        ["panel", "boundary_coverage"],
    ].rename(columns={"boundary_coverage": "complete_adequate_boundary_coverage"})
    process_panel = process_truth_audit.groupby("panel", as_index=False).agg(
        n_validation_taxa=("species", "nunique"),
        n_complete_process_certificates=("certificate_status", lambda x: int(pd.Series(x).astype(str).eq("complete").sum())),
        total_false_required_processes=("n_false_required_processes", "sum"),
        minimum_possible_process_recall=("possible_process_recall", "min"),
        mean_possible_process_precision=("possible_process_precision", "mean"),
    )
    boundary_complete_species = (
        raw_envelopes.assign(complete=raw_envelopes["interval_status"].astype(str).eq("complete"))
        .groupby(["panel", "species", "product"], as_index=False)
        .agg(all_keys_complete=("complete", "all"))
        .groupby(["panel", "species"], as_index=False)
        .agg(all_products_complete=("all_keys_complete", "all"))
    )
    boundary_panel = boundary_complete_species.groupby("panel", as_index=False).agg(
        n_complete_boundary_certificates=("all_products_complete", "sum")
    )
    panel_summary = (
        process_panel.merge(boundary_panel, on="panel", validate="one_to_one")
        .merge(comparator, on="panel", validate="one_to_one")
        .merge(calibrated_summary, on="panel", validate="one_to_one")
        .sort_values("panel", kind="mergesort")
        .reset_index(drop=True)
    )
    decision = v2_5_decision(panel_summary)

    result_contract = {
        "purpose": "product_a_v2_5_predeclared_fresh_validation_decision",
        "source_base_contract_sha256": base_contract.sha256,
        "source_calibration_contract_sha256": calibration_contract["source_contract_sha256"],
        "source_calibration_run_id": str(calibration_run_id),
        "source_calibration_head_sha": str(calibration_head_sha),
        "source_calibration_artifact_id": str(calibration_artifact_id),
        "source_calibration_artifact_digest": str(calibration_artifact_digest),
        "n_model_only_validation_workers": len(workers["contracts"]),
        "all_process_and_boundary_products_written_before_truth_read": True,
        "pretruth_fingerprints": fingerprints,
        "validation_generating_truth_read_after_product_freeze": True,
        "validation_truth_used_for_calibration": False,
        "candidate_selection_performed_during_validation": False,
        "scientific_threshold_tuning_performed_during_validation": False,
        "decision": str(decision.iloc[0]["decision"]),
        "process_support": bool(decision.iloc[0]["process_support"]),
        "boundary_support": bool(decision.iloc[0]["boundary_support"]),
        "scientific_promotion_allowed": False,
        "known_truth_result_directly_allows_empirical_promotion": False,
        "product_b_unblocked": False,
    }

    outputs = {
        "worker_contracts": pd.DataFrame(workers["contracts"]),
        "expected_members": expected,
        "expected_response_keys": keys,
        "fit_ledger": fits,
        "response_estimates": responses,
        "truth_response": truth_response,
        "truth_processes": truth_processes,
        "raw_boundary_audit": raw_boundary_audit,
        "calibrated_boundary_audit": calibrated_boundary_audit,
        "process_truth_audit": process_truth_audit,
        "boundary_summary": boundary_summary,
        "panel_summary": panel_summary,
        "decision": decision,
    }
    for name, frame in outputs.items():
        frame.to_csv(out / f"{name}.csv", index=False)
    (out / "contract.json").write_text(
        json.dumps(result_contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"contract": result_contract, **outputs}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-contract", required=True)
    parser.add_argument("--validation-contract", required=True)
    parser.add_argument("--worker-root", required=True)
    parser.add_argument("--discovery-root", required=True)
    parser.add_argument("--calibration-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--calibration-run-id", required=True)
    parser.add_argument("--calibration-head-sha", required=True)
    parser.add_argument("--calibration-artifact-id", required=True)
    parser.add_argument("--calibration-artifact-digest", required=True)
    args = parser.parse_args(argv)
    run_v2_5_validation_aggregate(
        base_contract_path=args.base_contract,
        validation_contract_path=args.validation_contract,
        worker_root=args.worker_root,
        discovery_root=args.discovery_root,
        calibration_root=args.calibration_root,
        output_dir=args.output_dir,
        calibration_run_id=args.calibration_run_id,
        calibration_head_sha=args.calibration_head_sha,
        calibration_artifact_id=args.calibration_artifact_id,
        calibration_artifact_digest=args.calibration_artifact_digest,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
