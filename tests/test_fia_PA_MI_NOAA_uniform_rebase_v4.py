"""All-five-state same-NOAA source-only rebasing; no biological response."""
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
import fia_PA_MI_NOAA_uniform_rebase_v4 as m


def cfg():
    return json.loads((ROOT/"configs/fia_PA_MI_NOAA_uniform_rebase_v4.json").read_text())


def plot_zip(state="RI"):
    z=io.BytesIO()
    with ZipFile(z,"w",ZIP_DEFLATED) as out:
        content=("CN,PREV_PLT_CN,STATECD,COUNTYCD,MEASYEAR,MEASMON,DIA,STATUSCD\n"
                 f"p0,,{int(m.FIPS[state])},001,2000,7,NOT_READ,NOT_READ\n"
                 f"p1,p0,{int(m.FIPS[state])},001,2010,7,NOT_READ,NOT_READ\n")
        out.writestr(f"{state}_PLOT.csv",content)
    return z.getvalue()


def plot_rows():
    return {
        "p0":("", "51001", (2000,7)),
        "p1":("p0", "51001", (2010,7))
    }


def climate():
    return {("51001",y,mn):(15.,3.)
            for y in range(1991,2026)
            for mn in range(4,10)}


def test_frozen_versions_and_geography():
    m.verify_contract(cfg())
    assert m.STATES==("RI","VA","WI")
    assert m.PROGRAM=="fia_source_only_all_five_states_NOAA_20261105_rebased_v4"
    assert m.NOAA_NEW_SHAS=={
        "temperature":"ea6a159d3ad9a25b60cce6e3889d79898e17cf4e29b3d2c2282d19d7fb073a4d",
        "precipitation":"1f21b2435a29cc40369a4666a69b4f6d851643bad2811f7b8f1bab6521217b27"}
    for name,v in (
        ("original_3state_PLOT_ZIP_SHA256",{"RI":"0","VA":"0","WI":"0"}),
        ("training_source_row_count_fixed",1),
        ("require_same_original_PLOT_zip_or_STOP",False),
        ("all_5_states_same_NOAA_20261105_historical_release",False),
        ("frozen_primary_five_codes",["316"])):
        x=cfg();x[name]=v
        with pytest.raises(ValueError,match="contract changed"):
            m.verify_contract(x)


def test_original_first_receipt_locks_every_source_plot_sha(tmp_path,monkeypatch):
    raw={"status":"source_only_pre_response",
         "states":[
           {"state":s,"plot_source":{"sha256":m.PLOT_ORIGINAL[s]},
            "no_tree_growth_or_status_read":True}
           for s in m.STATES]}
    path=tmp_path/"first_source_receipt.json"
    path.write_text(json.dumps(raw))
    monkeypatch.setattr(m,"OLD_FIRST_SOURCE_RECEIPT_SHA",hashlib.sha256(path.read_bytes()).hexdigest())
    m.verify_historical_receipt(path)
    raw["states"][0]["plot_source"]["sha256"]="modified"
    path.write_text(json.dumps(raw))
    monkeypatch.setattr(m,"OLD_FIRST_SOURCE_RECEIPT_SHA",hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError,match="original first source PLOT SHA"):
        m.verify_historical_receipt(path)


def test_exact_first_PLOT_archive_recovered_and_fields_restricted(tmp_path,monkeypatch):
    raw=plot_zip("RI")
    correct=hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(m,"PLOT_ORIGINAL",{**m.PLOT_ORIGINAL,"RI":correct})
    path,qc=m.fetch_PLOT("RI",tmp_path,fetcher=lambda st:raw)
    assert qc["status"]=="exact_original_first_source_PLOT_bytes_recovered"
    assert qc["current_SHA"]==correct
    assert m.plot_visit_dates(path,qc["member"],"RI")=={
       "p0":("", "44001", (2000,7)),
       "p1":("p0", "44001", (2010,7))}
    with pytest.raises(ValueError,match="cannot be re-established"):
        m.fetch_PLOT("RI",tmp_path,fetcher=lambda st:b"changed DataMart")
    with pytest.raises(ValueError,match="unknown original"):
        m.fetch_PLOT("PA",tmp_path,fetcher=lambda st:raw)


