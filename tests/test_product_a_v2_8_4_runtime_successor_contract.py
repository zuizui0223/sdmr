import json
from pathlib import Path


V283 = Path('configs/product_a_v2_8_3_fresh_confirmation_contract.json')
V284 = Path('configs/product_a_v2_8_4_runtime_successor_contract.json')


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def test_v284_is_design_only_runtime_successor_not_new_science():
    c = _load(V284)
    assert c['purpose'] == 'product_a_v2_8_4_runtime_only_successor_design'
    assert c['tracks_issue'] == 170
    assert c['predecessor_scientific_issue'] == 158
    assert c['predecessor_design_contract']['blob_sha'] == (
        '1928de6d8f1289117415047c7a8d1ee894ca6bbe'
    )
    assert c['predecessor_design_contract'][
        'scientific_semantics_inherited_without_change'
    ] is True
    assert c['motivation']['runtime_only'] is True
    assert c['motivation']['scientific_outcome_reinterpretation'] is False

    boundary = c['execution_boundary']
    assert boundary['design_only'] is True
    assert boundary['runtime_implementation_sha'] is None
    assert boundary['runtime_frozen_ref'] is None
    assert boundary['presealed_execution_allowed'] is False
    assert boundary['sealed_execution_allowed'] is False
    assert boundary['workflow_dispatch_allowed'] is False
    assert boundary['scientific_promotion_allowed'] is False
    assert boundary['product_b_unblocked'] is False
    assert boundary['separate_external_authorization_required'] is True


def test_v284_preserves_v283_scientific_denominator_panel_source_and_design():
    p = _load(V283)
    c = _load(V284)
    inv = c['scientific_invariants']

    assert inv['source_receipt_blob_sha'] == p['upstream_fresh_source']['receipt_blob_sha']
    assert inv['source_workflow_run_id'] == p['upstream_fresh_source']['workflow_run_id']
    assert inv['fresh_taxon_panel_sha256'] == p['fresh_taxon_panel']['sha256']
    assert inv['sealed_fraction'] == p['fixed_design']['sealed_fractions'][0] == 0.25
    assert inv['split_seeds'] == p['fixed_design']['split_seeds']
    assert inv['M_km'] == p['fixed_design']['M_km']
    assert inv['n_confirmation_parts'] == p['fixed_design']['n_confirmation_parts'] == 3
    assert inv['outer_folds'] == p['fixed_design']['outer_folds'] == 4
    assert inv['spatial_microblocks'] == p['fixed_design']['spatial_microblocks'] == 12
    assert inv['assignment_attempts'] == p['fixed_design']['assignment_attempts'] == 32
    assert inv['assignment_seed_formula'] == p['fixed_design']['assignment_seed_formula']

    lib = p['fixed_design']['procedure_library']
    assert inv['procedure_strategies'] == lib['strategies']
    assert inv['model_specs'] == lib['model_specs']
    assert inv['inner_folds'] == lib['inner_folds'] == 3
    assert inv['max_predictors'] == lib['max_predictors'] == 8
    assert inv['vif_threshold'] == lib['vif_threshold'] == 5.0
    assert inv['predictive_min_gain'] == lib['predictive_min_gain'] == 0.0
    assert inv['model_random_state'] == p['inherited_scientific_semantics']['model_random_state'] == 0
    assert inv['selection_process_numpy_seed'] == p['inherited_scientific_semantics']['selection_process_numpy_seed'] == 0
    assert inv['process_domains'] == p['fixed_design']['process_domains']

    rule = p['decision_rule']
    assert inv['prediction_guardrail_mean_presence_rank_delta_vs_auc_min'] == (
        rule['prediction_guardrail']['mean_presence_rank_deficit_vs_auc_comparator_min']
    )
    assert inv['ecological_nondomination_minimum_parts'] == (
        rule['ecological_noninferiority']['minimum_parts']
    )
    assert inv['strict_ecological_improvement_minimum_parts'] == (
        rule['ecological_noninferiority']['strict_improvement_minimum_parts']
    )
    assert inv['process_modal_status_fraction_min'] == (
        rule['process_reproducibility']['modal_status_fraction_min']
    )
    assert inv['primary_denominator'] == 3

    for key in (
        'candidate_predictor_universe_changed',
        'candidate_library_changed',
        'thresholds_changed',
        'taxa_changed',
        'M_changed',
        'seeds_changed',
        'fraction_changed',
        'denominator_changed',
        'decision_rule_changed',
        'scientific_promotion_allowed',
        'product_b_unblocked',
    ):
        assert inv[key] is False


