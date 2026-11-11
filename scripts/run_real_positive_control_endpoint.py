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


def _sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _exclude_focal_taxa(target: pd.DataFrame, taxa: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    name_cols = [x for x in ('species', 'acceptedScientificName', 'scientificName') if x in target.columns]
    if not name_cols:
        raise SystemExit('target group has no usable scientific-name column for focal exclusion')
    remove = pd.Series(False, index=target.index)
    removed: dict[str, int] = {}
    for species in taxa['scientific_name'].astype(str):
        one = pd.Series(False, index=target.index)
        for col in name_cols:
            one |= target[col].fillna('').astype(str).str.strip().str.casefold().eq(species.casefold())
        removed[species] = int(one.sum())
        remove |= one
    return target.loc[~remove].reset_index(drop=True), removed


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--focal-parquet', required=True)
    p.add_argument('--target-parquet', required=True)
    p.add_argument('--contract', default='configs/product_a_real_positive_control_contract_v1.json')
    p.add_argument('--output-root', required=True)
    args = p.parse_args(argv)

    contract_path = Path(args.contract)
    contract = json.loads(contract_path.read_text(encoding='utf-8'))
    if contract.get('purpose') != 'product_a_real_positive_control_process_membership_v1':
        raise SystemExit('wrong positive-control contract')
    if contract.get('frozen_before_sdm_outcome') is not True:
        raise SystemExit('positive-control contract was not frozen pre-outcome')

    root = Path(args.output_root)
    input_dir = root / 'input'
    feature_dir = root / 'feature_cache'
    result_dir = root / 'result'
    input_dir.mkdir(parents=True, exist_ok=True)
    feature_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    taxa = pd.read_csv(contract['source']['taxa_file'])
    if len(taxa) != 4:
        raise SystemExit('frozen positive-control denominator must remain four taxa')
    manifest = pd.read_csv(contract['source']['environment_manifest'])
    if len(manifest) != 10:
        raise SystemExit('focused environmental registry must contain 10 predictors')

    focal_path = Path(args.focal_parquet)
    target_path = Path(args.target_parquet)
    expected_target_sha = str(contract['source']['target_group_sha256_before_new_focal_exclusion'])
    actual_target_sha = _sha256(target_path)
    if actual_target_sha != expected_target_sha:
        raise SystemExit(f'target-group SHA mismatch: {actual_target_sha}')

    target = pd.read_parquet(target_path)
    filtered_target, removed = _exclude_focal_taxa(target, taxa)
    filtered_target_path = input_dir / 'target_group_nonfocal.parquet'
    filtered_target.to_parquet(filtered_target_path, index=False)
    exclusion_ledger = {
        'source_sha256': actual_target_sha,
        'filtered_sha256': _sha256(filtered_target_path),
        'source_rows': int(len(target)),
        'filtered_rows': int(len(filtered_target)),
        'removed_rows': int(len(target) - len(filtered_target)),
        'removed_by_taxon': removed,
        'all_four_focal_taxa_excluded_before_M': True,
    }
    (input_dir / 'target_exclusion_ledger.json').write_text(
        json.dumps(exclusion_ledger, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )

    focal = load_gbif_download(
        focal_path,
        download_key='real-positive-control-focal',
        checklist_key='snapshot-interpreted:2026-08-01',
    )
    target_loaded = load_gbif_download(
        filtered_target_path,
        download_key='real-positive-control-target',
        checklist_key='snapshot-interpreted:2026-08-01',
    )

    grid = read_pilot_grid(contract['accessible_area']['grid_file'])
    required_specs = tuple(str(x) for x in contract['accessible_area']['required_specs'])
    grid = grid.loc[grid['name'].astype(str).isin(required_specs)].reset_index(drop=True)
    if tuple(grid['name'].astype(str)) != required_specs:
        raise SystemExit('M grid order/content differs from frozen contract')

    admission = OccurrenceAdmissionConfig()
    prepared_by_name = {}
    ledgers = []
    for row in grid.itertuples(index=False):
        prepared = prepare_product_a_pilot(
            focal.records,
            taxa,
            admission_config=admission,
            min_occurrences=int(contract['occurrence_gate']['minimum_occurrences']),
            min_unique_cells=int(contract['occurrence_gate']['minimum_unique_cells']),
            gate_cell_size_degrees=float(contract['occurrence_gate']['cell_size_degrees']),
            m_strategy=str(row.m_strategy),
            target_group_pool=target_loaded.records,
            bbox_buffer_degrees=float(row.bbox_buffer_degrees),
            occurrence_buffer_km=float(row.occurrence_buffer_km),
            background_points=int(row.background_points),
            background_cell_size_degrees=float(row.background_cell_size_degrees),
            random_state=int(contract['occurrence_gate']['seed']),
            strict_background=False,
            focal_thin_cell_size_degrees=float(contract['occurrence_gate']['cell_size_degrees']),
            outer_sealed_fraction=float(contract['occurrence_gate']['outer_sealed_fraction']),
            outer_n_spatial_blocks=8,
        )
        name = str(row.name)
        prepared_by_name[name] = prepared
        specdir = feature_dir / 'specifications' / name
        specdir.mkdir(parents=True, exist_ok=True)
        prepared.species_gate.assign(m_spec=name).to_csv(specdir / 'species_gate.csv', index=False)
        prepared.background_ledger.assign(m_spec=name).to_csv(specdir / 'background_ledger.csv', index=False)
        prepared.background.to_csv(specdir / 'background_pre_raster.csv', index=False)
        ledgers.append(prepared.species_gate.assign(m_spec=name))

    first = prepared_by_name[required_specs[0]]
    first.occurrences.to_csv(feature_dir / 'pilot_occurrences_pre_raster.csv', index=False)
    pd.concat(ledgers, ignore_index=True).to_csv(feature_dir / 'species_gate_all_M.csv', index=False)
    grid.to_csv(feature_dir / 'pilot_grid_frozen.csv', index=False)

    layers, resolution = raster_specs_from_chelsa_manifest(
        manifest,
        include_availability=('current',),
        strict=True,
    )
    if len(layers) != 10:
        raise SystemExit(f'expected 10 focused layers, got {len(layers)}')
    resolution.to_csv(feature_dir / 'chelsa_resolution_ledger.csv', index=False)

    backgrounds = {name: prepared.background for name, prepared in prepared_by_name.items()}
    featured_occ, featured_bg, provenance = extract_protocol_grid_rasters(
        first.occurrences,
        backgrounds,
        layers,
    )
    featured_occ.to_csv(feature_dir / 'pilot_occurrences.csv', index=False)
    provenance.to_csv(feature_dir / 'raster_provenance_joint_protocol_grid.csv', index=False)
    for name, frame in featured_bg.items():
        frame.to_csv(feature_dir / 'specifications' / name / 'background.csv', index=False)

    predictors = [str(x) for x in manifest['predictor']]
    all_na = [x for x in predictors if x not in featured_occ or featured_occ[x].isna().all()]
    if all_na:
        raise SystemExit(f'all-NA focused predictors: {all_na}')

    feature_contract = {
        'status': 'real_positive_control_prepared_feature_evidence_only',
        'source_snapshot_date': contract['source']['gbif_snapshot_date'],
        'source_snapshot_doi': contract['source']['gbif_snapshot_doi'],
        'external_positive_labels_used_in_preparation': False,
        'outer_sealed_before_M': True,
        'M_grid_as_sensitivity': True,
        'n_predictors': 10,
        'focused_manifest_sha256': _sha256(contract['source']['environment_manifest']),
        'featured_occurrence_sha256': _sha256(feature_dir / 'pilot_occurrences.csv'),
    }
    (feature_dir / 'feature_cache_contract.json').write_text(
        json.dumps(feature_contract, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )

    decision = run_endpoint(
        feature_dir,
        contract['source']['environment_manifest'],
        contract['source']['taxa_file'],
        contract_path,
        result_dir,
    )
    (result_dir / 'REAL_POSITIVE_CONTROL_BOUNDARY.txt').write_text(
        'This is a prospectively frozen real-occurrence positive-control endpoint.\n'
        'External experiments/transplants provide positive process controls only; they do not define complete process sets or negative truth.\n'
        'The endpoint does not alter the frozen v2.8.4 empirical decision and does not establish physiological causation or full proxy closure.\n',
        encoding='utf-8',
    )
    print(json.dumps(exclusion_ledger, indent=2, sort_keys=True))
    print(json.dumps(feature_contract, indent=2, sort_keys=True))
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
