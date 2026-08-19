"""Real-data Product-A pilot preparation from a versioned GBIF bulk download."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import numpy as np
import pandas as pd

from .data.background import bbox_membership, occurrence_buffer_membership, sample_target_group_background
from .data.quality import OccurrenceAdmissionConfig, admit_occurrences, thin_to_grid
from .data.species_gate import species_admission_table
from .validation import make_presence_spatial_partition


OUTER_ROLE_COL = "__sdmr_outer_role"
OUTER_BLOCK_COL = "__sdmr_outer_block"
MODEL_ROLE = "model"
SEALED_ROLE = "sealed"


@dataclass
class ProductAPilotData:
    occurrences: pd.DataFrame
    background: pd.DataFrame
    taxon_selection_ledger: pd.DataFrame
    occurrence_admission_ledger: pd.DataFrame
    species_gate: pd.DataFrame
    background_ledger: pd.DataFrame


def _string_match(series: pd.Series, value: str) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.casefold().eq(str(value).strip().casefold())


def select_configured_taxa(
    records: pd.DataFrame,
    taxa: pd.DataFrame,
    *,
    species_col: str = "species",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select a predeclared pilot taxon list from a GBIF occurrence table.

    A supplied taxon key is attempted first. During the GBIF Backbone -> COL XR
    transition, however, v2 name matching and occurrence outputs can expose keys
    from different namespaces. If a supplied key matches zero rows, SDMR falls
    back to exact canonical-name matching and records that fallback explicitly in
    the ledger. The fallback is never silent and does not broaden beyond exact
    case-insensitive scientific-name equality.
    """

    if "scientific_name" not in taxa:
        raise KeyError("taxa config must contain scientific_name")
    name_columns = [c for c in (species_col, "acceptedScientificName", "scientificName") if c in records]
    key_columns = [c for c in ("acceptedTaxonKey", "taxonKey") if c in records]
    if not name_columns and not key_columns:
        raise KeyError("records contain neither usable taxon keys nor name columns")

    selected_frames: list[pd.DataFrame] = []
    ledger_rows: list[dict[str, object]] = []
    for row in taxa.to_dict(orient="records"):
        name = str(row.get("scientific_name", "")).strip()
        if not name:
            continue
        key_raw = row.get("taxon_key")
        key = "" if key_raw is None or pd.isna(key_raw) else str(key_raw).strip()

        key_mask = pd.Series(False, index=records.index)
        if key:
            for col in key_columns:
                key_mask |= records[col].fillna("").astype(str).str.strip().eq(key)
        key_rows = int(key_mask.sum())

        name_mask = pd.Series(False, index=records.index)
        for col in name_columns:
            name_mask |= _string_match(records[col], name)
        name_rows = int(name_mask.sum())

        if key and key_rows:
            mask = key_mask
            mode = "taxon_key"
        elif key and name_rows:
            mask = name_mask
            mode = "taxon_key_fallback_exact_name"
        elif key:
            mask = key_mask
            mode = "taxon_key_no_match"
        else:
            mask = name_mask
            mode = "exact_name"

        subset = records.loc[mask].copy()
        if len(subset):
            subset[species_col] = name
            subset["pilot_taxon_query"] = name
            selected_frames.append(subset)
        ledger_rows.append(
            {
                **row,
                "selection_mode": mode,
                "key_match_rows": key_rows,
                "name_match_rows": name_rows,
                "matched_rows": int(mask.sum()),
                "matched": bool(mask.any()),
            }
        )
    selected = pd.concat(selected_frames, ignore_index=True) if selected_frames else records.iloc[0:0].copy()
    return selected, pd.DataFrame(ledger_rows)


def _bbox_mask_with_buffer(
    target_group: pd.DataFrame,
    focal: pd.DataFrame,
    *,
    buffer_degrees: float,
) -> np.ndarray:
    if buffer_degrees < 0:
        raise ValueError("bbox_buffer_degrees must be >= 0")
    lon = pd.to_numeric(focal["longitude"], errors="coerce").dropna()
    lat = pd.to_numeric(focal["latitude"], errors="coerce").dropna()
    if not len(lon) or not len(lat):
        raise ValueError("focal occurrences contain no finite coordinates")
    west = max(-180.0, float(lon.min()) - buffer_degrees)
    east = min(180.0, float(lon.max()) + buffer_degrees)
    south = max(-90.0, float(lat.min()) - buffer_degrees)
    north = min(90.0, float(lat.max()) + buffer_degrees)
    return bbox_membership(target_group, west=west, east=east, south=south, north=north)


