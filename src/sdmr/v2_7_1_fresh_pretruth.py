"""Freeze one fresh v2.7.1 part before any sealed environment is opened."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .candidate_outer_fold_evidence import require_complete_outer_fold_evidence
from .niche_recovery_selection import RECOVERY_DIRECTIONS, select_generalization_gated_niche_recovery_protocol
from .v2_6_empirical_pretruth_aggregate import (
    EXPECTED_FOLDS,
    M_NAMES,
    _auc_representative,
    _decorate_for_complete_gate,
    _frame_sha256,
    _process_statuses,
)
from .v2_7_1_fresh_contract import load_v2_7_1_fresh_confirmation_contract

PURPOSE = "product_a_v2_7_1_fresh_part_pretruth_freeze"
WORKER_PURPOSE = "product_a_v2_7_1_fresh_model_pool_worker"


def _worker_contracts(root: Path) -> tuple[list[dict], dict[str, Path]]:
    contracts: list[dict] = []
    roots: dict[str, Path] = {}
    for path in sorted(root.rglob("contract.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") != WORKER_PURPOSE:
            continue
        if payload.get("sealed_occurrence_environment_read") is not False:
            raise ValueError("fresh pretruth received a worker that opened sealed environments")
        if payload.get("sealed_occurrence_used_for_selection") is not False:
            raise ValueError("fresh pretruth received sealed-selected evidence")
        taxon = str(payload.get("taxon", ""))
        if not taxon or taxon in roots:
            raise ValueError("fresh pretruth worker taxon missing or duplicated")
        contracts.append(payload); roots[taxon] = path.parent
    if len(contracts) != 12:
        raise ValueError(f"fresh part requires exactly 12 taxon workers, found {len(contracts)}")
    if len(roots) != 12:
        raise ValueError("fresh worker taxa are not unique")
    if len({int(c["part_seed"]) for c in contracts}) != 1:
        raise ValueError("fresh pretruth mixed part seeds")
    return contracts, roots


def _write_unavailable(
    out: Path, *, contract: dict, workers: list[dict], reason: str,
) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    taxa = tuple(sorted(str(c["taxon"]) for c in workers))
    domains = tuple(str(x) for x in contract["fixed_design"]["process_domains"])
    process = pd.DataFrame([
        {"taxon": taxon, "process_domain": domain, "status": "unavailable",
         "n_expected_routes": 8, "n_observed_routes": 0, "n_complete_routes": 0, "n_adequate_routes": 0}
        for taxon in taxa for domain in domains
    ])
    process.to_csv(out / "pretruth_process_status.csv", index=False)
    pd.DataFrame().to_csv(out / "pretruth_base_complete_cell_ledger.csv", index=False)
    pd.DataFrame().to_csv(out / "pretruth_base_complete_candidate_summary.csv", index=False)
    pd.DataFrame().to_csv(out / "pretruth_base_adequacy_gate.csv", index=False)
    pd.DataFrame().to_csv(out / "pretruth_ecological_selection.csv", index=False)
    pd.DataFrame().to_csv(out / "pretruth_auc_selection.csv", index=False)
    pd.DataFrame().to_csv(out / "pretruth_knockout_route_status.csv", index=False)
    pd.DataFrame(workers).to_csv(out / "pretruth_worker_contracts.csv", index=False)
    pd.DataFrame().to_csv(out / "pretruth_fingerprints.csv", index=False)
    result = {
        "purpose": PURPOSE,
        "available": False,
        "unavailable_reason": str(reason),
        "part_seed": int(workers[0]["part_seed"]),
        "n_taxa": 12,
        "M_specs": list(M_NAMES),
        "expected_outer_folds": EXPECTED_FOLDS,
        "complete_adequate_candidates": [],
        "ecological_representative": None,
        "auc_representative": None,
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_candidate_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "sealed_audit_authorized": False,
        "structural_or_audit_abstention_makes_part_unavailable": True,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_fresh_pretruth(
    *, contract_path: str | Path, worker_root: str | Path, output_dir: str | Path,
) -> dict[str, object]:
    contract = load_v2_7_1_fresh_confirmation_contract(contract_path)
    workers, roots = _worker_contracts(Path(worker_root))
    out = Path(output_dir)
    unavailable = [c for c in workers if c.get("available") is not True]
    if unavailable:
        details = "; ".join(
            f"{c['taxon']}:{c.get('unavailable_stage')}:{c.get('unavailable_reason')}" for c in unavailable
        )
        return _write_unavailable(out, contract=contract, workers=workers, reason=details)

    base_frames, knockout_frames = [], []
    for taxon in sorted(roots):
        root = roots[taxon]
        base = pd.read_csv(root / "base_fold_metrics.csv")
        knockout = pd.read_csv(root / "knockout_fold_metrics.csv")
        if base.empty:
            return _write_unavailable(out, contract=contract, workers=workers, reason=f"{taxon}:base_metrics_empty")
        base_frames.append(base)
        if not knockout.empty:
            knockout_frames.append(knockout)
    base = pd.concat(base_frames, ignore_index=True)
    knockout = pd.concat(knockout_frames, ignore_index=True) if knockout_frames else pd.DataFrame()
    taxa = tuple(sorted(str(c["taxon"]) for c in workers))
    required_metrics = ("presence_rank", *tuple(RECOVERY_DIRECTIONS))
    complete = require_complete_outer_fold_evidence(
        _decorate_for_complete_gate(base), discovery_taxa=taxa, perturbations=M_NAMES,
        required_columns=required_metrics, expected_outer_folds=EXPECTED_FOLDS,
    )
    if not complete.eligible_candidates:
        return _write_unavailable(out, contract=contract, workers=workers, reason="no base procedure has complete 12-taxon x 3-M x 4-fold evidence")
    complete_metrics = base.loc[base["candidate"].astype(str).isin(complete.eligible_candidates)].copy()
    adequacy = contract["fixed_design"]["prediction_adequacy"]
    try:
        ecological = select_generalization_gated_niche_recovery_protocol(
            complete_metrics,
            chance_auc=float(adequacy["chance_auc"]),
            minimum_auc_margin=float(adequacy["minimum_auc_margin"]),
            auc_sem_multiplier=float(adequacy["auc_sem_multiplier"]),
        )
    except ValueError as exc:
        return _write_unavailable(out, contract=contract, workers=workers, reason=f"prediction_adequacy:{exc}")
    adequate_candidates = tuple(ecological.eligible_candidates)
    ecological_rep = str(ecological.candidate)
    try:
        auc_rep, auc_summary = _auc_representative(complete_metrics, adequate_candidates)
    except ValueError as exc:
        return _write_unavailable(out, contract=contract, workers=workers, reason=f"auc_comparator:{exc}")

    domains = tuple(str(x) for x in contract["fixed_design"]["process_domains"])
    process_status, knockout_routes = _process_statuses(knockout, taxa=taxa, domains=domains, adequacy=adequacy)
    if len(process_status) != 12 * len(domains):
        return _write_unavailable(out, contract=contract, workers=workers, reason="process_status_denominator_incomplete")

    out.mkdir(parents=True, exist_ok=True)
    complete.cell_ledger.to_csv(out / "pretruth_base_complete_cell_ledger.csv", index=False)
    complete.candidate_summary.to_csv(out / "pretruth_base_complete_candidate_summary.csv", index=False)
    ecological.gate_summary.to_csv(out / "pretruth_base_adequacy_gate.csv", index=False)
    ecological.recovery_selection.summary.to_csv(out / "pretruth_ecological_selection.csv", index=False)
    auc_summary.to_csv(out / "pretruth_auc_selection.csv", index=False)
    process_status.to_csv(out / "pretruth_process_status.csv", index=False)
    knockout_routes.to_csv(out / "pretruth_knockout_route_status.csv", index=False)
    pd.DataFrame(workers).to_csv(out / "pretruth_worker_contracts.csv", index=False)
    fingerprints = {
        "complete_candidate_summary_sha256": _frame_sha256(complete.candidate_summary, ["candidate"]),
        "ecological_selection_sha256": _frame_sha256(ecological.recovery_selection.summary, ["candidate"]),
        "auc_selection_sha256": _frame_sha256(auc_summary, ["candidate"]),
        "process_status_sha256": _frame_sha256(process_status, ["taxon", "process_domain"]),
        "knockout_route_status_sha256": _frame_sha256(knockout_routes, ["taxon", "process_domain", "candidate"]),
    }
    pd.DataFrame([{"name": k, "sha256": v} for k, v in fingerprints.items()]).to_csv(out / "pretruth_fingerprints.csv", index=False)
    result = {
        "purpose": PURPOSE,
        "available": True,
        "unavailable_reason": None,
        "part_seed": int(workers[0]["part_seed"]),
        "n_taxa": 12,
        "M_specs": list(M_NAMES),
        "expected_outer_folds": EXPECTED_FOLDS,
        "complete_adequate_candidates": list(adequate_candidates),
        "ecological_representative": ecological_rep,
        "auc_representative": auc_rep,
        "pretruth_fingerprints": fingerprints,
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_used_for_candidate_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "sealed_audit_authorized": True,
        "structural_or_audit_abstention_makes_part_unavailable": True,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(); p.add_argument("--contract", required=True); p.add_argument("--worker-root", required=True); p.add_argument("--output-dir", required=True)
    a = p.parse_args(argv); run_fresh_pretruth(contract_path=a.contract, worker_root=a.worker_root, output_dir=a.output_dir); return 0


if __name__ == "__main__":
    raise SystemExit(main())
