"""Post-process Product A with conventional AUC/Boyce selector contrasts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .evaluation_contrast import benchmark_selector_contrast
from .universe import candidate_universes_from_manifest


def _read_choice(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _canonical_specification(grid: pd.DataFrame, explicit: str | None) -> str:
    names = grid["name"].astype(str).tolist()
    if explicit:
        if explicit not in names:
            raise ValueError(f"canonical specification {explicit!r} not found in grid")
        return explicit
    if "buffer_300km" in names:
        return "buffer_300km"
    buffer_rows = grid.loc[grid["m_strategy"].astype(str).eq("buffer")].copy()
    if len(buffer_rows) and "occurrence_buffer_km" in buffer_rows:
        values = pd.to_numeric(buffer_rows["occurrence_buffer_km"], errors="coerce")
        if values.notna().any():
            median = float(values.dropna().median())
            idx = (values - median).abs().idxmin()
            return str(buffer_rows.loc[idx, "name"])
    if not names:
        raise ValueError("pilot grid is empty")
    return names[len(names) // 2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare discovery-frozen canonical-M AUC/Boyce selection and a strong per-species nested-AUC selector "
            "against the SDMR M-robust selector on the same unseen taxa."
        )
    )
    parser.add_argument("--product-a-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--canonical-specification")
    args = parser.parse_args(argv)

    root = Path(args.product_a_dir)
    discovery_path = root / "protocol_discovery_metrics.csv"
    choice_path = root / "product_a_protocol_choice.txt"
    run_spec_path = root / "pilot_grid_specification.json"
    grid_path = root / "pilot_grid_frozen.csv"
    occurrence_path = root / "pilot_occurrences.csv"
    for path in (discovery_path, choice_path, run_spec_path, grid_path, occurrence_path):
        if not path.exists():
            raise SystemExit(f"missing Product-A contrast input: {path}")

    discovery = pd.read_csv(discovery_path)
    choice = _read_choice(choice_path)
    run_spec = json.loads(run_spec_path.read_text(encoding="utf-8"))
    grid = pd.read_csv(grid_path)
    occurrences = pd.read_csv(occurrence_path)
    canonical = _canonical_specification(grid, args.canonical_specification)

    validation_species = [x for x in choice.get("validation_species", "").split(",") if x]
    if not validation_species:
        raise SystemExit("Product-A choice does not contain validation_species")
    sdmr_universe = choice.get("winning_universe", "")
    sdmr_strategy = choice.get("winning_strategy", "")
    if not sdmr_universe or not sdmr_strategy:
        raise SystemExit("Product-A choice does not contain winning universe/strategy")

    manifest = pd.read_csv(args.manifest)
    universes = candidate_universes_from_manifest(manifest)
    specifications = {}
    for name in grid["name"].astype(str):
        background_path = root / "specifications" / name / "background.csv"
        if not background_path.exists():
            raise SystemExit(f"missing Product-A background for contrast: {background_path}")
        specifications[name] = (occurrences.copy(), pd.read_csv(background_path))

    result = benchmark_selector_contrast(
        specifications,
        universes,
        discovery,
        validation_species,
        canonical_specification=canonical,
        sdmr_universe=sdmr_universe,
        sdmr_strategy=sdmr_strategy,
        sealed_fraction=float(run_spec["spatial_test_fraction"]),
        vif_threshold=float(run_spec["vif_threshold"]),
        max_predictors=int(run_spec["max_predictors"]),
        random_repeats=0,
        compute_drop_one=False,
        random_state=int(run_spec["seed"]),
    )
    result.choices.to_csv(root / "selector_contrast_choices.csv", index=False)
    result.transfer_metrics.to_csv(root / "selector_contrast_transfer_metrics.csv", index=False)
    result.transfer_summary.to_csv(root / "selector_contrast_transfer_summary.csv", index=False)
    result.paired_deltas.to_csv(root / "selector_contrast_paired_deltas.csv", index=False)
    (root / "selector_contrast_contract.json").write_text(
        json.dumps(
            {
                "canonical_specification": canonical,
                "selection_data": "discovery_taxa_only_for_cross_taxon_selectors; model_pool_only_for_local_nested_auc",
                "evaluation_data": "same_outer_sealed_unseen_taxa_across_all_predeclared_M_specs",
                "auc_interpretation": "presence_rank is numerically presence-background ROC AUC with half-credit ties",
                "boyce_interpretation": "binned presence-background Boyce-style index",
                "sdmr_interpretation": "cross-M within-case rank selector; no weighted super-score",
                "local_nested_auc_interpretation": (
                    "for each unseen species x M case, choose universe x strategy only by model-pool inner spatial-CV "
                    "AUC-equivalent score, then open the same preassigned outer sealed rows"
                ),
                "selector_set": ["sdmr_m_robust", "canonical_m_auc", "canonical_m_boyce", "local_nested_auc"],
                "validation_species": validation_species,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
