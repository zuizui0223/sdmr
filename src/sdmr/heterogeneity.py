"""Stratum-level environmental-process heterogeneity for Product B.

This module is descriptive by design. It identifies where evidence for a process
changes across clades, growth forms, biomes, or other declared species strata;
it does not turn those differences into causal or inferential claims by itself.
"""

from __future__ import annotations

from collections.abc import Sequence
import numpy as np
import pandas as pd

from .drivers import aggregate_process_evidence, validate_candidate_manifest


def _modeled_species_from_evidence(
    selection_rows: pd.DataFrame,
    drop_one_rows: pd.DataFrame,
    *,
    species_col: str,
) -> list[str]:
    species = set()
    if species_col in selection_rows:
        species.update(selection_rows[species_col].dropna().astype(str))
    if species_col in drop_one_rows:
        species.update(drop_one_rows[species_col].dropna().astype(str))
    return sorted(species)


def validate_species_metadata(
    species_metadata: pd.DataFrame,
    *,
    species_col: str = "species",
    required_strata: Sequence[str] = (),
) -> pd.DataFrame:
    """Require one metadata row per species and explicit requested strata."""

    missing = {species_col, *required_strata} - set(species_metadata.columns)
    if missing:
        raise KeyError(f"species metadata missing columns: {sorted(missing)}")
    data = species_metadata.copy()
    data[species_col] = data[species_col].astype(str)
    duplicated = data.loc[data[species_col].duplicated(keep=False), species_col].unique().tolist()
    if duplicated:
        raise ValueError(f"species metadata contains duplicate species rows: {sorted(duplicated)}")
    return data.reset_index(drop=True)


def aggregate_process_evidence_by_stratum(
    selection_rows: pd.DataFrame,
    drop_one_rows: pd.DataFrame,
    manifest: pd.DataFrame,
    species_metadata: pd.DataFrame,
    *,
    stratum_col: str,
    modeled_species: Sequence[str] | None = None,
    min_species: int = 5,
    species_col: str = "species",
) -> pd.DataFrame:
    """Recompute equal-species process evidence independently within one stratum.

    Species that selected no predictor from a process still remain in that
    stratum's denominator. ``modeled_species`` should therefore be supplied when
    the full analyzed species universe is known; otherwise it is inferred from
    the union of selection/drop-one tables.
    """

    if min_species < 1:
        raise ValueError("min_species must be >= 1")
    meta = validate_candidate_manifest(manifest)
    species_meta = validate_species_metadata(
        species_metadata, species_col=species_col, required_strata=[stratum_col]
    )
    universe = (
        sorted({str(x) for x in modeled_species})
        if modeled_species is not None
        else _modeled_species_from_evidence(selection_rows, drop_one_rows, species_col=species_col)
    )
    if not universe:
        return pd.DataFrame()

    species_meta = species_meta.loc[species_meta[species_col].isin(universe)].copy()
    species_meta = species_meta.loc[species_meta[stratum_col].notna()].copy()
    species_meta[stratum_col] = species_meta[stratum_col].astype(str)
    known = set(species_meta[species_col])
    missing_metadata = sorted(set(universe) - known)
    if missing_metadata:
        raise ValueError(
            f"modeled species missing non-null {stratum_col!r} metadata: {missing_metadata[:10]}"
            + ("..." if len(missing_metadata) > 10 else "")
        )

    frames: list[pd.DataFrame] = []
    for stratum, group in species_meta.groupby(stratum_col, sort=True):
        species = sorted(group[species_col].astype(str).tolist())
        if len(species) < min_species:
            continue
        species_set = set(species)
        sel = selection_rows.loc[
            selection_rows[species_col].astype(str).isin(species_set)
        ].copy() if species_col in selection_rows else pd.DataFrame()
        drop = drop_one_rows.loc[
            drop_one_rows[species_col].astype(str).isin(species_set)
        ].copy() if species_col in drop_one_rows else pd.DataFrame()
        summary = aggregate_process_evidence(
            sel,
            drop,
            meta,
            species_universe=species,
            species_col=species_col,
        )
        if len(summary):
            frames.append(
                summary.assign(
                    stratum_type=stratum_col,
                    stratum=str(stratum),
                    n_species_stratum=len(species),
                )
            )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def aggregate_process_evidence_across_strata(
    selection_rows: pd.DataFrame,
    drop_one_rows: pd.DataFrame,
    manifest: pd.DataFrame,
    species_metadata: pd.DataFrame,
    *,
    stratum_cols: Sequence[str],
    modeled_species: Sequence[str] | None = None,
    min_species: int = 5,
    species_col: str = "species",
) -> pd.DataFrame:
    """Stack process summaries for multiple predeclared heterogeneity dimensions."""

    if not stratum_cols:
        raise ValueError("At least one stratum column is required")
    frames = []
    for column in stratum_cols:
        frame = aggregate_process_evidence_by_stratum(
            selection_rows,
            drop_one_rows,
            manifest,
            species_metadata,
            stratum_col=column,
            modeled_species=modeled_species,
            min_species=min_species,
            species_col=species_col,
        )
        if len(frame):
            frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def summarize_process_heterogeneity(stratified: pd.DataFrame) -> pd.DataFrame:
    """Describe between-stratum spread without treating it as a significance test."""

    required = {"stratum_type", "stratum", "process", "selection_fraction"}
    missing = required - set(stratified.columns)
    if missing:
        raise KeyError(f"stratified process table missing columns: {sorted(missing)}")
    if not len(stratified):
        return pd.DataFrame()

    rows = []
    for (stratum_type, process), group in stratified.groupby(["stratum_type", "process"], sort=True):
        selection = pd.to_numeric(group["selection_fraction"], errors="coerce")
        max_idx = selection.idxmax() if selection.notna().any() else None
        min_idx = selection.idxmin() if selection.notna().any() else None
        drop = pd.to_numeric(group.get("mean_max_drop_one_loss", np.nan), errors="coerce")
        gain = pd.to_numeric(group.get("mean_incremental_gain", np.nan), errors="coerce")
        rows.append(
            {
                "stratum_type": str(stratum_type),
                "process": str(process),
                "n_strata": int(group["stratum"].nunique()),
                "mean_selection_fraction": float(selection.mean()),
                "min_selection_fraction": float(selection.min()),
                "max_selection_fraction": float(selection.max()),
                "selection_fraction_range": float(selection.max() - selection.min()),
                "selection_fraction_sd": float(selection.std(ddof=0)),
                "max_selection_stratum": "" if max_idx is None else str(group.loc[max_idx, "stratum"]),
                "min_selection_stratum": "" if min_idx is None else str(group.loc[min_idx, "stratum"]),
                "mean_drop_one_loss_across_strata": float(drop.mean()) if drop.notna().any() else np.nan,
                "drop_one_loss_range": float(drop.max() - drop.min()) if drop.notna().any() else np.nan,
                "mean_incremental_gain_across_strata": float(gain.mean()) if gain.notna().any() else np.nan,
                "incremental_gain_range": float(gain.max() - gain.min()) if gain.notna().any() else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["stratum_type", "selection_fraction_range", "process"],
        ascending=[True, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
