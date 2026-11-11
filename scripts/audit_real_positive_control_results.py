"""Independently audit consumed SDMR real positive-control results (no model fit).

Reads only result tables in digest-pinned archives; never reads occurrence,
background or raster feature tables. Historical rules and decisions are retained.
The output diagnoses availability and fold completeness, not a new validation.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

SPECS = ('buffer_150km', 'buffer_300km', 'buffer_500km')
PROCESSES = ('temperature', 'water')
CANDIDATES = {
    'neutral_only': (),
    'temperature_only': ('temperature',),
    'water_only': ('water',),
    'temperature_water': PROCESSES,
}
SOURCES = {
    'plant': {
        'run_id': 34028927021, 'artifact_id': 9989319865,
        'sha256': '833324aedad4a49875d7d433e69530bf4792ac1ce8cb26e472607dd34409ed20',
        'labels': {'Quercus robur': 'water', 'Silene ciliata': 'water',
                   'Plantago alpina': 'temperature', 'Silene acaulis': 'temperature'},
    },
    'nonplant': {
        'run_id': 34030629917, 'artifact_id': 9989754054,
        'sha256': '1e36b9dca17e09265bd35f08cfce4fba202eb3ac70478728ee845b7db8fe7e0d',
        'labels': {'Bombus terrestris': 'temperature', 'Ochotona princeps': 'temperature',
                   'Plethodon cinereus': 'water', 'Cepaea nemoralis': 'water'},
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def close(actual: float, expected: float, label: str) -> None:
    require(bool(np.isclose(actual, expected, rtol=1e-10, atol=1e-12, equal_nan=True)),
            f'{label}: recomputed {actual!r} != saved {expected!r}')


def boolean(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if str(value) in ('True', 'False'):
        return str(value) == 'True'
    raise ValueError(f'invalid boolean: {value!r}')


def classify_expected(scores: list[float]) -> dict:
    """Historical all-three-M rule, with non-promotional partial diagnostics."""
    require(len(scores) == 3, 'exactly three predeclared M values required')
    values = np.asarray(scores, dtype=float)
    complete = bool(np.isfinite(values).all())
    mean = float(values.mean()) if complete else np.nan
    finite_positive = int((np.isfinite(values) & (values > 0)).sum())
    historical_positive = finite_positive if complete else 0
    recovered = bool(complete and mean > 0 and historical_positive >= 2)
    return {'complete': complete, 'mean': mean, 'positive_m_count': historical_positive,
            'finite_positive_m_count': finite_positive,
            'missing_m_count': int((~np.isfinite(values)).sum()), 'recovered': recovered}


def score_process(summary: pd.DataFrame, process: str) -> tuple[float, str, float, str, str]:
    adequate = summary.loc[summary['prediction_adequate']].copy()
    if adequate.empty:
        return np.nan, 'no_adequate_candidate', np.nan, '', ''
    with_p = adequate.loc[adequate['candidate'].map(lambda c: process in CANDIDATES[c])]
    without_p = adequate.loc[adequate['candidate'].map(lambda c: process not in CANDIDATES[c])]
    metric = 'mean_niche_overlap_schoener_d_pc12'
    def winner(frame: pd.DataFrame) -> str:
        if frame.empty:
            return ''
        return ';'.join(sorted(frame.loc[frame[metric].eq(frame[metric].max()), 'candidate']))
    if with_p.empty:
        return -1., 'no_adequate_process_candidate', np.nan, '', winner(without_p)
    if without_p.empty:
        return 1., 'no_adequate_excluded_candidate', np.nan, winner(with_p), ''
    gap = float(with_p[metric].max() - without_p[metric].max())
    span = float(adequate[metric].max() - adequate[metric].min())
    if span <= 1e-12:
        return 0., 'zero_overlap_range', gap, winner(with_p), winner(without_p)
    return gap / span, 'compared', gap, winner(with_p), winner(without_p)


def load_results(path: Path, expected_digest: str) -> tuple[dict, dict]:
    require(digest(path) == expected_digest, f'archive SHA-256 mismatch: {path.name}')
    tables, shas = {}, {}
    with zipfile.ZipFile(path) as archive:
        for suffix in ('fold_metrics.csv', 'candidate_summary.csv', 'process_scores.csv',
                       'aggregated_scores.csv', 'availability.csv', 'taxon_results.csv',
                       'decision.json'):
            matches = [n for n in archive.namelist()
                       if '/result/' in n and n.endswith('real_positive_control_' + suffix)]
            require(len(matches) == 1, f'exactly one {suffix} required')
            raw = archive.read(matches[0])
            shas[suffix] = hashlib.sha256(raw).hexdigest()
            tables[suffix] = json.loads(raw) if suffix.endswith('.json') else pd.read_csv(io.BytesIO(raw))
    return tables, shas


def audit_lane(lane: str, path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    source = SOURCES[lane]
    data, file_shas = load_results(path, source['sha256'])
    folds = data['fold_metrics.csv']
    saved = data['candidate_summary.csv']
    process_saved = data['process_scores.csv']
    taxon_saved = data['taxon_results.csv'].set_index('species')
    technical = data['availability.csv'].set_index(['species', 'm_spec'])
    require(set(taxon_saved.index) == set(source['labels']), f'{lane}: taxon denominator changed')
    require(len(saved) == 48 and len(process_saved) == 24 and len(technical) == 12,
            f'{lane}: incomplete table denominator')
    require(not folds.duplicated(['species', 'm_spec', 'candidate', 'fold']).any(), 'duplicate fold key')
    for table, keys in ((saved, ['species', 'm_spec', 'candidate']),
                        (process_saved, ['species', 'm_spec', 'process'])):
        require(not table.duplicated(keys).any(), f'duplicate {keys}')
    candidate_rows, cell_rows, taxon_rows = [], [], []
    for species, expected_process in source['labels'].items():
        expected_scores, competing_scores = [], []
        require(taxon_saved.loc[species, 'expected_process'] == expected_process, 'external label changed')
        for m in SPECS:
            cell_summaries = []
            for candidate in CANDIDATES:
                f = folds.loc[(folds.species == species) & (folds.m_spec == m) & (folds.candidate == candidate)]
                valid = np.isfinite(f.presence_rank) & np.isfinite(f.niche_overlap_schoener_d_pc12)
                require(bool(valid.all()), 'nonfinite raw fold metrics require separate audit')
                require(0 < len(f) <= 3, 'unexpected fold denominator')
                rank = float(f.presence_rank.mean())
                sem = float(f.presence_rank.std(ddof=1) / np.sqrt(len(f))) if len(f) > 1 else 0.
                overlap = float(f.niche_overlap_schoener_d_pc12.mean())
                adequate = bool(rank >= .51 - 1e-12 and rank - sem >= .50 - 1e-12)
                old = saved.loc[(saved.species == species) & (saved.m_spec == m) & (saved.candidate == candidate)].iloc[0]
                for col, value in [('n_folds', len(f)), ('mean_presence_rank', rank),
                                   ('sem_presence_rank', sem), ('mean_niche_overlap_schoener_d_pc12', overlap)]:
                    close(value, float(old[col]), f'{lane}/{species}/{m}/{candidate}/{col}')
                require(adequate == boolean(old.prediction_adequate), 'adequacy classification mismatch')
                row = {'lane': lane, 'species': species, 'm_spec': m, 'candidate': candidate,
                       'n_folds': len(f), 'all_three_folds': len(f) == 3,
                       'mean_presence_rank': rank, 'sem_presence_rank': sem,
                       'mean_minus_sem': rank - sem, 'mean_gate_pass': rank >= .51 - 1e-12,
                       'lower_gate_pass': rank - sem >= .50 - 1e-12,
                       'mean_niche_overlap_schoener_d_pc12': overlap,
                       'prediction_adequate': adequate}
                candidate_rows.append(row)
                cell_summaries.append(row)
            summary = pd.DataFrame(cell_summaries)
            expected_detail = None
            for p in PROCESSES:
                value, status, raw_gap, with_name, without_name = score_process(summary, p)
                old = process_saved.loc[(process_saved.species == species) &
                                        (process_saved.m_spec == m) & (process_saved.process == p)].iloc[0]
                close(value, float(old.score), f'{lane}/{species}/{m}/{p}')
                require(status == old.status, 'score status mismatch')
                if p == expected_process:
                    expected_scores.append(value)
                    expected_detail = (value, status, raw_gap, with_name, without_name)
                else:
                    competing_scores.append(value)
            value, status, raw_gap, with_name, without_name = expected_detail
            cell_rows.append({'lane': lane, 'species': species, 'expected_process': expected_process,
                              'm_spec': m, 'expected_score': value, 'score_status': status,
                              'raw_schoener_d_gap': raw_gap,
                              'best_containing_candidate': with_name, 'best_excluded_candidate': without_name,
                              'n_adequate': int(summary.prediction_adequate.sum()),
                              'pipeline_available': boolean(technical.loc[(species, m), 'available']),
                              'expected_process_comparable': status == 'compared',
                              'boundary_code_not_measured_loss': status in ('no_adequate_process_candidate', 'no_adequate_excluded_candidate'),
                              'all_candidates_three_folds': bool(summary.all_three_folds.all())})
        result = classify_expected(expected_scores)
        competitor = classify_expected(competing_scores)
        available = result['complete'] and competitor['complete']
        recovered = available and result['recovered']
        old = taxon_saved.loc[species]
        close(result['mean'], float(old.expected_process_score), f'{species}/taxon score')
        close(competitor['mean'], float(old.competing_process_score_descriptive), f'{species}/competitor score')
        require(available == boolean(old.available) and recovered == boolean(old.recovered), 'taxon decision mismatch')
        require(result['positive_m_count'] == int(old.expected_process_positive_m_count), 'positive count mismatch')
        reason = ('recovered_positive_control' if recovered else
                  'prediction_adequacy_incomplete_across_M' if not available else
                  'nonpositive_expected_process_mean' if result['mean'] <= 0 else 'positive_M_count_below_two')
        taxon_rows.append({'lane': lane, 'species': species, 'expected_process': expected_process,
                           'mean_score_all_three_M': result['mean'],
                           'positive_finite_M_count': result['finite_positive_m_count'],
                           'missing_M_count': result['missing_m_count'],
                           'available': available, 'recovered': recovered, 'diagnosis': reason})
    candidates, cells, taxa = map(pd.DataFrame, (candidate_rows, cell_rows, taxon_rows))
    counts = {p: int(taxa.loc[taxa.expected_process.eq(p), 'recovered'].sum()) for p in PROCESSES}
    supported = bool(taxa.recovered.sum() >= 3 and min(counts.values()) >= 1)
    decision = data['decision.json']
    require(int(taxa.recovered.sum()) == decision['recovered_n'], 'recovered total mismatch')
    require(int((~taxa.available).sum()) == decision['unavailable_n'], 'availability total mismatch')
    require(supported == decision['supported'] and counts == decision['recovered_by_expected_process'], 'lane decision mismatch')
    receipt = {'source': {k: v for k, v in source.items() if k != 'labels'}, 'n_taxa': 4,
               'recovered_n': int(taxa.recovered.sum()), 'required_recovered_n': 3,
               'supported': supported, 'unavailable_n': int((~taxa.available).sum()),
               'recovered_by_expected_process': counts,
               'pipeline_cells_available': int(cells.pipeline_available.sum()), 'expected_cells': 12,
               'cells_without_prediction_adequate_candidates': int(cells.n_adequate.eq(0).sum()),
               'cells_with_comparable_expected_process': int(cells.expected_process_comparable.sum()),
               'expected_process_boundary_code_cells': int(cells.boundary_code_not_measured_loss.sum()),
               'raw_fold_rows': len(folds), 'nominal_fold_rows': 144,
               'candidate_cells_missing_a_requested_fold': int((~candidates.all_three_folds).sum()),
               'result_file_sha256': file_shas}
    return taxa, cells, candidates, receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plant-zip', type=Path, required=True)
    parser.add_argument('--nonplant-zip', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    results = [audit_lane(lane, getattr(args, lane + '_zip')) for lane in SOURCES]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for i, label in enumerate(('taxon', 'cell', 'candidate')):
        pd.concat([r[i] for r in results], ignore_index=True).to_csv(
            args.output_dir / f'real_positive_control_v1_{label}_audit.csv', index=False)
    receipt = {'audit': 'independent_recalculation_of_consumed_v1_results',
               'model_fitting_performed': False, 'raw_feature_tables_read': False,
               'new_outer_sealed_audit_performed': False, 'thresholds_changed': False,
               'joint_8_taxon_summary_is_descriptive_only': True,
               'lanes': dict(zip(SOURCES, [r[3] for r in results]))}
    (args.output_dir / 'real_positive_control_v1_audit.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(pd.concat([r[0] for r in results], ignore_index=True).to_string(index=False))
    print('AUDIT_PASS (does not mean scientific support)')


if __name__ == '__main__':
    main()
