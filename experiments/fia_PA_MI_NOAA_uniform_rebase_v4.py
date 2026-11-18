"""Rebuild *source-only* five-state FIA interval climate under NOAA 20261105.

Older 20261006 NOAA historical county months were actually revised. To compare
FIA external PA/MI with already source-selected VA/WI without combining NOAA
releases, verify original RI/VA/WI PLOT ZIP bytes against their FIRST source
receipt, and recompute ORIGINAL (89,616) taxon×PLOT intervals from archived
PLOT pair measurement dates and NEW same-edition NOAA 20261105 raw bytes.
All 13 taxa retain the original source-only selection and denominator.
HOLDOUT (83,046) source climate is read from sealed version-bridge v3, not
obtained again from changing public sources. No TREE, COND, DIA, survival,
growth, mortality, biological response, or model fitting is read.
"""
from __future__ import annotations
import argparse
from collections import defaultdict,Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from urllib.request import Request,urlopen
from zipfile import ZipFile

import fia_PA_MI_NOAA_version_bridge_v3 as bridge
import fia_joint_source_only_v1 as source
import fia_joint_support_gate_v1 as joint
import fia_climate_tree_source_gate_v3 as climate
import fia_external_PA_MI_first_source_v1 as crossgate
import fia_noaa_county_climate_source_v1 as noaa

PROGRAM="fia_source_only_all_five_states_NOAA_20261105_rebased_v4"
OLD_FIRST_SOURCE_RECEIPT_SHA="0adcdeac7b974e91b83d986fca32ad0851000658f79fbe099407ce2fb37fa408"
PLOT_ORIGINAL={
 "RI":"c19953851a4d804337959b772c1a9f4f1b7bb16d5686d49705b571a759684648",
 "VA":"18e791098390ce3543d48ebc53073da6df5901589edd55c22fe33e1cd14fc6fd",
 "WI":"0ec63fb21e03439a40771f28e5d535e0ae1d2a3ff2dc308b31ed2348936dac10",
}
NOAA_NEW_SHAS={
 "temperature":"ea6a159d3ad9a25b60cce6e3889d79898e17cf4e29b3d2c2282d19d7fb073a4d",
 "precipitation":"1f21b2435a29cc40369a4666a69b4f6d851643bad2811f7b8f1bab6521217b27",
}
NOAA_V3_RECEIPT_SHA="5d44b9315cf8125bd3a3abe544422abeee506b2e1814e88dced134defb3c3e2c"
NOAA_V3_SOURCE_SHA="b83298bfd792b25e71d62ade38486979d37b7618b8dece5da5f071921949de85"
NOAA_V3_RESULT_SHA="78c42e52c56b05243fe466f6042b84acb3ae39abfd3f09e798830dac20e14639"
STATES=("RI","VA","WI")
FIPS={"RI":"44","VA":"51","WI":"55"}
EXPECTED_TRAIN_ROWS=89616
EXPECTED_HOLDOUT_ROWS=83046
EXPECTED_NOAA_ROWS=75390
OUTPUT_COLS=bridge.SOURCE_FIELDS
MAX_SOURCE_ZIP_BYTES=320_000_000


def sha(path:Path)->str:
 return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_contract(cfg:dict):
 expected={
  "program":PROGRAM,
  "unopened_test_states":["PA","MI"],
  "original_training_source_states":list(STATES),
  "original_3state_first_source_receipt_SHA256":OLD_FIRST_SOURCE_RECEIPT_SHA,
  "original_3state_PLOT_ZIP_SHA256":PLOT_ORIGINAL,
  "new_NOAA_20261105_raw_SHA256":NOAA_NEW_SHAS,
  "source_noaa_v3_receipt_sha256":NOAA_V3_RECEIPT_SHA,
  "source_noaa_v3_PA_MI_csv_sha256":NOAA_V3_SOURCE_SHA,
  "old_training_source_reconciled_CSV_sha256":bridge.ORIGINAL_TRAIN_CSV_SHA,
  "original_13_species_codes":list(source.SPECIES),
  "frozen_primary_five_codes":list(crossgate.PRIOR_5),
  "no_FIA_TREES_COND_or_biological_outcomes_opened":True,
  "no_refetch_new_NOAA_or_external_PA_MI_FIA":True,
  "require_same_original_PLOT_zip_or_STOP":True,
  "training_source_row_count_fixed":EXPECTED_TRAIN_ROWS,
  "holdout_source_row_count_fixed":EXPECTED_HOLDOUT_ROWS,
  "all_5_states_same_NOAA_20261105_historical_release":True,
  "Product_A_M5_unchanged_and_Product_B_blocked":True,
  "no_automatic_retry_if_source_changed":True,
 }
 for k,v in expected.items():
  if cfg.get(k)!=v:raise ValueError("NOAA 20261105 uniform-rebase contract changed: "+k)


