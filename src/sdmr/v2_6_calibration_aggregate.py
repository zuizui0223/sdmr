"""Freeze Product-A v2.6 calibration before reserved validation is consumed."""
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
from .v2_5_calibration_aggregate import calibrate_complete_calibration_taxa
from .v2_6_contract import load_v2_6_contract


PANELS = ("panel_D1", "panel_D2", "panel_D3")
EXPECTED_WORKERS = 3 * 9 * len(GROUPS)
WORKER_PURPOSE = "product_a_v2_6_model_only_refit_worker"


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
        if row.get("purpose") != WORKER_PURPOSE:
            continue
        if row.get("contract_sha256") != contract_sha256:
            raise ValueError("v2.6 worker used a different frozen contract")
        if row.get("role") != "calibration":
            raise ValueError("v2.6 calibration aggregate contains validation worker")
        if row.get("generating_truth_read") is not False:
            raise ValueError("v2.6 worker crossed the generating-truth barrier")
        if row.get("candidate_selection_performed") is not False:
            raise ValueError("v2.6 worker reselected candidates")
        if row.get("scientific_threshold_tuning_performed") is not False:
            raise ValueError("v2.6 worker tuned scientific thresholds")
        worker = path.parent
        expected = _read_csv(worker / "expected_members.csv")
        keys = _read_csv(worker / "expected_response_keys.csv")
        fits = _read_csv(worker / "fit_ledger.csv")
        responses = _read_csv(worker / "response_estimates.csv")
        if expected.empty or keys.empty or fits.empty:
            raise ValueError(f"incomplete v2.6 worker artifact: {worker}")
        contracts.append(row)
        expected_frames.append(expected)
        key_frames.append(keys)
        fit_frames.append(fits)
        if not responses.empty:
            response_frames.append(responses)

    if len(contracts) != EXPECTED_WORKERS:
        raise ValueError(f"expected {EXPECTED_WORKERS} v2.6 workers, found {len(contracts)}")
    worker_keys = {
        (str(row["panel"]), int(row["taxon_index"]), str(row["group"]))
        for row in contracts
    }
    if len(worker_keys) != EXPECTED_WORKERS:
        raise ValueError("v2.6 panel x taxon x group worker keys are not unique")
    return {
        "contracts": contracts,
        "expected_members": pd.concat(expected_frames, ignore_index=True),
        "expected_response_keys": pd.concat(key_frames, ignore_index=True),
        "fit_ledger": pd.concat(fit_frames, ignore_index=True),
        "response_estimates": (
            pd.concat(response_frames, ignore_index=True)
            if response_frames else pd.DataFrame()
        ),
    }


def run_v2_6_calibration_aggregate(
    *, contract_path: str | Path, worker_root: str | Path, output_dir: str | Path
) -> dict[str, Any]:
    contract = load_v2_6_contract(contract_path)
    workers = _load_workers(Path(worker_root), contract_sha256=contract.sha256)
    expected = workers["expected_members"].drop_duplicates().reset_index(drop=True)
    keys = workers["expected_response_keys"].drop_duplicates().reset_index(drop=True)
    responses = workers["response_estimates"]
    if responses.empty:
        raise ValueError("no successful v2.6 calibration responses supplied")
    if expected.duplicated(["panel", "species", "member_id"]).any():
        raise ValueError("v2.6 expected members are duplicated")
    if responses.duplicated(
        ["panel", "species", "member_id", "predictor", "quantity"]
    ).any():
        raise ValueError("v2.6 response estimates are duplicated")

    raw_frames: list[pd.DataFrame] = []
    for panel in PANELS:
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
        envelope["envelope_stage"] = "v2_6_raw_before_calibration_truth"
        raw_frames.append(envelope)
    raw_envelopes = pd.concat(raw_frames, ignore_index=True)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / "raw_envelopes.csv"
    raw_envelopes.to_csv(raw_path, index=False)
    raw_sha256 = _sha256(raw_path)

    # Seeds 446-472 are first opened only after every raw model-only envelope is on disk.
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
            predictors = tuple(infer_response_predictors(environment))
            truth = response_point_estimates(
                environment, truth_values, predictors, member_id="truth"
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
    for panel in PANELS:
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
    unavailable_rows: list[dict[str, object]] = []
    for panel in PANELS:
        subset = calibration.loc[calibration["panel"].astype(str).eq(panel)]
        observed = set(zip(subset["predictor"].astype(str), subset["quantity"].astype(str)))
        if observed != required:
            raise ValueError(f"panel {panel} calibration keys differ from frozen support keys")
        bad = subset.loc[
            ~subset["calibration_status"].astype(str).eq("complete"),
            ["panel", "predictor", "quantity", "calibration_status", "n_evaluable_discovery_keys"],
        ]
        unavailable_rows.extend(bad.to_dict(orient="records"))
    if unavailable_rows:
        pd.DataFrame(unavailable_rows).to_csv(out / "unavailable_calibration_keys.csv", index=False)
        raise ValueError(f"v2.6 unavailable calibration keys: {unavailable_rows}")

    support = pd.to_numeric(calibration["n_evaluable_discovery_keys"], errors="coerce")
    radius = pd.to_numeric(calibration["normalized_expansion_radius"], errors="coerce")
    if (support < minimum_complete).any() or not np.isfinite(radius).all():
        raise ValueError("v2.6 complete calibration violates frozen support/radius contract")

    calibration.to_csv(out / "calibration.csv", index=False)
    calibration_audit.to_csv(out / "calibration_truth_audit.csv", index=False)
    calibration_truth.to_csv(out / "calibration_truth.csv", index=False)
    pd.DataFrame(workers["contracts"]).to_csv(out / "worker_contracts.csv", index=False)
    support_summary = (
        calibration[["panel", "predictor", "quantity", "n_evaluable_discovery_keys"]]
        .sort_values(["panel", "predictor", "quantity"], kind="mergesort")
        .reset_index(drop=True)
    )
    support_summary.to_csv(out / "calibration_support_summary.csv", index=False)

    result_contract = {
        "purpose": "product_a_v2_6_frozen_calibration_radii",
        "source_contract_sha256": contract.sha256,
        "raw_envelopes_sha256_before_truth": raw_sha256,
        "n_model_only_calibration_workers": len(workers["contracts"]),
        "n_calibration_taxa": 27,
        "n_soil_capable_calibration_taxa": 18,
        "n_calibration_keys": len(calibration),
        "minimum_complete_calibration_taxa_per_key": minimum_complete,
        "minimum_observed_complete_calibration_taxa_per_key": int(support.min()),
        "calibration_radius_uses_complete_taxa_only": True,
        "all_required_validation_keys_calibrated": True,
        "raw_envelopes_frozen_before_calibration_truth_read": True,
        "calibration_generating_truth_read_after_raw_freeze": True,
        "reserved_validation_seeds": [501,502,503,511,512,513,521,522,523],
        "reserved_validation_taxa_simulated_or_read": False,
        "reserved_validation_truth_read": False,
        "validation_truth_used_for_calibration": False,
        "candidate_selection_performed_during_calibration": False,
        "scientific_threshold_tuning_performed_during_calibration": False,
        "scientific_promotion_allowed": False,
    }
    (out / "contract.json").write_text(
        json.dumps(result_contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "contract": result_contract,
        "raw_envelopes": raw_envelopes,
        "calibration": calibration,
        "calibration_audit": calibration_audit,
        "support_summary": support_summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--worker-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    run_v2_6_calibration_aggregate(
        contract_path=args.contract,
        worker_root=args.worker_root,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
