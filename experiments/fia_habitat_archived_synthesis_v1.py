"""Deterministic, post-outcome FIA habitat synthesis of a frozen aggregate.

No individual tree access or inference of causal competition/moisture limitation.
All matched comparisons are descriptive statistics on selected live survivors.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

SOURCE_SHA256 = '2534ee724e177c15a9399b6d538f0cbdb765bfe018d21cc73ee2a9575917bb62'
STATES = ('RI', 'VA', 'WI')
SPECIES_CODES = ('68', '129', '261', '316', '318', '371', '531', '541', '743', '762', '802', '833', '837')
THRESHOLDS = (10, 20, 30, 50, 100)


def verify_source(path: Path) -> dict:
    b = path.read_bytes()
    if hashlib.sha256(b).hexdigest() != SOURCE_SHA256:
        raise ValueError('frozen source aggregate SHA-256 mismatch')
    result = json.loads(b)
    if result.get('study') != 'fia_habitat_structure_extension_v1':
        raise ValueError('unexpected source study')
    if not result.get('raw_tree_zip_source_hashes_verified') or not result.get('no_causal_moisture_limitation_or_growth_process_claim'):
        raise ValueError('source integrity and inference limits not certified')
    if [state.get('state') for state in result.get('states', [])] != list(STATES):
        raise ValueError('source states/order changed')
    for st in result['states']:
        observed = [sp['spcd'] for sp in st['species']]
        if observed != list(SPECIES_CODES) or len(set(observed)) != len(observed):
            raise ValueError('fixed 13 species/order changed')
    return result


def eligible_rows(states: list[dict], code: str, grouping: str, minimum: int) -> list[dict]:
    grouped = [next(x for x in state['species'] if x['spcd'] == code)[grouping] for state in states]
    if not all(isinstance(s, dict) for s in grouped):
        raise ValueError('invalid source group')
    rows = []
    for label in sorted(set().union(*(set(s) for s in grouped))):
        cells = [s.get(label) for s in grouped]
        if any(cell is None or cell['n'] < minimum for cell in cells):
            continue
        counts = [int(x['n']) for x in cells]
        vals = [float(x['mean_growth']) for x in cells]
        if any(n <= 0 for n in counts):
            raise ValueError('invalid cell count')
        rows.append({'stratum': label, 'counts': counts, 'means': vals})
    return rows


def standardized(rows: list[dict], strategy: str = 'pooled') -> dict:
    if strategy not in ('pooled', 'equal', 'balanced_min'):
        raise ValueError('unrecognized weighting strategy')
    if not rows:
        return {'n_common_strata': 0, 'n_source_pairs': 0, 'RI': None, 'VA': None, 'WI': None,
                'WI_minus_RI': None, 'WI_gt_RI': None, 'n_strata_WI_gt_RI': 0}
    w = [sum(d['counts']) if strategy == 'pooled' else 1 if strategy == 'equal' else min(d['counts']) for d in rows]
    total = sum(w)
    means = [sum(weight * row['means'][i] for weight, row in zip(w, rows)) / total for i in range(3)]
    return {'n_common_strata': len(rows), 'n_source_pairs': sum(sum(d['counts']) for d in rows),
            'RI': means[0], 'VA': means[1], 'WI': means[2],
            'WI_minus_RI': means[2]-means[0], 'WI_gt_RI': bool(means[2] > means[0]),
            'n_strata_WI_gt_RI': sum(row['means'][2] > row['means'][0] for row in rows)}


def within_state_mesic_xeric(states: list[dict], code: str, state: str, minimum: int = 10) -> dict:
    row = next(x for x in next(st for st in states if st['state'] == state)['species'] if x['spcd'] == code)
    pairs = defaultdict(dict)
    for label, item in row['size_age_density_physio'].items():
        *prefix, environment = label.split('|')
        if environment in ('mesic', 'xeric'):
            pairs['|'.join(prefix)][environment] = item
    included = []
    for name, group in sorted(pairs.items()):
        if set(group) != {'mesic', 'xeric'}:
            continue
        if min(group['mesic']['n'], group['xeric']['n']) < minimum:
            continue
        count = int(group['mesic']['n'] + group['xeric']['n'])
        included.append({'group':name, 'n':count,
                         'difference': group['mesic']['mean_growth'] - group['xeric']['mean_growth']})
    denom = sum(x['n'] for x in included)
    return {'state': state, 'spcd': code, 'n_common_groups': len(included),
            'n_matched_pairs': denom,
            'mesic_minus_xeric': sum(x['n']*x['difference'] for x in included)/denom if denom else None,
            'n_positive_groups': sum(x['difference']>0 for x in included)}


def _assert_old_metrics(source: dict):
    """Recalculate the published primary 10-per-state endpoint before sensitivity."""
    expected = {r['spcd']: r for r in source['matched_size_age_density']}
    expect_ph = {r['spcd']: r for r in source['matched_size_age_physiography']}
    for group, original in (('size_age_density', expected), ('size_age_physio', expect_ph)):
        for code in SPECIES_CODES:
            v = standardized(eligible_rows(source['states'], code, group, 10))
            old = original[code]
            if (v['n_common_strata'] != old['n_common_strata'] or
                    v['n_source_pairs'] != old['n_source_pairs_in_common_strata'] or
                    v['n_strata_WI_gt_RI'] != old['n_strata_WI_higher_RI'] or
                    v['WI_gt_RI'] != old['WI_higher_RI']):
                raise ValueError('original regional summary does not reproduce')
            for st in STATES:
                actual, prior = v[st], old['state_means'][st]
                if (actual is None) != (prior is None):
                    raise ValueError('original regional availability differs')
                if actual is not None and abs(actual - prior) > 1e-12:
                    raise ValueError('original regional growth does not reproduce')
    actual_mesic = {(z['spcd'], z['state']): z for z in source['mesic_minus_xeric_within_state_matched_density']}
    for code in SPECIES_CODES:
        for state in STATES:
            x = within_state_mesic_xeric(source['states'], code, state)
            y = actual_mesic[(code, state)]
            if (x['n_common_groups'] != y['n_common_stand_size_density_groups'] or
                    x['n_matched_pairs'] != y['sum_within_pairs']):
                raise ValueError('original physiographic denominator does not reproduce')
            if x['mesic_minus_xeric'] is not None and abs(x['mesic_minus_xeric']-y['mesic_minus_xeric_growth'])>1e-12:
                raise ValueError('original physiographic comparison does not reproduce')
            if (x['mesic_minus_xeric'] is None) != (y['mesic_minus_xeric_growth'] is None):
                raise ValueError('original physiographic missingness differs')


def summarize(source: dict) -> dict:
    _assert_old_metrics(source)
    panels = {}
    for grouping in ('size_age_density', 'size_age_physio'):
        scenarios = []
        for minimum in THRESHOLDS:
            rows = []
            for code in SPECIES_CODES:
                matches = eligible_rows(source['states'], code, grouping, minimum)
                row = {'spcd': code, 'min_n_each_state': minimum, 'pool': standardized(matches, 'pooled'),
                       'equal': standardized(matches, 'equal'), 'balanced_min': standardized(matches, 'balanced_min')}
                rows.append(row)
            eligible = [r for r in rows if r['pool']['n_common_strata'] > 0]
            scenarios.append({'min_n_per_state_stratum': minimum, 'eligible_species': len(eligible),
                              'WI_greater_RI_pooled': sum(r['pool']['WI_gt_RI'] for r in eligible),
                              'WI_greater_RI_equal_strata': sum(r['equal']['WI_gt_RI'] for r in eligible),
                              'WI_greater_RI_balanced_min': sum(r['balanced_min']['WI_gt_RI'] for r in eligible),
                              'n_shared_strata': sum(r['pool']['n_common_strata'] for r in eligible),
                              'n_shared_strata_WI_gt_RI': sum(r['pool']['n_strata_WI_gt_RI'] for r in eligible),
                              'rows': rows})
        panels[grouping] = scenarios
    phys = [within_state_mesic_xeric(source['states'], code, st) for code in SPECIES_CODES for st in STATES]
    avail = [x for x in phys if x['mesic_minus_xeric'] is not None]
    by_key = {(x['spcd'],x['state']):x for x in avail}
    cross = []
    for code in SPECIES_CODES:
        va, wi = by_key.get((code,'VA')), by_key.get((code,'WI'))
        if va and wi:
            cross.append({'spcd': code, 'VA_mesic_minus_xeric': va['mesic_minus_xeric'],
                          'WI_mesic_minus_xeric': wi['mesic_minus_xeric'],
                          'opposite_sign': va['mesic_minus_xeric']*wi['mesic_minus_xeric'] < 0})
    return {'study':'fia_habitat_archived_synthesis_v1',
            'source_file_sha256':SOURCE_SHA256,'n_fixed_species':len(SPECIES_CODES),'n_states':len(STATES),
            'regional_sensitivity':panels,
            'physiography':{'n_eligible_species_state':len(avail),
                 'mesic_greater_xeric':sum(x['mesic_minus_xeric'] > 0 for x in avail),
                 'region_counts': {s: {'estimable':sum(x['state']==s for x in avail),
                                      'positive':sum(x['state']==s and x['mesic_minus_xeric']>0 for x in avail)} for s in STATES},
                 'species_observed_in_VA_and_WI':len(cross),
                 'species_with_sign_reversal_VA_WI':sum(x['opposite_sign'] for x in cross),
                 'VA_WI_same_species':cross, 'all_species_states': phys},
            'claim_limit':'Retrospective source-verified live-survivor associations, not causal competition, measured soil water stress, physiological adaptation, forest-population growth or independent species replications.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    obj = summarize(verify_source(args.source))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True)+'\n', encoding='utf-8')
    base = obj['regional_sensitivity']['size_age_density'][0]
    ph = obj['physiography']
    print(f"source-verified: matched density WI>RI {base['WI_greater_RI_pooled']}/{base['eligible_species']}; "
          f"mesic>xeric {ph['mesic_greater_xeric']}/{ph['n_eligible_species_state']}; "
          f"dual-state sign reversals {ph['species_with_sign_reversal_VA_WI']}/{ph['species_observed_in_VA_and_WI']}")


if __name__ == '__main__':
    main()