def verify_historical_receipt(path:Path):
 if sha(path)!=OLD_FIRST_SOURCE_RECEIPT_SHA:
  raise ValueError("first source original RI VA WI PLOT receipt SHA mismatch")
 receipt=json.loads(path.read_text())
 if receipt.get("status")!="source_only_pre_response" or tuple(
  x.get("state") for x in receipt.get("states",[]))!=STATES:
  raise ValueError("first source provenance/state order missing")
 for entry in receipt["states"]:
  state=entry["state"]
  if entry["plot_source"]["sha256"]!=PLOT_ORIGINAL[state] or \
     not entry.get("no_tree_growth_or_status_read"):
   raise ValueError("original first source PLOT SHA or no-response boundary invalid")


def read_saved_NOAA(newraw:Path)->tuple[dict,dict]:
 config={
  "source_variables":{"temperature":{"element":"02"},"precipitation":{"element":"01"}},
  "ncei_ordinal_state_to_fips_state":bridge.NCEI_ORDINAL_TO_FIPS,
  "states_fips":bridge.FIPS_STATES,
  "year_start":1991,"year_end":2025,
  "baseline_start":1991,"baseline_end":2020,
  "growing_season_months":[4,5,6,7,8,9],
  "minimum_complete_counties":{"RI":5,"VA":60,"WI":50,"PA":30,"MI":40},
 }
 parsed={}
 for kind,name in bridge.NOAA_FILES.items():
  path=newraw/name
  if sha(path)!=NOAA_NEW_SHAS[kind]:
   raise ValueError("NOAA first-open 20261105 original raw SHA mismatch: "+kind)
  parsed[kind],_=noaa.parse_climdiv_county(path.read_bytes(),kind,config)
 rows,info=noaa.merge_validate_temperature_rainfall(parsed["temperature"],parsed["precipitation"],config)
 out={(fips,year,month):(t,p) for fips,year,month,t,p in rows}
 if len(out)!=EXPECTED_NOAA_ROWS:raise ValueError("new five state NOAA county-month fixed denominator changed")
 base=defaultdict(list)
 for (co,yr,mo),(t,p) in out.items():
  if 1991<=yr<=2020:base[co].append((yr,mo,t,p))
 baselines={}
 for co,vals in base.items():
  if len(vals)!=180 or len({(y,m) for y,m,_,_ in vals})!=180:
   raise ValueError("NOAA latest edition baseline county-month incomplete")
  baselines[co]=(sum(v[2] for v in vals)/180,sum(v[3] for v in vals)/30)
 return out,baselines