def test_v284_separates_presealed_retry_from_one_shot_sealed_read():
    c = _load(V284)
    barrier = c['information_barrier']
    arch = c['runtime_architecture']
    retry = c['retry_policy']

    assert barrier['structural_gate_precedes_environment'] is True
    assert barrier['model_pool_and_pretruth_are_presealed'] is True
    assert barrier['final_models_frozen_before_sealed_read'] is True
    assert barrier['sealed_occurrences_first_opened_in_separate_sealed_workflow'] is True
    assert barrier['technical_retry_may_never_open_sealed_evidence'] is True

    assert arch['scientific_execution_identity_separate_from_operational_attempt_identity'] is True
    assert arch['presealed_and_sealed_workflows_must_be_separate'] is True
    assert arch['presealed_receipt_is_required_input_to_sealed_workflow'] is True
    assert arch['shared_taxon_part_precompute_before_M_evaluation'] is True
    assert arch['truth_blind_checkpoint_restart_allowed'] is True
    assert arch['checkpoint_or_telemetry_content_may_not_change_selection'] is True

    assert retry['technical_retry_allowed_only_presealed'] is True
    assert retry['retry_requires_exact_scientific_and_runtime_identity_match'] is True
    assert retry['retry_may_not_broadly_repeat_successful_logical_shards'] is True
    assert retry['sealed_workflow_is_one_shot_after_receipt_validation'] is True
    assert retry['sealed_workflow_retry_after_any_sealed_read_requires_separate_explicit_contract'] is True


def test_v284_allows_only_exact_deterministic_runtime_optimizations():
    c = _load(V284)
    opt = c['deterministic_execution_optimizations_allowed']
    assert opt['reuse_M_shared_precompute'] is True
    assert opt['memoize_exact_duplicate_fit_keys'] is True
    assert opt['parallelize_independent_candidate_evaluations'] is True
    assert opt['parallelize_independent_process_knockout_groups'] is True
    assert opt['stable_sort_before_any_tie_break_or_reduction'] is True
    assert opt['approximation_allowed'] is False
    assert opt['early_stopping_rule_change_allowed'] is False
    assert opt['candidate_pruning_for_speed_allowed'] is False
    assert 'training_row_identity_digest' in opt['fit_cache_key_must_include']
    assert 'background_row_identity_digest' in opt['fit_cache_key_must_include']


def test_v284_runtime_environment_and_timeout_are_frozen_before_authorization():
    c = _load(V284)
    env = c['runtime_environment']
    timeout = c['timeout_policy']
    telemetry = c['telemetry']

    assert env['fully_locked_before_scientific_authorization'] is True
    assert env['python_patch_version_must_be_pinned'] is True
    assert env['dependency_lock_with_hashes_required'] is True
    assert env['container_or_runner_environment_digest_required'] is True
    assert env['github_action_revisions_must_be_pinned_by_commit_sha'] is True
    assert set(env['minimum_required_dependency_identities']) == {
        'numpy', 'pandas', 'scipy', 'scikit-learn', 'pyarrow'
    }

    assert timeout['runtime_calibration_must_precede_scientific_authorization'] is True
    assert timeout['calibration_may_use_unsealed_or_synthetic_runtime_workloads_only'] is True
    assert timeout['calibration_may_not_use_sealed_ecological_outcomes'] is True
    assert timeout['scientific_execution_timeout_must_be_frozen_before_launch'] is True
    assert timeout['post_launch_timeout_extension_allowed'] is False
    assert timeout['post_outcome_timeout_retuning_allowed'] is False

    assert telemetry['required'] is True
    assert telemetry['truth_blind'] is True
    assert telemetry['telemetry_may_be_used_for_future_runtime_calibration'] is True
    assert telemetry['telemetry_may_be_used_for_scientific_selection'] is False
