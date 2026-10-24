"""Technical size-cap successor for the unchanged predeclared Wisconsin FIA arm.

Original v1's 135 MB limit made WI unavailable BEFORE ANY biological outcomes.
This source-only successor raises the archive byte cap but changes no tree
identity-link or taxon candidate rules. It is not a novel independent test.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tree_gate',HERE/'geographic_tree_demography_source_gate_v1.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-receipt',type=Path,default=Path('evidence/geographic_tree_demography_source_gate_v1/fia_ri_va_wi_identity_linkages.json'))
    parser.add_argument('--output',type=Path,default=Path('artifacts/fia_wi_capacity_successor_v2.json'))
    args=parser.parse_args()
    raw=args.source_receipt.read_bytes();old=json.loads(raw)
    prior=old.get('fia',{}).get('states')
    if [x['state'] for x in prior]!=list(gate.FIA_STATES):
        raise ValueError('Only exact archived RI VA WI cohort can be continued')
    if prior[-1]['status']!='source_invalid' or prior[-1].get('error')!='archive_above_predeclared_size_limit':
        raise ValueError('No source-cap technical stop to recover')
    if any(s['status']!='ready' for s in prior[:2]):
        raise ValueError('RI/VA must be source-complete in frozen receipt')
    gate.MAX_ARCHIVE_BYTES=310_000_000
    gate.MAX_UNCOMPRESSED_BYTES=3_500_000_000
    with tempfile.TemporaryDirectory(prefix='wi_fia_source_') as tmp:
        wi=gate.process_state_zip('WI',Path(tmp))
    states=prior[:2]+[wi]
    out={"analysis":"fia_wi_source_cap_successor_v2","source_receipt_sha256":hashlib.sha256(raw).hexdigest(),
         "preserved_same_states":[s['state'] for s in states],
         "old_archive_byte_cap":135_000_000,"new_archive_byte_cap":310_000_000,
         "technical_only_successor_no_demographic_outcome":True,
         "eligible_species":gate.nominate_cross_state_species(states),"states":states,
         "no_selected_state_or_species_replacement":True,
         "new_result_does_not_rewrite_v1":True}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
    print('WI successor:',wi['status'],'links:',wi.get('n_strict_forward_same_species_links'),
          'candidate species across states:',out['eligible_species']['n_candidate_spcd'])

if __name__=='__main__':main()
