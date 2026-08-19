"""Secondary continuous-Boyce selector contrast on frozen Product-A evidence.

This is intentionally outside the frozen Product-A v1 promotion/differentiation
gate. It asks whether choosing a conventional recipe by moving-window CBI on
discovery taxa changes the transfer comparison relative to SDMR.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .evaluation_contrast import _best_discovery_combo, evaluate_selector_transfer
from .evaluation_contrast_cli import _canonical_specification, _read_choice
from .universe import candidate_universes_from_manifest


def _paired_cbi(metrics: pd.DataFrame) -> pd.DataFrame:
    data = metrics.loc[
        metrics["selector"].astype(str).isin(["sdmr_m_robust", "canonical_m_cbi"])
    ].copy()
    pivot = data.pivot_table(
        index=["data_specification", "species"],
        columns="selector",
        values="presence_rank",
        aggfunc="first",
    )
    if not {"sdmr_m_robust", "canonical_m_cbi"}.issubset(pivot.columns):
        return pd.DataFrame()
    paired = pivot[["sdmr_m_robust", "canonical_m_cbi"]].dropna()
    rows = []
    for (specification, species), values in paired.iterrows():
        rows.append(
            {
                "data_specification": str(specification),
                "species": str(species),
                "reference_selector": "sdmr_m_robust",
                "comparator": "canonical_m_cbi",
                "delta_presence_rank": float(values["sdmr_m_robust"] - values["canonical_m_cbi"]),
            }
        )
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Secondary moving-window continuous-Boyce selector contrast on frozen Product-A evidence."
    )
    parser.add_argument("--product-a-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--canonical-specification")
    args = parser.parse_args(argv)

    root = Path(args.product_a_dir)
    discovery = pd.read_csv(root / "protocol_discovery_metrics.csv")
    if "continuous_boyce" not in discovery.columns:
        raise SystemExit(
            "protocol_discovery_metrics.csv lacks continuous_boyce; rerun the same frozen evidence with an engine "
            "that reports the secondary CBI metric. Do not substitute the historical binned Boyce column."
        )
    choice = _read_choice(root / "product_a_protocol_choice.txt")
    run_spec = json.loads((root / "pilot_grid_specification.json").read_text(encoding="utf-8"))
    grid = pd.read_csv(root / "pilot_grid_frozen.csv")
    occurrences = pd.read_csv(root / "pilot_occurrences.csv")
    canonical = _canonical_specification(grid, args.canonical_specification)

    validation_species = [x for x in choice.get("validation_species", "").split(",") if x]
    sdmr_universe = choice.get("winning_universe", "")
    sdmr_strategy = choice.get("winning_strategy", "")
    if not validation_species or not sdmr_universe or not sdmr_strategy:
        raise SystemExit("Product-A choice lacks validation species or winning universe/strategy")

    cbi_u, cbi_s, cbi_score = _best_discovery_combo(
        discovery,
        canonical_specification=canonical,
        metric="continuous_boyce",
    )
    choices = pd.DataFrame(
        [
            {
                "selector": "sdmr_m_robust",
                "universe": sdmr_universe,
                "strategy": sdmr_strategy,
                "selection_metric": "cross_M_within_case_rank",
                "selection_score": np.nan,
                "canonical_specification": canonical,
            },
            {
                "selector": "canonical_m_cbi",
                "universe": cbi_u,
                "strategy": cbi_s,
                "selection_metric": "continuous_boyce",
                "selection_score": cbi_score,
                "canonical_specification": canonical,
            },
        ]
    )

    manifest = pd.read_csv(args.manifest)
    universes = candidate_universes_from_manifest(manifest)
    specifications = {}
    for name in grid["name"].astype(str):
        background_path = root / "specifications" / name / "background.csv"
        if not background_path.exists():
            raise SystemExit(f"missing background: {background_path}")
        specifications[name] = (occurrences.copy(), pd.read_csv(background_path))

    result = evaluate_selector_transfer(
        specifications,
        universes,
        choices,
        validation_species,
        sealed_fraction=float(run_spec["spatial_test_fraction"]),
        vif_threshold=float(run_spec["vif_threshold"]),
        max_predictors=int(run_spec["max_predictors"]),
        random_repeats=0,
        compute_drop_one=False,
        random_state=int(run_spec["seed"]),
    )
    keep = result.transfer_metrics["selector"].astype(str).isin(["sdmr_m_robust", "canonical_m_cbi"])
    transfer = result.transfer_metrics.loc[keep].reset_index(drop=True)
    summary = result.transfer_summary.loc[
        result.transfer_summary["selector"].astype(str).isin(["sdmr_m_robust", "canonical_m_cbi"])
    ].reset_index(drop=True)
    paired = _paired_cbi(transfer)

    choices.to_csv(root / "continuous_boyce_selector_choices.csv", index=False)
    transfer.to_csv(root / "continuous_boyce_selector_transfer_metrics.csv", index=False)
    summary.to_csv(root / "continuous_boyce_selector_transfer_summary.csv", index=False)
    paired.to_csv(root / "continuous_boyce_selector_paired_deltas.csv", index=False)
    (root / "continuous_boyce_selector_contract.json").write_text(
        json.dumps(
            {
                "status": "secondary_post_v1_sensitivity_only",
                "canonical_specification": canonical,
                "selection_data": "discovery_taxa_only",
                "selection_metric": "moving_window_continuous_boyce",
                "outer_sealed_used_for_selection": False,
                "evaluation_data": "same_outer_sealed_unseen_taxa_across_all_predeclared_M_specs",
                "changes_frozen_product_a_v1_criteria": False,
                "comparators": ["sdmr_m_robust", "canonical_m_cbi"],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
