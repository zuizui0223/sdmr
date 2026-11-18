"""PA/MI external holdout source-only controls: NO biological outcomes."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import fia_external_PA_MI_first_source_v1 as m


def cfg():
    return json.loads((ROOT/"configs/fia_PA_MI_external_source_only_v1.json").read_text())


def climatecfg():
    return json.loads((ROOT/"configs/fia_joint_climate_support_gate_v1.json").read_text())


def source_row(sp,state,county,plot,year=2010,t=0.2,p=20.):
    return {"species_code":sp,"state":state,"county_fips":county,
            "plot_chain_id":plot,"interval_id":"i-"+plot,
            "interval_end_year":year,"temperature_anomaly_c":t,
            "precipitation_anomaly_mm":p}


def source_panel():
    train=[]
    for state,prefix in (("RI","44"),("VA","51"),("WI","55")):
        for sp in m.PRIOR_13:
            # Two well-supported joint climate/time cells per state.
            for n in range(1,7):
                for j in range(5):
                    band=n%2
                    train.append(source_row(sp,state,f"{prefix}{n:03d}",
                        f"{sp}_{state}_{n}_{j}",2010,0.2+2*band,20+200*band))
    holdout=[]
    for state,prefix in (("PA","42"),("MI","26")):
        for n in range(1,7):
            for j in range(5):
                band=n%2
                holdout.append(source_row("129",state,f"{prefix}{n:03d}",
                    f"129_{state}_{n}_{j}",2010,0.2+2*band,20+200*band))
    return train,holdout


def make_zip(member,header,rows):
    buffer=io.BytesIO()
    with ZipFile(buffer,"w",ZIP_DEFLATED) as z:
        f=io.StringIO(newline="")
        wr=csv.writer(f,lineterminator="\n")
        wr.writerow(header)
        wr.writerows(rows)
        z.writestr(member,f.getvalue())
    return buffer.getvalue()


def test_first_external_holdouts_and_noaa_crosswalk_frozen():
    c=cfg()
    m.validate_settings(c)
    assert m.STATES==("PA","MI") and m.TRAIN_STATES==("VA","WI")
    assert m.NOAA_ORDINAL=={"36":"42","20":"26"}
    assert m.FIPS=={"PA":"42","MI":"26"}
    assert m.PRIOR_5==("129","316","802","833","837")
    assert len(m.PRIOR_13)==13
    assert c["no_automatic_retries"]
    assert c["source_only_no_tree_outcomes"] and c["product_B_blocked"]


def test_altering_model_selection_or_state_fails_closed():
    c=cfg()
    for key,bad in (("holdout_states",["RI","MI"]),
                    ("ncei_ordinal_to_fips",{"20":"42","36":"26"}),
                    ("source_training_csv_sha256","0"*64),
                    ("prior_primary_five",["129"]),
                    ("no_automatic_retries",False),
                    ("min_holdout_counties",3),
                    ("minimum_holdout_coverage",0.1)):
        cc=dict(c);cc[key]=bad
        with pytest.raises(ValueError,match="unfrozen|thresholds"):
            m.validate_settings(cc)


def test_training_cells_ignore_holdouts_and_preserve_all_13():
    train,holdout=source_panel()
    res=m.compare_train_holdout(train,holdout,climatecfg())
    assert res["source_species_denominator"]==13
    assert len(res["source_species"])==13
    q=next(z for z in res["source_species"] if z["species_code"]=="129")
    assert q["n_train_VA_WI_common_climate_time_cells"]==2
    assert q["both_holdout_states_source_eligible"]
    assert q["holdouts"]["PA"]["n_counties"]==6
    assert q["holdouts"]["MI"]["n_unique_plot_chains"]==30
    assert q["holdouts"]["PA"]["train_bin_plot_coverage_fraction"]==1.0
    assert res["n_primary_both_holdout_states_source_eligible"]==1
    empty=next(z for z in res["source_species"] if z["species_code"]=="316")
    assert empty["holdouts"]["PA"]["train_bin_plot_coverage_fraction"] is None
    assert not empty["both_holdout_states_source_eligible"]
    assert res["n_independent_biological_effect_tests"]==0
    shifted=[dict(r,temperature_anomaly_c=50.) for r in holdout]
    s=m.compare_train_holdout(train,shifted,climatecfg())
    assert s["source_species"][1]["n_train_VA_WI_common_climate_time_cells"]==q["n_train_VA_WI_common_climate_time_cells"]
    assert s["n_primary_both_holdout_states_source_eligible"]==0


def test_holdout_source_TREES_inspect_only_prior_species_not_current_growth(tmp_path):
    plots=make_zip("PA_PLOT.csv",
        ("CN","PREV_PLT_CN","STATECD","COUNTYCD","MEASYEAR","MEASMON"),
        [("p0","","42","001","2000","07"),("p1","p0","42","001","2010","07"),
         ("q0","","42","003","2001","07"),("q1","q0","42","005","2011","07")])
    trees=make_zip("PA_TREE.csv",
        ("SPCD","PLT_CN","DIA","STATUSCD"),
        [(129,"p0","THIS_IS_NOT_A_VALID_DIAMETER","DEAD"),
         (316,"p0","UNKNOWN","UNTRUSTWORTHY"),
         (802,"q0","10","1")])
    pp=tmp_path/"PA_PLOT.zip";pp.write_bytes(plots)
    tt=tmp_path/"PA_TREE.zip";tt.write_bytes(trees)
    p,roots,qc=m.plot_source(pp,"PA_PLOT.csv","PA")
    assert qc["counts"]["whole_chains_with_missing_or_unstable_county"]==1
    climate={( "42001",year,mo):(10.,20.) for year in range(2000,2011) for mo in range(4,10)}
    baseline={"42001":(9.,100.)}
    rows,audit=m.source_state("PA",p,roots,qc["unstable_plot_chains"],tt,
                              "PA_TREE.csv",climate,baseline)
    assert {x["species_code"] for x in rows}=={"129","316"}
    assert len(rows)==2
    assert all(z["county_fips"]=="42001" for z in rows)
    assert audit["no_status_DIA_growth_mortality_evaluated"]
    assert audit["plot_eligibility"]["plot_chain_county_unstable_excluded"]==1


def test_cond_schema_header_only_does_not_parse_basal_area(tmp_path):
    raw=make_zip("MI_COND.csv",
         ("PLT_CN","CONDID","COND_STATUS_CD","STDAGE","BALIVE"),
         [("p0","1","1","CORRUPT_SOURCE_AGE","THIS_IS_NOT_A_REAL_DENSITY")])
    dest=tmp_path/"MI_COND.zip";dest.write_bytes(raw)
    q=m.inspect_cond_source_header(dest,"MI_COND.csv")
    assert q==sorted(["PLT_CN","CONDID","COND_STATUS_CD","STDAGE","BALIVE"])


def test_holdout_zip_identity_and_refuse_wrong_table(tmp_path):
    raw=make_zip("PA_TREE.csv",("PLT_CN","SPCD"),[("p0","129")])
    path,receipt=m.fetch_fia_zip("PA","TREE",tmp_path,fetcher=lambda state,table:raw)
    assert receipt["zip_sha256"]==hashlib.sha256(raw).hexdigest()
    assert receipt["csv_member"]=="PA_TREE.csv"
    assert path.exists()
    with pytest.raises(ValueError,match="predeclared"):
        m.fetch_fia_zip("VA","TREE",tmp_path,fetcher=lambda *_:raw)
    with pytest.raises(ValueError,match="predeclared"):
        m.fetch_fia_zip("MI","DEATH",tmp_path,fetcher=lambda *_:raw)


def _noaa_file(ordinal,element):
    out=[]
    for y in range(1991,2026):
        key=f"{ordinal}001{element}{y:04d}"
        out.append(key+" "+" ".join(["50.0" if element=="02" else "2.0"]*12)+"\n")
    return "".join(out).encode()


def test_pinned_NOAA_source_parse_and_units(monkeypatch,tmp_path):
    temperature=_noaa_file("20","02")+_noaa_file("36","02")
    precip=_noaa_file("20","01")+_noaa_file("36","01")
    mp={
      m.NOAA_BASE+m.RAW_NOAA["temperature"][0]:temperature,
      m.NOAA_BASE+m.RAW_NOAA["precipitation"][0]:precip}
    monkeypatch.setattr(m,"RAW_NOAA",{
      "temperature":("climdiv-tmpccy-v1.0.0-20261006",hashlib.sha256(temperature).hexdigest()),
      "precipitation":("climdiv-pcpncy-v1.0.0-20261006",hashlib.sha256(precip).hexdigest())})
    monkeypatch.setattr(m,"MIN_NOAA_COMPLETE_COUNTIES",{"PA":1,"MI":1})
    climate,baseline,qc=m.fetch_exact_noaa(tmp_path,downloader=lambda url:mp[url])
    assert set(baseline)=={"26001","42001"}
    assert len(climate)==2*35*6
    assert baseline["42001"][0]==pytest.approx(10.0)
    assert baseline["26001"][1]==pytest.approx(6*2*25.4)
    assert qc["n_monthly_source_rows"]==420
    assert (tmp_path/"PA_MI_NOAA_20261006_county_growing_months.csv").exists()


def test_NOAA_wrong_old_source_bytes_must_stop(tmp_path):
    with pytest.raises(ValueError,match="SHA-locked NOAA"):
        m.fetch_exact_noaa(tmp_path,downloader=lambda _:b"NOT THE OCTOBER SOURCE")


def test_no_outcome_columns_in_derived_holdout_schema():
    assert set(m.OUTPUT_COLS)=={
        "species_code","state","county_fips","plot_chain_id","interval_id",
        "interval_end_year","temperature_anomaly_c","precipitation_anomaly_mm"}
    assert not any(x in m.OUTPUT_COLS for x in ("DIA","STATUSCD","growth","mortality"))
