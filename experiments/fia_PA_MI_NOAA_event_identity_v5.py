"""FIA five-state climate source-only rebase v5: selected-event identity proof.

Distinct successor after v4 refused strict full PLOT ZIP SHA equality. Uses the
exact updated RI PLOT bytes ALREADY acquired in the v4 STOP, then acquires VA/WI
PLOT only once. For ALL 89,616 old source-selected taxon×plot-interval rows,
requires unchanged plot/county/chain/end-year IDs AND recovery of the archived
old 20261006 NOAA climate anomalies from the newly acquired PLOT dates before
calculating 20261105 anomalies. A failure of ANY record stops the entire run.
No old/source species or observations dropped; no TREE, COND, DIA or STATUSCD.
This is event-identity reconstruction, NOT original raw-version equivalence.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from urllib.request import Request,urlopen
from zipfile import ZipFile

import fia_PA_MI_NOAA_uniform_rebase_v4 as strict
import fia_PA_MI_NOAA_version_bridge_v3 as bridge
import fia_joint_source_only_v1 as identities
import fia_climate_tree_source_gate_v3 as climate
import fia_external_PA_MI_first_source_v1 as external

PROGRAM="fia_five_state_NOAA_20261105_event_identity_verified_source_only_v5"
OLD_RAW_RI_UPDATED_SHA="b409bb55766011401ee581ca7ad97f7c7d3e5a3876db630c6a7027e5ea7fcde0"
V4_PLOT_SOURCE_STOP_RUN=44294243344
V4_RAW_RI_PLOT_ARTIFACT=14421539704
TRAIN_N=89616
HOLDOUT_N=83046
TOL_TEMP_C=1e-5
TOL_PRECIP_MM=1e-4
STATES=("RI","VA","WI")
MAX_ZIP=320_000_000
FIELDS=bridge.SOURCE_FIELDS


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(cfg:dict)->None:
    required={
      "study":PROGRAM, "states":list(STATES),
      "old_v4_full_sha_gate_failed_run":V4_PLOT_SOURCE_STOP_RUN,
      "v4_RI_updated_PLOT_zip_sha256":OLD_RAW_RI_UPDATED_SHA,
      "first_RI_new_source_artifact":V4_RAW_RI_PLOT_ARTIFACT,
      "training_source_row_count":TRAIN_N,
      "PA_MI_source_row_count":HOLDOUT_N,
      "new_NOAA_release":"20261105",
      "require_all_original_plot_interval_records_old_NOAA_reconstructed":True,
      "require_exact_original_plot_chain_and_county_and_year":True,
      "old_NOAA_temperature_tolerance_c":TOL_TEMP_C,
      "old_NOAA_precipitation_tolerance_mm":TOL_PRECIP_MM,
      "no_TREE_COND_or_biological_outcome_access":True,
      "not_the_original_FIA_PLOT_source_version":True,
      "no_automatic_repeat_or_replacement":True,
      "Product_A_M5_unchanged_Product_B_blocked":True,
    }
    for k,v in required.items():
        if cfg.get(k)!=v:
            raise ValueError("unfrozen event-identity rebase contract: "+k)


def fetch_PLOT_new(state:str, out:Path, *, reader=None)->tuple[Path,dict]:
    """One versioned source acquisition. Never infer equality from state name."""
    if state not in ("VA","WI"):
        raise ValueError("v5 can only newly acquire previously selected VA/WI PLOT")
    url=f"https://apps.fs.usda.gov/fia/datamart/CSV/{state}_PLOT.zip"
    path=out/f"{state}_PLOT.zip"
    h=hashlib.sha256()
    n=0
    stream=io.BytesIO(reader(state)) if reader else urlopen(
       Request(url,headers={"User-Agent":"sdmr-event-identity-climate-rebase-v5"}),timeout=110)
    with stream,path.open("wb") as f:
        while True:
            block=stream.read(1024*1024)
            if not block:break
            n+=len(block)
            if n>MAX_ZIP:raise ValueError("FIA PLOT source exceeded fixed cap")
            h.update(block);f.write(block)
    with ZipFile(path) as z:
        members=[x for x in z.infolist() if not x.is_dir()
                 and x.filename.upper().endswith(f"{state}_PLOT.CSV")]
        if len(members)!=1 or members[0].file_size>3_800_000_000:
            raise ValueError("FIA PLOT CSV source missing/ambiguous/oversized")
        member=members[0].filename
    return path,{"state":state,"status":"new_source_only_PLOT_version",
                 "url":url,"sha256":h.hexdigest(),"n_bytes":n,
                 "member":member,"same_full_source_SHA_as_old":h.hexdigest()==strict.PLOT_ORIGINAL[state]}


def _old_baseline(records:dict)->dict:
    d=defaultdict(list)
    for (county,year,month),(t,p) in records.items():
        if 1991<=year<=2020:
            d[county].append((year,month,t,p))
    baseline={}
    for county,items in d.items():
        if len(items)!=180 or len({(y,m) for y,m,_,_ in items})!=180:
            raise ValueError("old NOAA baseline source incomplete")
        baseline[county]=(sum(x[2] for x in items)/180,sum(x[3] for x in items)/30)
    return baseline


def rebase_all(original_rows:list[dict],plots_by_state:dict,old_climate:dict,
               new_climate:dict,new_baseline:dict)->tuple[list[dict],dict]:
    if len(original_rows)!=TRAIN_N:raise ValueError("original source full denominator changed")
    old_baseline=_old_baseline(old_climate)
    roots={}
    for st in STATES:
        index=plots_by_state[st]
        roots[st]=identities.plot_roots({
            cn:(record[0],record[1],record[2][0] if record[2] else None)
            for cn,record in index.items()})
    saved=[];counts={s:Counter() for s in STATES}
    identities_seen=set()
    for row in original_rows:
        state=row["state"]
        if state not in STATES:raise ValueError("unexpected original state")
        key=(row["species_code"],state,row["interval_id"])
        if key in identities_seen:raise ValueError("duplicate original source interval")
        identities_seen.add(key)
        now=plots_by_state[state].get(row["interval_id"])
        if not now:raise ValueError("original source plot interval absent in v5 version")
        prev,county,end=now
        past=plots_by_state[state].get(prev)
        if (past is None or county!=row["county_fips"] or
            past[1]!=county or end is None or past[2] is None or
            end[0]!=row["interval_end_year"] or
            roots[state][row["interval_id"]]!=row["plot_chain_id"]):
            raise ValueError("old source plot/county/chain/year identity not conserved")
        before=past[2]
        if county not in old_baseline or county not in new_baseline:
            raise ValueError("old/new NOAA source missing complete county baseline")
        old_exp=climate.interval_exposure(old_climate,county,before,end)
        new_exp=climate.interval_exposure(new_climate,county,before,end)
        if old_exp is None or new_exp is None:
            raise ValueError("original interval now has incomplete old or new NOAA history")
        old_t=old_exp["temperature_c"]-old_baseline[county][0]
        old_p=old_exp["precipitation_mm_per_six_months"]-old_baseline[county][1]
        if (abs(old_t-row["temperature_anomaly_c"])>TOL_TEMP_C or
            abs(old_p-row["precipitation_anomaly_mm"])>TOL_PRECIP_MM):
            raise ValueError("old source T/P anomaly cannot be reproduced for ALL original rows")
        updated={k:row[k] for k in FIELDS}
        updated["temperature_anomaly_c"]=(new_exp["temperature_c"]-new_baseline[county][0])
        updated["precipitation_anomaly_mm"]=(new_exp["precipitation_mm_per_six_months"]-new_baseline[county][1])
        if not math.isfinite(updated["temperature_anomaly_c"]) or not math.isfinite(updated["precipitation_anomaly_mm"]):
            raise ValueError("nonfinite rebased climate value")
        saved.append(updated)
        counts[state]["n_original_plot_interval_trees_species_identity_matched"]+=1
        if abs(updated["temperature_anomaly_c"]-row["temperature_anomaly_c"])>1e-9:
            counts[state]["n_updated_temperature_anomaly_intervals"]+=1
        if abs(updated["precipitation_anomaly_mm"]-row["precipitation_anomaly_mm"])>1e-9:
            counts[state]["n_updated_precipitation_anomaly_intervals"]+=1
    if len(saved)!=TRAIN_N or len(identities_seen)!=TRAIN_N:
        raise ValueError("original source-selected study sample altered")
    return saved,{s:dict(counts[s]) for s in STATES}


def run(out:Path, old_training:Path, old_NOAA_csv:Path, new_NOAA_raw:Path,
        PA_MI_v3:Path, RI_updated_zip:Path, contract:Path, train_config:Path,
        *, fetcher=None)->dict:
    out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(contract.read_text())
    verify(cfg)
    # All pre-existing sources are SHA audited BEFORE the first VA/WI GET.
    original,source_cfg=bridge.verify_training_source(old_training,train_config)
    old_climate=bridge.load_original_climate(old_NOAA_csv)
    new_climate,new_baseline=strict.read_saved_NOAA(new_NOAA_raw)
    holdout=strict.fixed_PA_MI_v3_source(PA_MI_v3)
    if sha(RI_updated_zip)!=OLD_RAW_RI_UPDATED_SHA:
        raise ValueError("v4 stopped RI PLOT source bytes changed")
    receipt={"study":PROGRAM,"status":"not_yet_checked",
             "old_v4_STOP_preserved":V4_PLOT_SOURCE_STOP_RUN,
             "n_original_training_rows":len(original),
             "n_holdout_PA_MI_source_rows":len(holdout),
             "PLOT_versions":[],
             "old_NOAA_20261006_source_sha256":bridge.OLD_NOAA_SHA,
             "new_NOAA_20261105_source_raw_sha256":strict.NOAA_NEW_SHAS,
             "old_original_PLOT_ZIP_full_SHA_all_three_verified":False,
             "no_TREE_COND_DIA_STATUSCD_or_growth_opened":True,
             "biological_promotion_authorized":False}
    try:
        # Preserve precisely the already-once-acquired v4 RI PLOT bytes.
        ri_path=out/"RI_PLOT.zip"
        ri_path.write_bytes(RI_updated_zip.read_bytes())
        with ZipFile(ri_path) as z:
            members=[s for s in z.namelist() if s.upper().endswith("RI_PLOT.CSV")]
            if len(members)!=1:raise ValueError("v4 RI PLOT source CSV member invalid")
        receipts=[{"state":"RI","status":"reused_v4_first_updated_RI_PLOT",
                   "sha256":OLD_RAW_RI_UPDATED_SHA,"member":members[0],
                   "same_full_source_SHA_as_old":False}]
        plots={"RI":strict.plot_visit_dates(ri_path,members[0],"RI")}
        for state in ("VA","WI"):
            path,info=fetch_PLOT_new(state,out,reader=fetcher)
            receipts.append(info)
            plots[state]=strict.plot_visit_dates(path,info["member"],state)
        receipt["PLOT_versions"]=receipts
        rebased,counts=rebase_all(original,plots,old_climate,new_climate,new_baseline)
        path=out/"RI_VA_WI_original_IDs_rebased_NOAA_20261105_v5.csv"
        csvsha=strict.write_source_csv(path,rebased)
        receipt["validated_original_identity_and_old_climate"]=counts
        receipt["training_rebased_CSV_sha256"]=csvsha
        compared=external.compare_train_holdout(rebased,holdout,source_cfg)
        compared.update({"status":"same_20261105_NOAA_v5_all_old_sampled_intervals_verified",
                         "n_original_training_source_rebased_rows":len(rebased),
                         "n_PA_MI_source_only_holdout_rows":len(holdout),
                         "updated_training_rebase_sha256":csvsha,
                         "old_PLOT_full_ZIP_SHA_identical":False,
                         "old_source_each_plot_and_date_reproduced_from_old_NOAA":True,
                         "all_original_89616_source_rows_preserved":True,
                         "source_selection_uses_PA_MI":False,
                         "biological_outcome_evaluated":False,
                         "n_biological_transfer_tests":0,
                         "source_only_not_a_prospective_growth_effect":True})
        (out/"PA_MI_same_NOAA_source_support_v5.json").write_text(
            json.dumps(compared,indent=2,sort_keys=True)+"\n")
        receipt["status"]="all_original_event_and_old_NOAA_source_verified_new_editions"
    except Exception as exc:
        receipt["status"]="event_identity_or_NOAA_v5_source_STOP"
        receipt["failure_class"]=type(exc).__name__
        receipt["failure_excerpt"]=str(exc)[:250]
        compared={"program":PROGRAM,
                  "status":"v5_source_unavailable_or_changed_stop_no_biology",
                  "no_biological_transfer_test":True,
                  "source_failure_not_zero_effect":True,
                  "biological_promotion_authorized":False}
        (out/"PA_MI_same_NOAA_source_support_v5.json").write_text(
            json.dumps(compared,indent=2,sort_keys=True)+"\n")
    (out/"PA_MI_source_receipt_v5.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    return compared


def main():
    p=argparse.ArgumentParser()
    for field in ("out","original-training","old-NOAA-csv","new-NOAA-raw",
                  "PA-MI-v3-source","RI-updated-zip"):
        p.add_argument("--"+field,type=Path,required=True)
    p.add_argument("--contract",type=Path,default=Path("configs/fia_PA_MI_NOAA_event_identity_v5.json"))
    p.add_argument("--training-config",type=Path,default=Path("configs/fia_joint_climate_support_gate_v1.json"))
    a=p.parse_args()
    x=run(a.out,a.original_training,a.old_NOAA_csv,a.new_NOAA_raw,
          a.PA_MI_v3_source,a.RI_updated_zip,a.contract,a.training_config)
    print(x["status"],"source-ready primary both PA+MI",
          x.get("n_primary_both_holdout_states_source_eligible"),"NO TREE RESPONSE")
    if x["status"]!="same_20261105_NOAA_v5_all_old_sampled_intervals_verified":
        raise SystemExit(2)


if __name__=="__main__":
    main()
