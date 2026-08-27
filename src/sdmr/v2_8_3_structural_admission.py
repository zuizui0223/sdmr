"""Pre-environment structural transportability admission for Product-A v2.8.3.

This gate consumes only the pinned raw occurrence/target sources, coordinates,
the frozen outer split/M geometry, spatial microblocks, fold assignments and row
counts.  It must run before any v2.8.3 CHELSA/environmental extraction or model
fitting.  A part is admitted only when all 12 taxa share one complete inherited
four-fold assignment across all three fixed M backgrounds.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .data import OccurrenceAdmissionConfig, load_gbif_download
from .pilot import MODEL_ROLE, OUTER_ROLE_COL, prepare_product_a_pilot
from .pilot_grid_cli import read_pilot_grid
from .specification import occurrence_table_fingerprint
from .v2_7_1_evidence_balanced_partition import make_evidence_balanced_spatial_partitions
from .v2_8_3_fresh_contract import (
    EXPECTED_FOCAL_SHA256,
    EXPECTED_M,
    EXPECTED_PANEL_SHA256,
    EXPECTED_SEEDS,
    EXPECTED_TARGET_SHA256,
    load_v2_8_3_fresh_confirmation_contract,
    load_v2_8_3_source_receipt,
    sha256_file,
)

PURPOSE = "product_a_v2_8_3_structural_transportability_admission"
CELL_PURPOSE = "product_a_v2_8_3_structural_taxon_M_part_cell"


def _false_barrier() -> dict[str, bool]:
    return {
        "environmental_values_read": False,
        "CHELSA_environmental_values_read": False,
        "candidate_model_fitting_performed": False,
        "candidate_scores_read": False,
        "niche_recovery_outcomes_read": False,
        "sealed_occurrence_environment_read": False,
        "sealed_confirmation_outcomes_read": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }


def _grid(path: str | Path) -> pd.DataFrame:
    grid = read_pilot_grid(str(path))
    observed = tuple(int(round(float(x))) for x in grid["occurrence_buffer_km"])
    if observed != EXPECTED_M:
        raise ValueError("v2.8.3 M grid differs from frozen 150/300/500 km")
    if not grid["m_strategy"].astype(str).eq("buffer").all():
        raise ValueError("v2.8.3 M grid must remain buffer based")
    if len(grid) != 3 or grid["name"].astype(str).nunique() != 3:
        raise ValueError("v2.8.3 requires exactly three M specifications")
    return grid.reset_index(drop=True)


def _empty_cell(
    *, seed: int, taxon: str, taxon_index: int, M_name: str,
    validation_stratum: str, stage: str, reason: str,
    model_pool_eligible: bool = False,
) -> dict[str, object]:
    return {
        "purpose": CELL_PURPOSE,
        "part_seed": int(seed),
        "sealed_fraction": 0.25,
        "taxon": str(taxon),
        "taxon_index": int(taxon_index),
        "validation_stratum": str(validation_stratum),
        "M": str(M_name),
        "model_pool_eligible": bool(model_pool_eligible),
        "shared_assignment_available": False,
        "structurally_supported": False,
        "selected_assignment_attempt": None,
        "minimum_evaluation_occurrences_observed": None,
        "minimum_evaluation_background_rows_observed": None,
        "minimum_training_background_rows_observed": None,
        "unavailable_stage": str(stage),
        "unavailable_reason": str(reason),
    }


def run_structural_admission(
    *, contract_path: str | Path, source_receipt_path: str | Path,
    focal_path: str | Path, target_path: str | Path, taxa_path: str | Path,
    grid_path: str | Path, output_dir: str | Path,
) -> dict[str, object]:
    contract = load_v2_8_3_fresh_confirmation_contract(contract_path)
    receipt = load_v2_8_3_source_receipt(source_receipt_path)
    if sha256_file(focal_path) != EXPECTED_FOCAL_SHA256:
        raise ValueError("v2.8.3 structural focal source SHA mismatch")
    if sha256_file(target_path) != EXPECTED_TARGET_SHA256:
        raise ValueError("v2.8.3 structural target source SHA mismatch")
    if sha256_file(taxa_path) != EXPECTED_PANEL_SHA256:
        raise ValueError("v2.8.3 structural taxon panel SHA mismatch")
    if receipt["focal"]["file_sha256"] != EXPECTED_FOCAL_SHA256 or receipt["target_group"]["file_sha256"] != EXPECTED_TARGET_SHA256:
        raise ValueError("v2.8.3 source receipt differs from downloaded raw sources")

    focal = load_gbif_download(focal_path).records
    target = load_gbif_download(target_path).records
    taxa = pd.read_csv(taxa_path)
    expected_taxa = tuple(taxa["scientific_name"].astype(str))
    if len(expected_taxa) != 12 or len(set(expected_taxa)) != 12:
        raise ValueError("v2.8.3 structural admission requires exactly 12 taxa")
    grid = _grid(grid_path)
    M_names = tuple(grid["name"].astype(str))
    design = contract["fixed_design"]

    cells: list[dict[str, object]] = []
    taxon_rows: list[dict[str, object]] = []
    part_rows: list[dict[str, object]] = []

    for seed in EXPECTED_SEEDS:
        prepared_by_name: dict[str, object] = {}
        for row in grid.itertuples(index=False):
            prepared_by_name[str(row.name)] = prepare_product_a_pilot(
                focal,
                taxa,
                admission_config=OccurrenceAdmissionConfig(),
                min_occurrences=80,
                min_unique_cells=50,
                gate_cell_size_degrees=0.05,
                m_strategy=str(row.m_strategy),
                target_group_pool=target,
                bbox_buffer_degrees=float(row.bbox_buffer_degrees),
                occurrence_buffer_km=float(row.occurrence_buffer_km),
                background_points=int(row.background_points),
                background_cell_size_degrees=float(row.background_cell_size_degrees),
                random_state=int(seed),
                strict_background=False,
                focal_thin_cell_size_degrees=0.05,
                outer_sealed_fraction=0.25,
            )

        for taxon_index, taxon_row in enumerate(taxa.itertuples(index=False)):
            taxon = str(taxon_row.scientific_name)
            stratum = str(taxon_row.validation_stratum)
            gates: dict[str, pd.Series | None] = {}
            occurrences: dict[str, pd.DataFrame] = {}
            backgrounds: dict[str, pd.DataFrame] = {}
            resource_errors: dict[str, str] = {}

            for M_name in M_names:
                prepared = prepared_by_name[M_name]
                gate_match = prepared.species_gate.loc[
                    prepared.species_gate["species"].astype(str).eq(taxon)
                ]
                gate = None if gate_match.empty else gate_match.iloc[0]
                gates[M_name] = gate
                if gate is None or not bool(gate["eligible"]):
                    resource_errors[M_name] = "model-pool occurrence eligibility gate unavailable"
                    continue
                occurrence = prepared.occurrences.loc[
                    prepared.occurrences["species"].astype(str).eq(taxon)
                    & prepared.occurrences[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
                ].reset_index(drop=True)
                background = prepared.background.loc[
                    prepared.background["species"].astype(str).eq(taxon)
                    & prepared.background[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
                ].reset_index(drop=True)
                if occurrence.empty:
                    resource_errors[M_name] = "empty model-pool occurrence resource"
                    continue
                if background.empty:
                    resource_errors[M_name] = "empty model-pool background resource"
                    continue
                occurrences[M_name] = occurrence
                backgrounds[M_name] = background

            if resource_errors:
                for M_name in M_names:
                    cells.append(_empty_cell(
                        seed=seed, taxon=taxon, taxon_index=taxon_index, M_name=M_name,
                        validation_stratum=stratum, stage="model_pool_resource",
                        reason=resource_errors.get(M_name, "shared three-M assignment unavailable because another M resource failed"),
                        model_pool_eligible=M_name not in resource_errors,
                    ))
                taxon_rows.append({
                    "part_seed": int(seed), "sealed_fraction": 0.25,
                    "taxon": taxon, "taxon_index": int(taxon_index),
                    "validation_stratum": stratum, "structurally_auditable": False,
                    "unavailable_stage": "model_pool_resource",
                    "unavailable_reason": "; ".join(f"{k}:{v}" for k, v in sorted(resource_errors.items())),
                })
                continue

            occurrence_fingerprints = {
                occurrence_table_fingerprint(occurrences[name]) for name in M_names
            }
            if len(occurrence_fingerprints) != 1:
                raise ValueError(f"v2.8.3 M changed model-pool occurrence split for {taxon}")
            occurrence = occurrences[M_names[0]]
            partition_seed = int(seed) + int(taxon_index) * 100 + 271
            try:
                partition = make_evidence_balanced_spatial_partitions(
                    occurrence["longitude"].to_numpy(float),
                    occurrence["latitude"].to_numpy(float),
                    {
                        name: (
                            backgrounds[name]["longitude"].to_numpy(float),
                            backgrounds[name]["latitude"].to_numpy(float),
                        )
                        for name in M_names
                    },
                    n_microblocks=int(design["spatial_microblocks"]),
                    outer_folds=int(design["outer_folds"]),
                    minimum_evaluation_occurrences=int(design["minimum_evaluation_occurrences_per_fold"]),
                    minimum_evaluation_background_rows=int(design["minimum_evaluation_background_rows_per_M_fold"]),
                    minimum_training_background_rows=int(design["minimum_training_background_rows_per_M_fold"]),
                    assignment_attempts=int(design["assignment_attempts"]),
                    random_state=partition_seed,
                )
            except ValueError as exc:
                for M_name in M_names:
                    cells.append(_empty_cell(
                        seed=seed, taxon=taxon, taxon_index=taxon_index, M_name=M_name,
                        validation_stratum=stratum, stage="evidence_balanced_partition",
                        reason=str(exc), model_pool_eligible=True,
                    ))
                taxon_rows.append({
                    "part_seed": int(seed), "sealed_fraction": 0.25,
                    "taxon": taxon, "taxon_index": int(taxon_index),
                    "validation_stratum": stratum, "structurally_auditable": False,
                    "unavailable_stage": "evidence_balanced_partition",
                    "unavailable_reason": str(exc),
                })
                continue

            ledger = partition.support_ledger
            if not ledger["structural_support_complete"].astype(bool).all():
                raise AssertionError("inherited partition returned an incomplete selected assignment")
            min_occ = int(ledger["n_evaluation_occurrences"].min())
            for M_name in M_names:
                min_eval_bg = int(ledger[f"n_evaluation_background__{M_name}"].min())
                min_train_bg = int(ledger[f"n_training_background__{M_name}"].min())
                cells.append({
                    "purpose": CELL_PURPOSE,
                    "part_seed": int(seed),
                    "sealed_fraction": 0.25,
                    "taxon": taxon,
                    "taxon_index": int(taxon_index),
                    "validation_stratum": stratum,
                    "M": M_name,
                    "model_pool_eligible": True,
                    "shared_assignment_available": True,
                    "structurally_supported": True,
                    "selected_assignment_attempt": int(partition.selected_attempt),
                    "partition_seed": partition_seed,
                    "minimum_evaluation_occurrences_observed": min_occ,
                    "minimum_evaluation_background_rows_observed": min_eval_bg,
                    "minimum_training_background_rows_observed": min_train_bg,
                    "unavailable_stage": None,
                    "unavailable_reason": None,
                })
            taxon_rows.append({
                "part_seed": int(seed), "sealed_fraction": 0.25,
                "taxon": taxon, "taxon_index": int(taxon_index),
                "validation_stratum": stratum, "structurally_auditable": True,
                "selected_assignment_attempt": int(partition.selected_attempt),
                "partition_seed": partition_seed,
                "unavailable_stage": None, "unavailable_reason": None,
            })

        part_cells = [row for row in cells if int(row["part_seed"]) == int(seed)]
        if len(part_cells) != 36:
            raise AssertionError(f"v2.8.3 structural part {seed} has {len(part_cells)} cells, expected 36")
        n_supported = sum(bool(row["structurally_supported"]) for row in part_cells)
        auditable = n_supported == 36
        part_rows.append({
            "part_seed": int(seed),
            "part_id": f"seed_{seed}_fraction_0.25",
            "sealed_fraction": 0.25,
            "n_taxon_M_cells": 36,
            "n_structurally_supported_cells": int(n_supported),
            "structurally_auditable": bool(auditable),
            "environmental_extraction_allowed_for_this_part_after_authorization": bool(auditable),
        })

    cell_frame = pd.DataFrame(cells)
    taxon_frame = pd.DataFrame(taxon_rows)
    part_frame = pd.DataFrame(part_rows)
    if len(cell_frame) != 108 or cell_frame[["part_seed", "taxon", "M"]].duplicated().any():
        raise AssertionError("v2.8.3 structural cell denominator is not exactly 108 unique cells")
    if len(taxon_frame) != 36 or taxon_frame[["part_seed", "taxon"]].duplicated().any():
        raise AssertionError("v2.8.3 structural taxon denominator is not exactly 36")
    if len(part_frame) != 3 or set(part_frame["part_seed"].astype(int)) != set(EXPECTED_SEEDS):
        raise AssertionError("v2.8.3 structural part denominator is not exactly three seeds")

    n_auditable = int(part_frame["structurally_auditable"].astype(bool).sum())
    ready_full = n_auditable == 3
    primary_state = "pending_ecological_confirmation" if ready_full else "empirical_confirmation_unavailable"
    auditable_seeds = [
        int(row.part_seed) for row in part_frame.itertuples(index=False)
        if bool(row.structurally_auditable)
    ]

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cell_frame.sort_values(["part_seed", "taxon_index", "M"], kind="mergesort").to_csv(
        out / "structural_cells.csv", index=False
    )
    taxon_frame.sort_values(["part_seed", "taxon_index"], kind="mergesort").to_csv(
        out / "taxon_summary.csv", index=False
    )
    part_frame.sort_values("part_seed", kind="mergesort").to_csv(
        out / "part_summary.csv", index=False
    )
    result = {
        "purpose": PURPOSE,
        "contract_issue": 158,
        "source_run_id": int(receipt["workflow_run_id"]),
        "focal_sha256": EXPECTED_FOCAL_SHA256,
        "target_sha256": EXPECTED_TARGET_SHA256,
        "fresh_taxon_panel_sha256": EXPECTED_PANEL_SHA256,
        "sealed_fraction": 0.25,
        "split_seeds": list(EXPECTED_SEEDS),
        "M_km": list(EXPECTED_M),
        "n_taxon_M_part_cells": 108,
        "n_structurally_supported_cells": int(cell_frame["structurally_supported"].astype(bool).sum()),
        "n_structurally_auditable_parts": n_auditable,
        "structurally_auditable_part_seeds": auditable_seeds,
        "all_3_parts_structurally_auditable": ready_full,
        "primary_full_denominator_state_after_structural_admission": primary_state,
        "conditional_ecology_allowed_for_complete_parts_after_separate_authorization": n_auditable > 0,
        "zero_auditable_parts_forbids_environmental_model_and_sealed_evidence": n_auditable == 0,
        "taxon_M_or_seed_replacement_allowed": False,
        "incomplete_part_partial_repair_allowed": False,
        "structural_admission_is_ecological_support": False,
        **_false_barrier(),
    }
    (out / "admission.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", required=True)
    p.add_argument("--source-receipt", required=True)
    p.add_argument("--focal", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--taxa", required=True)
    p.add_argument("--grid", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args(argv)
    run_structural_admission(
        contract_path=a.contract,
        source_receipt_path=a.source_receipt,
        focal_path=a.focal,
        target_path=a.target,
        taxa_path=a.taxa,
        grid_path=a.grid,
        output_dir=a.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
