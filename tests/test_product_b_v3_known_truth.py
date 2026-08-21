from pathlib import Path
import json

import pandas as pd

from sdmr.niche_recovery_selection import RECOVERY_DIRECTIONS
from sdmr.product_b_v2_known_truth_contract import M_SPECS
from sdmr.product_b_v3_known_truth import A_SHARD_PURPOSE, freeze_product_a_representative
from sdmr.product_b_v3_known_truth_contract import load_product_b_v3_known_truth_contract

CONFIG = Path('configs/product_b_v3_known_truth_contract.json')


def test_v3_contract_redefines_b_as_conditional_on_product_a_selector():
    c = load_product_b_v3_known_truth_contract(CONFIG)
    assert c['opened_generating_truth_seed_maximum'] == 523
    assert [x['seed'] for x in c['product_b_evaluation_taxa']] == list(range(701, 713))
    assert c['diagnosis']['candidate_selection_uses_process_ablation_outcomes'] is False
    assert c['diagnosis']['candidate_selection_uses_generating_truth'] is False
    assert c['product_a_selector']['requires_complete_taxon_M_fold_evidence'] is True
    assert c['product_a_selector']['representative_frozen_before_any_product_b_process_ablation'] is True
    assert c['process_ablation_semantics']['predictor_reselection_after_process_drop'] is False


def test_product_a_representative_is_frozen_from_complete_truth_blind_cohort(tmp_path):
    c = load_product_b_v3_known_truth_contract(CONFIG)
    root = tmp_path / 'workers'; root.mkdir()
    taxa = c['product_b_evaluation_taxon_names']
    for taxon_index, taxon in enumerate(taxa):
        for m_index, m_name in enumerate(M_SPECS):
            cell = root / f't{taxon_index}_m{m_index}'; cell.mkdir()
            (cell / 'contract.json').write_text(json.dumps({
                'purpose': A_SHARD_PURPOSE,
                'source_contract_sha256': c['contract_sha256'],
                'taxon': taxon,
                'M': m_name,
                'product_b_process_ablation_outcomes_read': False,
                'generating_truth_read': False,
                'real_empirical_data_read': False,
                'empirical_sealed_outcomes_read': False,
                'scientific_threshold_tuning_performed': False,
            }) + '\n')
            rows = []
            for fold in (0, 1):
                row = {
                    'taxon': taxon,
                    'M': m_name,
                    'fold': fold,
                    'candidate': 'candidate_complete',
                    'presence_rank': 0.75,
                    'n_predictors': 3,
                }
                for metric, direction in RECOVERY_DIRECTIONS.items():
                    row[metric] = 0.85 if direction == 'max' else 0.15
                rows.append(row)
            # An incomplete alternative must never be rescued by score quality.
            alt = dict(rows[0]); alt['candidate'] = 'candidate_incomplete'; alt['presence_rank'] = 0.99
            for metric, direction in RECOVERY_DIRECTIONS.items():
                alt[metric] = 0.99 if direction == 'max' else 0.01
            rows.append(alt)
            pd.DataFrame(rows).to_csv(cell / 'base_fold_metrics.csv', index=False)

    out = tmp_path / 'freeze'
    result = freeze_product_a_representative(contract_path=CONFIG, worker_root=root, output_dir=out)
    assert result['product_a_representative'] == 'candidate_complete'
    assert result['product_a_representative_frozen_before_any_product_b_process_ablation'] is True
    assert result['product_b_process_ablation_outcomes_read'] is False
    assert result['generating_truth_read'] is False
    summary = pd.read_csv(out / 'product_a_complete_candidate_summary.csv')
    assert set(summary.loc[summary['complete_outer_evidence'].astype(bool), 'candidate']) == {'candidate_complete'}