def _assign_outer_roles(
    frame: pd.DataFrame,
    *,
    sealed_fraction: float,
    n_spatial_blocks: int,
    random_state: int,
    species_col: str = "species",
) -> pd.DataFrame:
    """Assign model/sealed roles before any M or background construction."""

    frames: list[pd.DataFrame] = []
    for i, (species, group) in enumerate(frame.groupby(species_col, sort=True)):
        group = group.reset_index(drop=True).copy()
        if len(group) < 4:
            continue
        part = make_presence_spatial_partition(
            pd.to_numeric(group["longitude"], errors="coerce").to_numpy(float),
            pd.to_numeric(group["latitude"], errors="coerce").to_numpy(float),
            n_blocks=n_spatial_blocks,
            holdout_fraction=sealed_fraction,
            random_state=random_state + i,
        )
        group[OUTER_BLOCK_COL] = part.presence_blocks.astype(int)
        group[OUTER_ROLE_COL] = np.where(
            np.isin(part.presence_blocks, part.train_blocks),
            MODEL_ROLE,
            SEALED_ROLE,
        )
        frames.append(group)
    return pd.concat(frames, ignore_index=True) if frames else frame.iloc[0:0].copy()


def _outer_model_gate(
    thinned: pd.DataFrame,
    partitioned: pd.DataFrame,
    *,
    min_occurrences: int,
    min_unique_cells: int,
    cell_size_degrees: float,
    species_col: str = "species",
) -> pd.DataFrame:
    """Require modelling-data sufficiency using model-pool rows only."""

    total = species_admission_table(
        thinned,
        min_occurrences=1,
        min_unique_cells=1,
        cell_size_degrees=cell_size_degrees,
        species_col=species_col,
    ).rename(
        columns={
            "n_occurrences": "n_occurrences_total_thinned",
            "n_unique_cells": "n_unique_cells_total_thinned",
        }
    )
    total = total[[species_col, "n_occurrences_total_thinned", "n_unique_cells_total_thinned"]]

    model = partitioned.loc[partitioned[OUTER_ROLE_COL].astype(str) == MODEL_ROLE].reset_index(drop=True)
    model_gate = species_admission_table(
        model,
        min_occurrences=min_occurrences,
        min_unique_cells=min_unique_cells,
        cell_size_degrees=cell_size_degrees,
        species_col=species_col,
    ).rename(
        columns={
            "n_occurrences": "n_occurrences_model_pool",
            "n_unique_cells": "n_unique_cells_model_pool",
        }
    )
    keep = [
        species_col,
        "n_occurrences_model_pool",
        "n_unique_cells_model_pool",
        "eligible",
        "min_occurrences",
        "min_unique_cells",
        "cell_size_degrees",
    ]
    gate = total.merge(model_gate[keep], on=species_col, how="left")
    gate["n_occurrences_model_pool"] = gate["n_occurrences_model_pool"].fillna(0).astype(int)
    gate["n_unique_cells_model_pool"] = gate["n_unique_cells_model_pool"].fillna(0).astype(int)
    gate["eligible"] = gate["eligible"].fillna(False).astype(bool)
    gate["min_occurrences"] = gate["min_occurrences"].fillna(int(min_occurrences)).astype(int)
    gate["min_unique_cells"] = gate["min_unique_cells"].fillna(int(min_unique_cells)).astype(int)
    gate["cell_size_degrees"] = gate["cell_size_degrees"].fillna(float(cell_size_degrees)).astype(float)

    sealed_counts = (
        partitioned.loc[partitioned[OUTER_ROLE_COL].astype(str) == SEALED_ROLE]
        .groupby(species_col)
        .size()
        .rename("n_occurrences_sealed")
        .reset_index()
    )
    gate = gate.merge(sealed_counts, on=species_col, how="left")
    gate["n_occurrences_sealed"] = gate["n_occurrences_sealed"].fillna(0).astype(int)
    return gate.sort_values(species_col, kind="mergesort").reset_index(drop=True)


