"""Fail-closed contract loader for Product-A v2.7.1 fold development."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PURPOSE = "product_a_v2_7_1_evidence_balanced_folds_development_contract"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_v2_7_1_evidence_balanced_contract(path: str | Path) -> dict[str, Any]:
    source=Path(path)
    payload=json.loads(source.read_text(encoding='utf-8'))
    if payload.get('purpose') != PURPOSE:
        raise ValueError('Product-A v2.7.1 purpose changed')
    if payload.get('development_only') is not True:
        raise ValueError('Product-A v2.7.1 must remain development only')
    for key in ('scientific_promotion_allowed','independent_empirical_confirmation_claim_allowed','product_b_unblocked'):
        if payload.get(key) is not False:
            raise ValueError(f'Product-A v2.7.1 requires {key}=false')
    predecessor=payload.get('predecessor_v2_7_development_result',{})
    if predecessor != {
        'run_id':32447844270,
        'head_sha':'0bb0bdd99303ca956681de15cfe3fad903dad7a9',
        'summary_artifact_id':9434699815,
        'summary_artifact_digest':'sha256:389a1d4008e7373ccee8741b4defc4705e0fe44c6f25c4060613b6e0a0f4bda4',
        'n_diagnostics':72,
        'n_audit_support_available':39,
        'availability_fraction':39/72,
        'legacy_43_predictor_supported_M_fold_cells_total':573,
        'total_M_fold_cells':864,
        'sealed_environment_read':False,
        'candidate_model_fitting_performed':False,
    }:
        raise ValueError('Product-A v2.7 predecessor result changed')
    source_cfg=payload.get('development_source',{})
    if int(source_cfg.get('model_pool_materialization_run_id',-1)) != 32260616084:
        raise ValueError('Product-A v2.7.1 development source changed')
    for key in ('model_pool_only_reuse_allowed','current_model_pool_may_inform_partition_development','current_v2_6_split_may_not_be_relabelled_as_fresh_confirmation','future_independent_confirmation_requires_genuinely_fresh_empirical_evidence'):
        if source_cfg.get(key) is not True:
            raise ValueError(f'Product-A v2.7.1 source requires {key}=true')
    if source_cfg.get('outer_sealed_environment_read_allowed') is not False:
        raise ValueError('Product-A v2.7.1 cannot read sealed environments')
    partition=payload.get('evidence_balanced_partition',{})
    expected_partition={
        'constructor':'make_evidence_balanced_spatial_partitions',
        'spatial_microblocks':12,
        'outer_folds':4,
        'microblock_constructor':'KMeans_on_model_pool_occurrence_unit_sphere_coordinates',
        'microblock_atomicity_preserved':True,
        'fold_assignment':'StratifiedGroupKFold_over_presence_and_all_M_background_resource_types',
        'assignment_attempts':32,
        'assignment_seed_formula':'part_seed + taxon_index*100 + 271',
        'shared_occurrence_fold_assignment_across_all_M':True,
        'backgrounds_used_jointly_for_fold_support':['buffer_150km','buffer_300km','buffer_500km'],
        'minimum_evaluation_occurrences_per_fold':2,
        'minimum_evaluation_background_rows_per_M_fold':5,
        'minimum_training_background_rows_per_M_fold':5,
        'environmental_values_used':False,
        'candidate_scores_used':False,
        'candidate_response_magnitudes_used':False,
        'process_knockout_outcomes_used':False,
        'sealed_rows_used':False,
        'choose_feasible_assignment_by':'minimum_max_then_mean_normalized_row_count_imbalance',
        'abstain_if_no_feasible_assignment':True,
    }
    if partition != expected_partition:
        raise ValueError('Product-A v2.7.1 partition contract changed')
    audit=payload.get('audit_space_after_partition',{})
    expected_audit={
        'selector':'select_partition_aware_empirical_audit_space',
        'minimum_predictor_coverage':0.95,
        'minimum_joint_coverage':0.80,
        'minimum_processes':4,
        'minimum_complete_fit_background_rows_per_M_fold':5,
        'minimum_complete_evaluation_background_rows_per_M_fold':5,
        'minimum_complete_heldout_occurrence_rows_per_M_fold':2,
        'candidate_scores_used':False,
        'sealed_rows_used':False,
        'thresholds_unchanged_from_v2_7':True,
    }
    if audit != expected_audit:
        raise ValueError('Product-A v2.7.1 audit support thresholds changed')
    for key in ('structural_partition_support_complete_before_environmental_missingness_check','audit_support_complete_before_candidate_evaluation','does_not_validate_or_promote_Product_A'):
        if payload.get('diagnostic_success_means',{}).get(key) is not True:
            raise ValueError(f'Product-A v2.7.1 success semantics require {key}=true')
    payload['contract_sha256']=_sha256(source)
    return payload
