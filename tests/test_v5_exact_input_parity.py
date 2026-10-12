"""Catch distinctions that an equal tree-model score cannot exclude."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'experiments/v5_exact_input_parity.py'
def module():
    assert SCRIPT.exists(), 'exact-input comparator is not implemented'
    spec=importlib.util.spec_from_file_location('exact_input_parity',SCRIPT)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def test_identical_values_with_different_memory_layout():
    m=module(); a=np.arange(12,dtype=float).reshape(4,3)
    b=np.asfortranarray(a)
    r=m.compare_arrays(a,b)
    assert r['same_values'] and r['same_bytes']
    assert r['a_c_contiguous'] and not r['b_c_contiguous']

def test_one_ulp_is_not_treated_as_identical():
    m=module();a=np.array([[1.,2.]])
    b=a.copy(); b[0,0]=np.nextafter(1.,2.)
    assert np.allclose(a,b)
    r=m.compare_arrays(a,b)
    assert not r['same_values'] and not r['same_bytes']
    assert r['changed_entries']==1 and r['max_absolute_difference']>0

def test_row_reordering_and_shape_mismatch_are_detected():
    m=module();a=np.array([[1.,2.],[3.,4.]])
    assert not m.compare_arrays(a,a[::-1])['same_values']
    assert not m.compare_arrays(a,a[:1])['same_shape']

def test_nonfinite_inputs_fail_closed():
    m=module()
    with pytest.raises(ValueError,match='finite'):
        m.compare_arrays(np.array([np.nan]),np.array([np.nan]))

def test_original_source_hash_validated_before_import(tmp_path):
    m=module();bad=tmp_path/'not_original.py'
    bad.write_text("raise AssertionError('must never run')")
    with pytest.raises(ValueError,match='source blob'):
        m.load_original_module(bad)
