"""Freeze one empirical part's model-pool products before sealed environments are opened."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .candidate_outer_fold_evidence import require_complete_outer_fold_evidence
from .niche_recovery_selection import RECOVERY_DIRECTIONS, select_generalization_gated_niche_recovery_protocol
from .v2_6_empirical_model_contract import load_v2_6_empirical_model_contract

M_NAMES = ("buffer_150km", "buffer_300km", "buffer_500km")
EXPECTED_FOLDS = 4


def _frame_sha256(frame: pd.DataFrame, sort_by: list[str]) -> str:
    stable = frame.sort_values(sort_by, kind="mergesort", na_position="last").reset_index(drop=True)
    return hashlib.sha256(stable.to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()


def _load_workers(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base_frames = []
    knockout_frames = []
    contracts = []
    for path in sorted(root.rglob("contract.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") != "product_a_v2_6_empirical_model_pool_worker":
            continue
        if payload.get("sealed_occurrence_environment_read") is not False:
            raise ValueError("empirical pretruth aggregate received a worker that opened sealed environments")
        if payload.get("sealed_occurrence_used_for_selection") is not False:
            raise ValueError("empirical pretruth aggregate received sealed-selected evidence")
        worker = path.parent
        base = pd.read_csv(worker / "base_fold_metrics.csv")
        knockout = pd.read_csv(worker / "knockout_fold_metrics.csv")
        if base.empty:
            raise ValueError(f"worker has no base metrics: {worker}")
        contracts.append(payload)
        base_frames.append(base)
        if not knockout.empty:
            knockout_frames.append(knockout)
    if len(contracts) != 12:
        raise ValueError(f"empirical part requires exactly 12 taxon workers, found {len(contracts)}")
    taxa = [str(c["taxon"]) for c in contracts]
    if len(set(taxa)) != 12:
        raise ValueError("empirical taxon workers are not unique")
    seeds = {int(c["part_seed"]) for c in contracts}
    if len(seeds) != 1:
        raise ValueError("empirical part mixed model-pool split seeds")
    return (
        pd.concat(base_frames, ignore_index=True),
        pd.concat(knockout_frames, ignore_index=True) if knockout_frames else pd.DataFrame(),
        pd.DataFrame(contracts),
    )


def _decorate_for_complete_gate(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    data["species"] = data["taxon"].astype(str)
    data["perturbation"] = data["M"].astype(str)
    return data


def _auc_representative(metrics: pd.DataFrame, eligible: tuple[str, ...]) -> tuple[str, pd.DataFrame]:
    subset = metrics.loc[metrics["candidate"].astype(str).isin(eligible)].copy()
    rows = []
    for candidate, group in subset.groupby("candidate", sort=True):
        auc = pd.to_numeric(group["presence_rank"], errors="coerce")
        n_pred = pd.to_numeric(group["n_predictors"], errors="coerce")
        rows.append({
            "candidate": str(candidate),
            "mean_presence_rank": float(auc.mean()),
            "mean_predictors": float(n_pred.mean()),
        })
    summary = pd.DataFrame(rows).sort_values(
        ["mean_presence_rank", "mean_predictors", "candidate"],
        ascending=[False, True, True], kind="mergesort"
    ).reset_index(drop=True)
    if summary.empty:
        raise ValueError("no adequate candidate is available for the AUC comparator")
    return str(summary.iloc[0]["candidate"]), summary


def _route_adequacy(group: pd.DataFrame, *, chance: float, margin: float, sem_multiplier: float) -> tuple[bool, bool, float, float]:
    folds_complete = True
    for m in M_NAMES:
        cell = group.loc[group["M"].astype(str).eq(m)]
        observed = set(pd.to_numeric(cell["fold"], errors="coerce").dropna().astype(int))
        values = pd.to_numeric(cell["presence_rank"], errors="coerce").to_numpy(float)
        if observed != set(range(EXPECTED_FOLDS)) or len(cell) != EXPECTED_FOLDS or not np.isfinite(values).all():
            folds_complete = False
    auc = pd.to_numeric(group["presence_rank"], errors="coerce")
    auc = auc[np.isfinite(auc)]
    mean = float(auc.mean()) if len(auc) else float("nan")
    sem = float(auc.std(ddof=1) / np.sqrt(len(auc))) if len(auc) >= 2 else float("nan")
    adequate = bool(
        folds_complete and np.isfinite(mean) and np.isfinite(sem)
        and mean >= chance + margin - 1e-12
        and mean - sem_multiplier * sem >= chance - 1e-12
    )
    return folds_complete, adequate, mean, sem


def _process_statuses(knockout: pd.DataFrame, *, taxa: tuple[str, ...], domains: tuple[str, ...], adequacy: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    route_rows = []
    status_rows = []
    expected_base_routes = 8
    for taxon in taxa:
        for domain in domains:
            subset = knockout.loc[
                knockout["taxon"].astype(str).eq(taxon)
                & knockout["excluded_process_domain"].astype(str).eq(domain)
            ].copy()
            candidates = tuple(sorted(subset["candidate"].dropna().astype(str).unique())) if not subset.empty else ()
            n_complete = 0
            n_adequate = 0
            for candidate in candidates:
                route = subset.loc[subset["candidate"].astype(str).eq(candidate)]
                complete, adequate, mean, sem = _route_adequacy(
                    route,
                    chance=float(adequacy["chance_auc"]),
                    margin=float(adequacy["minimum_auc_margin"]),
                    sem_multiplier=float(adequacy["auc_sem_multiplier"]),
                )
                n_complete += int(complete)
                n_adequate += int(adequate)
                route_rows.append({
                    "taxon": taxon, "process_domain": domain, "candidate": candidate,
                    "complete_outer_evidence": complete, "adequate": adequate,
                    "mean_presence_rank": mean, "sem_presence_rank": sem,
                })
            if n_adequate > 0:
                status = "refuted_as_necessary"
            elif len(candidates) == expected_base_routes and n_complete == expected_base_routes:
                status = "required_by_frozen_evidence_contract"
            else:
                status = "unresolved"
            status_rows.append({
                "taxon": taxon, "process_domain": domain, "status": status,
                "n_expected_routes": expected_base_routes,
                "n_observed_routes": len(candidates),
                "n_complete_routes": n_complete,
                "n_adequate_routes": n_adequate,
            })
    return pd.DataFrame(status_rows), pd.DataFrame(route_rows)


def run_pretruth_aggregate(
    *,
    contract_path: str | Path,
    worker_root: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    contract = load_v2_6_empirical_model_contract(contract_path)
    base, knockout, worker_contracts = _load_workers(Path(worker_root))
    taxa = tuple(sorted(worker_contracts["taxon"].astype(str)))
    required_metrics = ("presence_rank", *tuple(RECOVERY_DIRECTIONS))
    complete = require_complete_outer_fold_evidence(
        _decorate_for_complete_gate(base),
        discovery_taxa=taxa,
        perturbations=M_NAMES,
        required_columns=required_metrics,
        expected_outer_folds=EXPECTED_FOLDS,
    )
    if not complete.eligible_candidates:
        raise ValueError("no base procedure has complete 12-taxon x 3-M x 4-fold evidence")
    complete_metrics = base.loc[base["candidate"].astype(str).isin(complete.eligible_candidates)].copy()
    adequacy = contract["fixed_design"]["prediction_adequacy"]
    ecological = select_generalization_gated_niche_recovery_protocol(
        complete_metrics,
        chance_auc=float(adequacy["chance_auc"]),
        minimum_auc_margin=float(adequacy["minimum_auc_margin"]),
        auc_sem_multiplier=float(adequacy["auc_sem_multiplier"]),
    )
    adequate_candidates = tuple(ecological.eligible_candidates)
    ecological_rep = str(ecological.candidate)
    auc_rep, auc_summary = _auc_representative(complete_metrics, adequate_candidates)

    domains = tuple(str(x) for x in contract["fixed_design"]["process_domains"])
    process_status, knockout_routes = _process_statuses(
        knockout, taxa=taxa, domains=domains, adequacy=adequacy
    )
    if len(process_status) != 12 * len(domains):
        raise ValueError("pretruth process status denominator is incomplete")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    complete.cell_ledger.to_csv(out / "pretruth_base_complete_cell_ledger.csv", index=False)
    complete.candidate_summary.to_csv(out / "pretruth_base_complete_candidate_summary.csv", index=False)
    ecological.gate_summary.to_csv(out / "pretruth_base_adequacy_gate.csv", index=False)
    ecological.recovery_selection.summary.to_csv(out / "pretruth_ecological_selection.csv", index=False)
    auc_summary.to_csv(out / "pretruth_auc_selection.csv", index=False)
    process_status.to_csv(out / "pretruth_process_status.csv", index=False)
    knockout_routes.to_csv(out / "pretruth_knockout_route_status.csv", index=False)
    worker_contracts.to_csv(out / "pretruth_worker_contracts.csv", index=False)

    fingerprints = {
        "complete_candidate_summary_sha256": _frame_sha256(complete.candidate_summary, ["candidate"]),
        "ecological_selection_sha256": _frame_sha256(ecological.recovery_selection.summary, ["candidate"]),
        "auc_selection_sha256": _frame_sha256(auc_summary, ["candidate"]),
        "process_status_sha256": _frame_sha256(process_status, ["taxon", "process_domain"]),
        "knockout_route_status_sha256": _frame_sha256(knockout_routes, ["taxon", "process_domain", "candidate"]),
    }
    pd.DataFrame([{"name": k, "sha256": v} for k, v in fingerprints.items()]).to_csv(
        out / "pretruth_fingerprints.csv", index=False
    )
    result_contract = {
        "purpose": "product_a_v2_6_empirical_part_pretruth_freeze",
        "part_seed": int(worker_contracts["part_seed"].iloc[0]),
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
    }
    (out / "contract.json").write_text(json.dumps(result_contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result_contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--worker-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    run_pretruth_aggregate(contract_path=args.contract, worker_root=args.worker_root, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
