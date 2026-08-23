"""Apply the unchanged six-part decision to v2.7.2 rank-2 sealed evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .v2_6_empirical_decision import empirical_confirmation_decision
from .v2_7_2_fresh_contract import load_v2_7_2_fresh_confirmation_contract

PURPOSE = "product_a_v2_7_2_fresh_taxon_holdout_empirical_confirmation_decision"
AUDIT_PURPOSE = "product_a_v2_7_2_fresh_part_sealed_audit"


def run_fresh_aggregate(
    *, contract_path: str | Path, audit_root: str | Path, output_dir: str | Path,
) -> dict[str, object]:
    contract = load_v2_7_2_fresh_confirmation_contract(contract_path)
    part_frames, process_frames, contracts = [], [], []
    for path in sorted(Path(audit_root).rglob("contract.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") != AUDIT_PURPOSE:
            continue
        if payload.get("deterministic_successor") is not True:
            raise ValueError("v2.7.2 aggregate received non-deterministic sealed evidence")
        if payload.get("candidate_or_threshold_retuning_after_sealed_read") is not False:
            raise ValueError("v2.7.2 empirical part retuned after sealed evidence")
        if payload.get("random_seed_change_after_sealed_read") is not False:
            raise ValueError("v2.7.2 empirical part changed RNG identity after sealed evidence")
        if payload.get("available") is True:
            if payload.get("sealed_occurrence_environment_read") is not True:
                raise ValueError("available v2.7.2 part did not open declared sealed evidence")
            if payload.get("sealed_occurrence_first_read_after_pretruth_freeze") is not True:
                raise ValueError("available v2.7.2 part violated pretruth-to-sealed order")
            if payload.get("required_sealed_metrics_all_finite") is not True:
                raise ValueError("available v2.7.2 part lacks complete ecological evidence")
        else:
            sealed_read = payload.get("sealed_occurrence_environment_read") is True
            if sealed_read:
                if payload.get("sealed_occurrence_first_read_after_pretruth_freeze") is not True:
                    raise ValueError("opened unavailable v2.7.2 part violated pretruth-to-sealed order")
                if payload.get("undefined_sealed_ecological_evidence_propagated_as_unavailable") is not True:
                    raise ValueError("opened unavailable v2.7.2 part lacks fail-closed marker")
            else:
                if payload.get("structural_or_audit_abstention_propagated_as_unavailable") is not True:
                    raise ValueError("presealed unavailable v2.7.2 part lacks abstention marker")
        root = path.parent
        part_frames.append(pd.read_csv(root / "part_summary.csv"))
        process_frames.append(pd.read_csv(root / "process_status.csv"))
        contracts.append(payload)
    if len(contracts) != 6:
        raise ValueError(
            f"v2.7.2 confirmation requires exactly six parts, found {len(contracts)}"
        )
    part_summary = pd.concat(part_frames, ignore_index=True)
    process_status = pd.concat(process_frames, ignore_index=True)
    if part_summary["part_id"].astype(str).nunique() != 6 or len(part_summary) != 6:
        raise ValueError("v2.7.2 sealed part denominator changed")
    expected_taxa = set(
        pd.read_csv(contract["fresh_taxon_panel"]["path"])["scientific_name"].astype(str)
    )
    if set(process_status["taxon"].astype(str)) != expected_taxa:
        raise ValueError("v2.7.2 process-status taxon denominator changed")

    # The decision function is intentionally inherited unchanged from v2.6/v2.7.1.
    decision = empirical_confirmation_decision(part_summary, process_status)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    part_summary.sort_values("part_id", kind="mergesort").to_csv(
        out / "part_summary.csv", index=False
    )
    process_status.sort_values(
        ["part_id", "taxon", "process_domain"], kind="mergesort"
    ).to_csv(out / "process_status.csv", index=False)
    decision.to_csv(out / "decision.csv", index=False)
    result = {
        "purpose": PURPOSE,
        "n_parts": 6,
        "n_available_parts": int(
            part_summary.get(
                "part_available", pd.Series(False, index=part_summary.index)
            ).fillna(False).astype(bool).sum()
        ),
        "n_unavailable_before_sealed_read": int(sum(
            c.get("available") is not True
            and c.get("sealed_occurrence_environment_read") is False
            for c in contracts
        )),
        "n_unavailable_after_sealed_read": int(sum(
            c.get("available") is not True
            and c.get("sealed_occurrence_environment_read") is True
            for c in contracts
        )),
        "decision": str(decision.iloc[0]["decision"]),
        "model_random_state": 0,
        "selection_process_numpy_seed": 0,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
        "development_thresholds_retuned_from_fresh_outcomes": False,
        "fresh_thresholds_retuned_after_sealed_read": False,
        "post_outcome_candidate_reselection_performed": False,
        "post_outcome_random_seed_change_performed": False,
        "independence_axis": "taxon_holdout_not_temporal",
        "temporal_independence_claim_allowed": False,
        "deterministic_successor": True,
        "next_action": str(decision.iloc[0]["next_action"]),
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", required=True)
    p.add_argument("--audit-root", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args(argv)
    run_fresh_aggregate(
        contract_path=a.contract, audit_root=a.audit_root, output_dir=a.output_dir
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
