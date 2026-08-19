"""Apply the predeclared Product-A v2.6 empirical decision across six sealed parts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .v2_6_empirical_decision import empirical_confirmation_decision


def run_empirical_confirmation_aggregate(
    *, audit_root: str | Path, output_dir: str | Path
) -> dict[str, object]:
    part_frames = []
    process_frames = []
    contracts = []
    for path in sorted(Path(audit_root).rglob("contract.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") != "product_a_v2_6_empirical_part_sealed_audit":
            continue
        if payload.get("sealed_occurrence_first_read_after_pretruth_freeze") is not True:
            raise ValueError("empirical part violated the pretruth-to-sealed order")
        if payload.get("candidate_or_threshold_retuning_after_sealed_read") is not False:
            raise ValueError("empirical part retuned after sealed outcomes were opened")
        root = path.parent
        part_frames.append(pd.read_csv(root / "part_summary.csv"))
        process_frames.append(pd.read_csv(root / "process_status.csv"))
        contracts.append(payload)
    if len(contracts) != 6:
        raise ValueError(f"empirical confirmation requires exactly six sealed parts, found {len(contracts)}")
    part_summary = pd.concat(part_frames, ignore_index=True)
    process_status = pd.concat(process_frames, ignore_index=True)
    if part_summary["part_id"].astype(str).nunique() != 6:
        raise ValueError("empirical sealed part IDs are not unique")
    decision = empirical_confirmation_decision(part_summary, process_status)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    part_summary.sort_values("part_id", kind="mergesort").to_csv(out / "part_summary.csv", index=False)
    process_status.sort_values(["part_id", "taxon", "process_domain"], kind="mergesort").to_csv(
        out / "process_status.csv", index=False
    )
    decision.to_csv(out / "decision.csv", index=False)
    result = {
        "purpose": "product_a_v2_6_independent_empirical_confirmation_decision",
        "n_parts": 6,
        "decision": str(decision.iloc[0]["decision"]),
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
        "known_truth_thresholds_retuned_from_empirical_outcomes": False,
        "empirical_thresholds_retuned_after_sealed_read": False,
        "next_action": str(decision.iloc[0]["next_action"]),
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    run_empirical_confirmation_aggregate(audit_root=args.audit_root, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
