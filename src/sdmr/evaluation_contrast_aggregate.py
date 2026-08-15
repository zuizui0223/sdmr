"""Aggregate repeated Product-A selector contrasts without changing promotion criteria."""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd


_REQUIRED_FILES = (
    "part_metadata.json",
    "selector_contrast_choices.csv",
    "selector_contrast_transfer_summary.csv",
    "selector_contrast_paired_deltas.csv",
)


def _part_dirs(root: Path) -> list[Path]:
    hits = []
    for metadata in root.rglob("part_metadata.json"):
        directory = metadata.parent
        if all((directory / name).exists() for name in _REQUIRED_FILES):
            hits.append(directory)
    return sorted(set(hits))


def aggregate_selector_contrasts(parts_root: str | Path) -> dict[str, pd.DataFrame]:
    """Combine already-frozen selector contrasts from repeated stability parts."""
    root = Path(parts_root)
    parts = _part_dirs(root)
    if not parts:
        raise ValueError("No complete selector-contrast stability parts found")

    choice_frames = []
    summary_frames = []
    delta_frames = []
    run_rows = []
    for directory in parts:
        metadata = json.loads((directory / "part_metadata.json").read_text(encoding="utf-8"))
        seed = int(metadata["seed"])
        fraction = float(metadata["sealed_fraction"])
        run_id = f"seed_{seed}_fraction_{fraction:.2f}"
        common = {"stability_run": run_id, "seed": seed, "sealed_fraction": fraction}

        choices = pd.read_csv(directory / "selector_contrast_choices.csv").assign(**common)
        summaries = pd.read_csv(directory / "selector_contrast_transfer_summary.csv").assign(**common)
        deltas = pd.read_csv(directory / "selector_contrast_paired_deltas.csv").assign(**common)
        choice_frames.append(choices)
        summary_frames.append(summaries)
        delta_frames.append(deltas)

        run_row = dict(common)
        for comparator in ("canonical_m_auc", "canonical_m_boyce"):
            subset = deltas.loc[deltas["comparator"].astype(str) == comparator].copy()
            values = pd.to_numeric(subset.get("delta_presence_rank"), errors="coerce")
            values = values[np.isfinite(values)]
            run_row[f"{comparator}_n_pairs"] = int(len(values))
            run_row[f"{comparator}_mean_delta"] = float(values.mean()) if len(values) else np.nan
            run_row[f"{comparator}_positive_fraction"] = float((values > 0).mean()) if len(values) else np.nan
        run_rows.append(run_row)

    choices = pd.concat(choice_frames, ignore_index=True)
    summaries = pd.concat(summary_frames, ignore_index=True)
    deltas = pd.concat(delta_frames, ignore_index=True)
    runs = pd.DataFrame(run_rows)

    comparator_rows = []
    for comparator, subset in deltas.groupby("comparator", sort=True):
        values = pd.to_numeric(subset["delta_presence_rank"], errors="coerce")
        values = values[np.isfinite(values)]
        run_means = (
            subset.assign(delta=pd.to_numeric(subset["delta_presence_rank"], errors="coerce"))
            .groupby("stability_run")["delta"]
            .mean()
            .dropna()
        )
        comparator_rows.append(
            {
                "comparator": str(comparator),
                "n_runs": int(subset["stability_run"].nunique()),
                "n_pairs": int(len(values)),
                "mean_delta_presence_rank": float(values.mean()) if len(values) else np.nan,
                "median_delta_presence_rank": float(values.median()) if len(values) else np.nan,
                "positive_pair_fraction": float((values > 0).mean()) if len(values) else np.nan,
                "positive_run_fraction": float((run_means > 0).mean()) if len(run_means) else np.nan,
                "worst_run_mean_delta": float(run_means.min()) if len(run_means) else np.nan,
                "best_run_mean_delta": float(run_means.max()) if len(run_means) else np.nan,
            }
        )
    comparator_summary = pd.DataFrame(comparator_rows)

    conventional = choices.loc[choices["selector"].isin(["canonical_m_auc", "canonical_m_boyce"])].copy()
    if "same_method_as_sdmr" in conventional:
        conventional["same_method_as_sdmr"] = conventional["same_method_as_sdmr"].astype(str).str.lower().map(
            {"true": True, "false": False}
        ).fillna(conventional["same_method_as_sdmr"].astype(bool))
    choice_summary = (
        conventional.groupby("selector", as_index=False)
        .agg(
            n_runs=("stability_run", "nunique"),
            same_method_as_sdmr_fraction=("same_method_as_sdmr", "mean"),
            n_distinct_universes=("universe", "nunique"),
            n_distinct_strategies=("strategy", "nunique"),
        )
        if len(conventional)
        else pd.DataFrame()
    )

    return {
        "selector_contrast_choices_all_runs": choices,
        "selector_contrast_transfer_summary_all_runs": summaries,
        "selector_contrast_paired_deltas_all_runs": deltas,
        "selector_contrast_run_summary": runs,
        "selector_contrast_comparator_summary": comparator_summary,
        "selector_contrast_choice_summary": choice_summary,
    }


def write_selector_contrast_aggregate(parts_root: str | Path, output_dir: str | Path) -> dict[str, pd.DataFrame]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    tables = aggregate_selector_contrasts(parts_root)
    for name, table in tables.items():
        table.to_csv(output / f"{name}.csv", index=False)
    return tables
