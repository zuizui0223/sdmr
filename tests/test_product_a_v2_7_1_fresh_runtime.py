import json
from pathlib import Path

import numpy as np
import pandas as pd

from sdmr.v2_7_1_fresh_aggregate import run_fresh_aggregate
from sdmr.v2_7_1_fresh_contract import (
    load_fresh_eligibility_thresholds,
    load_fresh_source_receipt,
    load_v2_7_1_fresh_confirmation_contract,
)
from sdmr.v2_7_1_fresh_pretruth import run_fresh_pretruth

CONTRACT = Path('configs/product_a_v2_7_1_fresh_confirmation_contract.json')
RECEIPT = Path('configs/product_a_v2_7_1_fresh_raw_source_receipt.json')
PANEL = Path('configs/product_a_v2_7_1_fresh_confirmation_taxa.csv')


def test_fresh_runtime_loaders_pin_decision_source_and_eligibility():
    c = load_v2_7_1_fresh_confirmation_contract(CONTRACT)
    r = load_fresh_source_receipt(RECEIPT)
    t = load_fresh_eligibility_thresholds(CONTRACT)
    assert c['fixed_design']['split_seeds'] == [2026082201, 2026082202, 2026082203]
    assert c['v2_7_1_evidence_balanced_partition']['assignment_attempts'] == 32
    assert r['workflow_run_id'] == 32477393089
    assert r['information_barrier']['sealed_confirmation_outcomes_read'] is False
    assert t == {'minimum_occurrences': 80, 'minimum_unique_cells': 50}


def test_unavailable_worker_makes_pretruth_unavailable_without_sealed_access(tmp_path):
    taxa = list(pd.read_csv(PANEL)['scientific_name'].astype(str))
    root = tmp_path / 'workers'
    for i, taxon in enumerate(taxa):
        d = root / f'w{i}'
        d.mkdir(parents=True)
        payload = {
            'purpose': 'product_a_v2_7_1_fresh_model_pool_worker',
            'available': i != 3,
            'unavailable_stage': 'structural_partition' if i == 3 else None,
            'unavailable_reason': 'frozen structural support unavailable' if i == 3 else None,
            'taxon': taxon,
            'taxon_index': i,
            'part_seed': 2026082201,
            'sealed_occurrence_environment_read': False,
            'sealed_occurrence_used_for_selection': False,
            'sealed_occurrence_used_for_process_status': False,
        }
        (d / 'contract.json').write_text(json.dumps(payload), encoding='utf-8')
    out = tmp_path / 'pretruth'
    result = run_fresh_pretruth(contract_path=CONTRACT, worker_root=root, output_dir=out)
    assert result['available'] is False
    assert result['sealed_audit_authorized'] is False
    assert result['sealed_occurrence_environment_read'] is False
    status = pd.read_csv(out / 'pretruth_process_status.csv')
    assert len(status) == 12 * 6
    assert set(status['status']) == {'unavailable'}


def test_unavailable_parts_before_or_after_sealed_read_force_unavailable_decision(tmp_path):
    taxa = list(pd.read_csv(PANEL)['scientific_name'].astype(str))
    domains = ['thermal', 'water', 'seasonality_phenology', 'energy_productivity', 'snow', 'wind']
    root = tmp_path / 'audits'
    parts = [(seed, fraction) for seed in (2026082201, 2026082202, 2026082203) for fraction in (0.20, 0.30)]
    for j, (seed, fraction) in enumerate(parts):
        d = root / f'p{j}'
        d.mkdir(parents=True)
        part_id = f'seed{seed}_sealed{fraction:.2f}'
        opened = j == 0
        (d / 'contract.json').write_text(json.dumps({
            'purpose': 'product_a_v2_7_1_fresh_part_sealed_audit',
            'part_id': part_id,
            'available': False,
            'sealed_occurrence_environment_read': opened,
            'sealed_occurrence_first_read_after_pretruth_freeze': opened,
            'candidate_or_threshold_retuning_after_sealed_read': False,
            'structural_or_audit_abstention_propagated_as_unavailable': not opened,
            'undefined_sealed_ecological_evidence_propagated_as_unavailable': opened,
        }), encoding='utf-8')
        pd.DataFrame([{
            'part_id': part_id,
            'all_12_taxa': False,
            'all_3_M_specs': False,
            'mean_presence_rank_delta_vs_auc': np.nan,
            'ecologically_nondominated_vs_auc': False,
            'strict_ecological_improvement_vs_auc': False,
            'part_available': False,
        }]).to_csv(d / 'part_summary.csv', index=False)
        pd.DataFrame([
            {'part_id': part_id, 'taxon': taxon, 'process_domain': domain, 'status': 'unavailable'}
            for taxon in taxa for domain in domains
        ]).to_csv(d / 'process_status.csv', index=False)
    out = tmp_path / 'decision'
    result = run_fresh_aggregate(contract_path=CONTRACT, audit_root=root, output_dir=out)
    assert result['decision'] == 'empirical_confirmation_unavailable'
    assert result['n_available_parts'] == 0
    assert result['n_unavailable_before_sealed_read'] == 5
    assert result['n_unavailable_after_sealed_read'] == 1
    assert result['scientific_promotion_allowed'] is False
    assert result['product_b_unblocked'] is False
    assert result['fresh_thresholds_retuned_after_sealed_read'] is False
