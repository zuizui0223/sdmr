"""Product-B aggregation from raster-level evidence to environmental processes."""

from __future__ import annotations

from collections.abc import Sequence
import pandas as pd


REQUIRED_MANIFEST_COLUMNS = {
    "predictor",
    "source",
    "version",
    "candidate_class",
    "process",
    "mechanism",
}


def validate_candidate_manifest(manifest: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize predictor metadata used for universal-driver synthesis."""

    missing = REQUIRED_MANIFEST_COLUMNS - set(manifest.columns)
    if missing:
        raise KeyError(f"candidate manifest missing columns: {sorted(missing)}")
    out = manifest.copy()
    out["predictor"] = out["predictor"].astype(str).str.strip()
    if out["predictor"].eq("").any():
        raise ValueError("candidate manifest contains an empty predictor name")
    duplicated = out.loc[out["predictor"].duplicated(keep=False), "predictor"].unique().tolist()
    if duplicated:
        raise ValueError(f"candidate manifest contains duplicate predictors: {sorted(duplicated)}")
    if out["process"].isna().any() or out["process"].astype(str).str.strip().eq("").any():
        raise ValueError("every candidate predictor must have a process label")
    return out.reset_index(drop=True)


def annotate_predictor_metadata(
    rows: pd.DataFrame,
    manifest: pd.DataFrame,
    *,
    predictor_col: str = "predictor",
) -> pd.DataFrame:
    """Attach source/process/mechanism metadata and reject silent unknown rasters."""

    if predictor_col not in rows:
        raise KeyError(predictor_col)
    meta = validate_candidate_manifest(manifest)
    renamed = meta.rename(columns={"predictor": predictor_col})
    merged = rows.merge(renamed, on=predictor_col, how="left", validate="many_to_one")
    missing = merged.loc[merged["process"].isna(), predictor_col].astype(str).unique().tolist()
    if missing:
        raise ValueError(f"predictors missing from candidate manifest: {sorted(missing)}")
    return merged


def aggregate_process_evidence(
    selection_rows: pd.DataFrame,
    drop_one_rows: pd.DataFrame,
    manifest: pd.DataFrame,
    *,
    species_universe: Sequence[str] | None = None,
    species_col: str = "species",
) -> pd.DataFrame:
    """Summarize universal-driver evidence at the environmental-process level.

    Selection frequency uses every species in ``species_universe`` as the
    denominator, including species where a process contributed no selected
    raster. Incremental gains from multiple selected rasters in the same process
    are summed within species. Drop-one evidence is summarized separately and
    reports coverage because only predictors present in a fitted reference model
    can have a drop-one score.
    """

    meta = validate_candidate_manifest(manifest)
    processes = meta["process"].drop_duplicates().astype(str).tolist()

    if species_universe is None:
        species = sorted(
            set(selection_rows.get(species_col, pd.Series(dtype=str)).astype(str))
            | set(drop_one_rows.get(species_col, pd.Series(dtype=str)).astype(str))
        )
    else:
        species = sorted({str(x) for x in species_universe})
    if not species:
        return pd.DataFrame(
            columns=[
                "process", "n_species", "selection_fraction", "mean_incremental_gain",
                "median_incremental_gain", "drop_one_coverage_fraction",
                "mean_max_drop_one_loss", "median_max_drop_one_loss",
            ]
        )

    sel_required = {species_col, "predictor", "gain"}
    if not selection_rows.empty:
        missing = sel_required - set(selection_rows.columns)
        if missing:
            raise KeyError(f"selection_rows missing columns: {sorted(missing)}")
        sel = annotate_predictor_metadata(selection_rows, meta)
        sel[species_col] = sel[species_col].astype(str)
        sel_sp = (
            sel.groupby([species_col, "process"], as_index=False)
            .agg(selected=("predictor", "size"), incremental_gain=("gain", lambda x: x.sum(min_count=1)))
        )
    else:
        sel_sp = pd.DataFrame(columns=[species_col, "process", "selected", "incremental_gain"])

    grid = pd.MultiIndex.from_product([species, processes], names=[species_col, "process"]).to_frame(index=False)
    sel_grid = grid.merge(sel_sp, on=[species_col, "process"], how="left")
    sel_grid["selected"] = sel_grid["selected"].fillna(0).astype(int)
    sel_grid["incremental_gain"] = pd.to_numeric(sel_grid["incremental_gain"], errors="coerce")
    sel_grid.loc[(sel_grid["selected"] == 0) & sel_grid["incremental_gain"].isna(), "incremental_gain"] = 0.0
    sel_grid["gain_known"] = sel_grid["incremental_gain"].notna()
    sel_summary = (
        sel_grid.groupby("process", as_index=False)
        .agg(
            species_selected=("selected", lambda x: int((x > 0).sum())),
            species_with_incremental_gain=("gain_known", "sum"),
            mean_incremental_gain=("incremental_gain", "mean"),
            median_incremental_gain=("incremental_gain", "median"),
        )
    )
    sel_summary["n_species"] = len(species)
    sel_summary["selection_fraction"] = sel_summary["species_selected"] / len(species)
    sel_summary["incremental_gain_coverage_fraction"] = sel_summary["species_with_incremental_gain"] / len(species)

    drop_required = {species_col, "predictor", "loss"}
    if not drop_one_rows.empty:
        missing = drop_required - set(drop_one_rows.columns)
        if missing:
            raise KeyError(f"drop_one_rows missing columns: {sorted(missing)}")
        drop = annotate_predictor_metadata(drop_one_rows, meta)
        drop[species_col] = drop[species_col].astype(str)
        drop["loss"] = pd.to_numeric(drop["loss"], errors="coerce")
        drop_sp = (
            drop.groupby([species_col, "process"], as_index=False)
            .agg(max_drop_one_loss=("loss", "max"))
        )
        drop_summary = (
            drop_sp.groupby("process", as_index=False)
            .agg(
                species_with_drop_one=(species_col, "nunique"),
                mean_max_drop_one_loss=("max_drop_one_loss", "mean"),
                median_max_drop_one_loss=("max_drop_one_loss", "median"),
            )
        )
    else:
        drop_summary = pd.DataFrame(
            columns=["process", "species_with_drop_one", "mean_max_drop_one_loss", "median_max_drop_one_loss"]
        )

    out = sel_summary.merge(drop_summary, on="process", how="left")
    out["species_with_drop_one"] = out["species_with_drop_one"].fillna(0).astype(int)
    out["drop_one_coverage_fraction"] = out["species_with_drop_one"] / len(species)
    return out.sort_values(
        ["selection_fraction", "mean_incremental_gain", "mean_max_drop_one_loss"],
        ascending=[False, False, False],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)


def equivalence_group_process_map(
    equivalence: pd.DataFrame,
    manifest: pd.DataFrame,
) -> pd.DataFrame:
    """Describe whether a substitutable raster group belongs to one or several processes."""

    required = {"predictor", "equivalence_group"}
    missing = required - set(equivalence.columns)
    if missing:
        raise KeyError(f"equivalence missing columns: {sorted(missing)}")
    annotated = annotate_predictor_metadata(equivalence, manifest)
    rows = []
    for group_id, group in annotated.groupby("equivalence_group", sort=True):
        processes = sorted(group["process"].astype(str).unique().tolist())
        mechanisms = sorted(group["mechanism"].astype(str).unique().tolist())
        rows.append(
            {
                "equivalence_group": str(group_id),
                "processes": ",".join(processes),
                "mechanisms": ",".join(mechanisms),
                "n_processes": len(processes),
                "cross_process_substitution": len(processes) > 1,
            }
        )
    return pd.DataFrame(rows)