def fetch_PLOT(state:str,out:Path,fetcher=None)->tuple[Path,dict]:
 """One network request, response-blind. Return a file only if SHA == first source."""
 if state not in STATES:raise ValueError("unknown original development source state")
 p=out/f"{state}_PLOT.zip"
 url=f"https://apps.fs.usda.gov/fia/datamart/CSV/{state}_PLOT.zip"
 info={"state":state,"url":url,"original_SHA":PLOT_ORIGINAL[state],
       "status":"not_yet_verified"}
 try:
  if fetcher is not None:
   raw=fetcher(state)
   if not isinstance(raw,bytes):raise ValueError("invalid fixture archive")
   src=io.BytesIO(raw)
  else:
   src=urlopen(Request(url,headers={"User-Agent":"sdmr-FIA-PLOT-identity-rebase-v4"}),timeout=110)
  total=0;h=hashlib.sha256()
  with src,p.open("wb") as file:
   while True:
    block=src.read(1024*1024)
    if not block:break
    total+=len(block)
    if total>MAX_SOURCE_ZIP_BYTES:raise ValueError("PLOT archive exceeded fixed cap")
    h.update(block);file.write(block)
  info["current_SHA"]=h.hexdigest()
  info["source_bytes"]=total
  if h.hexdigest()!=PLOT_ORIGINAL[state]:
   raise ValueError("original first-source PLOT ZIP source changed; cannot reconstruct same plot visits")
  with ZipFile(p) as z:
   members=[f for f in z.namelist() if f.upper().endswith(f"{state}_PLOT.CSV")]
   if len(members)!=1:raise ValueError("ambiguous original PLOT table member")
   info["member"]=members[0]
  info["status"]="exact_original_first_source_PLOT_bytes_recovered"
  return p,info
 except Exception as exc:
  info["status"]="source_stop_no_TREE_outcomes"
  info["error_class"]=type(exc).__name__
  info["error_excerpt"]=str(exc)[:180]
  raise ValueError(f"{state}: original PLOT source cannot be re-established; " 
                   f"{type(exc).__name__}: {str(exc)[:180]}; "
                   f"source_expected_SHA={PLOT_ORIGINAL[state]}, "
                   f"acquired_SHA={info.get('current_SHA')}") from exc


def plot_visit_dates(path:Path,member:str,state:str)->dict:
 """Read only PLOT measurement source columns from SHA-recovered raw PLOT."""
 found={}
 with ZipFile(path) as z,z.open(member) as f:
  rd=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",newline=""))
  required={"CN","PREV_PLT_CN","STATECD","COUNTYCD","MEASYEAR","MEASMON"}
  if required-set(rd.fieldnames or []):raise ValueError("missing original PLOT identity/date columns")
  for row in rd:
   cn=(row.get("CN") or "").strip()
   if not cn or cn in found:raise ValueError("missing/duplicate original PLOT CN")
   prior=(row.get("PREV_PLT_CN") or "").strip()
   county,date=None,None
   try:
    if str(int(float(row["STATECD"])))!=str(int(FIPS[state])):
     raise ValueError("wrong PLOT source state")
    countycode=int(float(row["COUNTYCD"]))
    year,month=int(row["MEASYEAR"]),int(row["MEASMON"])
    if not 1<=countycode<=999 or not 1850<year<=2030 or not 1<=month<=12:
     raise ValueError("invalid date or county")
    county=FIPS[state]+f"{countycode:03d}";date=(year,month)
   except (ValueError,TypeError):
    pass
   found[cn]=(prior,county,date)
 return found


def rebase_original_training(prior_rows:list[dict],plots_by_state:dict,
                             latest_NOAA:dict,baseline:dict)->tuple[list[dict],dict]:
 """No source denominator/site/species selection changes are permitted."""
 if len(prior_rows)!=EXPECTED_TRAIN_ROWS:raise ValueError("original train source denominator changed")
 starts={}
 roots={}
 for st in STATES:
  raw=plots_by_state[st]
  roots[st]=source.plot_roots({cn:(z[0],z[1],z[2][0] if z[2] else None)
                             for cn,z in raw.items()})
 new=[];counters={st:Counter() for st in STATES}
 for r in prior_rows:
  state=r["state"];index=plots_by_state[state]
  now=index.get(r["interval_id"])
  if not now:raise ValueError("previously selected source PLOT CN absent in original PLOT bytes")
  prev,co,end=now;old=index.get(prev)
  if old is None or co!=r["county_fips"] or old[1]!=co or \
      end is None or old[2] is None or \
      end[0]!=r["interval_end_year"] or \
      roots[state][r["interval_id"]]!=r["plot_chain_id"]:
   raise ValueError("source-only original plot/time/county/chain identity changed")
  if co not in baseline:raise ValueError("new NOAA baseline missing original training county")
  exposure=climate.interval_exposure(latest_NOAA,co,old[2],end)
  if exposure is None:
   raise ValueError("an originally selected interval has no complete new-release NOAA exposure")
  t0,p0=baseline[co]
  t=exposure["temperature_c"]-t0
  p=exposure["precipitation_mm_per_six_months"]-p0
  if not math.isfinite(t) or not math.isfinite(p):
   raise ValueError("nonfinite recalculated climate anomaly")
  updated={k:r[k] for k in bridge.SOURCE_FIELDS}
  updated["temperature_anomaly_c"]=t
  updated["precipitation_anomaly_mm"]=p
  new.append(updated)
  counters[state]["n_identical_species_plot_interval_IDs"]+=1
  if abs(t-r["temperature_anomaly_c"])>1e-9:counters[state]["n_revised_temperature_intervals"]+=1
  if abs(p-r["precipitation_anomaly_mm"])>1e-9:counters[state]["n_revised_precipitation_intervals"]+=1
 if len(new)!=len(prior_rows):raise ValueError("rebuild lost original 13-taxon denominator")
 return new,{state:dict(counters[state]) for state in STATES}


