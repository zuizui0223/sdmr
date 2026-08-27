"""Finalize structural abstentions and apply the predeclared v2.8.3 decision.

The primary decision has a fixed denominator of three inherited split seeds at
sealed fraction 0.25.  Conditional ecological summaries never override a
full-denominator unavailable state.  Structural partial-identification bounds are
reported only when no additional post-structural scientific evidence is missing.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from .v2_8_3_fresh_contract import EXPECTED_SEEDS, load_v2_8_3_fresh_confirmation_contract
from .v2_8_3_presealed_transport import AGGREGATE_PURPOSE as STRUCTURAL_AGGREGATE_PURPOSE
from .v2_8_3_presealed_transport import PART_PURPOSE as STRUCTURAL_PART_PURPOSE

AUDIT_PURPOSE = "product_a_v2_7_2_fresh_part_sealed_audit"
DECISION_PURPOSE = "product_a_v2_8_3_fresh_taxon_holdout_empirical_confirmation_decision"
PREDICTION_DELTA_FLOOR = -0.01
ECO_NONDOMINATED_MIN_PARTS = 2
ECO_STRICT_IMPROVEMENT_MIN_PARTS = 2
PROCESS_MODAL_FRACTION_MIN = 2.0 / 3.0
PROCESS_DOMAINS = (
    "thermal", "water", "seasonality_phenology", "energy_productivity", "snow", "wind"
)


def _structural_part(path: str | Path) -> dict:
    payload = json.loads((Path(path) / "contract.json").read_text(encoding="utf-8"))
    if payload.get("purpose") != STRUCTURAL_PART_PURPOSE:
        raise ValueError("v2.8.3 finalizer received wrong structural part")
    for key in (
        "environmental_values_read", "CHELSA_environmental_values_read",
        "candidate_model_fitting_performed", "candidate_scores_read",
        "sealed_ecological_outcomes_read", "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if payload.get(key) is not False:
            raise ValueError(f"v2.8.3 structural part crossed barrier: {key}")
    return payload


def _empty_process_status(taxa_path: str | Path, part_id: str) -> pd.DataFrame:
    taxa = pd.read_csv(taxa_path)["scientific_name"].astype(str).tolist()
    if len(taxa) != 12 or len(set(taxa)) != 12:
        raise ValueError("v2.8.3 placeholder requires exactly 12 taxa")
    return pd.DataFrame([
        {
            "part_id": part_id,
            "taxon": taxon,
            "process_domain": domain,
            "status": "unavailable",
            "n_expected_routes": 8,
            "n_observed_routes": 0,
            "n_complete_routes": 0,
            "n_adequate_routes": 0,
        }
        for taxon in taxa for domain in PROCESS_DOMAINS
    ])


def finalize_part(
    *, structural_part_dir: str | Path, audit_dir: str | Path | None,
    taxa_path: str | Path, seed: int, output_dir: str | Path,
) -> dict[str, object]:
    structural = _structural_part(structural_part_dir)
    if int(structural.get("seed", -1)) != int(seed):
        raise ValueError("v2.8.3 structural/finalizer seed mismatch")
    if int(seed) not in EXPECTED_SEEDS or float(structural.get("sealed_fraction", -1)) != 0.25:
        raise ValueError("v2.8.3 finalizer identity changed")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    admitted = structural.get("structurally_auditable") is True
    if admitted:
        if audit_dir is None:
            raise ValueError("structurally admitted v2.8.3 part requires a scientific audit")
        root = Path(audit_dir)
        source_contract = json.loads((root / "contract.json").read_text(encoding="utf-8"))
        if source_contract.get("purpose") != AUDIT_PURPOSE:
            raise ValueError("v2.8.3 finalizer received wrong sealed-audit purpose")
        if source_contract.get("v2_8_3_scientific_transport") is not True:
            raise ValueError("v2.8.3 finalizer refuses untagged historical sealed evidence")
        if source_contract.get("scientific_promotion_allowed") is not False or source_contract.get("product_b_unblocked") is not False:
            raise ValueError("v2.8.3 sealed audit crossed promotion barrier")
        for child in root.iterdir():
            destination = out / child.name
            if child.is_dir():
                shutil.copytree(child, destination)
            else:
                shutil.copy2(child, destination)
        final = json.loads((out / "contract.json").read_text(encoding="utf-8"))
        final["v2_8_3_structural_admission"] = True
        final["v2_8_3_structural_seed"] = int(seed)
        (out / "contract.json").write_text(
            json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return final

    part_id = f"seed{int(seed)}_sealed0.25"
    pd.DataFrame([{
        "part_id": part_id,
        "seed": int(seed),
        "sealed_fraction": 0.25,
        "all_12_taxa": False,
        "all_3_M_specs": False,
        "mean_presence_rank_delta_vs_auc": float("nan"),
        "ecologically_nondominated_vs_auc": False,
        "strict_ecological_improvement_vs_auc": False,
        "part_available": False,
        "unavailable_reason": "pre_environment_structural_transport_unavailable",
    }]).to_csv(out / "part_summary.csv", index=False)
    _empty_process_status(taxa_path, part_id).to_csv(out / "process_status.csv", index=False)
    for filename in (
        "sealed_empirical_audit.csv", "sealed_role_summary.csv", "frozen_models_audited.csv",
        "sealed_chelsa_resolution_ledger.csv", "sealed_raster_provenance.csv",
    ):
        pd.DataFrame().to_csv(out / filename, index=False)
    result = {
        "purpose": AUDIT_PURPOSE,
        "part_id": part_id,
        "available": False,
        "unavailable_reason": "pre_environment_structural_transport_unavailable",
        "sealed_occurrence_environment_read": False,
        "sealed_occurrence_first_read_after_pretruth_freeze": False,
        "sealed_occurrence_used_for_candidate_selection": False,
        "sealed_occurrence_used_for_process_status": False,
        "candidate_or_threshold_retuning_after_sealed_read": False,
        "random_seed_change_after_sealed_read": False,
        "structural_or_audit_abstention_propagated_as_unavailable": True,
        "undefined_sealed_ecological_evidence_propagated_as_unavailable": False,
        "deterministic_successor": True,
        "v2_8_3_scientific_transport": True,
        "v2_8_3_stage": "structural_unavailable_placeholder_without_environmental_read",
        "v2_8_3_structural_admission": False,
        "v2_8_3_structural_seed": int(seed),
        "selected_global_sealed_fraction": 0.25,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _decision_frame(
    *, part_summary: pd.DataFrame, process_status: pd.DataFrame,
    structural_parts: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(part_summary) != 3 or part_summary["part_id"].astype(str).nunique() != 3:
        raise ValueError("v2.8.3 decision requires exactly three part summaries")
    if len(structural_parts) != 3 or set(pd.to_numeric(structural_parts["seed"]).astype(int)) != set(EXPECTED_SEEDS):
        raise ValueError("v2.8.3 decision requires exactly three structural parts")

    parts = part_summary.copy()
    parts["mean_presence_rank_delta_vs_auc"] = pd.to_numeric(
        parts["mean_presence_rank_delta_vs_auc"], errors="coerce"
    )
    all_structural = bool(structural_parts["structurally_auditable"].fillna(False).astype(bool).all())
    part_available = parts.get("part_available", pd.Series(False, index=parts.index)).fillna(False).astype(bool)
    complete_part_evidence = bool(
        all_structural
        and part_available.all()
        and parts["all_12_taxa"].fillna(False).astype(bool).all()
        and parts["all_3_M_specs"].fillna(False).astype(bool).all()
        and np.isfinite(parts["mean_presence_rank_delta_vs_auc"].to_numpy(float)).all()
    )

    process = process_status.copy()
    for key in ("part_id", "taxon", "process_domain", "status"):
        process[key] = process[key].astype(str)
    modal_rows = []
    process_available = True
    for (taxon, domain), group in process.groupby(["taxon", "process_domain"], sort=True):
        if len(group) != 3 or group["part_id"].nunique() != 3:
            process_available = False
            continue
        counts = group["status"].value_counts(dropna=False)
        modal_rows.append({
            "taxon": taxon,
            "process_domain": domain,
            "modal_fraction": float(counts.iloc[0] / 3.0),
        })
    modal = pd.DataFrame(modal_rows)
    if process.empty or len(modal) != 12 * len(PROCESS_DOMAINS):
        process_available = False
    if set(process["part_id"]) != set(parts["part_id"].astype(str)):
        process_available = False

    available = bool(complete_part_evidence and process_available)
    prediction_guardrail = bool(
        available and float(parts["mean_presence_rank_delta_vs_auc"].mean()) >= PREDICTION_DELTA_FLOOR - 1e-12
    )
    n_nondominated = int(parts["ecologically_nondominated_vs_auc"].fillna(False).astype(bool).sum())
    n_strict = int(parts["strict_ecological_improvement_vs_auc"].fillna(False).astype(bool).sum())
    ecological_support = bool(
        available and n_nondominated >= ECO_NONDOMINATED_MIN_PARTS
        and n_strict >= ECO_STRICT_IMPROVEMENT_MIN_PARTS
    )
    process_support = bool(
        available and not modal.empty
        and (modal["modal_fraction"] >= PROCESS_MODAL_FRACTION_MIN - 1e-12).all()
    )
    if not available:
        decision = "empirical_confirmation_unavailable"
        next_action = "retain frozen prior support and report primary/conditional/missing-evidence boundary without retuning"
    elif prediction_guardrail and ecological_support and process_support:
        decision = "empirical_confirmation_supported"
        next_action = "freeze v2.8.3 supported endpoint for a separate promotion decision"
    else:
        decision = "empirical_confirmation_not_supported"
        next_action = "retain negative v2.8.3 evidence without retuning after opened outcomes"

    structural_unavailable = int((~structural_parts["structurally_auditable"].fillna(False).astype(bool)).sum())
    structural_ids = {
        f"seed{int(row.seed)}_sealed0.25": bool(row.structurally_auditable)
        for row in structural_parts.itertuples(index=False)
    }
    admitted_mask = parts["part_id"].astype(str).map(structural_ids).fillna(False).astype(bool)
    conditional_mask = admitted_mask & part_available
    n_conditional = int(conditional_mask.sum())
    poststructural_unavailable = int((admitted_mask & ~part_available).sum())

    bounds_rows = []
    for indicator in ("ecologically_nondominated_vs_auc", "strict_ecological_improvement_vs_auc"):
        supporting = int(parts.loc[conditional_mask, indicator].fillna(False).astype(bool).sum())
        bounds_interpretable = structural_unavailable > 0 and poststructural_unavailable == 0
        bounds_rows.append({
            "indicator": indicator,
            "applicable_due_to_structural_unavailability": structural_unavailable > 0,
            "bounds_interpretable_without_additional_missing_scientific_evidence": bounds_interpretable,
            "observed_supporting_complete_parts": supporting,
            "structurally_unavailable_parts": structural_unavailable,
            "poststructural_scientifically_unavailable_parts": poststructural_unavailable,
            "lower_bound": supporting / 3.0 if bounds_interpretable else float("nan"),
            "upper_bound": (supporting + structural_unavailable) / 3.0 if bounds_interpretable else float("nan"),
            "can_override_primary_decision": False,
        })
    bounds = pd.DataFrame(bounds_rows)

    conditional_mean = (
        float(parts.loc[conditional_mask, "mean_presence_rank_delta_vs_auc"].mean())
        if n_conditional else float("nan")
    )
    result = pd.DataFrame([{
        "decision": decision,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
        "all_3_structural_parts_auditable": all_structural,
        "all_primary_scientific_evidence_available": available,
        "prediction_guardrail": prediction_guardrail,
        "ecological_support": ecological_support,
        "process_reproducibility_support": process_support,
        "n_parts": 3,
        "n_structurally_unavailable_parts": structural_unavailable,
        "n_poststructural_scientifically_unavailable_parts": poststructural_unavailable,
        "n_conditional_ecological_parts_available": n_conditional,
        "n_ecologically_nondominated_parts": n_nondominated,
        "n_strict_ecological_improvement_parts": n_strict,
        "mean_presence_rank_delta_vs_auc": (
            float(parts["mean_presence_rank_delta_vs_auc"].mean()) if available else float("nan")
        ),
        "conditional_mean_presence_rank_delta_vs_auc": conditional_mean,
        "minimum_process_modal_fraction": (
            float(modal["modal_fraction"].min()) if available and not modal.empty else float("nan")
        ),
        "partial_identification_bounds_descriptive_only": True,
        "conditional_results_can_override_primary_decision": False,
        "next_action": next_action,
    }])
    return result, bounds


def aggregate(
    *, contract_path: str | Path, structural_aggregate_dir: str | Path,
    audit_root: str | Path, output_dir: str | Path,
) -> dict[str, object]:
    load_v2_8_3_fresh_confirmation_contract(contract_path)
    structural_root = Path(structural_aggregate_dir)
    structural_contract = json.loads((structural_root / "contract.json").read_text(encoding="utf-8"))
    if structural_contract.get("purpose") != STRUCTURAL_AGGREGATE_PURPOSE:
        raise ValueError("v2.8.3 aggregate received wrong structural aggregate")
    structural_parts = pd.read_csv(structural_root / "structural_part_summary.csv")

    part_frames, process_frames, contracts = [], [], []
    for path in sorted(Path(audit_root).rglob("contract.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") != AUDIT_PURPOSE or payload.get("v2_8_3_scientific_transport") is not True:
            continue
        if payload.get("candidate_or_threshold_retuning_after_sealed_read") is not False:
            raise ValueError("v2.8.3 part retuned after sealed evidence")
        if payload.get("random_seed_change_after_sealed_read") is not False:
            raise ValueError("v2.8.3 part changed RNG after sealed evidence")
        if payload.get("scientific_promotion_allowed") is not False or payload.get("product_b_unblocked") is not False:
            raise ValueError("v2.8.3 part crossed promotion boundary")
        contracts.append(payload)
        part_frames.append(pd.read_csv(path.parent / "part_summary.csv"))
        process_frames.append(pd.read_csv(path.parent / "process_status.csv"))
    if len(contracts) != 3:
        raise ValueError(f"v2.8.3 aggregate requires exactly three finalized parts, found {len(contracts)}")
    parts = pd.concat(part_frames, ignore_index=True)
    process = pd.concat(process_frames, ignore_index=True)
    decision, bounds = _decision_frame(
        part_summary=parts, process_status=process, structural_parts=structural_parts
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    parts.sort_values("part_id", kind="mergesort").to_csv(out / "part_summary.csv", index=False)
    process.sort_values(["part_id", "taxon", "process_domain"], kind="mergesort").to_csv(
        out / "process_status.csv", index=False
    )
    structural_parts.to_csv(out / "structural_part_summary.csv", index=False)
    bounds.to_csv(out / "partial_identification_bounds.csv", index=False)
    decision.to_csv(out / "decision.csv", index=False)
    row = decision.iloc[0]
    result = {
        "purpose": DECISION_PURPOSE,
        "decision": str(row["decision"]),
        "n_parts": 3,
        "n_structurally_auditable_parts": int(structural_contract["n_structurally_auditable_parts"]),
        "n_conditional_ecological_parts_available": int(row["n_conditional_ecological_parts_available"]),
        "model_random_state": 0,
        "selection_process_numpy_seed": 0,
        "selected_global_sealed_fraction": 0.25,
        "primary_full_denominator_is_three_inherited_seeds": True,
        "conditional_ecology_cannot_override_primary": True,
        "partial_identification_bounds_cannot_override_primary": True,
        "development_thresholds_retuned_from_v2_8_3_outcomes": False,
        "post_outcome_candidate_reselection_performed": False,
        "post_outcome_random_seed_change_performed": False,
        "post_outcome_fraction_change_performed": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
        "independence_axis": "taxon_holdout_not_temporal",
        "temporal_independence_claim_allowed": False,
        "fundamental_niche_truth_claim_allowed": False,
        "next_action": str(row["next_action"]),
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("finalize-part")
    q.add_argument("--structural-part-dir", required=True)
    q.add_argument("--audit-dir")
    q.add_argument("--taxa", required=True)
    q.add_argument("--seed", required=True, type=int)
    q.add_argument("--output-dir", required=True)
    q = sub.add_parser("aggregate")
    q.add_argument("--contract", required=True)
    q.add_argument("--structural-aggregate-dir", required=True)
    q.add_argument("--audit-root", required=True)
    q.add_argument("--output-dir", required=True)
    return p


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "finalize-part":
        finalize_part(
            structural_part_dir=args.structural_part_dir,
            audit_dir=args.audit_dir,
            taxa_path=args.taxa,
            seed=args.seed,
            output_dir=args.output_dir,
        )
    else:
        aggregate(
            contract_path=args.contract,
            structural_aggregate_dir=args.structural_aggregate_dir,
            audit_root=args.audit_root,
            output_dir=args.output_dir,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