def _assign_background_outer_roles(
    background: pd.DataFrame,
    *,
    sealed_fraction: float,
    n_spatial_blocks: int,
    random_state: int,
) -> pd.DataFrame:
    """Hold out independent reference background without using sealed presences."""

    if len(background) < 4:
        raise ValueError("At least four background cells are required for a sealed reference split")
    part = make_presence_spatial_partition(
        pd.to_numeric(background["longitude"], errors="coerce").to_numpy(float),
        pd.to_numeric(background["latitude"], errors="coerce").to_numpy(float),
        n_blocks=n_spatial_blocks,
        holdout_fraction=sealed_fraction,
        random_state=random_state,
    )
    out = background.reset_index(drop=True).copy()
    out[OUTER_BLOCK_COL] = part.presence_blocks.astype(int)
    out[OUTER_ROLE_COL] = np.where(
        np.isin(part.presence_blocks, part.train_blocks),
        MODEL_ROLE,
        SEALED_ROLE,
    )
    if (out[OUTER_ROLE_COL] == MODEL_ROLE).sum() < 2 or (out[OUTER_ROLE_COL] == SEALED_ROLE).sum() < 2:
        raise ValueError("Background split did not yield enough model/reference cells")
    return out


def prepare_product_a_pilot(
    records: pd.DataFrame,
    taxa: pd.DataFrame,
    *,
    admission_config: OccurrenceAdmissionConfig,
    min_occurrences: int,
    min_unique_cells: int,
    gate_cell_size_degrees: float,
    m_strategy: Literal["bbox", "buffer"],
    target_group_pool: pd.DataFrame | None = None,
    bbox_buffer_degrees: float = 2.0,
    occurrence_buffer_km: float = 300.0,
    background_points: int = 5_000,
    background_cell_size_degrees: float = 1 / 120,
    random_state: int = 42,
    strict_background: bool = False,
    focal_thin_cell_size_degrees: float | None = None,
    outer_sealed_fraction: float | None = None,
    outer_n_spatial_blocks: int = 8,
) -> ProductAPilotData:
    """Prepare audited occurrence/background tables for a real Product-A pilot.

    When ``outer_sealed_fraction`` is supplied, focal occurrences are spatially
    sealed *before* M/background construction. Only model-pool occurrences may
    then define M or exclude focal cells from target-group background. This is
    the leakage-safe path used by the citable Product-A protocol grid.
    """

    selected, taxon_ledger = select_configured_taxa(records, taxa)
    admission = admit_occurrences(selected, config=admission_config)
    accepted = admission.accepted

    if focal_thin_cell_size_degrees is not None:
        accepted = thin_to_grid(
            accepted,
            cell_size_degrees=float(focal_thin_cell_size_degrees),
        )

    if outer_sealed_fraction is not None:
        if not 0 < float(outer_sealed_fraction) < 1:
            raise ValueError("outer_sealed_fraction must be between 0 and 1")
        partitioned = _assign_outer_roles(
            accepted,
            sealed_fraction=float(outer_sealed_fraction),
            n_spatial_blocks=int(outer_n_spatial_blocks),
            random_state=int(random_state),
        )
        gate = _outer_model_gate(
            accepted,
            partitioned,
            min_occurrences=min_occurrences,
            min_unique_cells=min_unique_cells,
            cell_size_degrees=gate_cell_size_degrees,
        )
        eligible = set(gate.loc[gate["eligible"], "species"].astype(str))
        accepted = partitioned.loc[partitioned["species"].astype(str).isin(eligible)].reset_index(drop=True)
    else:
        gate = species_admission_table(
            accepted,
            min_occurrences=min_occurrences,
            min_unique_cells=min_unique_cells,
            cell_size_degrees=gate_cell_size_degrees,
        )
        eligible = set(gate.loc[gate["eligible"], "species"].astype(str))
        accepted = accepted.loc[accepted["species"].astype(str).isin(eligible)].reset_index(drop=True)

    if target_group_pool is None:
        target_admission = admit_occurrences(selected, config=admission_config)
        target_group = target_admission.accepted
        target_group_source = "pilot_taxa_only"
    else:
        target_admission = admit_occurrences(target_group_pool, config=admission_config)
        target_group = target_admission.accepted
        target_group_source = "external_target_group"

    background_frames: list[pd.DataFrame] = []
    background_rows: list[dict[str, object]] = []
    for i, species in enumerate(sorted(eligible)):
        focal = accepted.loc[accepted["species"].astype(str) == species].reset_index(drop=True)
        if outer_sealed_fraction is not None:
            focal_for_m = focal.loc[focal[OUTER_ROLE_COL].astype(str) == MODEL_ROLE].reset_index(drop=True)
        else:
            focal_for_m = focal
        try:
            if m_strategy == "bbox":
                m_mask = _bbox_mask_with_buffer(target_group, focal_for_m, buffer_degrees=bbox_buffer_degrees)
                m_parameter = bbox_buffer_degrees
                m_parameter_name = "bbox_buffer_degrees"
            elif m_strategy == "buffer":
                m_mask = occurrence_buffer_membership(target_group, focal_for_m, buffer_km=occurrence_buffer_km)
                m_parameter = occurrence_buffer_km
                m_parameter_name = "occurrence_buffer_km"
            else:
                raise ValueError("m_strategy must be 'bbox' or 'buffer'")
            bg = sample_target_group_background(
                focal_for_m,
                target_group,
                m_mask=m_mask,
                n_points=background_points,
                cell_size_degrees=background_cell_size_degrees,
                focal_species=species,
                random_state=random_state + i,
            )
            if outer_sealed_fraction is not None:
                bg = _assign_background_outer_roles(
                    bg,
                    sealed_fraction=float(outer_sealed_fraction),
                    n_spatial_blocks=int(outer_n_spatial_blocks),
                    random_state=int(random_state) + 200_000 + i,
                )
                n_bg_model = int((bg[OUTER_ROLE_COL].astype(str) == MODEL_ROLE).sum())
                n_bg_sealed = int((bg[OUTER_ROLE_COL].astype(str) == SEALED_ROLE).sum())
            else:
                n_bg_model = len(bg)
                n_bg_sealed = 0
            background_frames.append(bg)
            background_rows.append(
                {
                    "species": species,
                    "status": "ok",
                    "n_focal_occurrences": len(focal),
                    "n_focal_model_occurrences": len(focal_for_m),
                    "n_focal_sealed_occurrences": len(focal) - len(focal_for_m),
                    "n_target_group_in_M": int(np.sum(m_mask)),
                    "n_background": len(bg),
                    "n_background_model": n_bg_model,
                    "n_background_sealed_reference": n_bg_sealed,
                    "m_strategy": m_strategy,
                    "m_parameter_name": m_parameter_name,
                    "m_parameter": m_parameter,
                    "target_group_source": target_group_source,
                    "outer_sealed_before_M": bool(outer_sealed_fraction is not None),
                    "error": "",
                }
            )
        except ValueError as exc:
            background_rows.append(
                {
                    "species": species,
                    "status": "failed",
                    "n_focal_occurrences": len(focal),
                    "n_focal_model_occurrences": len(focal_for_m),
                    "n_focal_sealed_occurrences": len(focal) - len(focal_for_m),
                    "n_target_group_in_M": 0,
                    "n_background": 0,
                    "n_background_model": 0,
                    "n_background_sealed_reference": 0,
                    "m_strategy": m_strategy,
                    "m_parameter_name": "",
                    "m_parameter": np.nan,
                    "target_group_source": target_group_source,
                    "outer_sealed_before_M": bool(outer_sealed_fraction is not None),
                    "error": str(exc),
                }
            )
            if strict_background:
                raise
    background = pd.concat(background_frames, ignore_index=True) if background_frames else accepted.iloc[0:0].copy()
    successful = set(background["species"].astype(str)) if len(background) else set()
    accepted = accepted.loc[accepted["species"].astype(str).isin(successful)].reset_index(drop=True)

    occurrence_ledger = admission.ledger.copy()
    occurrence_ledger["layer"] = "focal_occurrence_admission"
    return ProductAPilotData(
        occurrences=accepted,
        background=background,
        taxon_selection_ledger=taxon_ledger,
        occurrence_admission_ledger=occurrence_ledger,
        species_gate=gate,
        background_ledger=pd.DataFrame(background_rows),
    )
