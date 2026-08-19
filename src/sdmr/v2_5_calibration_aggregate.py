"""Freeze Product-A v2.5 calibration radii before fresh validation.

All model-only calibration workers are verified first. Raw refit envelopes are
written and fingerprinted before any calibration generating truth is recreated.
Only then are the predeclared calibration taxa opened to estimate fixed expansion
radii. Fresh validation taxa/seeds are never simulated or read here.
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
from .known_truth_response import infer_response_predictors
from .process_exclusion_certificate import build_complete_refit_envelope
from .v2_1_known_truth_gate_ablation import _simulate_taxon
from .v2_4_refit_contract import GROUPS
from .v2_5_contract import load_v2_5_contract


EXPECTED_WORKERS = 3 * 5 * len(GROUPS)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_workers(root: Path, *, contract_sha256: str) -> dict[str, Any]:
    contracts: list[dict[str, Any]] = []
    expected_frames: list[pd.DataFrame] = []
    key_frames: list[pd.DataFrame] = []
    fit_frames: list[pd.DataFrame] = []
    response_frames: list[pd.DataFrame] = []
    for path in sorted(root.rglob("contract.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("purpose") != "product_a_v2_5_model_only_refit_worker":
            continue
        if row.get("role") != "calibration":
            raise ValueError("calibration aggregate contains a non-calibration worker")
        if row.get("contract_sha256") != contract_sha256:
            raise ValueError("calibration worker used a different frozen v2.5 contract")
        if row.get("generating_truth_read") is not False:
            raise ValueError("calibration worker crossed the generating-truth barrier")
        if row.get("real_empirical_data_read") is not False:
            raise ValueError("calibration worker read real empirical data")
        if row.get("candidate_selection_performed") is not False:
            raise ValueError("calibration worker reselected candidates")
        if row.get("scientific_threshold_tuning_performed") is not False:
            raise ValueError("calibration worker tuned scientific thresholds")
        worker = path.parent
        expected = _read_csv(worker / "expected_members.csv")
        keys = _read_csv(worker / "expected_response_keys.csv")
        fits = _read_csv(worker / "fit_ledger.csv")
        responses = _read_csv(worker / "response_estimates.csv")
        if expected.empty or keys.empty or fits.empty:
            raise ValueError(f"incomplete calibration worker artifact: {worker}")
        contracts.append(row)
        expected_frames.append(expected)
        key_frames.append(keys)
        fit_frames.append(fits)
        if not responses.empty:
            response_frames.append(responses)

    if len(contracts) != EXPECTED_WORKERS:
        raise ValueError(
            f"expected {EXPECTED_WORKERS} calibration workers, found {len(contracts)}"
        )
    keys = {
        (str(row["panel"]), int(row["taxon_index"]), str(row["group"]))
        for row in contracts
    }
    if len(keys) != EXPECTED_WORKERS:
        raise ValueError("calibration worker panel x taxon x group keys are not unique")
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
    }


def calibrate_complete_calibration_taxa(
    raw_envelopes: pd.DataFrame,
    calibration_truth: pd.DataFrame,
    *,
    minimum_complete_taxa: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calibrate over complete taxa exactly as frozen in the v2.5 contract.

    v2.5 deliberately differs from the v2.4 discovery helper: a response key is
    calibrated from the maximum normalized outside-envelope miss among *complete*
    calibration taxa, provided the predeclared minimum number of complete taxa is
    available. Incomplete taxa remain visible in the audit and cannot contribute
    to the radius. This is the contract frozen before calibration outcomes were
    opened; it is not an outcome-adaptive relaxation.
    """

    minimum_complete_taxa = int(minimum_complete_taxa)
    if minimum_complete_taxa < 1:
        raise ValueError("minimum_complete_taxa must be >= 1")
    envelope_required = {
        "species",
        "predictor",
        "quantity",
        "interval_status",
        "lower_bound",
        "upper_bound",
        "environment_span",
    }
    truth_required = {"species", "predictor", "quantity", "estimate"}
    missing_envelope = sorted(envelope_required - set(raw_envelopes.columns))
    missing_truth = sorted(truth_required - set(calibration_truth.columns))
    if missing_envelope:
        raise KeyError(f"raw calibration envelopes missing columns: {missing_envelope}")
    if missing_truth:
        raise KeyError(f"calibration truth missing columns: {missing_truth}")

    envelope = raw_envelopes.copy()
    truth = calibration_truth[
        ["species", "predictor", "quantity", "estimate"]
    ].copy().rename(columns={"estimate": "truth_estimate"})
    for frame in (envelope, truth):
        for column in ("species", "predictor", "quantity"):
            frame[column] = frame[column].astype(str)
    if truth.duplicated(["species", "predictor", "quantity"]).any():
        raise ValueError("calibration truth contains duplicate response keys")

    audit = envelope.merge(
        truth,
        on=["species", "predictor", "quantity"],
        how="outer",
        validate="one_to_one",
    )
    for column in (
        "lower_bound",
        "upper_bound",
        "environment_span",
        "truth_estimate",
    ):
        audit[column] = pd.to_numeric(audit[column], errors="coerce")
    complete = (
        audit["interval_status"].astype(str).eq("complete")
        & np.isfinite(audit["lower_bound"])
        & np.isfinite(audit["upper_bound"])
        & np.isfinite(audit["environment_span"])
        & (audit["environment_span"] > 0)
        & np.isfinite(audit["truth_estimate"])
    )
    below = audit["truth_estimate"] < audit["lower_bound"]
    above = audit["truth_estimate"] > audit["upper_bound"]
    miss = np.full(len(audit), np.nan, dtype=float)
    inside = complete & ~below & ~above
    miss[inside.to_numpy(bool)] = 0.0
    below_complete = complete & below
    above_complete = complete & above
    miss[below_complete.to_numpy(bool)] = (
        audit.loc[below_complete, "lower_bound"]
        - audit.loc[below_complete, "truth_estimate"]
    ) / audit.loc[below_complete, "environment_span"]
    miss[above_complete.to_numpy(bool)] = (
        audit.loc[above_complete, "truth_estimate"]
        - audit.loc[above_complete, "upper_bound"]
    ) / audit.loc[above_complete, "environment_span"]
    audit["complete_calibration_taxon"] = complete
    audit["normalized_outside_interval_miss"] = miss
    audit["raw_interval_covers_truth"] = inside

    rows: list[dict[str, object]] = []
    for key, group in audit.groupby(["predictor", "quantity"], sort=True):
        predictor, quantity = (str(x) for x in key)
        values = pd.to_numeric(
            group["normalized_outside_interval_miss"], errors="coerce"
        ).to_numpy(float)
        finite = np.isfinite(values)
        n_complete = int(finite.sum())
        available = n_complete >= minimum_complete_taxa
        rows.append(
            {
                "predictor": predictor,
                "quantity": quantity,
                "calibration_status": (
                    "complete"
                    if available
                    else "unavailable_insufficient_complete_calibration_taxa"
                ),
                "n_discovery_keys": int(len(values)),
                "n_evaluable_discovery_keys": n_complete,
                "minimum_complete_calibration_taxa": minimum_complete_taxa,
                "normalized_expansion_radius": (
                    float(np.max(values[finite])) if available else float("nan")
                ),
                "calibration_uses_validation_truth": False,
            }
        )
    return pd.DataFrame(rows), audit


