"""Offline complete-source FIA PLOT and COND gate tests."""
import csv
import io
import importlib.util
from pathlib import Path
import zipfile
import pytest

SCRIPT=Path(__file__).parents[1]/"experiments"/"fia_plot_condition_source_gate_v1.py"
s=importlib.util.spec_from_file_location("fia_plot_condition_source_gate_v1", SCRIPT)
mod=importlib.util.module_from_spec(s);s.loader.exec_module(mod)


def make_zip(name, data):
    output=io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        z.writestr(name, data)
    return output.getvalue()


def fixture(state, table):
    if table=="PLOT":
        return make_zip(f"{state}_PLOT.csv", "CN,PREV_PLT_CN,INVYR,MEASYEAR,MEASMON,PLOT_STATUS_CD\n"
                        "p1,,2012,2011,6,1\np2,p1,2017,2017,8,1\n"
                        "p3,p2,2022,2021,11,1\np4,,2020,,4,2\n")
    if table=="COND":
        return make_zip(f"{state}_COND.csv", "PLT_CN,CONDID,STDAGE,STDORGCD,COND_STATUS_CD,CONDPROP_UNADJ,FORTYPCD,STDSZCD,DSTRBCD1\n"
                        "p1,1,40,0,1,1,502,3,0\np2,1,50,1,1,1,502,3,0\n"
                        "p3,1,-999,,1,1,503,2,0\np4,1,50,0,2,1,503,2,0\n")
    raise KeyError(table)


def test_complete_three_state_source_and_no_tree_outcomes():
    d=mod.run(fetcher=fixture)
    assert d["n_states_complete"]==3
    assert d["first_measurement_growth_or_survival_refitted"] is False
    for s in d["states"]:
        p=s["plot_validation"]
        assert p["n_source_plots"]==4
        assert p["n_invyr_measyear_disagree"]==2
        assert p["n_internal_previous_plot_links"]==2
        assert p["n_forward_links_with_interval_disagreement"]==2
        c=s["condition_validation"]["condition_qc"]
        assert c["forest_condition_with_plot"]==3
        assert c["forest_age_valid"]==2
        assert c["forest_natural_origin"]==1
        assert c["forest_artificial_origin"]==1


def test_reject_cohort_mutation():
    with pytest.raises(ValueError,match="must be RI VA WI"):
        mod.run(states=("VA","WI","RI"),fetcher=fixture)


def test_missing_plot_fails_not_zeros():
    def bad(state,table):
        if state=="RI" and table=="PLOT":return b"not a zip"
        return fixture(state,table)
    d=mod.run(fetcher=bad)
    assert d["n_states_complete"]==2
    assert d["states"][0]["status"]=="unavailable"
    assert "plot_validation" not in d["states"][0]


def test_bad_cond_schema_rejected():
    def bad(state,table):
        if state=="RI" and table=="COND":return make_zip("RI_COND.csv","PLT_CN,CONDID\np1,1\n")
        return fixture(state,table)
    d=mod.run(fetcher=bad)
    assert d["n_states_complete"]==2
    assert "COND missing" in d["states"][0]["reason"]


def test_duplicate_condition_key_blocks():
    def dup(state,table):
        if state=="RI" and table=="COND":
            return make_zip("RI_COND.csv","PLT_CN,CONDID,STDAGE,STDORGCD,COND_STATUS_CD\np1,1,10,0,1\np1,1,20,0,1\n")
        return fixture(state,table)
    d=mod.run(fetcher=dup)
    assert "duplicate condition key" in d["states"][0]["reason"]


def test_unmatched_condition_retained_as_unmatched_not_imputed():
    def changed(state,table):
        if state=="RI" and table=="COND":
            return make_zip("RI_COND.csv","PLT_CN,CONDID,STDAGE,STDORGCD,COND_STATUS_CD\nx1,1,25,0,1\n")
        return fixture(state,table)
    d=mod.run(fetcher=changed)
    assert d["states"][0]["condition_validation"]["condition_qc"]["condition_without_plot"]==1


def test_year_fields_do_not_silently_assume_invyr_actual():
    assert mod._year("9999") is None
    assert mod._year("2020")==2020
    assert mod._age("-999") is None
    assert mod._age("70")==70


def test_archive_requires_exact_member():
    def wrong(state,table):
        if state=="RI" and table=="PLOT":return make_zip("unexpected.csv","content")
        return fixture(state,table)
    d=mod.run(fetcher=wrong)
    assert d["n_states_complete"]==2
    assert "missing_or_ambiguous_table_member" in d["states"][0]["plot"]["reason"]
