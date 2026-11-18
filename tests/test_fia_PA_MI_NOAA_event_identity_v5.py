"""PA/MI v5: same selected 89616 events or STOP, no biology at all."""
from __future__ import annotations
import hashlib
import io
import json
import sys
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_PA_MI_NOAA_event_identity_v5 as m


def conf():
    return json.loads((ROOT/"configs/fia_PA_MI_NOAA_event_identity_v5.json").read_text())


def old_new_climate():
    old={}
    new={}
    for y in range(1991,2026):
        for mo in (4,5,6,7,8,9):
            k=("51001",y,mo)
            old[k]=(10.,2.)
            new[k]=(12. if y==2005 else 10.,3. if y==2005 else 2.)
    return old,new,{"51001":m._old_baseline(new)["51001"]}


def old_row():
    return {"species_code":"129","state":"VA","county_fips":"51001",
            "plot_chain_id":"v0","interval_id":"v1","interval_end_year":2010,
            "temperature_anomaly_c":0.,"precipitation_anomaly_mm":0.}


def visit():
    return {"RI":{},"VA":{"v0":("", "51001",(2000,7)),
                           "v1":("v0","51001",(2010,7))},"WI":{}}


def test_v5_separate_from_v4_locked_full_raw_SHA_failure():
    c=conf()
    m.verify(c)
    assert m.PROGRAM=="fia_five_state_NOAA_20261105_event_identity_verified_source_only_v5"
    assert m.V4_PLOT_SOURCE_STOP_RUN==44294243344
    assert m.V4_RAW_RI_PLOT_ARTIFACT==14421539704
    assert len(m.OLD_RAW_RI_UPDATED_SHA)==64
    assert c["not_the_original_FIA_PLOT_source_version"]
    assert c["require_all_original_plot_interval_records_old_NOAA_reconstructed"]
    assert c["no_TREE_COND_or_biological_outcome_access"]


def test_ineligible_changed_scientific_contract_refused():
    c=conf()
    for key,val in [
      ("training_source_row_count",1),
      ("no_TREE_COND_or_biological_outcome_access",False),
      ("require_all_original_plot_interval_records_old_NOAA_reconstructed",False),
      ("v4_RI_updated_PLOT_zip_sha256","0"*64),
      ("no_automatic_repeat_or_replacement",False),
    ]:
        changed=dict(c);changed[key]=val
        with pytest.raises(ValueError,match="unfrozen event-identity"):
            m.verify(changed)


def test_verifies_original_old_climate_before_rebased_exposure(monkeypatch):
    monkeypatch.setattr(m,"TRAIN_N",1)
    old,new,base=old_new_climate()
    out,stats=m.rebase_all([old_row()],visit(),old,new,base)
    assert len(out)==1
    assert out[0]["species_code"]=="129"
    assert out[0]["county_fips"]=="51001"
    assert out[0]["interval_id"]=="v1"
    assert out[0]["temperature_anomaly_c"]!=pytest.approx(0)
    assert out[0]["precipitation_anomaly_mm"]!=pytest.approx(0)
    assert stats["VA"]["n_original_plot_interval_trees_species_identity_matched"]==1
    assert stats["VA"]["n_updated_temperature_anomaly_intervals"]==1
    assert stats["VA"]["n_updated_precipitation_anomaly_intervals"]==1


@pytest.mark.parametrize("change",[
    {"plot_chain_id":"WRONG"},
    {"county_fips":"51003"},
    {"interval_id":"not original"},
    {"interval_end_year":2011},
    {"temperature_anomaly_c":.25},
    {"precipitation_anomaly_mm":3.},
])
def test_every_old_identity_and_climate_must_be_reproducible_or_fail(monkeypatch,change):
    monkeypatch.setattr(m,"TRAIN_N",1)
    old,new,base=old_new_climate()
    row=old_row();row.update(change)
    with pytest.raises(ValueError):
        m.rebase_all([row],visit(),old,new,base)


def test_duplicate_old_13_taxon_interval_not_treated_as_replication(monkeypatch):
    monkeypatch.setattr(m,"TRAIN_N",2)
    old,new,base=old_new_climate()
    with pytest.raises(ValueError,match="duplicate original source interval"):
        m.rebase_all([old_row(),old_row()],visit(),old,new,base)


def test_fetch_only_paused_updated_va_wi_plots_no_tree(tmp_path):
    buffer=io.BytesIO()
    with ZipFile(buffer,"w",ZIP_DEFLATED) as z:
        z.writestr("VA_PLOT.csv","CN,PREV_PLT_CN,STATECD,COUNTYCD,MEASYEAR,MEASMON\n")
    raw=buffer.getvalue()
    path,meta=m.fetch_PLOT_new("VA",tmp_path,reader=lambda _ :raw)
    assert path.name=="VA_PLOT.zip"
    assert meta["sha256"]==hashlib.sha256(raw).hexdigest()
    assert meta["state"]=="VA"
    assert meta["same_full_source_SHA_as_old"] is False
    with pytest.raises(ValueError,match="VA/WI PLOT"):
        m.fetch_PLOT_new("RI",tmp_path,reader=lambda _:raw)


def test_old_baseline_preserves_180_six_months_or_stops():
    old,_,_=old_new_climate()
    assert m._old_baseline(old)=={"51001":(10.,12.)}
    with pytest.raises(ValueError,match="old NOAA baseline source incomplete"):
        m._old_baseline({k:v for i,(k,v) in enumerate(old.items()) if i!=0})


def test_old_training_SHA_precheck_prevents_new_FIA_first_open(tmp_path):
    old=tmp_path/"old";old.mkdir()
    (old/"fia_new_cohort_joint_source_only_county_stable_v2.csv").write_text("tampered")
    (old/"derived_receipt.json").write_text("tampered")
    calls=[]
    def forbidden(st):
        calls.append(st)
        raise AssertionError("cannot GET when first source isn't verified")
    with pytest.raises(ValueError):
        m.run(tmp_path/"out",old,tmp_path/"noaa.csv",tmp_path/"noaa_raw",
              tmp_path/"external",tmp_path/"RI_PLOT.zip",
              ROOT/"configs/fia_PA_MI_NOAA_event_identity_v5.json",
              ROOT/"configs/fia_joint_climate_support_gate_v1.json",fetcher=forbidden)
    assert calls==[]