def run_v2_5_calibration_aggregate(
    *,
    contract_path: str | Path,
    worker_root: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Freeze raw calibration envelopes, then open calibration truth exactly once."""

    contract = load_v2_5_contract(contract_path)
    workers = _load_workers(Path(worker_root), contract_sha256=contract.sha256)
    expected = workers["expected_members"].drop_duplicates().reset_index(drop=True)
    keys = workers["expected_response_keys"].drop_duplicates().reset_index(drop=True)
    responses = workers["response_estimates"]
    if responses.empty:
        raise ValueError("no successful calibration response estimates were supplied")

    if expected.duplicated(["panel", "species", "member_id"]).any():
        raise ValueError("expected calibration members are duplicated")
    if responses.duplicated(
        ["panel", "species", "member_id", "predictor", "quantity"]
    ).any():
        raise ValueError("calibration response estimates are duplicated")

    raw_frames: list[pd.DataFrame] = []
    for panel in ("panel_D1", "panel_D2", "panel_D3"):
        member_rows = expected.loc[
            expected["panel"].astype(str).eq(panel)
            & expected["fit_mode"].astype(str).eq("spatial_refit")
        ].copy()
        panel_responses = responses.merge(
            member_rows[["panel", "species", "member_id"]],
            on=["panel", "species", "member_id"],
            how="inner",
            validate="many_to_one",
        )
        panel_keys = keys.loc[keys["panel"].astype(str).eq(panel)].copy()
        envelope = build_complete_refit_envelope(
            panel_responses,
            member_rows,
            expected_response_keys=panel_keys,
        )
        envelope["panel"] = panel
        envelope["envelope_stage"] = "raw_before_calibration_truth"
        raw_frames.append(envelope)
    raw_envelopes = pd.concat(raw_frames, ignore_index=True)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / "raw_envelopes.csv"
    raw_envelopes.to_csv(raw_path, index=False)
    raw_sha256 = _sha256(raw_path)

    # Calibration truth is first recreated after the complete raw product is on disk.
    truth_frames: list[pd.DataFrame] = []
    simulation_contract = contract.payload["simulation_contract"]
    for panel in contract.panels:
        for spec in panel.calibration:
            simulation = _simulate_taxon(
                spec,
                n_cells=int(simulation_contract["n_cells"]),
                n_occurrences=int(simulation_contract["n_occurrences"]),
                n_target_group=int(simulation_contract["n_target_group"]),
            )
            environment = simulation.environment
            truth_values = environment[simulation.true_suitability_column].to_numpy(float)
            response_predictors = tuple(infer_response_predictors(environment))
            truth = response_point_estimates(
                environment,
                truth_values,
                response_predictors,
                member_id="truth",
            )
            truth["panel"] = panel.name
            truth["species"] = spec.taxon
            truth["family"] = spec.family
            truth["seed"] = int(spec.seed)
            truth_frames.append(truth)
    calibration_truth = pd.concat(truth_frames, ignore_index=True)

    calibration_frames: list[pd.DataFrame] = []
    audit_frames: list[pd.DataFrame] = []
    minimum_complete = contract.support_audit.minimum_support_per_key
    for panel in ("panel_D1", "panel_D2", "panel_D3"):
        panel_envelopes = raw_envelopes.loc[
            raw_envelopes["panel"].astype(str).eq(panel)
        ].copy()
        panel_truth = calibration_truth.loc[
            calibration_truth["panel"].astype(str).eq(panel)
        ].copy()
        calibration, audit = calibrate_complete_calibration_taxa(
            panel_envelopes,
            panel_truth,
            minimum_complete_taxa=minimum_complete,
        )
        calibration["panel"] = panel
        audit["panel"] = panel
        calibration_frames.append(calibration)
        audit_frames.append(audit)

    calibration = pd.concat(calibration_frames, ignore_index=True)
    calibration_audit = pd.concat(audit_frames, ignore_index=True)
    required = set(contract.support_audit.required_validation_keys)
    for panel in ("panel_D1", "panel_D2", "panel_D3"):
        subset = calibration.loc[calibration["panel"].astype(str).eq(panel)]
        observed = set(
            zip(subset["predictor"].astype(str), subset["quantity"].astype(str))
        )
        if observed != required:
            raise ValueError(f"panel {panel} calibration keys differ from frozen support keys")
        if not subset["calibration_status"].astype(str).eq("complete").all():
            unavailable = subset.loc[
                ~subset["calibration_status"].astype(str).eq("complete"),
                [
                    "predictor",
                    "quantity",
                    "calibration_status",
                    "n_evaluable_discovery_keys",
                ],
            ]
            raise ValueError(
                f"panel {panel} has unavailable calibration keys: "
                + unavailable.to_dict(orient="records").__repr__()
            )
        support = pd.to_numeric(
            subset["n_evaluable_discovery_keys"], errors="coerce"
        )
        if (support < minimum_complete).any():
            raise ValueError(f"panel {panel} violates frozen minimum calibration support")
        radius = pd.to_numeric(subset["normalized_expansion_radius"], errors="coerce")
        if not np.isfinite(radius).all():
            raise ValueError(f"panel {panel} has non-finite calibration radii")

    calibration.to_csv(out / "calibration.csv", index=False)
    calibration_audit.to_csv(out / "calibration_truth_audit.csv", index=False)
    calibration_truth.to_csv(out / "calibration_truth.csv", index=False)
    pd.DataFrame(workers["contracts"]).to_csv(out / "worker_contracts.csv", index=False)

    result_contract = {
        "purpose": "product_a_v2_5_frozen_calibration_radii",
        "source_contract_sha256": contract.sha256,
        "raw_envelopes_sha256_before_truth": raw_sha256,
        "n_model_only_calibration_workers": len(workers["contracts"]),
        "n_raw_response_keys": len(raw_envelopes),
        "n_calibration_keys": len(calibration),
        "minimum_complete_calibration_taxa_per_key": minimum_complete,
        "calibration_radius_uses_complete_taxa_only": True,
        "all_required_validation_keys_calibrated": True,
        "raw_envelopes_frozen_before_calibration_truth_read": True,
        "calibration_generating_truth_read_after_raw_freeze": True,
        "fresh_validation_taxa_simulated_or_read": False,
        "fresh_validation_truth_read": False,
        "validation_truth_used_for_calibration": False,
        "candidate_selection_performed_during_calibration": False,
        "scientific_threshold_tuning_performed_during_calibration": False,
        "scientific_promotion_allowed": False,
    }
    (out / "contract.json").write_text(
        json.dumps(result_contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "contract": result_contract,
        "raw_envelopes": raw_envelopes,
        "calibration": calibration,
        "calibration_audit": calibration_audit,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--worker-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    run_v2_5_calibration_aggregate(
        contract_path=args.contract,
        worker_root=args.worker_root,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
