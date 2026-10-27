"""FIA taxonomy and technical source successor are separately auditable."""
import importlib.util
import io
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import pytest

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'experiments/geographic_tree_demography_fia_crosswalk_v1.py'
spec=importlib.util.spec_from_file_location('fia_ref',p)
ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)


def _reference():
    out=io.BytesIO()
    with ZipFile(out,'w',compression=ZIP_DEFLATED) as z:
        z.writestr('REF_SPECIES.csv',
        'SPCD,GENUS,SPECIES,SCIENTIFIC_NAME,COMMON_NAME\n'
        '316,Acer,rubrum,Acer rubrum,red maple\n'
        '832,Quercus,rubra,Quercus rubra,northern red oak\n')
    return out.getvalue()


def test_ref_names_are_public_source_not_invented():
    r,details=ref.parse_reference_zip(_reference())
    assert r['316']['scientific_name']=='Acer rubrum'
    assert r['832']['scientific_name']=='Quercus rubra'
    assert details['n_raw_reference_rows']==2


def test_different_decimal_spcd_string_maps_same_source_identity():
    assert ref.canonical_code('316.0')=='316'
    assert ref.canonical_code(316)==ref.canonical_code('316.00')
    with pytest.raises(ValueError,match='invalid species code'):
        ref.canonical_code('316.1')
    with pytest.raises(ValueError):ref.canonical_code('NA')


def test_unmatched_codes_remain_declared_unmatched():
    source={'fia':{'eligible_species':{'not_proof_of_survival_growth_or_native_species':True,
          'candidate_spcd':[{'spcd':'316.0','n_supported_states':2,'links_by_state':{'RI':35,'VA':50}},
                            {'spcd':'999.0','n_supported_states':2,'links_by_state':{'RI':60,'VA':60}}]}}}
    result=ref.candidate_crosswalk(source,ref.parse_reference_zip(_reference())[0])
    assert result['n_matched']==1
    assert result['taxa'][1]['status']=='unmatched_official_reference'
    assert 'scientific_name' not in result['taxa'][1]
    assert result['not_response_inference']


def test_reference_download_stub_is_checked():
    raw,status=ref.download_reference(downloader=lambda _: _reference())
    assert status['status']=='ready' and raw[:2]==b'PK'
    raw,status=ref.download_reference(downloader=lambda _: b'not a zip')
    assert raw is None and status['status']=='source_invalid'
