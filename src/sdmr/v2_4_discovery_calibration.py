"""Aggregate v2.4 discovery refits and freeze discovery-only calibration.

All worker products are model-only. This module first reconstructs every expected
product envelope from the frozen member denominator. Only after all raw envelopes
exist does it recreate discovery generating truth, audit coverage and freeze the
maximum normalized outside-envelope miss for each panel x predictor x quantity.
Validation taxa and validation truth are never simulated or read here.
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
from .process_exclusion_certificate import (
    apply_discovery_interval_calibration,
    build_complete_refit_envelope,
    calibrate_discovery_interval_expansion,
)
from .v2_1_known_truth_gate_ablation import CANONICAL_M, M_SPECS, _simulate_taxon
from .v2_4_exclusion_certificate_experiment import load_exclusion_certificate_config
from .v2_4_refit_contract import (
    GROUPS,
    PANELS,
    SOURCE_ARTIFACTS,
    SOURCE_HEAD_SHA,
    SOURCE_RUN_ID,
    load_refit_contract,
)


PRODUCTS = (
    "canonical_auc_point",
    "complete_adequate_certificate",
    "v2_3_mean_pareto_certificate",
    "v2_4_exclusion_calibrated_certificate",
)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _split_csv(value: object) -> tuple[str, ...]:
    if value is None or pd.isna(value) or not str(value):
        return ()
    return tuple(x for x in str(value).split(",") if x)


def _load_workers(root: Path) -> dict[str, pd.DataFrame | list[dict[str, Any]]]:
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
        if contract.get("role") != "discovery":
            raise ValueError("discovery calibration input contains a validation worker")
        if contract.get("generating_truth_read") is not False:
            raise ValueError("worker artifact crossed the generating-truth barrier")
        if contract.get("real_empirical_data_read") is not False:
            raise ValueError("worker artifact read empirical data")
        worker_dir = path.parent
        contracts.append(contract)
        expected = _read_csv(worker_dir / "expected_members.csv")
        keys = _read_csv(worker_dir / "expected_response_keys.csv")
        fits = _read_csv(worker_dir / "fit_ledger.csv")
        responses = _read_csv(worker_dir / "response_estimates.csv")
        candidates = _read_csv(worker_dir / "frozen_candidates.csv")
        for frame, label in (
            (expected, "expected_members"),
            (keys, "expected_response_keys"),
            (fits, "fit_ledger"),
            (candidates, "frozen_candidates"),
        ):
            if frame.empty:
                raise ValueError(f"worker {worker_dir} has empty {label}")
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
            f"expected {expected_workers} discovery workers, found {len(contracts)}"
        )
    worker_keys = {
        (
            str(contract["panel"]),
            int(contract["taxon_index"]),
            str(contract["group"]),
        )
        for contract in contracts
    }
    if len(worker_keys) != expected_workers:
        raise ValueError("discovery worker panel x taxon x group keys are not unique")
    return {
        "contracts": contracts,
        "expected_members": pd.concat(expected_frames, ignore_index=True),
        "expected_response_keys": pd.concat(key_frames, ignore_index=True),
        "fit_ledger": pd.concat(fit_frames, ignore_index=True),
        "response_estimates": (
            pd.concat(response_frames, ignore_index=True)
            if response_frames
            else pd.DataFrame()
        ),
        "frozen_candidates": pd.concat(candidate_frames, ignore_index=True),
    }


def _source_products(discovery_root: Path, panel: str) -> dict[str, tuple[str, ...]]:
    products = pd.read_csv(discovery_root / panel / "base_products.csv")
    indexed = products.set_index("product")
    required = {
        "canonical_auc_point",
        "complete_adequate_certificate",
        "ecological_pareto_certificate",
    }
    if not required <= set(indexed.index.astype(str)):
        raise ValueError(f"source discovery products are incomplete for {panel}")
    result: dict[str, tuple[str, ...]] = {}
    for source_name, target_name in (
        ("canonical_auc_point", "canonical_auc_point"),
        ("complete_adequate_certificate", "complete_adequate_certificate"),
        ("ecological_pareto_certificate", "v2_3_mean_pareto_certificate"),
    ):
        row = indexed.loc[source_name]
        if str(row["status"]) != "frozen":
            raise ValueError(f"source product {source_name} is not frozen for {panel}")
        result[target_name] = tuple(sorted(_split_csv(row["candidates"])))
    return result


def _product_expected_members(
    expected: pd.DataFrame,
    *,
    panel: str,
    product: str,
    source_products: dict[str, tuple[str, ...]],
) -> pd.DataFrame:
    data = expected.loc[expected["panel"].astype(str).eq(panel)].copy()
    if product == "canonical_auc_point":
        candidates = set(source_products[product])
        keep = (
            data["group"].astype(str).eq("base")
            & data["candidate"].astype(str).isin(candidates)
            & data["perturbation"].astype(str).eq(CANONICAL_M)
            & data["fit_mode"].astype(str).eq("full_fit")
        )
    elif product in {
        "complete_adequate_certificate",
        "v2_3_mean_pareto_certificate",
    }:
        candidates = set(source_products[product])
        keep = (
            data["group"].astype(str).eq("base")
            & data["candidate"].astype(str).isin(candidates)
            & data["perturbation"].astype(str).isin(M_SPECS)
            & data["fit_mode"].astype(str).eq("full_fit")
        )
    elif product == "v2_4_exclusion_calibrated_certificate":
        keep = (
            data["perturbation"].astype(str).isin(M_SPECS)
            & data["fit_mode"].astype(str).eq("spatial_refit")
        )
    else:
        raise ValueError(f"unknown v2.4 product: {product}")
    subset = data.loc[keep].copy()
    if subset.empty:
        raise ValueError(f"product {product} has no expected members for {panel}")
    return subset


def _truth_audit(
    envelopes: pd.DataFrame,
    truth: pd.DataFrame,
    *,
    lower_col: str = "lower_bound",
    upper_col: str = "upper_bound",
    status_col: str = "interval_status",
) -> pd.DataFrame:
    audit = envelopes.merge(
        truth[["panel", "species", "predictor", "quantity", "truth_estimate"]],
        on=["panel", "species", "predictor", "quantity"],
        how="outer",
        validate="one_to_one",
    )
    for column in (lower_col, upper_col, "truth_estimate"):
        audit[column] = pd.to_numeric(audit[column], errors="coerce")
    complete = (
        audit[status_col].astype(str).eq("complete")
        & np.isfinite(audit[lower_col])
        & np.isfinite(audit[upper_col])
        & np.isfinite(audit["truth_estimate"])
    )
    audit["truth_covered"] = (
        complete
        & (audit["truth_estimate"] >= audit[lower_col] - 1e-12)
        & (audit["truth_estimate"] <= audit[upper_col] + 1e-12)
    )
    return audit


def run_discovery_calibration(
    *,
    panel_config: str | Path,
    refit_contract: str | Path,
    worker_root: str | Path,
    discovery_root: str | Path,
) -> dict[str, Any]:
    """Freeze raw discovery envelopes, then open discovery truth and calibrate."""

    load_refit_contract(refit_contract)
    config, panels, _ = load_exclusion_certificate_config(panel_config)
    workers = _load_workers(Path(worker_root))
    expected = workers["expected_members"]
    keys = workers["expected_response_keys"]
    fits = workers["fit_ledger"]
    responses = workers["response_estimates"]
    if responses.empty:
        raise ValueError("no successful discovery refit responses were supplied")

    expected = expected.drop_duplicates().reset_index(drop=True)
    keys = keys.drop_duplicates().reset_index(drop=True)
    if expected.duplicated(["panel", "species", "member_id"]).any():
        raise ValueError("expected discovery members are duplicated")
    if responses.duplicated(
        ["panel", "species", "member_id", "predictor", "quantity"]
    ).any():
        raise ValueError("discovery response estimates are duplicated")

    discovery_root = Path(discovery_root)
    raw_frames: list[pd.DataFrame] = []
    membership_frames: list[pd.DataFrame] = []
    source_product_rows: list[dict[str, object]] = []
    for panel in PANELS:
        source_products = _source_products(discovery_root, panel)
        for product in PRODUCTS:
            member_rows = _product_expected_members(
                expected,
                panel=panel,
                product=product,
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
            envelope["envelope_stage"] = "raw_before_truth"
            raw_frames.append(envelope)
            membership = member_rows.copy()
            membership["product"] = product
            membership_frames.append(membership)
            source_product_rows.append(
                {
                    "panel": panel,
                    "product": product,
                    "n_candidates": int(member_rows["candidate"].nunique()),
                    "n_expected_members": len(member_rows),
                }
            )

    # Every raw envelope is fully reconstructed before discovery truth is opened.
    raw_envelopes = pd.concat(raw_frames, ignore_index=True)
    product_membership = pd.concat(membership_frames, ignore_index=True)

    truth_frames: list[pd.DataFrame] = []
    for panel in panels:
        for spec in panel.discovery:
            simulation = _simulate_taxon(
                spec,
                n_cells=int(config["simulation_contract"]["n_cells"]),
                n_occurrences=int(config["simulation_contract"]["n_occurrences"]),
                n_target_group=int(config["simulation_contract"]["n_target_group"]),
            )
            environment = simulation.environment
            truth_values = environment[simulation.true_suitability_column].to_numpy(float)
            response_predictors = tuple(infer_response_predictors(environment))
            truth = response_point_estimates(
                environment,
                truth_values,
                response_predictors,
                member_id="truth",
            ).rename(columns={"estimate": "truth_estimate"})
            truth["panel"] = panel.name
            truth["species"] = spec.taxon
            truth["family"] = spec.family
            truth["seed"] = int(spec.seed)
            truth_frames.append(truth)
    discovery_truth = pd.concat(truth_frames, ignore_index=True)

    raw_truth_audit = _truth_audit(raw_envelopes, discovery_truth)
    calibration_frames: list[pd.DataFrame] = []
    calibration_audit_frames: list[pd.DataFrame] = []
    calibrated_frames: list[pd.DataFrame] = []
    for panel in PANELS:
        v24 = raw_envelopes.loc[
            raw_envelopes["panel"].astype(str).eq(panel)
            & raw_envelopes["product"].astype(str).eq(
                "v2_4_exclusion_calibrated_certificate"
            )
        ].copy()
        panel_truth = discovery_truth.loc[
            discovery_truth["panel"].astype(str).eq(panel)
        ].copy()
        calibration, audit = calibrate_discovery_interval_expansion(
            v24,
            panel_truth.rename(columns={"truth_estimate": "estimate"}),
        )
        calibration["panel"] = panel
        audit["panel"] = panel
        calibrated = apply_discovery_interval_calibration(v24, calibration)
        calibrated["panel"] = panel
        calibrated["product"] = "v2_4_exclusion_calibrated_certificate"
        calibrated["envelope_stage"] = "discovery_calibrated"
        calibration_frames.append(calibration)
        calibration_audit_frames.append(audit)
        calibrated_frames.append(calibrated)

    calibration = pd.concat(calibration_frames, ignore_index=True)
    calibration_audit = pd.concat(calibration_audit_frames, ignore_index=True)
    calibrated_envelopes = pd.concat(calibrated_frames, ignore_index=True)
    calibrated_for_audit = calibrated_envelopes.rename(
        columns={
            "calibrated_lower_bound": "audit_lower_bound",
            "calibrated_upper_bound": "audit_upper_bound",
            "calibrated_interval_status": "audit_interval_status",
        }
    )
    calibrated_truth_audit = _truth_audit(
        calibrated_for_audit,
        discovery_truth,
        lower_col="audit_lower_bound",
        upper_col="audit_upper_bound",
        status_col="audit_interval_status",
    )

    product_summary = (
        raw_truth_audit.groupby(["panel", "product"], as_index=False)
        .agg(
            n_discovery_response_keys=("truth_covered", "size"),
            n_complete_intervals=(
                "interval_status",
                lambda values: int(pd.Series(values).astype(str).eq("complete").sum()),
            ),
            raw_boundary_coverage=("truth_covered", "mean"),
            mean_raw_normalized_width=("normalized_width", "mean"),
        )
        .sort_values(["panel", "product"], kind="mergesort")
        .reset_index(drop=True)
    )
    calibrated_summary = (
        calibrated_truth_audit.groupby("panel", as_index=False)
        .agg(
            n_calibrated_response_keys=("truth_covered", "size"),
            n_complete_calibrated_intervals=(
                "audit_interval_status",
                lambda values: int(pd.Series(values).astype(str).eq("complete").sum()),
            ),
            calibrated_boundary_coverage=("truth_covered", "mean"),
            mean_calibrated_normalized_width=(
                "calibrated_normalized_width",
                "mean",
            ),
        )
    )
    product_summary = product_summary.merge(
        calibrated_summary,
        on="panel",
        how="left",
        validate="many_to_one",
    )

    contract = {
        "purpose": "product_a_v2_4_discovery_refit_and_calibration_freeze",
        "scientific_promotion_run": False,
        "scientific_promotion_allowed": False,
        "real_empirical_data_read": False,
        "old_external_sealed_outcomes_read": False,
        "source_discovery_run_id": SOURCE_RUN_ID,
        "source_discovery_head_sha": SOURCE_HEAD_SHA,
        "source_discovery_artifacts": SOURCE_ARTIFACTS,
        "n_model_only_workers": len(workers["contracts"]),
        "all_raw_discovery_envelopes_frozen_before_truth_read": True,
        "discovery_generating_truth_read_after_raw_freeze": True,
        "validation_taxa_simulated_or_read": False,
        "validation_truth_read": False,
        "calibration_uses_validation_truth": False,
        "n_expected_members": len(expected),
        "n_successful_members": int(
            fits["fit_status"].astype(str).eq("success").sum()
        ),
        "n_raw_envelopes": len(raw_envelopes),
        "n_complete_raw_envelopes": int(
            raw_envelopes["interval_status"].astype(str).eq("complete").sum()
        ),
        "n_complete_calibration_keys": int(
            calibration["calibration_status"].astype(str).eq("complete").sum()
        ),
        "validation_stage_allowed": bool(
            calibration["calibration_status"].astype(str).eq("complete").all()
        ),
    }
    return {
        "contract": contract,
        "worker_contracts": pd.DataFrame(workers["contracts"]),
        "frozen_candidates": workers["frozen_candidates"],
        "product_membership": product_membership,
        "source_product_counts": pd.DataFrame(source_product_rows),
        "expected_members": expected,
        "expected_response_keys": keys,
        "fit_ledger": fits,
        "response_estimates": responses,
        "raw_envelopes": raw_envelopes,
        "discovery_truth": discovery_truth,
        "raw_truth_audit": raw_truth_audit,
        "calibration": calibration,
        "calibration_audit": calibration_audit,
        "calibrated_envelopes": calibrated_envelopes,
        "calibrated_truth_audit": calibrated_truth_audit,
        "product_summary": product_summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-config", required=True)
    parser.add_argument("--refit-contract", required=True)
    parser.add_argument("--worker-root", required=True)
    parser.add_argument("--discovery-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    result = run_discovery_calibration(
        panel_config=args.panel_config,
        refit_contract=args.refit_contract,
        worker_root=args.worker_root,
        discovery_root=args.discovery_root,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name in (
        "worker_contracts",
        "frozen_candidates",
        "product_membership",
        "source_product_counts",
        "expected_members",
        "expected_response_keys",
        "fit_ledger",
        "response_estimates",
        "raw_envelopes",
        "discovery_truth",
        "raw_truth_audit",
        "calibration",
        "calibration_audit",
        "calibrated_envelopes",
        "calibrated_truth_audit",
        "product_summary",
    ):
        result[name].to_csv(out / f"{name}.csv", index=False)
    (out / "contract.json").write_text(
        json.dumps(result["contract"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