def test_rebase_same_source_plot_dates_and_all_rows(monkeypatch):
    monkeypatch.setattr(m,"EXPECTED_TRAIN_ROWS",1)
    r={"species_code":"129","state":"VA","county_fips":"51001",
       "plot_chain_id":"p0","interval_id":"p1","interval_end_year":2010,
       "temperature_anomaly_c":2.0,"precipitation_anomaly_mm":20.0}
    original=dict(r)
    out,qc=m.rebase_original_training([r],{"RI":{},"VA":plot_rows(),"WI":{}},
                                   climate(),{"51001":(15.,18.)})
    assert len(out)==1
    assert out[0]["species_code"]==r["species_code"]
    assert out[0]["interval_id"]==r["interval_id"]
    assert out[0]["plot_chain_id"]=="p0"
    assert out[0]["temperature_anomaly_c"]==pytest.approx(0.)
    assert out[0]["precipitation_anomaly_mm"]==pytest.approx(0.)
    assert qc["VA"]["n_identical_species_plot_interval_IDs"]==1
    assert qc["VA"]["n_revised_temperature_intervals"]==1
    assert qc["VA"]["n_revised_precipitation_intervals"]==1
    assert r==original


def test_rebase_refuses_any_changed_plot_root_or_county(monkeypatch):
    monkeypatch.setattr(m,"EXPECTED_TRAIN_ROWS",1)
    r={"species_code":"129","state":"VA","county_fips":"51001",
       "plot_chain_id":"NOT-P0","interval_id":"p1","interval_end_year":2010,
       "temperature_anomaly_c":0.,"precipitation_anomaly_mm":0.}
    with pytest.raises(ValueError,match="original plot/time/county/chain identity changed"):
        m.rebase_original_training([r],{"RI":{},"VA":plot_rows(),"WI":{}},
                                  climate(),{"51001":(15.,18.)})


def test_new_noaa_source_sha_missing_or_changed_is_a_hard_stop(tmp_path):
    for name in m.bridge.NOAA_FILES.values():
        (tmp_path/name).write_text("DRIFTED EDITION")
    with pytest.raises(ValueError,match="source SHA mismatch"):
        m.read_saved_NOAA(tmp_path)


def test_pa_mi_heldout_v3_source_shas_fail_closed(tmp_path):
    for name in ("PA_MI_20261105_external_source_only_climate.csv",
                 "PA_MI_NOAA_version_bridge_receipt_v3.json",
                 "PA_MI_NOAA_version_bridge_result_v3.json"):
        (tmp_path/name).write_text("{}")
    with pytest.raises(ValueError,match="new NOAA source SHA mismatch"):
        m.fixed_PA_MI_v3_source(tmp_path)


def test_only_source_fields_written_and_original_noaa_not_silently_overwritten(tmp_path):
    assert m.OUTPUT_COLS==(
      "species_code","state","county_fips","plot_chain_id","interval_id",
      "interval_end_year","temperature_anomaly_c","precipitation_anomaly_mm")
    assert "DIA" not in m.OUTPUT_COLS and "STATUSCD" not in m.OUTPUT_COLS
    row={"species_code":"129","state":"VA","county_fips":"51001",
       "plot_chain_id":"p0","interval_id":"p1","interval_end_year":2010,
       "temperature_anomaly_c":0.4,"precipitation_anomaly_mm":16.}
    new=m.write_source_csv(tmp_path/"source.csv",[row])
    assert new==hashlib.sha256((tmp_path/"source.csv").read_bytes()).hexdigest()
    assert "growth" not in (tmp_path/"source.csv").read_text().lower()
