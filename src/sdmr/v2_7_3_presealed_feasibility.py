"""Pre-sealed structural-feasibility gate for Product-A v2.7.3 rank-3 confirmation.

This module is intentionally narrower than the scientific Product-A runtime. It
creates the frozen outer split and model-pool-only M backgrounds from raw GBIF
coordinates, then asks whether the inherited evidence-balanced 4-fold partition
is structurally feasible for every rank-3 taxon. It never opens environmental
raster values, fits a candidate model, or reads any rank-2 sealed outcome.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .data import OccurrenceAdmissionConfig, load_gbif_download
from .pilot import MODEL_ROLE, OUTER_ROLE_COL, prepare_product_a_pilot
from .pilot_grid_cli import read_pilot_grid
from .specification import occurrence_table_fingerprint
from .v2_7_1_evidence_balanced_partition import make_evidence_balanced_spatial_partitions
from .v2_7_1_fresh_contract import load_fresh_eligibility_thresholds

PART_PURPOSE = "product_a_v2_7_3_presealed_feasibility_part"
DECISION_PURPOSE = "product_a_v2_7_3_presealed_feasibility_decision"
EXPECTED_M_KM = (150, 300, 500)
EXPECTED_M_NAMES = ("buffer_150km", "buffer_300km", "buffer_500km")
EXPECTED_SEEDS = (2026082201, 2026082202, 2026082203)
EXPECTED_FRACTIONS = (0.20, 0.30)


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_design(path: str | Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_7_3_rank3_presealed_structural_feasibility_contract":
        raise ValueError("wrong v2.7.3 presealed feasibility contract")
    if payload.get("declared_before_any_v2_7_3_source_acquisition_partition_model_or_sealed_outcome") is not True:
        raise ValueError("v2.7.3 presealed design was not frozen before source acquisition")
    fixed = payload.get("fixed_design", {})
    if tuple(int(x) for x in fixed.get("M_km", ())) != EXPECTED_M_KM:
        raise ValueError("v2.7.3 M grid changed")
    if tuple(int(x) for x in fixed.get("split_seeds", ())) != EXPECTED_SEEDS:
        raise ValueError("v2.7.3 split seeds changed")
    if tuple(float(x) for x in fixed.get("sealed_fractions", ())) != EXPECTED_FRACTIONS:
        raise ValueError("v2.7.3 sealed fractions changed")
    gate = payload.get("presealed_admission_gate", {})
    if gate.get("runs_before_model_pool_fitting") is not True or gate.get("runs_before_sealed_raster_extraction") is not True:
        raise ValueError("v2.7.3 feasibility gate order changed")
    if gate.get("require_all_12_taxa_x_3_M_in_every_part") is not True or gate.get("require_all_6_parts_structurally_feasible") is not True:
        raise ValueError("v2.7.3 feasibility denominator changed")
    return payload


def _load_source_pin(path: str | Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_7_3_rank3_fresh_raw_source_pin":
        raise ValueError("wrong v2.7.3 raw-source pin")
    if int(payload.get("workflow_run_id", -1)) != 32858840773 or payload.get("workflow_conclusion") != "success":
        raise ValueError("v2.7.3 raw-source run identity changed")
    if payload.get("ready_for_presealed_feasibility") is not True or payload.get("ready_for_scientific_model_fitting") is not False:
        raise ValueError("v2.7.3 source pin crossed the feasibility boundary")
    barrier = payload.get("information_barrier", {})
    for key in (
        "environmental_values_read",
        "candidate_model_fitting_performed",
        "presealed_feasibility_executed",
        "rank2_sealed_confirmation_outcomes_read",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if barrier.get(key) is not False:
            raise ValueError(f"v2.7.3 source pin crossed barrier: {key}")
    return payload


def _empty_taxon_rows(taxa: list[str], reason: str) -> list[dict[str, object]]:
    return [
        {
            "taxon_index": int(i),
            "taxon": str(taxon),
            "structurally_feasible": False,
            "partition_seed": None,
            "selected_assignment_attempt": None,
            "unavailable_reason": str(reason),
        }
        for i, taxon in enumerate(taxa)
    ]


def run_part(
    *,
    design_path: str | Path,
    source_pin_path: str | Path,
    focal_path: str | Path,
    target_path: str | Path,
    taxa_path: str | Path,
    grid_path: str | Path,
    seed: int,
    sealed_fraction: float,
    output_dir: str | Path,
) -> dict[str, object]:
    design = _load_design(design_path)
    source = _load_source_pin(source_pin_path)
    if int(seed) not in EXPECTED_SEEDS:
        raise ValueError("v2.7.3 part seed is not frozen")
    if float(sealed_fraction) not in EXPECTED_FRACTIONS:
        raise ValueError("v2.7.3 sealed fraction is not frozen")
    if _sha256(focal_path) != source["focal"]["file_sha256"]:
        raise ValueError("v2.7.3 focal source SHA mismatch")
    if _sha256(target_path) != source["target_group"]["file_sha256"]:
        raise ValueError("v2.7.3 target source SHA mismatch")
    if _sha256(taxa_path) != design["rank3_panel"]["sha256"]:
        raise ValueError("v2.7.3 rank-3 panel SHA mismatch")

    taxa_frame = pd.read_csv(taxa_path)
    taxa = taxa_frame["scientific_name"].astype(str).tolist()
    if len(taxa) != 12 or len(set(taxa)) != 12:
        raise ValueError("v2.7.3 requires exactly 12 unique rank-3 taxa")
    expected_taxa = set(taxa)

    focal = load_gbif_download(focal_path).records
    target = load_gbif_download(target_path).records
    grid = read_pilot_grid(str(grid_path))
    if tuple(int(round(float(x))) for x in grid["occurrence_buffer_km"]) != EXPECTED_M_KM:
        raise ValueError("v2.7.3 grid differs from 150/300/500 km")
    if tuple(grid["name"].astype(str)) != EXPECTED_M_NAMES:
        raise ValueError("v2.7.3 M names changed")
    if not grid["m_strategy"].astype(str).eq("buffer").all():
        raise ValueError("v2.7.3 M must remain buffer based")

    thresholds = load_fresh_eligibility_thresholds(design_path)
    prepared_by_name: dict[str, object] = {}
    occurrence_sha: str | None = None
    eligibility_error: str | None = None
    for row in grid.itertuples(index=False):
        prepared = prepare_product_a_pilot(
            focal,
            taxa_frame,
            admission_config=OccurrenceAdmissionConfig(),
            min_occurrences=int(thresholds["minimum_occurrences"]),
            min_unique_cells=int(thresholds["minimum_unique_cells"]),
            gate_cell_size_degrees=0.05,
            m_strategy=str(row.m_strategy),
            target_group_pool=target,
            bbox_buffer_degrees=float(row.bbox_buffer_degrees),
            occurrence_buffer_km=float(row.occurrence_buffer_km),
            background_points=int(row.background_points),
            background_cell_size_degrees=float(row.background_cell_size_degrees),
            random_state=int(seed),
            strict_background=True,
            focal_thin_cell_size_degrees=0.05,
            outer_sealed_fraction=float(sealed_fraction),
        )
        eligible = set(
            prepared.species_gate.loc[
                prepared.species_gate["eligible"].astype(bool), "species"
            ].astype(str)
        )
        if eligible != expected_taxa:
            eligibility_error = (
                "fresh structural eligibility lost predeclared rank-3 taxa: "
                f"missing={sorted(expected_taxa-eligible)} extra={sorted(eligible-expected_taxa)}"
            )
            prepared_by_name[str(row.name)] = prepared
            break
        sha = occurrence_table_fingerprint(prepared.occurrences)
        if occurrence_sha is None:
            occurrence_sha = sha
        elif sha != occurrence_sha:
            raise ValueError("v2.7.3 M changed the frozen focal occurrence split")
        prepared_by_name[str(row.name)] = prepared

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if eligibility_error is not None:
        taxon_rows = _empty_taxon_rows(taxa, eligibility_error)
        pd.DataFrame(taxon_rows).to_csv(out / "taxon_feasibility.csv", index=False)
        result = {
            "purpose": PART_PURPOSE,
            "available": False,
            "seed": int(seed),
            "sealed_fraction": float(sealed_fraction),
            "n_taxa": 12,
            "n_feasible_taxa": 0,
            "M_specs": list(EXPECTED_M_NAMES),
            "unavailable_stage": "fresh_structural_eligibility",
            "unavailable_reason": eligibility_error,
            "fresh_focal_sha256": source["focal"]["file_sha256"],
            "fresh_target_sha256": source["target_group"]["file_sha256"],
            "outer_sealed_before_M": True,
            "M_built_from_model_pool_only": True,
            "environmental_values_read": False,
            "sealed_environmental_values_read": False,
            "candidate_model_fitting_performed": False,
            "candidate_scores_read": False,
            "rank2_sealed_confirmation_outcomes_read": False,
            "scientific_model_execution_allowed": False,
        }
        (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result

    first = prepared_by_name[EXPECTED_M_NAMES[0]]
    model_occurrences = first.occurrences.loc[
        first.occurrences[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
    ].reset_index(drop=True)
    model_backgrounds: dict[str, pd.DataFrame] = {}
    for name in EXPECTED_M_NAMES:
        prepared = prepared_by_name[name]
        model_backgrounds[name] = prepared.background.loc[
            prepared.background[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
        ].reset_index(drop=True)

    fold_cfg = design["inherited_evidence_balanced_partition"]
    taxon_rows: list[dict[str, object]] = []
    for taxon_index, taxon in enumerate(taxa):
        occurrence = model_occurrences.loc[
            model_occurrences["species"].astype(str).eq(str(taxon))
        ].reset_index(drop=True)
        backgrounds = {
            name: model_backgrounds[name].loc[
                model_backgrounds[name]["species"].astype(str).eq(str(taxon))
            ].reset_index(drop=True)
            for name in EXPECTED_M_NAMES
        }
        partition_seed = int(seed) + int(taxon_index) * 100 + 271
        if occurrence.empty or any(frame.empty for frame in backgrounds.values()):
            missing = [name for name, frame in backgrounds.items() if frame.empty]
            taxon_rows.append({
                "taxon_index": int(taxon_index),
                "taxon": str(taxon),
                "structurally_feasible": False,
                "partition_seed": partition_seed,
                "selected_assignment_attempt": None,
                "unavailable_reason": f"empty model-pool resource; occurrence_empty={occurrence.empty}; background_empty={missing}",
            })
            continue
        try:
            partition = make_evidence_balanced_spatial_partitions(
                occurrence["longitude"].to_numpy(float),
                occurrence["latitude"].to_numpy(float),
                {
                    name: (
                        backgrounds[name]["longitude"].to_numpy(float),
                        backgrounds[name]["latitude"].to_numpy(float),
                    )
                    for name in EXPECTED_M_NAMES
                },
                n_microblocks=int(fold_cfg["spatial_microblocks"]),
                outer_folds=int(fold_cfg["outer_folds"]),
                minimum_evaluation_occurrences=int(fold_cfg["minimum_evaluation_occurrences_per_fold"]),
                minimum_evaluation_background_rows=int(fold_cfg["minimum_evaluation_background_rows_per_M_fold"]),
                minimum_training_background_rows=int(fold_cfg["minimum_training_background_rows_per_M_fold"]),
                assignment_attempts=int(fold_cfg["assignment_attempts"]),
                random_state=partition_seed,
            )
        except ValueError as exc:
            taxon_rows.append({
                "taxon_index": int(taxon_index),
                "taxon": str(taxon),
                "structurally_feasible": False,
                "partition_seed": partition_seed,
                "selected_assignment_attempt": None,
                "unavailable_reason": str(exc),
            })
            continue
        taxon_dir = out / f"taxon_{taxon_index:02d}"
        taxon_dir.mkdir(exist_ok=True)
        partition.support_ledger.to_csv(taxon_dir / "partition_support.csv", index=False)
        partition.attempt_ledger.to_csv(taxon_dir / "partition_attempts.csv", index=False)
        taxon_rows.append({
            "taxon_index": int(taxon_index),
            "taxon": str(taxon),
            "structurally_feasible": True,
            "partition_seed": partition_seed,
            "selected_assignment_attempt": int(partition.selected_attempt),
            "unavailable_reason": None,
        })

    taxon_frame = pd.DataFrame(taxon_rows)
    taxon_frame.to_csv(out / "taxon_feasibility.csv", index=False)
    n_feasible = int(taxon_frame["structurally_feasible"].astype(bool).sum())
    available = n_feasible == 12
    unavailable = taxon_frame.loc[~taxon_frame["structurally_feasible"].astype(bool)]
    reason = None if available else "; ".join(
        f"{row.taxon}:{row.unavailable_reason}" for row in unavailable.itertuples(index=False)
    )
    result = {
        "purpose": PART_PURPOSE,
        "available": bool(available),
        "seed": int(seed),
        "sealed_fraction": float(sealed_fraction),
        "occurrence_sha256": str(occurrence_sha),
        "n_taxa": 12,
        "n_feasible_taxa": n_feasible,
        "M_specs": list(EXPECTED_M_NAMES),
        "unavailable_stage": None if available else "structural_partition",
        "unavailable_reason": reason,
        "fresh_focal_sha256": source["focal"]["file_sha256"],
        "fresh_target_sha256": source["target_group"]["file_sha256"],
        "outer_sealed_before_M": True,
        "M_built_from_model_pool_only": True,
        "sealed_rows_used_for_partition_assignment": False,
        "environmental_values_read": False,
        "sealed_environmental_values_read": False,
        "candidate_model_fitting_performed": False,
        "candidate_scores_read": False,
        "rank2_sealed_confirmation_outcomes_read": False,
        "scientific_model_execution_allowed": False,
    }
    (out / "contract.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def aggregate_parts(*, parts_root: str | Path, output_dir: str | Path) -> dict[str, object]:
    root = Path(parts_root)
    contracts = []
    for path in root.rglob("contract.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") == PART_PURPOSE:
            contracts.append((path, payload))
    if len(contracts) != 6:
        raise ValueError(f"expected exactly six v2.7.3 feasibility parts, found {len(contracts)}")
    expected = {(seed, fraction) for seed in EXPECTED_SEEDS for fraction in EXPECTED_FRACTIONS}
    observed = {(int(c["seed"]), float(c["sealed_fraction"])) for _, c in contracts}
    if observed != expected:
        raise ValueError(f"v2.7.3 feasibility part denominator changed: {sorted(observed)}")
    for _, c in contracts:
        for key in (
            "environmental_values_read",
            "sealed_environmental_values_read",
            "candidate_model_fitting_performed",
            "candidate_scores_read",
            "rank2_sealed_confirmation_outcomes_read",
            "scientific_model_execution_allowed",
        ):
            if c.get(key) is not False:
                raise ValueError(f"v2.7.3 feasibility part crossed barrier: {key}")
        if int(c.get("n_taxa", -1)) != 12 or tuple(c.get("M_specs", ())) != EXPECTED_M_NAMES:
            raise ValueError("v2.7.3 feasibility denominator changed")

    ordered = [
        c for _, c in sorted(
            contracts,
            key=lambda item: (int(item[1]["seed"]), float(item[1]["sealed_fraction"])),
        )
    ]
    n_available = sum(bool(c["available"]) for c in ordered)
    decision = "presealed_admitted" if n_available == 6 else "presealed_unavailable"
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for c in ordered:
        rows.append({
            "seed": int(c["seed"]),
            "sealed_fraction": float(c["sealed_fraction"]),
            "available": bool(c["available"]),
            "n_feasible_taxa": int(c["n_feasible_taxa"]),
            "unavailable_stage": c.get("unavailable_stage"),
            "unavailable_reason": c.get("unavailable_reason"),
        })
    pd.DataFrame(rows).to_csv(out / "part_feasibility.csv", index=False)
    result = {
        "purpose": DECISION_PURPOSE,
        "decision": decision,
        "n_parts": 6,
        "n_available_parts": int(n_available),
        "all_12_taxa_x_3_M_required_in_every_part": True,
        "environmental_values_read": False,
        "sealed_environmental_values_read": False,
        "candidate_model_fitting_performed": False,
        "candidate_scores_read": False,
        "rank2_sealed_confirmation_outcomes_read": False,
        "scientific_model_execution_allowed": False,
        "separate_scientific_runtime_authorization_required_if_admitted": True,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }
    (out / "decision.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    part = sub.add_parser("part")
    part.add_argument("--design", required=True)
    part.add_argument("--source-pin", required=True)
    part.add_argument("--focal", required=True)
    part.add_argument("--target", required=True)
    part.add_argument("--taxa", required=True)
    part.add_argument("--grid", required=True)
    part.add_argument("--seed", type=int, required=True)
    part.add_argument("--sealed-fraction", type=float, required=True)
    part.add_argument("--output-dir", required=True)
    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--parts-root", required=True)
    aggregate.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.mode == "part":
        run_part(
            design_path=args.design,
            source_pin_path=args.source_pin,
            focal_path=args.focal,
            target_path=args.target,
            taxa_path=args.taxa,
            grid_path=args.grid,
            seed=args.seed,
            sealed_fraction=args.sealed_fraction,
            output_dir=args.output_dir,
        )
    else:
        aggregate_parts(parts_root=args.parts_root, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
