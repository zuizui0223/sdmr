import json
from pathlib import Path


def test_v10_contract_is_consumed_development_only():
    cfg = json.loads(Path('configs/decorrelation_contrast_v10_development.json').read_text())
    assert cfg['purpose'] == 'decorrelation_contrast_v10_development_only'
    assert cfg['development_only'] is True
    assert cfg['eligible_for_prospective_performance_claim'] is False
    assert cfg['consumed_seed_denominator'] == list(range(15001, 15011))
    assert cfg['material_r2_drop'] == 0.10
    assert cfg['sem_multiplier'] == 1.0
    assert cfg['competitor_total_candidate_only'] is True
    assert cfg['pairwise_rank_margin'] == 0.02
    assert cfg['pairwise_density_margin'] == 0.01
    assert cfg['pairwise_sem_multiplier'] == 1.0
    assert cfg['separator_selection_uses_occurrence_or_truth'] is False
    assert cfg['post_outcome_threshold_relaxation_allowed'] is False
    assert cfg['fresh_known_truth_validation_authorized'] is False
    assert cfg['fresh_empirical_validation_authorized'] is False
