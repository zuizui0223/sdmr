"""Audit safeguards; these tests never fit models or consume external outcomes."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_real_positive_control_results.py'
_SPEC = importlib.util.spec_from_file_location('positive_control_result_audit', _PATH)
audit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(audit)


def test_two_positive_M_do_not_rescue_missing_third():
    result = audit.classify_expected([.8, np.nan, 1.])
    assert not result['complete'] and not result['recovered']
    assert result['positive_m_count'] == 0
    assert result['finite_positive_m_count'] == 2


def test_two_positive_M_do_not_rescue_negative_mean():
    result = audit.classify_expected([.00574, .009025, -.016877])
    assert result['complete'] and result['mean'] < 0
    assert result['finite_positive_m_count'] == 2 and not result['recovered']


def test_positive_mean_alone_is_not_enough():
    assert not audit.classify_expected([1., -.1, -.1])['recovered']


def test_positive_complete_case_passes():
    assert audit.classify_expected([.7, .6, -.1])['recovered']


def test_incomplete_denominator_rejected():
    with pytest.raises(ValueError):
        audit.classify_expected([1., 1.])


def test_string_false_is_not_truthy():
    assert audit.boolean('False') is False
    with pytest.raises(ValueError):
        audit.boolean('maybe')


def test_no_adequate_candidate_is_unavailable_not_negative_truth():
    frame = pd.DataFrame({'candidate': ['neutral_only'], 'prediction_adequate': [False],
                          'mean_niche_overlap_schoener_d_pc12': [.2]})
    score, status, gap, _, _ = audit.score_process(frame, 'temperature')
    assert np.isnan(score) and np.isnan(gap) and status == 'no_adequate_candidate'


def test_empty_exclusion_is_code_not_measured_perfect_loss():
    frame = pd.DataFrame({'candidate': ['temperature_only'], 'prediction_adequate': [True],
                          'mean_niche_overlap_schoener_d_pc12': [.2]})
    score, status, gap, _, _ = audit.score_process(frame, 'temperature')
    assert score == 1. and np.isnan(gap) and status == 'no_adequate_excluded_candidate'


def test_positive_normalized_one_can_have_small_raw_gap():
    frame = pd.DataFrame({'candidate': ['temperature_only', 'temperature_water'],
                          'prediction_adequate': [True, True],
                          'mean_niche_overlap_schoener_d_pc12': [.62, .626]})
    score, status, gap, _, _ = audit.score_process(frame, 'water')
    assert score == 1. and status == 'compared' and np.isclose(gap, .006)


def test_changed_archive_digest_is_rejected(tmp_path):
    path = tmp_path / 'bad.zip'
    path.write_bytes(b'not the frozen archive')
    with pytest.raises(ValueError, match='SHA-256 mismatch'):
        audit.load_results(path, '0' * 64)
