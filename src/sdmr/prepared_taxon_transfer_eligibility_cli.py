"""Build a model-outcome-free eligibility ledger for empirical taxon transfer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .pilot import MODEL_ROLE, OUTER_ROLE_COL
from .prepared_recovery_procedure_cli import _read_selected_csv, _sha256, _validate_cache
from .prepared_taxon_transfer_cli import _load_taxon_role_config, _validate_outcome_blind_panel
from .taxon_transfer_spatial_eligibility import (
    assign_outcome_blind_taxon_roles,
    spatial_support_fold_ledger,
)
from .validation import make_spatial_partition


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Screen a frozen taxon-transfer panel for pre-model spatial support."
    )
    parser.add_argument("--prepared-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--candidate-taxa", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--outer-folds", type=int, default=2)
    parser.add_argument("--n-spatial-blocks", type=int, default=4)
    parser.add_argument("--minimum-background-rows-per-side", type=int, default=5)
    parser.add_argument("--minimum-presence-rows-per-side", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260814)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument("--source-artifact-id", default="")
    args = parser.parse_args(argv)
    if args.outer_folds < 2 or args.n_spatial_blocks < 4:
        parser.error("outer-folds must be >=2 and n-spatial-blocks must be >=4")

    root = Path(args.prepared_dir)
    manifest_path = Path(args.manifest)
    candidate_path = Path(args.candidate_taxa)
    manifest = pd.read_csv(manifest_path)
    source_contract = _validate_cache(root, manifest)
    candidate_roles = _load_taxon_role_config(candidate_path)
    panel_contract = _validate_outcome_blind_panel(root, candidate_roles, source_contract)
    candidate_taxa = tuple(candidate_roles["scientific_name"].astype(str))
    panel_index = {species: i for i, species in enumerate(candidate_taxa)}

    usecols = ["species", "longitude", "latitude", OUTER_ROLE_COL]
    occurrences = _read_selected_csv(
        root / "pilot_occurrences.csv", set(candidate_taxa), usecols
    )
    grid = pd.read_csv(root / "pilot_grid_frozen.csv")
    specs = tuple(grid["name"].astype(str))
    backgrounds = {
        spec: _read_selected_csv(
            root / "specifications" / spec / "background.csv",
            set(candidate_taxa),
            usecols,
        )
        for spec in specs
    }

    fold_frames: list[pd.DataFrame] = []
    species_rows: list[dict[str, object]] = []
    model_presence_counts: dict[str, int] = {}
    for species in candidate_taxa:
        p_model = occurrences.loc[
            occurrences["species"].astype(str).eq(species)
            & occurrences[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
        ].reset_index(drop=True)
        model_presence_counts[species] = int(len(p_model))
        species_cell_failures: list[str] = []
        for spec_index, spec in enumerate(specs):
            b_all = backgrounds[spec]
            b_model = b_all.loc[
                b_all["species"].astype(str).eq(species)
                & b_all[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
            ].reset_index(drop=True)
            random_state = int(args.seed + panel_index[species] * 100 + spec_index)
            try:
                partition = make_spatial_partition(
                    pd.to_numeric(p_model["longitude"], errors="raise").to_numpy(float),
                    pd.to_numeric(p_model["latitude"], errors="raise").to_numpy(float),
                    pd.to_numeric(b_model["longitude"], errors="raise").to_numpy(float),
                    pd.to_numeric(b_model["latitude"], errors="raise").to_numpy(float),
                    n_blocks=int(args.n_spatial_blocks),
                    holdout_fraction=0.20,
                    random_state=random_state,
                )
                ledger = spatial_support_fold_ledger(
                    partition.presence_blocks,
                    partition.background_blocks,
                    outer_folds=args.outer_folds,
                    minimum_background_rows_per_side=args.minimum_background_rows_per_side,
                    minimum_presence_rows_per_side=args.minimum_presence_rows_per_side,
                )
            except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                ledger = pd.DataFrame(
                    [
                        {
                            "outer_fold": -1,
                            "n_presence_train": 0,
                            "n_presence_test": 0,
                            "n_background_train": 0,
                            "n_background_test": 0,
                            "eligible_fold": False,
                            "failure_reason": f"partition_error:{exc}",
                        }
                    ]
                )
            ledger = ledger.copy()
            ledger["species"] = species
            ledger["perturbation"] = spec
            ledger["random_state"] = random_state
            ledger["n_model_presence_total"] = len(p_model)
            ledger["n_model_background_total"] = len(b_model)
            fold_frames.append(ledger)
            if not bool(ledger["eligible_fold"].all()):
                species_cell_failures.append(spec)
        species_rows.append(
            {
                "scientific_name": species,
                "eligible": not species_cell_failures,
                "failing_perturbations": ",".join(species_cell_failures),
                "model_presence_count": len(p_model),
                "original_panel_index": panel_index[species],
            }
        )

    fold_ledger = pd.concat(fold_frames, ignore_index=True)
    species_eligibility = pd.DataFrame(species_rows)
    eligible_taxa = tuple(
        species_eligibility.loc[species_eligibility["eligible"], "scientific_name"].astype(str)
    )
    validation_fraction = float(source_contract["taxon_validation_fraction_for_future_search"])
    role_frame = assign_outcome_blind_taxon_roles(
        eligible_taxa,
        seed=int(source_contract["seed"]),
        validation_fraction=validation_fraction,
        minimum_validation_taxa=2,
        minimum_discovery_taxa=2,
    )
    role_frame = role_frame.merge(
        species_eligibility[
            ["scientific_name", "model_presence_count", "original_panel_index"]
        ],
        on="scientific_name",
        how="left",
        validate="one_to_one",
    ).sort_values("original_panel_index", kind="mergesort")

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fold_ledger.to_csv(out / "spatial_support_fold_ledger.csv", index=False)
    species_eligibility.to_csv(out / "spatial_support_species_eligibility.csv", index=False)
    role_frame.to_csv(out / "eligible_taxon_roles.csv", index=False)

    contract = {
        "purpose": "empirical_product_a_v2_taxon_transfer_spatial_eligibility",
        "scientific_promotion_run": False,
        "source_run_id": args.source_run_id,
        "source_artifact_id": args.source_artifact_id,
        "source_feature_cache_contract": source_contract,
        "candidate_panel_contract": panel_contract,
        "candidate_taxa_config": str(candidate_path),
        "candidate_taxa_config_sha256": _sha256(candidate_path),
        "candidate_panel_taxa": list(candidate_taxa),
        "eligible_taxa": list(role_frame["scientific_name"].astype(str)),
        "ineligible_taxa": list(
            species_eligibility.loc[~species_eligibility["eligible"], "scientific_name"].astype(str)
        ),
        "role_assignments": {
            str(row.scientific_name): str(row.role)
            for row in role_frame.itertuples(index=False)
        },
        "panel_index_by_species": panel_index,
        "outer_folds": args.outer_folds,
        "n_spatial_blocks": args.n_spatial_blocks,
        "minimum_background_rows_per_side": args.minimum_background_rows_per_side,
        "minimum_presence_rows_per_side": args.minimum_presence_rows_per_side,
        "spatial_partition_seed": args.seed,
        "role_assignment_seed": int(source_contract["seed"]),
        "role_assignment_validation_fraction": validation_fraction,
        "model_scores_used": False,
        "environmental_predictor_values_used": False,
        "hidden_truth_used": False,
        "sealed_rows_used_for_eligibility": False,
        "eligibility_uses_model_pool_coordinates_and_row_counts_only": True,
    }
    (out / "taxon_transfer_spatial_eligibility_contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