def fixed_PA_MI_v3_source(dir:Path)->list[dict]:
 files={
 "PA_MI_20261105_external_source_only_climate.csv":NOAA_V3_SOURCE_SHA,
 "PA_MI_NOAA_version_bridge_receipt_v3.json":NOAA_V3_RECEIPT_SHA,
 "PA_MI_NOAA_version_bridge_result_v3.json":NOAA_V3_RESULT_SHA
 }
 for name,dig in files.items():
  if sha(dir/name)!=dig:raise ValueError("PA/MI original v3 new NOAA source SHA mismatch")
 info=json.loads((dir/"PA_MI_NOAA_version_bridge_receipt_v3.json").read_text())
 if info.get("status")!="historical_NOAA_revision_detected_source_only_bridge_stopped" or \
    info.get("new_holdout_joint_climate_source_rows")!=EXPECTED_HOLDOUT_ROWS:
  raise ValueError("PA MI source climate v3 earlier revision branch is not sealed")
 with (dir/"PA_MI_20261105_external_source_only_climate.csv").open(encoding="utf-8",newline="") as f:
  rd=csv.DictReader(f)
  if set(rd.fieldnames or [])!=set(bridge.SOURCE_FIELDS):
   raise ValueError("PA/MI new source-only climate CSV schema changed")
  out=[];ids=set()
  for r in rd:
   key=(r["species_code"],r["state"],r["interval_id"])
   if key in ids or r["state"] not in ("PA","MI"):
    raise ValueError("duplicate or foreign PA MI source row")
   ids.add(key)
   r["interval_end_year"]=int(r["interval_end_year"])
   for k in ("temperature_anomaly_c","precipitation_anomaly_mm"):
    r[k]=float(r[k])
   out.append(r)
 if len(out)!=EXPECTED_HOLDOUT_ROWS:raise ValueError("fixed PA/MI climate source denominator changed")
 return out


def write_source_csv(path:Path,rows:list[dict])->str:
 with path.open("w",newline="",encoding="utf-8") as f:
  wr=csv.DictWriter(f,fieldnames=OUTPUT_COLS,lineterminator="\n")
  wr.writeheader()
  wr.writerows(sorted(rows,key=lambda r:(int(r["species_code"]),r["state"],
               r["county_fips"],r["plot_chain_id"],r["interval_id"])))
 return sha(path)


