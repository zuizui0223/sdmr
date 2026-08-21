"""Sealed-blind development diagnostic for Product-A v2.7.1 folds."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .v2_6_empirical_model_contract import load_v2_6_empirical_model_contract
from .v2_6_empirical_model_pool_worker import M_NAMES, _partition_contract
from .v2_7_1_evidence_balanced_contract import load_v2_7_1_evidence_balanced_contract
from .v2_7_1_evidence_balanced_partition import make_evidence_balanced_spatial_partitions
from .v2_7_empirical_audit_support import select_partition_aware_empirical_audit_space
from .validation import make_spatial_partition

PURPOSE = "product_a_v2_7_1_evidence_balanced_fold_diagnostic"


def _audit_manifest(path: str | Path) -> pd.DataFrame:
    registry=pd.read_csv(path)
    required={'predictor','empirical_process_domain'}
    missing=required-set(registry.columns)
    if missing:
        raise KeyError(f'v2.7.1 process registry missing columns: {sorted(missing)}')
    return registry[['predictor','empirical_process_domain']].rename(columns={'empirical_process_domain':'process'})


def _select_audit(manifest, occurrence, backgrounds, partitions, *, outer_folds, audit_cfg):
    try:
        selected=select_partition_aware_empirical_audit_space(
            manifest,
            occurrence,
            backgrounds,
            partitions,
            outer_folds=int(outer_folds),
            minimum_predictor_coverage=float(audit_cfg['minimum_predictor_coverage']),
            minimum_joint_coverage=float(audit_cfg['minimum_joint_coverage']),
            minimum_processes=int(audit_cfg['minimum_processes']),
            minimum_fit_background_rows=int(audit_cfg['minimum_complete_fit_background_rows_per_M_fold']),
            minimum_evaluation_background_rows=int(audit_cfg['minimum_complete_evaluation_background_rows_per_M_fold']),
            minimum_heldout_occurrence_rows=int(audit_cfg['minimum_complete_heldout_occurrence_rows_per_M_fold']),
        )
    except ValueError as exc:
        return False, str(exc), None
    return True, None, selected


def run_evidence_balanced_diagnostic(
    *,
    development_contract_path: str | Path,
    model_contract_path: str | Path,
    legacy_partition_contract_path: str | Path,
    process_registry_path: str | Path,
    part_dir: str | Path,
    taxon: str,
    taxon_index: int,
    part_seed: int,
    part_label: str,
    output_dir: str | Path,
) -> dict[str, object]:
    development=load_v2_7_1_evidence_balanced_contract(development_contract_path)
    model_contract=load_v2_6_empirical_model_contract(model_contract_path)
    legacy_partition_contract=_partition_contract(legacy_partition_contract_path)
    root=Path(part_dir)
    materialization=json.loads((root/'contract.json').read_text(encoding='utf-8'))
    for key in ('sealed_occurrence_raster_values_extracted','sealed_background_raster_values_extracted'):
        if materialization.get(key) is not False:
            raise ValueError(f'v2.7.1 diagnostic requires {key}=false')
    if int(materialization.get('seed',-1)) != int(part_seed):
        raise ValueError('v2.7.1 materialization seed differs from requested seed')
    if str(materialization.get('sealed_fraction')) != str(part_label):
        # JSON may serialize 0.20 as numeric 0.2.
        try:
            if abs(float(materialization.get('sealed_fraction'))-float(part_label))>1e-12:
                raise ValueError('v2.7.1 part label differs from materialization')
        except (TypeError, ValueError):
            raise ValueError('v2.7.1 part label differs from materialization')

    occurrences_all=pd.read_parquet(root/'model_occurrences.parquet')
    occurrence=occurrences_all.loc[occurrences_all['species'].astype(str).eq(str(taxon))].reset_index(drop=True)
    if occurrence.empty:
        raise ValueError(f'v2.7.1 occurrence missing taxon: {taxon}')
    backgrounds={}
    for name in M_NAMES:
        frame=pd.read_parquet(root/'M'/name/'model_background.parquet')
        background=frame.loc[frame['species'].astype(str).eq(str(taxon))].reset_index(drop=True)
        if background.empty:
            raise ValueError(f'v2.7.1 background missing {taxon} in {name}')
        backgrounds[name]=background

    manifest=_audit_manifest(process_registry_path)
    audit_cfg=development['audit_space_after_partition']
    fold_cfg=development['evidence_balanced_partition']
    outer_folds=int(fold_cfg['outer_folds'])

    # Recompute the v2.7 partition-aware audit result using the legacy per-M
    # partition semantics, so the new diagnostic has a like-for-like baseline.
    legacy_partitions={}
    for m_index,name in enumerate(M_NAMES):
        background=backgrounds[name]
        legacy_partitions[name]=make_spatial_partition(
            occurrence['longitude'].to_numpy(float),
            occurrence['latitude'].to_numpy(float),
            background['longitude'].to_numpy(float),
            background['latitude'].to_numpy(float),
            n_blocks=int(legacy_partition_contract['n_spatial_blocks']),
            holdout_fraction=float(legacy_partition_contract['partition_holdout_fraction']),
            random_state=int(part_seed)+int(taxon_index)*100+int(m_index),
        )
    old_available, old_error, old_selected=_select_audit(
        manifest, occurrence, backgrounds, legacy_partitions,
        outer_folds=outer_folds, audit_cfg=audit_cfg,
    )

    partition_available=False
    partition_error=None
    partition=None
    audit_available=False
    audit_error=None
    selected=None
    seed=int(part_seed)+int(taxon_index)*100+271
    try:
        partition=make_evidence_balanced_spatial_partitions(
            occurrence['longitude'].to_numpy(float),
            occurrence['latitude'].to_numpy(float),
            {
                name:(
                    backgrounds[name]['longitude'].to_numpy(float),
                    backgrounds[name]['latitude'].to_numpy(float),
                )
                for name in M_NAMES
            },
            n_microblocks=int(fold_cfg['spatial_microblocks']),
            outer_folds=outer_folds,
            minimum_evaluation_occurrences=int(fold_cfg['minimum_evaluation_occurrences_per_fold']),
            minimum_evaluation_background_rows=int(fold_cfg['minimum_evaluation_background_rows_per_M_fold']),
            minimum_training_background_rows=int(fold_cfg['minimum_training_background_rows_per_M_fold']),
            assignment_attempts=int(fold_cfg['assignment_attempts']),
            random_state=seed,
        )
    except ValueError as exc:
        partition_error=str(exc)
    else:
        partition_available=True
        if not partition.support_ledger['structural_support_complete'].astype(bool).all():
            raise AssertionError('v2.7.1 partition marked available without complete structural support')
        partitions={name:partition.for_M(name) for name in M_NAMES}
        audit_available,audit_error,selected=_select_audit(
            manifest, occurrence, backgrounds, partitions,
            outer_folds=outer_folds, audit_cfg=audit_cfg,
        )

    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    if partition is not None:
        partition.support_ledger.to_csv(out/'evidence_balanced_partition_support.csv',index=False)
        partition.attempt_ledger.to_csv(out/'evidence_balanced_partition_attempts.csv',index=False)
        pd.DataFrame([
            {'microblock':block,'fold':fold}
            for block,fold in sorted(partition.microblock_to_fold.items())
        ]).to_csv(out/'microblock_to_fold.csv',index=False)
    else:
        pd.DataFrame().to_csv(out/'evidence_balanced_partition_support.csv',index=False)
        pd.DataFrame().to_csv(out/'evidence_balanced_partition_attempts.csv',index=False)
        pd.DataFrame().to_csv(out/'microblock_to_fold.csv',index=False)
    if selected is not None:
        selected.support_ledger.to_csv(out/'v2_7_1_audit_support.csv',index=False)
        selected.pruning_ledger.to_csv(out/'v2_7_1_audit_pruning.csv',index=False)
        selected.base_audit_ledger.to_csv(out/'v2_7_1_base_audit_space_ledger.csv',index=False)
    else:
        pd.DataFrame().to_csv(out/'v2_7_1_audit_support.csv',index=False)
        pd.DataFrame().to_csv(out/'v2_7_1_audit_pruning.csv',index=False)
        pd.DataFrame().to_csv(out/'v2_7_1_base_audit_space_ledger.csv',index=False)

    result={
        'purpose':PURPOSE,
        'development_contract_sha256':development['contract_sha256'],
        'taxon':str(taxon),
        'taxon_index':int(taxon_index),
        'part_seed':int(part_seed),
        'part_label':str(part_label),
        'M_specs':list(M_NAMES),
        'legacy_v2_7_audit_support_available':bool(old_available),
        'legacy_v2_7_unavailable_reason':old_error,
        'legacy_v2_7_selected_processes':list(old_selected.processes) if old_selected is not None else [],
        'evidence_balanced_partition_available':bool(partition_available),
        'evidence_balanced_partition_unavailable_reason':partition_error,
        'selected_assignment_attempt':int(partition.selected_attempt) if partition is not None else None,
        'selected_assignment_random_state':int(partition.selected_random_state) if partition is not None else None,
        'structural_support_complete':bool(partition_available),
        'v2_7_1_audit_support_available':bool(audit_available),
        'v2_7_1_audit_support_unavailable_reason':audit_error,
        'v2_7_1_selected_audit_predictors':list(selected.predictors) if selected is not None else [],
        'v2_7_1_selected_audit_processes':list(selected.processes) if selected is not None else [],
        'v2_7_1_n_selected_audit_processes':len(selected.processes) if selected is not None else 0,
        'shared_occurrence_fold_assignment_across_all_M':bool(partition_available),
        'environmental_values_used_for_partition_assignment':False,
        'candidate_scores_read':False,
        'candidate_model_fitting_performed':False,
        'process_knockout_outcomes_read':False,
        'sealed_occurrence_environment_read':False,
        'sealed_background_environment_read':False,
        'development_only':True,
        'scientific_promotion_allowed':False,
        'independent_empirical_confirmation_claim_allowed':False,
    }
    (out/'contract.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return result


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--development-contract',required=True)
    parser.add_argument('--model-contract',required=True)
    parser.add_argument('--legacy-partition-contract',required=True)
    parser.add_argument('--process-registry',required=True)
    parser.add_argument('--part-dir',required=True)
    parser.add_argument('--taxon',required=True)
    parser.add_argument('--taxon-index',type=int,required=True)
    parser.add_argument('--part-seed',type=int,required=True)
    parser.add_argument('--part-label',required=True)
    parser.add_argument('--output-dir',required=True)
    args=parser.parse_args(argv)
    run_evidence_balanced_diagnostic(
        development_contract_path=args.development_contract,
        model_contract_path=args.model_contract,
        legacy_partition_contract_path=args.legacy_partition_contract,
        process_registry_path=args.process_registry,
        part_dir=args.part_dir,
        taxon=args.taxon,
        taxon_index=args.taxon_index,
        part_seed=args.part_seed,
        part_label=args.part_label,
        output_dir=args.output_dir,
    )
    return 0


if __name__=='__main__':
    raise SystemExit(main())
