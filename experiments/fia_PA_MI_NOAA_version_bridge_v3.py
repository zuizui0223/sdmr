"""PA/MI external FIA source-only NOAA 20261105 version bridge.

Check historical 1991–2025 April–September values of a separately frozen
new NOAA raw edition against exact original October-06 NOAA derived VA/WI/RI
county-month source BEFORE mixing source panels. If ANY original county-month
differs, refuse to infer shared climate-time support from mixed versions.
External source is already opened *only for prior-species/PLOT identities*:
no tree DIA, STATUSCD, growth, survival, current TREE inspection or fit.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

import fia_noaa_county_climate_source_v1 as noaa
import fia_climate_tree_source_gate_v3 as climate
import fia_external_PA_MI_first_source_v1 as original
import fia_joint_support_gate_v1 as joint

PROGRAM="fia_PA_MI_NOAA_20261105_version_bridge_source_only_v3"
NOAA_SOURCE_DATE="20261105"
NOAA_FILES={
    "temperature":"climdiv-tmpccy-v1.0.0-20261105",
    "precipitation":"climdiv-pcpncy-v1.0.0-20261105",
}
NOAA_SOURCE_BASE="https://www.ncei.noaa.gov/monitoring-content/data/us/climdiv/monthly/current/"
NCEI_ORDINAL_TO_FIPS={"37":"44","44":"51","47":"55","36":"42","20":"26"}
FIPS_STATES={"RI":"44","VA":"51","WI":"55","PA":"42","MI":"26"}
HOLDOUT_STATES=("PA","MI")
OLD_STATES=("RI","VA","WI")
PRIMARY=("129","316","802","833","837")
OLD_NOAA_SHA="623ae07eed2d9a33bf067bf00556338e6e34eb9cc15fc934e0ccf3dfbb6fd6c8"
V2_SOURCE_SHA="70cf6e8db95c864d80e684ed7292606d6a8df64d71e8bd952ae1a1a2adc4d1c2"
V2_RECEIPT_SHA="1392858a521f466e0b39892202883cec4a645f39dad6b5ab7e5d2afa534b5e3c"
V2_GATE_SHA="7b54ee7a8a855c8a5db64498e5fb68c221de827bd1dcef29f3269e69e4afd4ee"
ORIGINAL_TRAIN_CSV_SHA=original.SOURCE_CSV_SHA
ORIGINAL_TRAIN_RECEIPT_SHA=original.SOURCE_RECEIPT_SHA
MAX_RAW_BYTES=70_000_000
EXPECTED_OLD_ROWS=43890
EXPECTED_SOURCE_V2_ROWS=83046
EXPECTED_TRAIN_ROWS=89616
SOURCE_FIELDS=("species_code","state","county_fips","plot_chain_id","interval_id",
               "interval_end_year","temperature_anomaly_c","precipitation_anomaly_mm")


def sha_file(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_contract(config:dict)->None:
    expected={
      "program":PROGRAM,"noaa_release":NOAA_SOURCE_DATE,
      "NOAA_filenames":NOAA_FILES,"ordinal_to_FIPS":NCEI_ORDINAL_TO_FIPS,
      "holdout_states":list(HOLDOUT_STATES),"old_climate_states":list(OLD_STATES),
      "previous_source_v2_run":44238110335,"previous_source_v2_artifact":14397884111,
      "previous_source_v2_CSV_sha256":V2_SOURCE_SHA,
      "previous_source_v2_receipt_sha256":V2_RECEIPT_SHA,
      "previous_source_v2_gate_sha256":V2_GATE_SHA,
      "old_NOAA_1991_2025_CSV_sha256":OLD_NOAA_SHA,
      "original_training_source_CSV_sha256":ORIGINAL_TRAIN_CSV_SHA,
      "original_training_source_receipt_sha256":ORIGINAL_TRAIN_RECEIPT_SHA,
      "all_prior_FIA_growth_results_sealed":True,
      "new_source_ONLY_no_TREE_status_diameter_growth":True,
      "refuse_mixed_NOAA_versions_if_historical_values_change":True,
      "four_states_niche_process_inference_blocked":True,
      "do_not_rerun_mutable_NOAA_after_first_open":True,
      "NEON_not_required":True,
    }
    for k,v in expected.items():
        if config.get(k)!=v:raise ValueError("NOAA external bridge contract not frozen: "+k)


def fetch_source(out:Path,fetcher=None)->tuple[dict,dict]:
    """Acquire each fixed named edition only once, store exact original bytes."""
    out.mkdir(parents=True,exist_ok=True)
    cfg={
      "source_variables":{
        "temperature":{"file":NOAA_FILES["temperature"],"element":"02","source_units":"degree_fahrenheit"},
        "precipitation":{"file":NOAA_FILES["precipitation"],"element":"01","source_units":"inches_per_month"},
      },
      "ncei_ordinal_state_to_fips_state":NCEI_ORDINAL_TO_FIPS,
      "states_fips":FIPS_STATES,
      "growing_season_months":[4,5,6,7,8,9],
      "year_start":1991,"year_end":2025,
      "baseline_start":1991,"baseline_end":2020,
      "minimum_complete_counties":{"RI":5,"VA":60,"WI":50,"PA":30,"MI":40}
    }
    data={};qc={}
    for k,name in NOAA_FILES.items():
        url=NOAA_SOURCE_BASE+name
        if fetcher is not None:
            raw=fetcher(url)
        else:
            with urlopen(Request(url,headers={"User-Agent":"sdmr-source-noaa-bridge-v3"}),timeout=120) as f:
                raw=f.read(MAX_RAW_BYTES+1)
        if not isinstance(raw,bytes) or len(raw)==0 or len(raw)>MAX_RAW_BYTES:
            raise ValueError("NOAA 20261105 original bytes missing or oversized")
        p=out/name
        p.write_bytes(raw)
        parsed,info=noaa.parse_climdiv_county(raw,k,cfg)
        data[k]=parsed
        qc[k]={"url":url,"source_raw_sha256":sha_file(p),"source_bytes":len(raw),**info}
    rows,coverage=noaa.merge_validate_temperature_rainfall(data["temperature"],data["precipitation"],cfg)
    # All 5 states form one immutable, source-consistent release.
    lookup={(f,y,m):(float(t),float(p)) for f,y,m,t,p in rows}
    if len(lookup)!=len(rows):
        raise ValueError("duplicated current NOAA climate county-month")
    qc["coverage"]=coverage
    qc["n_derived_month_rows"]=len(rows)
    return lookup,qc


def load_original_climate(path:Path)->dict:
    if sha_file(path)!=OLD_NOAA_SHA:
        raise ValueError("original 20261006 VA/WI/RI climate CSV SHA mismatch")
    rows={}
    with path.open(encoding="utf-8",newline="") as fh:
        reader=csv.DictReader(fh)
        if set(reader.fieldnames or [])!={"fips_county","year","month","temperature_c","precipitation_mm"}:
            raise ValueError("old NOAA source schema changed")
        for r in reader:
            key=(r["fips_county"],int(r["year"]),int(r["month"]))
            if key in rows:raise ValueError("duplicate original NOAA county month")
            if key[0][:2] not in ("44","51","55"):
                raise ValueError("unexpected original state")
            rows[key]=(float(r["temperature_c"]),float(r["precipitation_mm"]))
    if len(rows)!=EXPECTED_OLD_ROWS:
        raise ValueError("old NOAA county climate denominator changed")
    return rows


def compare_versions(old:dict,new:dict)->dict:
    """Strict original-month identity, report revision rather than tolerate drift."""
    states={"RI":"44","VA":"51","WI":"55"}
    tally={}
    all_same=True
    for state,prefix in states.items():
        keys=[k for k in old if k[0].startswith(prefix)]
        changes=Counter()
        maxima={"temperature_c":0.,"precipitation_mm":0.}
        missing=0
        for key in keys:
            if key not in new:
                missing+=1;continue
            for axis,ix in (("temperature_c",0),("precipitation_mm",1)):
                delta=abs(float(old[key][ix])-float(new[key][ix]))
                if not math.isfinite(delta):
                    raise ValueError("nonfinite NOAA historical revision")
                if delta!=0:
                    changes[axis]+=1
                if delta>maxima[axis]:maxima[axis]=delta
        equal=not missing and not sum(changes.values())
        all_same &= equal
        tally[state]={
            "n_original_months":len(keys),
            "n_missing_original_months_in_new_source":missing,
            "n_changed_temperature_months":changes["temperature_c"],
            "n_changed_precipitation_months":changes["precipitation_mm"],
            "max_abs_temperature_revision_C":maxima["temperature_c"],
            "max_abs_precipitation_revision_mm_per_month":maxima["precipitation_mm"],
            "unchanged_at_six_decimal_normalization":equal
        }
    return {
        "historical_1991_2025_original_3state_monthly_values_exactly_unchanged":bool(all_same),
        "old_source_months_compared":len(old),
        "old_NOAA_source_file_CSV_sha256":OLD_NOAA_SHA,
        "states":tally,
        "do_not_combine_mismatched_source_versions":True,
    }


def source_v2_records(source_dir:Path)->list[dict]:
    paths={
      "PA_MI_source_only_prior_species_plot_intervals_v2.csv":V2_SOURCE_SHA,
      "PA_MI_identity_source_receipt_v2.json":V2_RECEIPT_SHA,
      "PA_MI_identity_only_cohort_preflight_v2.json":V2_GATE_SHA,
    }
    for name,digest in paths.items():
        if sha_file(source_dir/name)!=digest:
            raise ValueError("PA/MI independent source-only v2 SHA mismatch: "+name)
    report=json.loads((source_dir/"PA_MI_identity_only_cohort_preflight_v2.json").read_text())
    receipt=json.loads((source_dir/"PA_MI_identity_source_receipt_v2.json").read_text())
    if report.get("holdout_prior_species_plot_intervals")!=EXPECTED_SOURCE_V2_ROWS or \
       receipt.get("holdout_identity_source_rows")!=EXPECTED_SOURCE_V2_ROWS or \
       receipt.get("status")!="source_identity_only_ready_no_climate_join":
        raise ValueError("PA/MI identity source v2 fixed denominator changed")
    found=set();out=[]
    with (source_dir/"PA_MI_source_only_prior_species_plot_intervals_v2.csv").open(encoding="utf-8",newline="") as f:
        rd=csv.DictReader(f)
        required={"species_code","state","county_fips","plot_chain_id","interval_id",
                  "prior_visit_year","prior_visit_month","current_visit_year",
                  "current_visit_month","interval_end_year","remeasurement_months"}
        if set(rd.fieldnames or [])!=required:raise ValueError("source v2 schema mismatch")
        for r in rd:
            if r["state"] not in HOLDOUT_STATES or r["species_code"] not in original.PRIOR_13:
                raise ValueError("unexpected holdout taxon or state")
            if not r["county_fips"].startswith({"PA":"42","MI":"26"}[r["state"]]):
                raise ValueError("holdout county FIPS inconsistent")
            identity=(r["species_code"],r["state"],r["interval_id"])
            if identity in found:raise ValueError("duplicate holdout source interval")
            found.add(identity)
            for key in ("prior_visit_year","prior_visit_month","current_visit_year","current_visit_month","interval_end_year","remeasurement_months"):
                r[key]=int(r[key])
            if r["interval_end_year"]!=r["current_visit_year"] or \
               r["remeasurement_months"] != (r["current_visit_year"]*12+r["current_visit_month"])-(r["prior_visit_year"]*12+r["prior_visit_month"]):
                raise ValueError("holdout source visit dates inconsistent")
            out.append(r)
    if len(out)!=EXPECTED_SOURCE_V2_ROWS:
        raise ValueError("PA/MI source-only sample denominator changed")
    return out


def build_new_external_climate(rows:list[dict],lookup:dict)->tuple[list[dict],dict]:
    # 1991–2020 six growing-month baseline per county, for new PA/MI states.
    county_vals=defaultdict(list)
    for (county,year,month),(t,p) in lookup.items():
        if county[:2] in ("42","26") and 1991<=year<=2020:
            county_vals[county].append((year,month,t,p))
    base={}
    for co,months in county_vals.items():
        if len(months)!=180 or len({(y,m) for y,m,_,_ in months})!=180:
            raise ValueError("incomplete 1991–2020 new NOAA baseline at county "+co)
        base[co]=(sum(q[2] for q in months)/180,sum(q[3] for q in months)/30)
    new=[]
    counters=defaultdict(Counter)
    for row in rows:
        state=row["state"];county=row["county_fips"]
        if county not in base:
            counters[state]["county_without_complete_climate_baseline"]+=1;continue
        from_visit=(row["prior_visit_year"],row["prior_visit_month"])
        to_visit=(row["current_visit_year"],row["current_visit_month"])
        exposure=climate.interval_exposure(lookup,county,from_visit,to_visit)
        if exposure is None:
            counters[state]["incomplete_intervening_growing_months"]+=1;continue
        t0,p0=base[county]
        t=exposure["temperature_c"]-t0
        p=exposure["precipitation_mm_per_six_months"]-p0
        if not math.isfinite(t) or not math.isfinite(p):
            raise ValueError("invalid newly derived PA/MI interval anomaly")
        new.append({
            "species_code":row["species_code"],"state":state,
            "county_fips":county,"plot_chain_id":row["plot_chain_id"],
            "interval_id":row["interval_id"],"interval_end_year":row["interval_end_year"],
            "temperature_anomaly_c":t,"precipitation_anomaly_mm":p})
        counters[state]["climate_anomaly_eligible_source_taxon_plot_interval"]+=1
    return new,{st:dict(counters[st]) for st in HOLDOUT_STATES}


def verify_training_source(train_dir:Path,config_path:Path)->tuple[list[dict],dict]:
    cfg=json.loads(config_path.read_text())
    joint.verify_config(cfg)
    if sha_file(train_dir/"fia_new_cohort_joint_source_only_county_stable_v2.csv")!=ORIGINAL_TRAIN_CSV_SHA or \
       sha_file(train_dir/"derived_receipt.json")!=ORIGINAL_TRAIN_RECEIPT_SHA:
        raise ValueError("original locked VA/WI training source SHA mismatch")
    prior_panel=joint.read_source_only_csv(
       train_dir/"fia_new_cohort_joint_source_only_county_stable_v2.csv",
       train_dir/"derived_receipt.json",cfg)
    if len(prior_panel)!=EXPECTED_TRAIN_ROWS:raise ValueError("old 13 taxon training source denominator drift")
    return prior_panel,cfg


def run(out:Path,old_noaa:Path,v2_dir:Path,training_dir:Path,
        training_cfg:Path,source_cfg:Path,*,fetcher=None)->dict:
    out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(source_cfg.read_text())
    verify_contract(cfg)
    # Everything immutable must verify BEFORE first new NOAA GET.
    old=load_original_climate(old_noaa)
    old_train,source_settings=verify_training_source(training_dir,training_cfg)
    fixed_holdout=source_v2_records(v2_dir)
    receipt={"program":PROGRAM,"noaa_version":NOAA_SOURCE_DATE,
       "status":"not_yet_source_available","fixed_external_states":list(HOLDOUT_STATES),
       "n_original_training_source_only_records":len(old_train),
       "n_holdout_identity_time_records":len(fixed_holdout),
       "original_identity_v2_CSV_sha256":V2_SOURCE_SHA,
       "original_NOAA_old_CSV_sha256":OLD_NOAA_SHA,
       "raw_TREE_DIA_STATUSCD_growth_death_opened":False,
       "source_ONLY_no_biological_model_fitted":True,
       "biological_promotion_authorized":False}
    try:
        new_climate,raw_info=fetch_source(out,fetcher=fetcher)
        receipt["raw_NOAA_source"]=raw_info
        check=compare_versions(old,new_climate)
        receipt["historical_original_monthly_comparison"]=check
        out_rows,external_qc=build_new_external_climate(fixed_holdout,new_climate)
        receipt["new_external_climate_eligibility_counts"]=external_qc
        holdout_path=out/"PA_MI_20261105_external_source_only_climate.csv"
        with holdout_path.open("w",newline="",encoding="utf-8") as stream:
            wr=csv.DictWriter(stream,fieldnames=SOURCE_FIELDS,lineterminator="\n")
            wr.writeheader()
            wr.writerows(sorted(out_rows,key=lambda r:(int(r["species_code"]),r["state"],r["county_fips"],r["plot_chain_id"],r["interval_id"])))
        receipt["new_holdout_joint_climate_source_rows"]=len(out_rows)
        receipt["new_holdout_climate_CSV_sha256"]=sha_file(holdout_path)
        if check["historical_1991_2025_original_3state_monthly_values_exactly_unchanged"]:
            report=original.compare_train_holdout(old_train,out_rows,source_settings)
            report.update({"status":"time_climate_common_support_external_source_ready_not_biological",
                           "new_NOAA_source_release":NOAA_SOURCE_DATE,
                           "original_climate_historical_month_values_identical":True,
                           "external_source_only_climate_rows":len(out_rows),
                           "source_no_biological_outcomes_opened":True})
            receipt["status"]="bridge_old_and_new_NOAA_historical_observations_exactly_identical"
        else:
            report={"program":PROGRAM,
                    "status":"historical_NOAA_revision_blocks_mixed_version_common_support",
                    "n_source_only_holdout_climate_rows":len(out_rows),
                    "changed_original_NOAA_historical_months_by_state":check["states"],
                    "training_and_holdout_joint_climate_comparability":None,
                    "n_primary_both_holdout_states_source_eligible":None,
                    "not_a_negative_climate_transfer_result":True,
                    "source_only_no_demographic_outcomes_opened":True,
                    "biological_promotion_authorized":False}
            receipt["status"]="historical_NOAA_revision_detected_source_only_bridge_stopped"
        (out/"PA_MI_NOAA_version_bridge_result_v3.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n")
    except Exception as exc:
        receipt["status"]="new_NOAA_first_open_source_unavailable_or_changed_STOP"
        receipt["error_class"]=type(exc).__name__
        receipt["error_message"]=str(exc)[:270]
        report={"program":PROGRAM,"status":"new_NOAA_source_STOP_no_biological_outcomes",
                "source_missing_not_zero":True,
                "n_independent_biological_effect_tests":0,
                "biological_promotion_authorized":False}
        (out/"PA_MI_NOAA_version_bridge_result_v3.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n")
    (out/"PA_MI_NOAA_version_bridge_receipt_v3.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    return report


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--old-NOAA-csv",required=True,type=Path)
    p.add_argument("--holdout-identity-v2",required=True,type=Path)
    p.add_argument("--training-source-v2",required=True,type=Path)
    p.add_argument("--training-config",type=Path,default=Path("configs/fia_joint_climate_support_gate_v1.json"))
    p.add_argument("--bridge-config",type=Path,default=Path("configs/fia_PA_MI_NOAA_version_bridge_v3.json"))
    a=p.parse_args()
    result=run(a.out,a.old_NOAA_csv,a.holdout_identity_v2,
               a.training_source_v2,a.training_config,a.bridge_config)
    print(result["status"],"external source-only rows",result.get("external_source_only_climate_rows",result.get("n_source_only_holdout_climate_rows")), "NO biological outcome")
    if result["status"] not in (
        "time_climate_common_support_external_source_ready_not_biological",
        "historical_NOAA_revision_blocks_mixed_version_common_support"):
        raise SystemExit(2)


if __name__=="__main__":
    main()
