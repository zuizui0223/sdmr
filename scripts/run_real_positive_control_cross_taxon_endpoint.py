from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from sdmr.data import OccurrenceAdmissionConfig, load_gbif_download, raster_specs_from_chelsa_manifest
from sdmr.pilot import prepare_product_a_pilot
from sdmr.pilot_grid_cli import extract_protocol_grid_rasters, read_pilot_grid
from sdmr.real_positive_control import run_endpoint


def _sha(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--focal-parquet", required=True)
    p.add_argument("--target-groups-parquet", required=True)
    p.add_argument("--contract", default="configs/product_a_real_positive_control_nonplant_contract_v1.json")
    p.add_argument("--output-root", required=True)
    args = p.parse_args(argv)

    contract_path = Path(args.contract)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("purpose") != "product_a_real_positive_control_process_membership_v1":
        raise SystemExit("wrong positive-control purpose")
    if contract.get("scope") != "cross_taxon_nonplant_v1":
        raise SystemExit("wrong cross-taxon scope")
    if contract.get("frozen_before_sdm_outcome") is not True:
        raise SystemExit("cross-taxon contract was not frozen pre-outcome")

    source = contract["source"]
    taxa_path = Path(source["taxa_file"])
    groups_path = Path(source["target_groups_file"])
    if _sha(taxa_path) != source["taxa_sha256"]:
        raise SystemExit("cross-taxon taxa SHA mismatch")
    if _sha(groups_path) != source["target_groups_sha256"]:
        raise SystemExit("cross-taxon target-group SHA mismatch")

    root = Path(args.output_root)
    input_dir = root / "input"
    feature_dir = root / "feature_cache"
    result_dir = root / "result"
    input_dir.mkdir(parents=True, exist_ok=True)
    feature_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    taxa = pd.read_csv(taxa_path)
    groups = pd.read_csv(groups_path)
    if len(taxa) != 4 or taxa["scientific_name"].nunique() != 4:
        raise SystemExit("cross-taxon denominator must remain four taxa")
    if set(taxa["target_group"].astype(str)) != set(groups["target_group"].astype(str)):
        raise SystemExit("focal target groups differ from frozen target-group registry")

    focal_loaded = load_gbif_download(args.focal_parquet, download_key="real-positive-control-nonplant-focal", checklist_key="snapshot-interpreted:2026-08-01")
    target_all = pd.read_parquet(args.target_groups_parquet)
    if "target_group" not in target_all:
        raise SystemExit("target-group source lacks target_group")
    if set(target_all["target_group"].astype(str)) != set(groups["target_group"].astype(str)):
        raise SystemExit("observed target groups differ from frozen registry")

    grid = read_pilot_grid(contract["accessible_area"]["grid_file"])
    required_specs = tuple(str(x) for x in contract["accessible_area"]["required_specs"])
    grid = grid.loc[grid["name"].astype(str).isin(required_specs)].reset_index(drop=True)
    if tuple(grid["name"].astype(str)) != required_specs:
        raise SystemExit("M grid differs from frozen contract")

    admission = OccurrenceAdmissionConfig()
    occurrences_by_species = []
    backgrounds_by_spec = {x: [] for x in required_specs}
    gates = []
    background_ledgers = []
    target_group_ledger = []

    for taxon in taxa.itertuples(index=False):
        species = str(taxon.scientific_name)
        target_group = str(taxon.target_group)
        one_taxon = taxa.loc[taxa["scientific_name"].astype(str).eq(species)].reset_index(drop=True)
        target_subset = target_all.loc[target_all["target_group"].astype(str).eq(target_group)].copy()
        if target_subset.empty:
            raise SystemExit(f"empty target group for {species}: {target_group}")
        target_subset = target_subset.drop(columns=["target_group"])
        target_path = input_dir / f"target_{target_group}.parquet"
        target_subset.to_parquet(target_path, index=False)
        target_loaded = load_gbif_download(target_path, download_key=f"real-positive-control-target-{target_group}", checklist_key="snapshot-interpreted:2026-08-01")
        target_group_ledger.append({"species": species, "target_group": target_group, "target_rows": int(len(target_loaded.records)), "target_source_sha256": _sha(target_path)})

        first_occ = None
        first_ids = None
        for row in grid.itertuples(index=False):
            prepared = prepare_product_a_pilot(
                focal_loaded.records,
                one_taxon,
                admission_config=admission,
                min_occurrences=int(contract["occurrence_gate"]["minimum_occurrences"]),
                min_unique_cells=int(contract["occurrence_gate"]["minimum_unique_cells"]),
                gate_cell_size_degrees=float(contract["occurrence_gate"]["cell_size_degrees"]),
                m_strategy=str(row.m_strategy),
                target_group_pool=target_loaded.records,
                bbox_buffer_degrees=float(row.bbox_buffer_degrees),
                occurrence_buffer_km=float(row.occurrence_buffer_km),
                background_points=int(row.background_points),
                background_cell_size_degrees=float(row.background_cell_size_degrees),
                random_state=int(contract["occurrence_gate"]["seed"]),
                strict_background=False,
                focal_thin_cell_size_degrees=float(contract["occurrence_gate"]["cell_size_degrees"]),
                outer_sealed_fraction=float(contract["occurrence_gate"]["outer_sealed_fraction"]),
                outer_n_spatial_blocks=8,
            )
            m_name = str(row.name)
            if first_occ is None:
                first_occ = prepared.occurrences.copy()
                if "gbifID" in first_occ:
                    first_ids = tuple(sorted(first_occ["gbifID"].astype(str)))
            elif first_ids is not None and "gbifID" in prepared.occurrences:
                if tuple(sorted(prepared.occurrences["gbifID"].astype(str))) != first_ids:
                    raise SystemExit(f"outer occurrence set changed across M for {species}")
            bg = prepared.background.copy()
            if "species" not in bg:
                bg["species"] = species
            backgrounds_by_spec[m_name].append(bg)
            gates.append(prepared.species_gate.assign(m_spec=m_name, target_group=target_group))
            background_ledgers.append(prepared.background_ledger.assign(m_spec=m_name, species=species, target_group=target_group))
        if first_occ is None or first_occ.empty:
            raise SystemExit(f"no prepared occurrences for {species}")
        occurrences_by_species.append(first_occ)

    occurrences = pd.concat(occurrences_by_species, ignore_index=True)
    backgrounds = {name: pd.concat(parts, ignore_index=True) for name, parts in backgrounds_by_spec.items()}
    occurrences.to_csv(feature_dir / "pilot_occurrences_pre_raster.csv", index=False)
    pd.concat(gates, ignore_index=True).to_csv(feature_dir / "species_gate_all_M.csv", index=False)
    pd.concat(background_ledgers, ignore_index=True).to_csv(feature_dir / "background_ledger_all_M.csv", index=False)
    pd.DataFrame(target_group_ledger).to_csv(input_dir / "target_group_ledger.csv", index=False)
    grid.to_csv(feature_dir / "pilot_grid_frozen.csv", index=False)
    for name, bg in backgrounds.items():
        d = feature_dir / "specifications" / name
        d.mkdir(parents=True, exist_ok=True)
        bg.to_csv(d / "background_pre_raster.csv", index=False)

    manifest = pd.read_csv(source["environment_manifest"])
    if len(manifest) != 10:
        raise SystemExit("cross-taxon focused registry must contain 10 predictors")
    layers, resolution = raster_specs_from_chelsa_manifest(manifest, include_availability=("current",), strict=True)
    if len(layers) != 10:
        raise SystemExit(f"expected 10 focused layers, got {len(layers)}")
    resolution.to_csv(feature_dir / "chelsa_resolution_ledger.csv", index=False)
    featured_occ, featured_bg, provenance = extract_protocol_grid_rasters(occurrences, backgrounds, layers)
    featured_occ.to_csv(feature_dir / "pilot_occurrences.csv", index=False)
    provenance.to_csv(feature_dir / "raster_provenance_joint_protocol_grid.csv", index=False)
    for name, frame in featured_bg.items():
        frame.to_csv(feature_dir / "specifications" / name / "background.csv", index=False)

    predictors = [str(x) for x in manifest["predictor"]]
    all_na = [x for x in predictors if x not in featured_occ or featured_occ[x].isna().all()]
    if all_na:
        raise SystemExit(f"all-NA focused predictors: {all_na}")

    feature_contract = {
        "status": "cross_taxon_real_positive_control_prepared_feature_evidence_only",
        "source_snapshot_date": source["gbif_snapshot_date"],
        "source_snapshot_doi": source["gbif_snapshot_doi"],
        "external_positive_labels_used_in_preparation": False,
        "class_matched_target_groups": sorted(set(taxa["target_group"].astype(str))),
        "outer_sealed_before_M": True,
        "M_grid_as_sensitivity": True,
        "n_predictors": 10,
        "featured_occurrence_sha256": _sha(feature_dir / "pilot_occurrences.csv"),
    }
    (feature_dir / "feature_cache_contract.json").write_text(json.dumps(feature_contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    decision = run_endpoint(feature_dir, source["environment_manifest"], source["taxa_file"], contract_path, result_dir)
    (result_dir / "CROSS_TAXON_REAL_POSITIVE_CONTROL_BOUNDARY.txt").write_text(
        "Prospectively frozen non-plant cross-taxon positive-control endpoint.\n"
        "External studies provide positive process controls only, not complete process truth.\n"
        "Four class-matched GBIF sampling footprints were constructed from the same frozen monthly snapshot.\n",
        encoding="utf-8",
    )
    print(json.dumps(feature_contract, indent=2, sort_keys=True))
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
