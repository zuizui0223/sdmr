"""Geometry-only validation-design calibration for Product-A v2.8.

The calibration uses the consumed rank-1/2/3 taxon registry only as a geometry
corpus.  It varies the predeclared outer sealed fraction, reconstructs M from
model-pool coordinates, and evaluates the inherited evidence-balanced fold
support.  Environmental values, fitted models, and ecological outcomes are not
inputs to this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from .data import (
    OccurrenceAdmissionConfig,
    load_gbif_download,
    thin_to_grid,
)
from .pilot import (
    MODEL_ROLE,
    OUTER_ROLE_COL,
    prepare_product_a_pilot,
)
from .pilot_grid_cli import read_pilot_grid
from .specification import occurrence_table_fingerprint
from .v2_7_1_evidence_balanced_partition import make_evidence_balanced_spatial_partitions
from .v2_7_1_fresh_contract import load_fresh_eligibility_thresholds

PART_PURPOSE = "product_a_v2_8_geometry_calibration_part"
DECISION_PURPOSE = "product_a_v2_8_geometry_calibration_decision"
EXPECTED_M_KM = (150, 300, 500)
EXPECTED_M_NAMES = ("buffer_150km", "buffer_300km", "buffer_500km")
EXPECTED_SEEDS = (2026082201, 2026082202, 2026082203, 2026082204, 2026082205)
EXPECTED_FRACTIONS = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35)
EXPECTED_TAXA = 36
EXPECTED_STRATA = 12
WILSON_Z_95 = 1.959963984540054


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_design(path: str | Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_8_geometry_only_validation_design_calibration":
        raise ValueError("wrong v2.8 geometry calibration design")
    if payload.get("predeclared_before_v2_8_geometry_calibration_execution") is not True:
        raise ValueError("v2.8 geometry calibration design was not predeclared")

    corpus = payload.get("calibration_corpus", {})
    if (
        int(corpus.get("n_taxa", -1)) != EXPECTED_TAXA
        or int(corpus.get("n_validation_strata", -1)) != EXPECTED_STRATA
        or tuple(int(x) for x in corpus.get("candidate_ranks", ())) != (1, 2, 3)
        or corpus.get("future_scientific_confirmation_reuse_allowed") is not False
    ):
        raise ValueError("v2.8 geometry calibration corpus changed")

    partition = payload.get("inherited_partition", {})
    expected_partition = {
        "outer_folds": 4,
        "spatial_microblocks": 12,
        "assignment_attempts": 32,
        "minimum_evaluation_occurrences_per_fold": 2,
        "minimum_evaluation_background_rows_per_M_fold": 5,
        "minimum_training_background_rows_per_M_fold": 5,
    }
    if tuple(int(x) for x in partition.get("M_km", ())) != EXPECTED_M_KM:
        raise ValueError("v2.8 geometry calibration M grid changed")
    for key, expected in expected_partition.items():
        if int(partition.get(key, -1)) != expected:
            raise ValueError(f"v2.8 inherited partition changed: {key}")
    for key in (
        "partition_algorithm_changed",
        "row_count_thresholds_changed",
        "assignment_attempts_changed",
    ):
        if partition.get(key) is not False:
            raise ValueError(f"v2.8 inherited partition is not frozen: {key}")

    axis = payload.get("calibration_axis", {})
    if tuple(float(x) for x in axis.get("sealed_fraction_grid", ())) != EXPECTED_FRACTIONS:
        raise ValueError("v2.8 sealed-fraction grid changed")
    if tuple(int(x) for x in axis.get("split_seeds", ())) != EXPECTED_SEEDS:
        raise ValueError("v2.8 calibration seeds changed")
    if axis.get("candidate_or_threshold_adaptation_within_a_fraction") is not False:
        raise ValueError("v2.8 calibration permits within-fraction adaptation")

    rule = payload.get("selection_rule_for_future_confirmation", {})
    if rule.get("rule") != (
        "choose_the_largest_predeclared_fraction_whose_geometry_only_calibration_"
        "lower_95pct_wilson_bound_is_at_least_0.95"
    ):
        raise ValueError("v2.8 geometry calibration selection rule changed")
    if rule.get("future_fraction_fixed_globally_not_per_taxon") is not True:
        raise ValueError("v2.8 geometry calibration permits taxon-specific fractions")

    forbidden = set(payload.get("forbidden_inputs", ()))
    required_forbidden = {
        "environmental_raster_values",
        "CHELSA_values",
        "auc",
        "candidate_scores",
        "fitted_coefficients",
        "sealed_ecological_outcomes",
    }
    if not required_forbidden <= forbidden:
        raise ValueError("v2.8 geometry calibration information barrier changed")
    return payload


def _load_source_pin(path: str | Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_8_geometry_calibration_raw_source_pin":
        raise ValueError("wrong v2.8 geometry calibration source pin")
    if int(payload.get("workflow_run_id", -1)) <= 0 or payload.get("workflow_conclusion") != "success":
        raise ValueError("v2.8 geometry source run is not pinned successful")
    if payload.get("ready_for_geometry_calibration") is not True:
        raise ValueError("v2.8 geometry source is not admitted for calibration")
    if payload.get("ready_for_scientific_confirmation") is not False:
        raise ValueError("v2.8 geometry source pin crossed the scientific boundary")
    barrier = payload.get("information_barrier", {})
    for key in (
        "environmental_values_read",
        "candidate_model_fitting_performed",
        "geometry_calibration_executed",
        "sealed_ecological_outcomes_read",
        "scientific_confirmation_allowed",
        "scientific_promotion_allowed",
        "product_b_unblocked",
    ):
        if barrier.get(key) is not False:
            raise ValueError(f"v2.8 geometry source pin crossed barrier: {key}")
    return payload


def _load_registry(path: str | Path, expected_sha256: str) -> pd.DataFrame:
    if _sha256(path) != str(expected_sha256):
        raise ValueError("v2.8 geometry calibration registry SHA mismatch")
    frame = pd.read_csv(path)
    required = {"scientific_name", "validation_stratum", "candidate_rank"}
    if not required <= set(frame.columns):
        raise ValueError("v2.8 geometry calibration registry columns changed")
    if len(frame) != EXPECTED_TAXA or frame["scientific_name"].astype(str).nunique() != EXPECTED_TAXA:
        raise ValueError("v2.8 geometry calibration requires exactly 36 unique taxa")
    if frame["validation_stratum"].astype(str).nunique() != EXPECTED_STRATA:
        raise ValueError("v2.8 geometry calibration requires exactly 12 strata")
    counts = frame.groupby("validation_stratum", sort=True)["candidate_rank"].agg(
        lambda values: tuple(sorted(int(x) for x in values))
    )
    if len(counts) != EXPECTED_STRATA or any(value != (1, 2, 3) for value in counts):
        raise ValueError("v2.8 geometry calibration requires ranks 1-3 in every stratum")
    return frame.reset_index(drop=True)


def _grid(path: str | Path) -> pd.DataFrame:
    grid = read_pilot_grid(str(path))
    if tuple(int(round(float(x))) for x in grid["occurrence_buffer_km"]) != EXPECTED_M_KM:
        raise ValueError("v2.8 geometry calibration grid differs from 150/300/500 km")
    if tuple(grid["name"].astype(str)) != EXPECTED_M_NAMES:
        raise ValueError("v2.8 geometry calibration M names changed")
    if not grid["m_strategy"].astype(str).eq("buffer").all():
        raise ValueError("v2.8 geometry calibration M must remain buffer based")
    return grid


def _barrier_fields() -> dict[str, bool]:
    return {
        "environmental_values_read": False,
        "CHELSA_values_read": False,
        "candidate_model_fitting_performed": False,
        "candidate_scores_read": False,
        "sealed_ecological_outcomes_read": False,
        "scientific_confirmation_allowed": False,
        "scientific_promotion_allowed": False,
        "product_b_unblocked": False,
    }


def _load_raw_geometry_columns(path: str | Path) -> pd.DataFrame:
    """Read only columns used by the pre-split geometry transport."""

    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - exercised by packaging
        raise ImportError("v2.8 geometry transport requires sdmr[parquet]") from exc
    source = Path(path)
    schema_names = pq.ParquetFile(source).schema_arrow.names
    by_lower = {str(name).lower(): str(name) for name in schema_names}
    wanted = (
        "species",
        "scientificname",
        "acceptedscientificname",
        "decimallongitude",
        "decimallatitude",
        "gbifid",
        "occurrencestatus",
    )
    columns = [by_lower[name] for name in wanted if name in by_lower]
    frame = pd.read_parquet(source, columns=list(dict.fromkeys(columns)))
    rename = {}
    for column in frame.columns:
        lower = str(column).lower()
        if lower == "decimallongitude":
            rename[column] = "longitude"
        elif lower == "decimallatitude":
            rename[column] = "latitude"
        elif lower == "gbifid":
            rename[column] = "gbifID"
        elif lower == "occurrencestatus":
            rename[column] = "occurrenceStatus"
        elif lower == "scientificname":
            rename[column] = "scientificName"
        elif lower == "acceptedscientificname":
            rename[column] = "acceptedScientificName"
    frame = frame.rename(columns=rename)
    if "species" not in frame:
        if "acceptedScientificName" in frame:
            frame["species"] = frame["acceptedScientificName"]
        elif "scientificName" in frame:
            frame["species"] = frame["scientificName"]
    required = {"species", "longitude", "latitude"}
    if not required <= set(frame.columns):
        raise ValueError("pinned geometry source lacks species/coordinate columns")
    return frame


def _admit_geometry_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Vectorized equivalent of the default occurrence admission for transport."""

    data = frame.copy()
    lon = pd.to_numeric(data["longitude"], errors="coerce")
    lat = pd.to_numeric(data["latitude"], errors="coerce")
    keep = lon.notna() & lat.notna() & lon.between(-180.0, 180.0) & lat.between(-90.0, 90.0)
    if "occurrenceStatus" in data:
        status = data["occurrenceStatus"].fillna("").astype(str).str.upper()
        keep &= status.eq("") | status.eq("PRESENT")
    data = data.loc[keep].copy()
    data["longitude"] = lon.loc[keep].to_numpy(float)
    data["latitude"] = lat.loc[keep].to_numpy(float)
    return data.drop_duplicates(
        subset=["species", "longitude", "latitude"], keep="first"
    ).reset_index(drop=True)


