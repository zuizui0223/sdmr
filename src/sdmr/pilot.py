"""Real-data Product-A pilot preparation from a versioned GBIF bulk download."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import numpy as np
import pandas as pd

from .data.background import bbox_membership, occurrence_buffer_membership, sample_target_group_background
from .data.quality import OccurrenceAdmissionConfig, admit_occurrences
from .data.species_gate import species_admission_table


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
) -> ProductAPilotData:
    """Prepare audited occurrence/background tables for a real Product-A pilot."""

    selected, taxon_ledger = select_configured_taxa(records, taxa)
    admission = admit_occurrences(selected, config=admission_config)
    accepted = admission.accepted
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
        try:
            if m_strategy == "bbox":
                m_mask = _bbox_mask_with_buffer(target_group, focal, buffer_degrees=bbox_buffer_degrees)
                m_parameter = bbox_buffer_degrees
                m_parameter_name = "bbox_buffer_degrees"
            elif m_strategy == "buffer":
                m_mask = occurrence_buffer_membership(target_group, focal, buffer_km=occurrence_buffer_km)
                m_parameter = occurrence_buffer_km
                m_parameter_name = "occurrence_buffer_km"
            else:
                raise ValueError("m_strategy must be 'bbox' or 'buffer'")
            bg = sample_target_group_background(
                focal,
                target_group,
                m_mask=m_mask,
                n_points=background_points,
                cell_size_degrees=background_cell_size_degrees,
                focal_species=species,
                random_state=random_state + i,
            )
            background_frames.append(bg)
            background_rows.append(
                {
                    "species": species,
                    "status": "ok",
                    "n_focal_occurrences": len(focal),
                    "n_target_group_in_M": int(np.sum(m_mask)),
                    "n_background": len(bg),
                    "m_strategy": m_strategy,
                    "m_parameter_name": m_parameter_name,
                    "m_parameter": m_parameter,
                    "target_group_source": target_group_source,
                    "error": "",
                }
            )
        except ValueError as exc:
            background_rows.append(
                {
                    "species": species,
                    "status": "failed",
                    "n_focal_occurrences": len(focal),
                    "n_target_group_in_M": 0,
                    "n_background": 0,
                    "m_strategy": m_strategy,
                    "m_parameter_name": "",
                    "m_parameter": np.nan,
                    "target_group_source": target_group_source,
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
