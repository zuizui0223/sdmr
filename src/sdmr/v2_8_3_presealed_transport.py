"""Coordinate-only structural transportability gate for Product-A v2.8.3.

This adapter reuses the v2.7.3 presealed partition-feasibility implementation
but fixes the v2.8.3 denominator to three inherited seeds at the single globally
calibrated sealed fraction 0.25.  It must run before any CHELSA/environmental
value, candidate fit/score, or sealed ecological outcome is opened.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from . import v2_7_3_presealed_feasibility as structural_core
from .v2_8_3_fresh_contract import (
    EXPECTED_FRACTIONS,
    EXPECTED_M,
    EXPECTED_SEEDS,
    load_v2_8_3_fresh_confirmation_contract,
    load_v2_8_3_source_receipt,
    v2_7_3_structural_core_view,
)

PART_PURPOSE = "product_a_v2_8_3_pre_environment_structural_transport_part"
AGGREGATE_PURPOSE = "product_a_v2_8_3_pre_environment_structural_transportability_decision"
M_NAMES = ("buffer_150km", "buffer_300km", "buffer_500km")


def _patch_core() -> None:
    structural_core.EXPECTED_SEEDS = EXPECTED_SEEDS
    structural_core.EXPECTED_FRACTIONS = EXPECTED_FRACTIONS
    structural_core.EXPECTED_M_KM = EXPECTED_M
    structural_core.EXPECTED_M_NAMES = M_NAMES
    structural_core.PART_PURPOSE = PART_PURPOSE
    structural_core._load_design = lambda path: v2_7_3_structural_core_view(
        load_v2_8_3_fresh_confirmation_contract(path)
    )
    structural_core._load_source_pin = load_v2_8_3_source_receipt


def run_part(
    *, contract_path: str | Path, source_receipt_path: str | Path,
    focal_path: str | Path, target_path: str | Path, taxa_path: str | Path,
    grid_path: str | Path, seed: int, output_dir: str | Path,
) -> dict[str, object]:
    contract = load_v2_8_3_fresh_confirmation_contract(contract_path)
    load_v2_8_3_source_receipt(source_receipt_path)
    if int(seed) not in EXPECTED_SEEDS:
        raise ValueError("v2.8.3 structural seed is not frozen")
    _patch_core()
    result = structural_core.run_part(
        design_path=contract_path,
        source_pin_path=source_receipt_path,
        focal_path=focal_path,
        target_path=target_path,
        taxa_path=taxa_path,
        grid_path=grid_path,
        seed=int(seed),
        sealed_fraction=0.25,
        output_dir=output_dir,
    )

    out = Path(output_dir)
    taxa = pd.read_csv(out / "taxon_feasibility.csv")
    cell_rows: list[dict[str, object]] = []
    for row in taxa.itertuples(index=False):
        for M_name in M_NAMES:
            cell_rows.append({
                "seed": int(seed),
                "sealed_fraction": 0.25,
                "taxon_index": int(row.taxon_index),
                "taxon": str(row.taxon),
                "M": M_name,
                "structurally_feasible": bool(row.structurally_feasible),
                "partition_seed": row.partition_seed,
                "selected_assignment_attempt": row.selected_assignment_attempt,
                "unavailable_reason": row.unavailable_reason,
                "joint_partition_support_across_all_3_M": True,
            })
    cells = pd.DataFrame(cell_rows)
    if len(cells) != 36:
        raise ValueError("v2.8.3 structural part must report exactly 36 taxon×M cells")
    cells.to_csv(out / "cell_feasibility.csv", index=False)

    result.update({
        "purpose": PART_PURPOSE,
        "seed": int(seed),
        "sealed_fraction": 0.25,
        "n_structural_cells": 36,
        "n_feasible_structural_cells": int(cells["structurally_feasible"].astype(bool).sum()),
        "joint_partition_support_across_all_3_M": True,
        "structurally_auditable": bool(result.get("available") is True),
        "environmental_values_read": False,
        "CHELSA_environmental_values_read": False,
        "candidate_model_fitting_performed": False,
        "candidate_scores_read": False,
        "sealed_ecological_outcomes_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
        "v2_7_3_coordinate_only_core_reused": True,
        "conditional_scientific_execution_allowed_for_this_part": bool(
            result.get("available") is True
        ),
    })
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def aggregate_parts(*, parts_root: str | Path, output_dir: str | Path) -> dict[str, object]:
    contracts: list[dict] = []
    cell_frames: list[pd.DataFrame] = []
    roots: list[Path] = []
    for path in sorted(Path(parts_root).rglob("contract.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") != PART_PURPOSE:
            continue
        for key in (
            "environmental_values_read", "CHELSA_environmental_values_read",
            "candidate_model_fitting_performed", "candidate_scores_read",
            "sealed_ecological_outcomes_read", "scientific_promotion_allowed",
            "product_b_unblocked",
        ):
            if payload.get(key) is not False:
                raise ValueError(f"v2.8.3 structural evidence crossed information barrier: {key}")
        contracts.append(payload)
        cell_frames.append(pd.read_csv(path.parent / "cell_feasibility.csv"))
        roots.append(path.parent)
    del roots
    if len(contracts) != 3:
        raise ValueError(f"v2.8.3 requires exactly three structural parts, found {len(contracts)}")
    if {int(c["seed"]) for c in contracts} != set(EXPECTED_SEEDS):
        raise ValueError("v2.8.3 structural seeds changed")
    if {float(c["sealed_fraction"]) for c in contracts} != {0.25}:
        raise ValueError("v2.8.3 structural fraction changed")

    cells = pd.concat(cell_frames, ignore_index=True)
    if len(cells) != 108:
        raise ValueError("v2.8.3 structural aggregate must contain 108 taxon×M×part cells")
    key_count = cells[["seed", "taxon", "M"]].astype(str).drop_duplicates().shape[0]
    if key_count != 108:
        raise ValueError("v2.8.3 structural cell identity duplicated or missing")

    part_rows = []
    for c in sorted(contracts, key=lambda x: int(x["seed"])):
        part_rows.append({
            "seed": int(c["seed"]),
            "sealed_fraction": 0.25,
            "part_id": f"seed{int(c['seed'])}_sealed0.25",
            "structurally_auditable": bool(c.get("structurally_auditable") is True),
            "n_feasible_taxa": int(c.get("n_feasible_taxa", 0)),
            "n_feasible_structural_cells": int(c.get("n_feasible_structural_cells", 0)),
            "n_structural_cells": 36,
            "unavailable_stage": c.get("unavailable_stage"),
            "unavailable_reason": c.get("unavailable_reason"),
        })
    parts = pd.DataFrame(part_rows)
    auditable = [
        int(row.seed) for row in parts.itertuples(index=False)
        if bool(row.structurally_auditable)
    ]
    n_auditable = len(auditable)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cells.sort_values(["seed", "taxon_index", "M"], kind="mergesort").to_csv(
        out / "structural_cell_coverage.csv", index=False
    )
    parts.to_csv(out / "structural_part_summary.csv", index=False)
    result = {
        "purpose": AGGREGATE_PURPOSE,
        "n_expected_structural_cells": 108,
        "n_feasible_structural_cells": int(cells["structurally_feasible"].astype(bool).sum()),
        "n_parts": 3,
        "n_structurally_auditable_parts": n_auditable,
        "auditable_seeds": auditable,
        "all_3_parts_structurally_auditable": n_auditable == 3,
        "primary_full_denominator_scientific_confirmation_available_from_structure": n_auditable == 3,
        "conditional_scientific_execution_allowed_only_for_auditable_seeds": True,
        "zero_auditable_parts_blocks_all_environmental_model_and_sealed_reads": n_auditable == 0,
        "environmental_values_read": False,
        "CHELSA_environmental_values_read": False,
        "candidate_model_fitting_performed": False,
        "candidate_scores_read": False,
        "sealed_ecological_outcomes_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
        "taxon_seed_M_source_or_threshold_replacement_allowed": False,
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("part")
    q.add_argument("--contract", required=True)
    q.add_argument("--source-receipt", required=True)
    q.add_argument("--focal", required=True)
    q.add_argument("--target", required=True)
    q.add_argument("--taxa", required=True)
    q.add_argument("--grid", required=True)
    q.add_argument("--seed", type=int, required=True)
    q.add_argument("--output-dir", required=True)
    q = sub.add_parser("aggregate")
    q.add_argument("--parts-root", required=True)
    q.add_argument("--output-dir", required=True)
    return p


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "part":
        run_part(
            contract_path=args.contract,
            source_receipt_path=args.source_receipt,
            focal_path=args.focal,
            target_path=args.target,
            taxa_path=args.taxa,
            grid_path=args.grid,
            seed=args.seed,
            output_dir=args.output_dir,
        )
    else:
        aggregate_parts(parts_root=args.parts_root, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
