"""Predeclared aggregate decision for Product-A v2.6 empirical confirmation."""
from __future__ import annotations

import numpy as np
import pandas as pd

EXPECTED_PARTS = 6
PREDICTION_DELTA_FLOOR = -0.01
ECO_NONDOMINATED_MIN_PARTS = 4
ECO_STRICT_IMPROVEMENT_MIN_PARTS = 3
PROCESS_MODAL_FRACTION_MIN = 2.0 / 3.0


def empirical_confirmation_decision(
    part_summary: pd.DataFrame,
    process_status: pd.DataFrame,
) -> pd.DataFrame:
    """Apply only the decision rule frozen before new sealed outcomes are opened."""
    part_required = {
        "part_id",
        "all_12_taxa",
        "all_3_M_specs",
        "mean_presence_rank_delta_vs_auc",
        "ecologically_nondominated_vs_auc",
        "strict_ecological_improvement_vs_auc",
    }
    missing = sorted(part_required - set(part_summary.columns))
    if missing:
        raise KeyError(f"empirical part summary missing columns: {missing}")
    process_required = {"part_id", "taxon", "process_domain", "status"}
    missing_process = sorted(process_required - set(process_status.columns))
    if missing_process:
        raise KeyError(f"empirical process status missing columns: {missing_process}")

    parts = part_summary.copy()
    parts["part_id"] = parts["part_id"].astype(str)
    parts["mean_presence_rank_delta_vs_auc"] = pd.to_numeric(
        parts["mean_presence_rank_delta_vs_auc"], errors="coerce"
    )
    unique_parts = int(parts["part_id"].nunique())
    part_available = bool(
        len(parts) == EXPECTED_PARTS
        and unique_parts == EXPECTED_PARTS
        and parts["all_12_taxa"].fillna(False).astype(bool).all()
        and parts["all_3_M_specs"].fillna(False).astype(bool).all()
        and np.isfinite(parts["mean_presence_rank_delta_vs_auc"].to_numpy(float)).all()
    )

    process = process_status.copy()
    process["part_id"] = process["part_id"].astype(str)
    process["taxon"] = process["taxon"].astype(str)
    process["process_domain"] = process["process_domain"].astype(str)
    process["status"] = process["status"].astype(str)
    process_keys = process.groupby(["taxon", "process_domain"], sort=True)
    modal_rows = []
    process_available = True
    for (taxon, domain), group in process_keys:
        if group["part_id"].nunique() != EXPECTED_PARTS or len(group) != EXPECTED_PARTS:
            process_available = False
            continue
        counts = group["status"].value_counts(dropna=False)
        modal_rows.append({
            "taxon": taxon,
            "process_domain": domain,
            "modal_fraction": float(counts.iloc[0] / EXPECTED_PARTS),
        })
    modal = pd.DataFrame(modal_rows)
    if process.empty or modal.empty:
        process_available = False
    expected_part_ids = set(parts["part_id"])
    if set(process["part_id"]) != expected_part_ids:
        process_available = False

    available = bool(part_available and process_available)
    prediction_guardrail = bool(
        available
        and float(parts["mean_presence_rank_delta_vs_auc"].mean()) >= PREDICTION_DELTA_FLOOR - 1e-12
    )
    ecological_support = bool(
        available
        and int(parts["ecologically_nondominated_vs_auc"].fillna(False).astype(bool).sum())
        >= ECO_NONDOMINATED_MIN_PARTS
        and int(parts["strict_ecological_improvement_vs_auc"].fillna(False).astype(bool).sum())
        >= ECO_STRICT_IMPROVEMENT_MIN_PARTS
    )
    process_support = bool(
        available
        and (modal["modal_fraction"] >= PROCESS_MODAL_FRACTION_MIN - 1e-12).all()
    )

    if not available:
        decision = "empirical_confirmation_unavailable"
        next_action = "retain known-truth support only and diagnose incomplete empirical evidence"
    elif prediction_guardrail and ecological_support and process_support:
        decision = "empirical_confirmation_supported"
        next_action = "freeze empirically confirmed Product A for a separate promotion decision"
    else:
        decision = "empirical_confirmation_not_supported"
        next_action = "retain negative empirical evidence without retuning against opened sealed outcomes"

    return pd.DataFrame([{
        "decision": decision,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
        "all_empirical_evidence_available": available,
        "prediction_guardrail": prediction_guardrail,
        "ecological_support": ecological_support,
        "process_reproducibility_support": process_support,
        "n_parts": unique_parts,
        "n_ecologically_nondominated_parts": int(parts["ecologically_nondominated_vs_auc"].fillna(False).astype(bool).sum()),
        "n_strict_ecological_improvement_parts": int(parts["strict_ecological_improvement_vs_auc"].fillna(False).astype(bool).sum()),
        "mean_presence_rank_delta_vs_auc": float(parts["mean_presence_rank_delta_vs_auc"].mean()) if len(parts) else float("nan"),
        "minimum_process_modal_fraction": float(modal["modal_fraction"].min()) if len(modal) else float("nan"),
        "next_action": next_action,
    }])