def prepare_transport(
    *,
    source_pin_path: str | Path,
    raw_focal_path: str | Path,
    raw_target_path: str | Path,
    taxa_path: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    """Create one geometry-only, pre-split transport shared by all 30 parts."""

    source = _load_source_pin(source_pin_path)
    if _sha256(raw_focal_path) != source["focal"]["file_sha256"]:
        raise ValueError("v2.8 raw focal source SHA mismatch before transport")
    if _sha256(raw_target_path) != source["target_group"]["file_sha256"]:
        raise ValueError("v2.8 raw target source SHA mismatch before transport")
    taxa = _load_registry(taxa_path, source["calibration_corpus_sha256"])

    expected_taxa = set(taxa["scientific_name"].astype(str))
    raw_focal = _load_raw_geometry_columns(raw_focal_path)
    selected = raw_focal.loc[raw_focal["species"].astype(str).isin(expected_taxa)].copy()
    selected_taxa = set(selected["species"].astype(str))
    if selected_taxa != expected_taxa:
        raise ValueError(
            "v2.8 raw focal source lacks calibration taxa: "
            f"missing={sorted(expected_taxa-selected_taxa)} extra={sorted(selected_taxa-expected_taxa)}"
        )
    focal = thin_to_grid(_admit_geometry_rows(selected), cell_size_degrees=0.05)
    target = _admit_geometry_rows(_load_raw_geometry_columns(raw_target_path))
    observed_taxa = set(focal["species"].astype(str))
    if observed_taxa != expected_taxa:
        raise ValueError(
            "v2.8 geometry transport lost calibration taxa: "
            f"missing={sorted(expected_taxa-observed_taxa)} extra={sorted(observed_taxa-expected_taxa)}"
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    focal_path = out / "focal_geometry.parquet"
    target_path = out / "target_geometry.parquet"
    focal.to_parquet(focal_path, index=False)
    target.to_parquet(target_path, index=False)
    result = {
        "purpose": "product_a_v2_8_geometry_calibration_transport",
        "source_run_id": int(source["workflow_run_id"]),
        "calibration_corpus_sha256": str(source["calibration_corpus_sha256"]),
        "raw_focal_sha256": str(source["focal"]["file_sha256"]),
        "raw_target_sha256": str(source["target_group"]["file_sha256"]),
        "focal_geometry_sha256": _sha256(focal_path),
        "target_geometry_sha256": _sha256(target_path),
        "n_focal_geometry_rows": int(len(focal)),
        "n_target_geometry_rows": int(len(target)),
        "n_focal_taxa": int(focal["species"].astype(str).nunique()),
        "focal_thin_cell_size_degrees": 0.05,
        "focal_thinning_before_outer_split": True,
        "outer_split_executed": False,
        "M_membership_executed": False,
        "geometry_calibration_executed": False,
        **_barrier_fields(),
    }
    (out / "transport.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _load_transport(
    path: str | Path,
    *,
    source: dict[str, object],
    focal_path: str | Path,
    target_path: str | Path,
) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("purpose") != "product_a_v2_8_geometry_calibration_transport":
        raise ValueError("wrong v2.8 geometry calibration transport")
    if int(payload.get("source_run_id", -1)) != int(source["workflow_run_id"]):
        raise ValueError("v2.8 geometry transport source run changed")
    if payload.get("calibration_corpus_sha256") != source["calibration_corpus_sha256"]:
        raise ValueError("v2.8 geometry transport corpus changed")
    if (
        payload.get("raw_focal_sha256") != source["focal"]["file_sha256"]
        or payload.get("raw_target_sha256") != source["target_group"]["file_sha256"]
    ):
        raise ValueError("v2.8 geometry transport raw-source identity changed")
    if _sha256(focal_path) != payload.get("focal_geometry_sha256"):
        raise ValueError("v2.8 focal geometry transport SHA mismatch")
    if _sha256(target_path) != payload.get("target_geometry_sha256"):
        raise ValueError("v2.8 target geometry transport SHA mismatch")
    if (
        payload.get("focal_thinning_before_outer_split") is not True
        or payload.get("outer_split_executed") is not False
        or payload.get("M_membership_executed") is not False
        or payload.get("geometry_calibration_executed") is not False
    ):
        raise ValueError("v2.8 geometry transport crossed the pre-split boundary")
    for key, expected in _barrier_fields().items():
        if payload.get(key) is not expected:
            raise ValueError(f"v2.8 geometry transport crossed barrier: {key}")
    return payload


def run_part(
    *,
    design_path: str | Path,
    source_pin_path: str | Path,
    transport_manifest_path: str | Path,
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
        raise ValueError("v2.8 calibration seed is not frozen")
    if float(sealed_fraction) not in EXPECTED_FRACTIONS:
        raise ValueError("v2.8 calibration sealed fraction is not frozen")
    _load_transport(
        transport_manifest_path,
        source=source,
        focal_path=focal_path,
        target_path=target_path,
    )

    taxa = _load_registry(taxa_path, source["calibration_corpus_sha256"])
    focal = load_gbif_download(focal_path).records
    target = load_gbif_download(target_path).records
    grid = _grid(grid_path)
    thresholds = load_fresh_eligibility_thresholds(design_path)

    prepared_by_name: dict[str, object] = {}
    for row in grid.itertuples(index=False):
        prepared_by_name[str(row.name)] = prepare_product_a_pilot(
            focal,
            taxa,
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
            strict_background=False,
            focal_thin_cell_size_degrees=0.05,
            outer_sealed_fraction=float(sealed_fraction),
        )

    partition_cfg = design["inherited_partition"]
    rows: list[dict[str, object]] = []
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for taxon_index, taxon_row in enumerate(taxa.itertuples(index=False)):
        taxon = str(taxon_row.scientific_name)
        base = {
            "seed": int(seed),
            "sealed_fraction": float(sealed_fraction),
            "taxon_index": int(taxon_index),
            "taxon": taxon,
            "validation_stratum": str(taxon_row.validation_stratum),
            "candidate_rank": int(taxon_row.candidate_rank),
            "partition_seed": int(seed) + int(taxon_index) * 100 + 271,
        }

        gates = []
        for name in EXPECTED_M_NAMES:
            gate = prepared_by_name[name].species_gate
            match = gate.loc[gate["species"].astype(str).eq(taxon)]
            gates.append(None if match.empty else match.iloc[0])
        if any(gate is None or not bool(gate["eligible"]) for gate in gates):
            first = next((gate for gate in gates if gate is not None), None)
            rows.append({
                **base,
                "structurally_feasible": False,
                "selected_assignment_attempt": None,
                "n_occurrences_model_pool": 0 if first is None else int(first["n_occurrences_model_pool"]),
                "n_unique_cells_model_pool": 0 if first is None else int(first["n_unique_cells_model_pool"]),
                "unavailable_stage": "model_pool_eligibility",
                "unavailable_reason": "model-pool occurrence eligibility threshold not met",
            })
            continue

        occurrences = []
        backgrounds: dict[str, pd.DataFrame] = {}
        for name in EXPECTED_M_NAMES:
            prepared = prepared_by_name[name]
            occurrences.append(
                prepared.occurrences.loc[
                    prepared.occurrences["species"].astype(str).eq(taxon)
                    & prepared.occurrences[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
                ].reset_index(drop=True)
            )
            backgrounds[name] = prepared.background.loc[
                prepared.background["species"].astype(str).eq(taxon)
                & prepared.background[OUTER_ROLE_COL].astype(str).eq(MODEL_ROLE)
            ].reset_index(drop=True)

        missing = [
            name for name, frame in zip(EXPECTED_M_NAMES, occurrences, strict=True) if frame.empty
        ] + [name for name, frame in backgrounds.items() if frame.empty]
        if missing:
            rows.append({
                **base,
                "structurally_feasible": False,
                "selected_assignment_attempt": None,
                "n_occurrences_model_pool": int(len(occurrences[0])),
                "n_unique_cells_model_pool": int(gates[0]["n_unique_cells_model_pool"]),
                "unavailable_stage": "model_pool_resource",
                "unavailable_reason": f"empty model-pool resource: {sorted(set(missing))}",
            })
            continue

        occurrence_fingerprints = {occurrence_table_fingerprint(frame) for frame in occurrences}
        if len(occurrence_fingerprints) != 1:
            raise ValueError(f"v2.8 M changed the model-pool occurrence split for {taxon}")
        occurrence = occurrences[0]
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
                n_microblocks=int(partition_cfg["spatial_microblocks"]),
                outer_folds=int(partition_cfg["outer_folds"]),
                minimum_evaluation_occurrences=int(
                    partition_cfg["minimum_evaluation_occurrences_per_fold"]
                ),
                minimum_evaluation_background_rows=int(
                    partition_cfg["minimum_evaluation_background_rows_per_M_fold"]
                ),
                minimum_training_background_rows=int(
                    partition_cfg["minimum_training_background_rows_per_M_fold"]
                ),
                assignment_attempts=int(partition_cfg["assignment_attempts"]),
                random_state=int(base["partition_seed"]),
            )
        except ValueError as exc:
            rows.append({
                **base,
                "structurally_feasible": False,
                "selected_assignment_attempt": None,
                "n_occurrences_model_pool": int(len(occurrence)),
                "n_unique_cells_model_pool": int(gates[0]["n_unique_cells_model_pool"]),
                "unavailable_stage": "evidence_balanced_partition",
                "unavailable_reason": str(exc),
            })
            continue

        taxon_dir = out / f"taxon_{taxon_index:02d}"
        taxon_dir.mkdir(exist_ok=True)
        partition.support_ledger.to_csv(taxon_dir / "partition_support.csv", index=False)
        partition.attempt_ledger.to_csv(taxon_dir / "partition_attempts.csv", index=False)
        rows.append({
            **base,
            "structurally_feasible": True,
            "selected_assignment_attempt": int(partition.selected_attempt),
            "n_occurrences_model_pool": int(len(occurrence)),
            "n_unique_cells_model_pool": int(gates[0]["n_unique_cells_model_pool"]),
            "unavailable_stage": None,
            "unavailable_reason": None,
        })

    taxon_frame = pd.DataFrame(rows)
    taxon_frame.to_csv(out / "taxon_feasibility.csv", index=False)
    result = {
        "purpose": PART_PURPOSE,
        "seed": int(seed),
        "sealed_fraction": float(sealed_fraction),
        "source_run_id": int(source["workflow_run_id"]),
        "focal_sha256": str(source["focal"]["file_sha256"]),
        "target_sha256": str(source["target_group"]["file_sha256"]),
        "calibration_corpus_sha256": str(source["calibration_corpus_sha256"]),
        "n_taxa": EXPECTED_TAXA,
        "n_feasible_taxa": int(taxon_frame["structurally_feasible"].astype(bool).sum()),
        "M_specs": list(EXPECTED_M_NAMES),
        "outer_sealed_before_M": True,
        "M_built_from_model_pool_only": True,
        "sealed_rows_used_for_partition_assignment": False,
        **_barrier_fields(),
    }
    (out / "contract.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def wilson_lower_bound(successes: int, total: int, *, z: float = WILSON_Z_95) -> float:
    if total <= 0 or successes < 0 or successes > total:
        raise ValueError("invalid Wilson interval counts")
    p = successes / total
    denominator = 1.0 + z * z / total
    centre = p + z * z / (2.0 * total)
    radius = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total))
    return (centre - radius) / denominator


def _boolean_values(series: pd.Series, *, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    if not normalized.isin({"true", "false"}).all():
        raise ValueError(f"{label} contains non-boolean values")
    return normalized.eq("true")


def aggregate_parts(
    *,
    design_path: str | Path,
    taxa_path: str | Path,
    parts_root: str | Path,
    output_dir: str | Path,
) -> dict[str, object]:
    design = _load_design(design_path)
    registry_sha = _sha256(taxa_path)
    taxa = _load_registry(taxa_path, registry_sha)
    expected_taxa = set(taxa["scientific_name"].astype(str))
    expected_parts = {(seed, fraction) for seed in EXPECTED_SEEDS for fraction in EXPECTED_FRACTIONS}

    contracts: list[tuple[Path, dict[str, object]]] = []
    for path in Path(parts_root).rglob("contract.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("purpose") == PART_PURPOSE:
            contracts.append((path, payload))
    if len(contracts) != len(expected_parts):
        raise ValueError(
            f"expected exactly {len(expected_parts)} v2.8 calibration parts, found {len(contracts)}"
        )
    observed_parts = {(int(c["seed"]), float(c["sealed_fraction"])) for _, c in contracts}
    if observed_parts != expected_parts:
        raise ValueError("v2.8 geometry calibration part denominator changed")

    frames = []
    source_run_ids: set[int] = set()
    focal_hashes: set[str] = set()
    target_hashes: set[str] = set()
    for contract_path, contract in contracts:
        if int(contract.get("n_taxa", -1)) != EXPECTED_TAXA:
            raise ValueError("v2.8 geometry calibration taxon denominator changed")
        if tuple(contract.get("M_specs", ())) != EXPECTED_M_NAMES:
            raise ValueError("v2.8 geometry calibration M denominator changed")
        if (
            contract.get("outer_sealed_before_M") is not True
            or contract.get("M_built_from_model_pool_only") is not True
            or contract.get("sealed_rows_used_for_partition_assignment") is not False
        ):
            raise ValueError("v2.8 geometry calibration partition information boundary changed")
        for key, expected in _barrier_fields().items():
            if contract.get(key) is not expected:
                raise ValueError(f"v2.8 geometry calibration part crossed barrier: {key}")
        if contract.get("calibration_corpus_sha256") != registry_sha:
            raise ValueError("v2.8 geometry calibration part registry fingerprint changed")
        source_run_ids.add(int(contract.get("source_run_id", -1)))
        focal_hashes.add(str(contract.get("focal_sha256", "")))
        target_hashes.add(str(contract.get("target_sha256", "")))
        frame_path = contract_path.with_name("taxon_feasibility.csv")
        if not frame_path.exists():
            raise ValueError(f"missing v2.8 taxon feasibility ledger: {frame_path}")
        frame = pd.read_csv(frame_path)
        required_columns = {
            "seed",
            "sealed_fraction",
            "taxon",
            "validation_stratum",
            "candidate_rank",
            "structurally_feasible",
        }
        if not required_columns <= set(frame.columns):
            raise ValueError("v2.8 part taxon feasibility ledger columns changed")
        if len(frame) != EXPECTED_TAXA or set(frame["taxon"].astype(str)) != expected_taxa:
            raise ValueError("v2.8 part taxon ledger denominator changed")
        if not frame["seed"].astype(int).eq(int(contract["seed"])).all():
            raise ValueError("v2.8 part taxon ledger seed mismatch")
        if not frame["sealed_fraction"].astype(float).eq(float(contract["sealed_fraction"])).all():
            raise ValueError("v2.8 part taxon ledger fraction mismatch")
        frame["structurally_feasible"] = _boolean_values(
            frame["structurally_feasible"], label="structurally_feasible"
        )
        if int(frame["structurally_feasible"].sum()) != int(contract.get("n_feasible_taxa", -1)):
            raise ValueError("v2.8 part feasibility count does not match its ledger")
        frames.append(frame)

    if (
        len(source_run_ids) != 1
        or next(iter(source_run_ids)) <= 0
        or len(focal_hashes) != 1
        or "" in focal_hashes
        or len(target_hashes) != 1
        or "" in target_hashes
    ):
        raise ValueError("v2.8 geometry calibration parts do not share one pinned raw source")

    cells = pd.concat(frames, ignore_index=True)
    key_columns = ["sealed_fraction", "seed", "taxon"]
    if cells.duplicated(key_columns).any() or len(cells) != len(expected_parts) * EXPECTED_TAXA:
        raise ValueError("v2.8 taxon x seed calibration cell denominator changed")
    expected_metadata = taxa.rename(columns={"scientific_name": "taxon"})[
        ["taxon", "validation_stratum", "candidate_rank"]
    ]
    merged = cells.merge(
        expected_metadata,
        on=["taxon", "validation_stratum", "candidate_rank"],
        how="inner",
        validate="many_to_one",
    )
    if len(merged) != len(cells):
        raise ValueError("v2.8 taxon metadata changed inside calibration parts")

    fraction_rows = []
    for fraction in EXPECTED_FRACTIONS:
        group = merged.loc[merged["sealed_fraction"].astype(float).eq(fraction)]
        total = int(len(group))
        feasible = int(group["structurally_feasible"].sum())
        if total != EXPECTED_TAXA * len(EXPECTED_SEEDS):
            raise ValueError("v2.8 fraction denominator changed")
        lower = wilson_lower_bound(feasible, total)
        fraction_rows.append({
            "sealed_fraction": float(fraction),
            "n_taxon_seed_cells": total,
            "n_structurally_feasible": feasible,
            "structural_feasibility_rate": feasible / total,
            "wilson_lower_95": lower,
            "passes_predeclared_rule": bool(lower >= 0.95),
        })
    fraction_summary = pd.DataFrame(fraction_rows)
    passing = fraction_summary.loc[fraction_summary["passes_predeclared_rule"].astype(bool)]
    selected_fraction = None if passing.empty else float(passing["sealed_fraction"].max())

    stratum_rows = []
    for (fraction, stratum), group in merged.groupby(
        ["sealed_fraction", "validation_stratum"], sort=True
    ):
        total = int(len(group))
        feasible = int(group["structurally_feasible"].sum())
        stratum_rows.append({
            "sealed_fraction": float(fraction),
            "validation_stratum": str(stratum),
            "n_taxon_seed_cells": total,
            "n_structurally_feasible": feasible,
            "structural_feasibility_rate": feasible / total,
            "wilson_lower_95": wilson_lower_bound(feasible, total),
        })

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fraction_summary.to_csv(out / "fraction_summary.csv", index=False)
    pd.DataFrame(stratum_rows).to_csv(out / "stratum_summary.csv", index=False)
    merged.loc[~merged["structurally_feasible"]].sort_values(
        key_columns, kind="mergesort"
    ).to_csv(out / "structural_failures.csv", index=False)

    decision = (
        "geometry_calibration_fraction_selected"
        if selected_fraction is not None
        else "geometry_calibration_no_fraction_qualifies"
    )
    result = {
        "purpose": DECISION_PURPOSE,
        "decision": decision,
        "selected_global_sealed_fraction": selected_fraction,
        "selection_threshold_wilson_lower_95": 0.95,
        "n_taxa": EXPECTED_TAXA,
        "n_seeds": len(EXPECTED_SEEDS),
        "n_fractions": len(EXPECTED_FRACTIONS),
        "n_taxon_seed_cells_per_fraction": EXPECTED_TAXA * len(EXPECTED_SEEDS),
        "source_run_id": next(iter(source_run_ids)),
        "focal_sha256": next(iter(focal_hashes)),
        "target_sha256": next(iter(target_hashes)),
        "calibration_corpus_sha256": registry_sha,
        "selection_rule_applied": True,
        "largest_qualifying_fraction_selected": selected_fraction is not None,
        "taxon_specific_fraction_selection_allowed": False,
        "future_confirmation_must_use_taxa_outside_calibration_corpus": True,
        "separate_future_scientific_runtime_authorization_required": True,
        "geometry_calibration_result_is_ecological_support": False,
        **_barrier_fields(),
    }
    (out / "decision.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    transport = sub.add_parser("transport")
    transport.add_argument("--source-pin", required=True)
    transport.add_argument("--raw-focal", required=True)
    transport.add_argument("--raw-target", required=True)
    transport.add_argument("--taxa", required=True)
    transport.add_argument("--output-dir", required=True)
    part = sub.add_parser("part")
    part.add_argument("--design", required=True)
    part.add_argument("--source-pin", required=True)
    part.add_argument("--transport-manifest", required=True)
    part.add_argument("--focal", required=True)
    part.add_argument("--target", required=True)
    part.add_argument("--taxa", required=True)
    part.add_argument("--grid", required=True)
    part.add_argument("--seed", type=int, required=True)
    part.add_argument("--sealed-fraction", type=float, required=True)
    part.add_argument("--output-dir", required=True)
    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--design", required=True)
    aggregate.add_argument("--taxa", required=True)
    aggregate.add_argument("--parts-root", required=True)
    aggregate.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if args.mode == "transport":
        prepare_transport(
            source_pin_path=args.source_pin,
            raw_focal_path=args.raw_focal,
            raw_target_path=args.raw_target,
            taxa_path=args.taxa,
            output_dir=args.output_dir,
        )
    elif args.mode == "part":
        run_part(
            design_path=args.design,
            source_pin_path=args.source_pin,
            transport_manifest_path=args.transport_manifest,
            focal_path=args.focal,
            target_path=args.target,
            taxa_path=args.taxa,
            grid_path=args.grid,
            seed=args.seed,
            sealed_fraction=args.sealed_fraction,
            output_dir=args.output_dir,
        )
    else:
        aggregate_parts(
            design_path=args.design,
            taxa_path=args.taxa,
            parts_root=args.parts_root,
            output_dir=args.output_dir,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
