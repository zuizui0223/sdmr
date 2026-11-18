"""Source-pinned descriptive 2-by-2 density x physiographic-class contrasts.

No individual-tree data are downloaded. Only the original archived FIA
live-to-live stratum counts and mean annualized log-diameter increments enter.
A difference in differences between groups is *not* a causal interaction.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ARCHIVE_SHA256 = '2534ee724e177c15a9399b6d538f0cbdb765bfe018d21cc73ee2a9575917bb62'
SPECIES = ('68', '129', '261', '316', '318', '371', '531', '541', '743', '762', '802', '833', '837')
STATES = ('RI', 'VA', 'WI')
DENSITY_PAIRS = (('0-<60', '60-<120'), ('60-<120', '120+'), ('0-<60', '120+'))
THRESHOLDS = (10, 20, 30, 50, 100)
PHYS = ('xeric', 'mesic')


def load_verified_source(path: Path) -> dict:
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('Source SHA-256 drift: do not substitute different FIA outcomes')
    obj = json.loads(content)
    if obj.get('study') != 'fia_habitat_structure_extension_v1':
        raise ValueError('Wrong frozen FIA source analysis')
    if not obj.get('raw_tree_zip_source_hashes_verified') or not obj.get('no_causal_moisture_limitation_or_growth_process_claim'):
        raise ValueError('Original source verification and inference ceiling required')
    if tuple(s['state'] for s in obj.get('states', [])) != STATES:
        raise ValueError('RI VA WI source universe changed')
    for s in obj['states']:
        if tuple(r['spcd'] for r in s['species']) != SPECIES:
            raise ValueError('Original 13 taxa changed or reordered')
    # Re-derive all published source primary denominators, not just file hash.
    mod_path = Path(__file__).with_name('fia_habitat_archived_synthesis_v1.py')
    if mod_path.exists():
        spec = importlib.util.spec_from_file_location('fia_archive_original_audit', mod_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module._assert_old_metrics(obj)
    return obj


def _four_cell_table(state: dict, code: str) -> dict[tuple[str, str], dict]:
    species = next(row for row in state['species'] if row['spcd'] == code)
    groups: dict[tuple[str, str], dict] = defaultdict(dict)
    for label, item in species['size_age_density_physio'].items():
        parts = label.split('|')
        if len(parts) != 4:
            raise ValueError('Malformed size|age|density|physio cell')
        size, age, density, phys = parts
        if density not in {'0-<60', '60-<120', '120+'} or phys not in {'xeric','mesic','hydric'}:
            raise ValueError('Unexpected FIA categories')
        n = item.get('n')
        mean = item.get('mean_growth')
        if type(n) is not int or n < 0 or (n and not isinstance(mean, (float,int))) or (n and not math.isfinite(float(mean))):
            raise ValueError('Invalid stratum count or mean')
        key = (density, phys)
        if key in groups[(size,age)]:
            raise ValueError('Duplicate source stratum')
        groups[(size,age)][key] = {'n':n,'mean_growth':float(mean) if n else None}
    return groups


def compute_panel(source: dict, min_per_cell: int = 10) -> dict:
    """Require all FOUR source cells within same species,state,size,age.

    mesic_minus_xeric moderation = (high-low in mesic) - (high-low in xeric).
    Positive means the adverse high-density difference is weaker in mesic.
    Multiple strata from one species/plot are *not* independent replicates.
    """
    if min_per_cell < 1:
        raise ValueError('minimum four-cell support must be positive')
    all_contrasts = []
    for lower, higher in DENSITY_PAIRS:
        strata = []
        species_states = []
        for state in source['states']:
            for code in SPECIES:
                cells = _four_cell_table(state, code)
                kept = []
                for (size, age), cell in sorted(cells.items()):
                    keys = [(d, p) for d in (lower,higher) for p in PHYS]
                    if not all(k in cell and cell[k]['n'] >= min_per_cell for k in keys):
                        continue
                    n = {f'{d}|{p}':cell[(d,p)]['n'] for d,p in keys}
                    # Contrasts share a four-cell denominator; no missing rows are imputed.
                    xeric = cell[(higher,'xeric')]['mean_growth'] - cell[(lower,'xeric')]['mean_growth']
                    mesic = cell[(higher,'mesic')]['mean_growth'] - cell[(lower,'mesic')]['mean_growth']
                    diff = mesic-xeric
                    kept.append({'stratum':size+'|'+age,'n_by_density_physiography':n,
                                'minimum_source_count':min(n.values()),
                                'n_observed_links_in_four_cells':sum(n.values()),
                                'high_minus_low_xeric':xeric,
                                'high_minus_low_mesic':mesic,
                                'mesic_minus_xeric_density_interaction':diff,
                                'both_contexts_crowding_negative':xeric < 0 and mesic < 0})
                if kept:
                    # Min-four-cell weights down-weight grossly imbalanced contexts.
                    weights = [z['minimum_source_count'] for z in kept]
                    wt = sum(weights)
                    d = sum(w * z['mesic_minus_xeric_density_interaction'] for w,z in zip(weights,kept))/wt
                    species_states.append({'state':state['state'],'spcd':code,
                        'n_qualifying_size_age_strata':len(kept),
                        'n_source_links_in_matched_cells':sum(z['n_observed_links_in_four_cells'] for z in kept),
                        'min_four_cell_weighted_interaction':d,
                        'interaction_positive':d>0,
                        'n_positive_interaction_strata':sum(z['mesic_minus_xeric_density_interaction']>0 for z in kept),
                        'n_both_crowding_negative':sum(z['both_contexts_crowding_negative'] for z in kept)})
                    strata.extend({'state':state['state'],'spcd':code,**z} for z in kept)
        by_state={s:{'eligible_species':sum(z['state']==s for z in species_states),
                     'mesic_weaker_density_penalty':sum(z['state']==s and z['interaction_positive'] for z in species_states)} for s in STATES}
        all_contrasts.append({'lower_density':lower,'higher_density':higher,
            'n_matched_four_cell_size_age_strata':len(strata),
            'n_strata_both_contexts_crowding_negative':sum(z['both_contexts_crowding_negative'] for z in strata),
            'n_xeric_strata_high_density_growth_lower':sum(z['high_minus_low_xeric']<0 for z in strata),
            'n_mesic_strata_high_density_growth_lower':sum(z['high_minus_low_mesic']<0 for z in strata),
            'n_mesic_weaker_strata':sum(z['mesic_minus_xeric_density_interaction']>0 for z in strata),
            'n_xeric_weaker_strata':sum(z['mesic_minus_xeric_density_interaction']<0 for z in strata),
            'n_species_states':len(species_states),
            'n_species_states_mesic_weaker_penalty':sum(z['interaction_positive'] for z in species_states),
            'by_state':by_state,'species_states':species_states,'strata':strata})
    return {'minimum_per_each_of_four_cells':min_per_cell,'density_pairs':all_contrasts}


def across_states_same_stratum(panel: dict, effect_cutoffs: tuple[float, ...] = (0.0, 0.001, 0.002)) -> dict:
    """Require eight complete four-cell groups: same species,size,age in VA and WI.

    Effect-size cutoffs are retrospective sensitivity, not significance tests.
    The RI row is not imputed as zero when it has no matched quadrants.
    """
    out = []
    for contrast in panel['density_pairs']:
        lookup: dict[tuple[str,str],dict] = defaultdict(dict)
        for r in contrast['strata']:
            lookup[(r['spcd'],r['stratum'])][r['state']] = r
        common = []
        for (sp,st),records in sorted(lookup.items()):
            if not all(k in records for k in ('VA','WI')):
                continue
            av = records['VA']['mesic_minus_xeric_density_interaction']
            wi = records['WI']['mesic_minus_xeric_density_interaction']
            common.append({'spcd':sp,'size_age_stratum':st,
                           'VA_interaction':av,'WI_interaction':wi,
                           'moderation_sign_reversal':bool(av*wi<0)})
        sensitivity=[]
        for cutoff in effect_cutoffs:
            if cutoff<0:raise ValueError('Invalid retrospective effect threshold')
            eligible=[r for r in common if min(abs(r['VA_interaction']),abs(r['WI_interaction']))>=cutoff]
            sensitivity.append({'absolute_interaction_in_both_states_at_least':cutoff,
                                'n_same_size_age_eight_cell_comparisons':len(eligible),
                                'n_opposite_moderation_sign':sum(x['moderation_sign_reversal'] for x in eligible)})
        out.append({'lower_density':contrast['lower_density'],'higher_density':contrast['higher_density'],
                    'n_same_size_age_eight_cell_comparisons':len(common),
                    'n_species_in_comparison':len({v['spcd'] for v in common}),
                    'n_opposite_moderation_sign':sum(v['moderation_sign_reversal'] for v in common),
                    'retrospective_magnitude_sensitivity':sensitivity,
                    'all_complete_eight_cell_comparisons':common})
    return {'paired_states':['VA','WI'],
            'identical_specimens_or_plots_across_states':False,
            'exactly_matching_size_age_and_four_source_density_physiography_cells':True,
            'not_statistically_independent':True,
            'comparisons':out}


def summarize(source: dict) -> dict:
    panels = [compute_panel(source,n) for n in THRESHOLDS]
    return {'study':'fia_density_x_physiography_moderation_v1',
      'source_fia_aggregate_sha256':ARCHIVE_SHA256,'status':'retrospective_associational_four_cell_interaction',
      'fixed_states':list(STATES),'fixed_taxa':list(SPECIES),'minimum_cell_support_sensitivity':list(THRESHOLDS),
      'contrast_definition':'(mesic high-density minus mesic low-density growth) minus (xeric high-density minus xeric low-density growth)',
      'interpretation':'positive: lower crowding penalty in mesic; negative: lower crowding penalty in xeric. This is descriptive moderation, not a causal competition-water interaction.',
      'threshold_panels':panels,
      'matched_across_states_eight_cell_sensitivity':[across_states_same_stratum(p) for p in panels],
      'causal_climate_claim_authorized':False,
      'limits':['FIA physiography is not measured soil moisture or annual drought exposure',
         'Basal area is not randomized and may correlate with site quality, management and tree size',
         'Aggregated strata do not contain plot IDs, repeated-tree residual variance or design weights',
         'Trees are conditional on survival and reobservation; cannot infer mortality or population responses',
         'Multiple matched strata and repeated species-state pairs are dependent, no p-values authorized',
         'This is post-outcome reuse of the previously opened FIADB response, not a prospective confirmation',
         'Fine-scale climate must not be joined to public fuzzed and swapped plot coordinates uncritically']}


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    obj=summarize(load_verified_source(a.source))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(obj,sort_keys=True,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    for panel in obj['threshold_panels'][:3]:
        print('min_cell',panel['minimum_per_each_of_four_cells'])
        for x in panel['density_pairs']:
            print(x['lower_density'],'to',x['higher_density'], 'four-cell n',x['n_matched_four_cell_size_age_strata'],
                  'both negative',x['n_strata_both_contexts_crowding_negative'],
                  'mesic weaker',x['n_mesic_weaker_strata'], 'species-state n',x['n_species_states'])

if __name__=='__main__':main()
