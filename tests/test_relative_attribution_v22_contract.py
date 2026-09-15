import json
from pathlib import Path


def test_v22_contract_keeps_consumed_denominator_and_symmetric_rules():
    root = Path(__file__).resolve().parents[1]
    cfg = json.loads((root / 'configs' / 'relative_attribution_v22_development.json').read_text())
    assert cfg['scope'] == 'development_only_on_consumed_v21_seeds'
    assert cfg['consumed_seed_denominator'] == list(range(17001, 17011))
    assert cfg['authoritative_v21_source']['workflow_run'] == 34671264361
    assert cfg['authoritative_v21_source']['terminal_artifact'] == 10291023518
    assert cfg['authoritative_v21_source']['expected_context_rows'] == 1920
    assert cfg['authoritative_v21_source']['expected_contexts_with_at_least_two_supported_processes'] == 122
    assert cfg['authoritative_v21_source']['expected_unordered_supported_pairs'] == 152
    rule = cfg['pairwise_rule']
    assert rule['symmetry_required'] is True
    assert rule['minimum_source_perturbations'] == 3
    assert rule['rank_margin'] == 0.02
    assert rule['density_margin'] == 0.01
    assert 'seasonality_specific_penalty' in cfg['forbidden']
    assert 'process_name_specific_threshold' in cfg['forbidden']