def run(out:Path,old_training_dir:Path,first_source_receipt:Path,
        new_NOAA_raw_dir:Path,PA_MI_v3_source_dir:Path,
        config_path:Path,train_config_path:Path,plot_fetcher=None)->dict:
 out.mkdir(parents=True,exist_ok=True)
 cfg=json.loads(config_path.read_text())
 verify_contract(cfg)
 verify_historical_receipt(first_source_receipt)
 train,cfg2=bridge.verify_training_source(old_training_dir,train_config_path)
 PA_MI=fixed_PA_MI_v3_source(PA_MI_v3_source_dir)
 latest,baseline=read_saved_NOAA(new_NOAA_raw_dir)
 receipt={"program":PROGRAM,"status":"initial_before_original_PLOT_identity_reverification",
   "original_13_species_source_rows":len(train),"new_external_PA_MI_source_rows":len(PA_MI),
   "first_original_PLOT_sources":[],"no_tree_responses_or_models_fitted":True,
   "historic_monthly_revision_detected_in_v3":True,
   "historical_original_source_unaltered":True,
   "biological_promotion_authorized":False}
 try:
  originals={}
  for st in STATES:
   path,info=fetch_PLOT(st,out,fetcher=plot_fetcher)
   receipt["first_original_PLOT_sources"].append(info)
   originals[st]=plot_visit_dates(path,info["member"],st)
  new_train,qc=rebase_original_training(train,originals,latest,baseline)
  trainpath=out/"source_RI_VA_WI_rebased_NOAA_20261105_v4.csv"
  derivedsha=write_source_csv(trainpath,new_train)
  receipt["source_rebase_QC"]=qc
  receipt["new_training_same_ids_as_original"]=len(new_train)==EXPECTED_TRAIN_ROWS
  receipt["new_training_CSV_sha256"]=derivedsha
  external=crossgate.compare_train_holdout(new_train,PA_MI,cfg2)
  external["status"]="same_NOAA_20261105_release_source_only_external_climate_support"
  external["all_original_training_source_IDs_retained"]=True
  external["new_training_source_CSV_sha256"]=derivedsha
  external["new_external_PA_MI_CSV_sha256"]=NOAA_V3_SOURCE_SHA
  external["n_rebased_13_taxon_source_rows"]=len(new_train)
  external["n_PA_MI_13_taxon_source_climate_rows"]=len(PA_MI)
  external["source_branch"]="NOAA_20261105_all_five_states_one_release_exact_previous_PLOT_metadata"
  external["first_original_PLOT_ZIPs_SHA_verified"]=True
  external["no_TREE_DIA_STATUSCD_or_biological_outcome_evaluated"]=True
  external["biological_promotion_authorized"]=False
  receipt["status"]="source_climate_rebuilt_without_any_demographic_outcomes"
  (out/"PA_MI_same_NOAA_source_support_v4.json").write_text(json.dumps(external,indent=2,sort_keys=True)+"\n")
 except Exception as exc:
  receipt["status"]="original_PLOT_SHA_or_source_rebase_failed_stop"
  receipt["error_class"]=type(exc).__name__
  receipt["error_excerpt"]=str(exc)[:270]
  external={"program":PROGRAM,
            "status":"source_identity_or_climate_rebase_failed_no_transfer_claim",
            "common_climate_support_not_verified":True,
            "source_failure_not_zero_biological_effect":True,
            "n_external_biological_effect_tests":0,
            "biological_promotion_authorized":False}
  (out/"PA_MI_same_NOAA_source_support_v4.json").write_text(json.dumps(external,indent=2,sort_keys=True)+"\n")
 (out/"PA_MI_same_NOAA_source_receipt_v4.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
 return external


def main():
 p=argparse.ArgumentParser()
 p.add_argument("--out",type=Path,required=True)
 p.add_argument("--original-training",type=Path,required=True)
 p.add_argument("--original-first-source-receipt",type=Path,required=True)
 p.add_argument("--new-NOAA-raw",type=Path,required=True)
 p.add_argument("--PA-MI-v3-source",type=Path,required=True)
 p.add_argument("--config",type=Path,default=Path("configs/fia_PA_MI_NOAA_uniform_rebase_v4.json"))
 p.add_argument("--training-config",type=Path,default=Path("configs/fia_joint_climate_support_gate_v1.json"))
 a=p.parse_args()
 result=run(a.out,a.original_training,a.original_first_source_receipt,a.new_NOAA_raw,
            a.PA_MI_v3_source,a.config,a.training_config)
 print("ALL STATE NOAA EDITION V4:",result["status"],
       "five priority source-qualified across both PA/MI",
       result.get("n_primary_both_holdout_states_source_eligible"),
       "no growth/mortality opened")
 if result["status"]!="same_NOAA_20261105_release_source_only_external_climate_support":
  raise SystemExit(2)


if __name__=="__main__":
 main()
